#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Database.py

# Copyright (c) 2015-2016, Richard Gerum, Sebastian Richter
#
# This file is part of ClickPoints.
#
# ClickPoints is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ClickPoints is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ClickPoints. If not, see <http://www.gnu.org/licenses/>

from __future__ import division, print_function
import os
import sys
import importlib
import itertools
from datetime import datetime, timedelta, MINYEAR
import peewee
from playhouse.reflection import Introspector
try:
    from StringIO import StringIO  # python 2
except ImportError:
    from io import StringIO  # python 3
import imageio
from threading import Thread
from qtpy import QtCore
import numpy as np

from clickpoints import DataFile as DataFileBase

import re


# add plugins to imageIO if available
plugin_searchpath = os.path.join(os.path.split(__file__)[0],'..',r'addons/imageio_plugin')
sys.path.append(plugin_searchpath)
if os.path.exists(plugin_searchpath):
    print("Searching ImageIO Plugins ...")
    plugin_list = os.listdir(os.path.abspath(plugin_searchpath))
    for plugin in plugin_list:
        if plugin.startswith('imageio_plugin_') and plugin.endswith('.py'):
            importlib.import_module(os.path.splitext(plugin)[0])
            print('Adding %s' % plugin)


def max_sql_variables():
    """Get the maximum number of arguments allowed in a query by the current
    sqlite3 implementation. Based on `this question
    `_

    Returns
    -------
    int
        inferred SQLITE_MAX_VARIABLE_NUMBER
    """
    import sqlite3
    db = sqlite3.connect(':memory:')
    cur = db.cursor()
    cur.execute('CREATE TABLE t (test)')
    low, high = 0, 100000
    while (high - 1) > low:
        guess = (high + low) // 2
        query = 'INSERT INTO t VALUES ' + ','.join(['(?)' for _ in
                                                    range(guess)])
        args = [str(i) for i in range(guess)]
        try:
            cur.execute(query, args)
        except sqlite3.OperationalError as e:
            if "too many SQL variables" in str(e) or "too many terms in compound SELECT" in str(e):
                high = guess
            else:
                raise
        else:
            low = guess
    cur.close()
    db.close()
    return low

SQLITE_MAX_VARIABLE_NUMBER = max_sql_variables()


def SQLMemoryDBFromFile(filename, *args, **kwargs):

    db_file = peewee.SqliteDatabase(filename, *args, **kwargs)

    db_file.connect()
    con = db_file.get_conn()
    tempfile = StringIO()
    for line in con.iterdump():
        tempfile.write('%s\n' % line)
    tempfile.seek(0)

    db_memory = peewee.SqliteDatabase(":memory:", *args, **kwargs)
    db_memory.get_conn().cursor().executescript(tempfile.read())
    db_memory.get_conn().commit()
    return db_memory

def SaveDB(db_memory, filename):
    if os.path.exists(filename):
        os.remove(filename)
    db_file = peewee.SqliteDatabase(filename)
    con_file = db_file.get_conn()
    con_memory = db_memory.get_conn()

    tempfile = StringIO()
    for line in con_memory.iterdump():
        tempfile.write('%s\n' % line)
    tempfile.seek(0)

    con_file.cursor().executescript(tempfile.read())
    con_file.commit()


# def SQLMemoryDBFromFileAPSW(filename):
#     from playhouse import apsw_ext
#     db_file = apsw_ext.APSWDatabase(filename)
#     db_memory = apsw_ext.APSWDatabase(':memory:')
#     with db_memory.get_conn().backup("main", db_file.get_conn(), "main") as backup:
#         backup.step()  # copy whole database in one go
#     return db_memory
#
# def SaveDBAPSW(db_memory, filename):
#     from playhouse import apsw_ext
#     db_file = apsw_ext.APSWDatabase(filename)
#     with db_file.get_conn().backup("main", db_memory.get_conn(), "main") as backup:
#         backup.step()  # copy whole database in one go

def timedelta_div(self, other):
    if isinstance(other, (int, float)):
        return timedelta(seconds=self.total_seconds()/other)
    else:
        return NotImplemented


def date_linspace(start_date, end_date, frames):
    delta = timedelta_div(end_date-start_date, frames)
    for n in range(frames):
        yield start_date
        start_date = start_date + delta


class DataFile(DataFileBase):
    def __init__(self, database_filename=None, config=None, storage_path=None):
        self.exists = os.path.exists(database_filename)
        self.config = config
        self.temporary_db = None
        self.database_filename = None

        # compile regexp for timestamp extraction
        self.reg_timestamp = []
        self.reg_timestamp2 = []
        self.initTimeStampRegEx()

        if self.exists:
            # go to the folder
            if os.path.dirname(database_filename):
                os.chdir(os.path.dirname(database_filename))
        else:
            database_filename = os.path.join(storage_path, "tmp%d.cdb" % os.getpid())
            index2 = 0
            while os.path.exists(database_filename):
                database_filename = os.path.join(storage_path, "tmp%d_%d.cdb" % (os.getpid(), index2))
                index2 += 1
            self.temporary_db = database_filename
            #self.db = peewee.SqliteDatabase(":memory:")

        DataFileBase.__init__(self, database_filename, mode='r+')

        # image, file reader and current index
        self.image = None
        self.reader = None
        self.current_image_index = None
        self.timestamp = None
        self.next_sort_index = 0
        self.image_count = None

        # image data loading buffer and thread
        self.buffer = FrameBuffer(self.config.buffer_size)
        self.thread = None

        self.last_added_timestamp = -1
        self.timestamp_thread = None

        # signals to notify others when a frame is loaded
        class DataFileSignals(QtCore.QObject):
            loaded = QtCore.pyqtSignal(int, int)
        self.signals = DataFileSignals()

    def start_adding_timestamps(self):
        if self.timestamp_thread:
            return
        #self.timestamp_thread = Thread(target=self.add_timestamps, args=())
        #self.timestamp_thread.start()
        self.add_timestamps()

    def add_timestamps(self):
        while True:
            next_frame = self.last_added_timestamp+1
            try:
                image = self.table_image.get(sort_index=next_frame)
            except peewee.DoesNotExist:
                break
            timestamp, _ = self.getTimeStamp(image.filename, image.ext)
            if timestamp:
                image.timestamp = timestamp
                image.save()
            self.last_added_timestamp += 1

    def getFilename(self):
        if not self.exists:
            return "unsaved project"
        return os.path.basename(self._database_filename)

    def save_database(self, file=None):
        # ensure that the file ends in .cdb
        if not file.lower().endswith(".cdb"):
            file += ".cdb"
        # if the database hasn't been written to file, write it
        if not self.exists or file != self.database_filename:
            # if the database already exists, copy it now before changing the paths
            if self.exists:
                # save the database and reload it
                SaveDB(self.db, file)
                self.db = peewee.SqliteDatabase(file)
                # update peewee models
                for table in self._tables:
                    table._meta.database = self.db
                self.exists = True
            # rewrite the paths
            if self.database_filename:
                old_directory = os.path.dirname(self.database_filename)
            else:
                old_directory = ""
            new_directory = os.path.dirname(file)
            paths = self.table_path.select()
            for path in paths:
                abs_path = os.path.join(old_directory, path.path)
                try:
                    path.path = os.path.relpath(abs_path, new_directory)
                except ValueError:
                    path.path = abs_path
                else:
                    # not more than one path up, the rest should stay with an absolute path
                    if path.path.find("../..") != -1 or path.path.find("..\\..") != -1:
                        print("path containes more ..", path.path)
                        path.path = abs_path
                path.save()
            if file:
                self.database_filename = file

            # if the database did not exist, we had to change the paths before saving
            if not self.exists:
                # save the database and reload it
                SaveDB(self.db, self.database_filename)
                self.db = peewee.SqliteDatabase(self.database_filename)
                # update peewee models
                for table in self._tables:
                    table._meta.database = self.db
                self.exists = True

            # change the directory to the new database
            os.chdir(new_directory)

    def add_path(self, path):
        if self.database_filename and not self.temporary_db:
            try:
                path = os.path.relpath(path, os.path.dirname(self.database_filename))
            except ValueError:
                path = os.path.abspath(path)
        path = os.path.normpath(path)
        try:
            path = self.table_path.get(path=path)
        except peewee.DoesNotExist:
            path = self.table_path(path=path)
            path.save()
        return path

    def add_image(self, filename, extension, external_id, frames, path, timestamp=None, commit=True):
        # if no timestamp is supplied quickly get one from the filename
        if timestamp is None:
            # do we have a video? then we need two timestamps
            if frames > 1:
                timestamp, timestamp2 = self.getTimeStamp(filename)
                if timestamp is not None:
                    timestamps = date_linspace(timestamp, timestamp2, frames)
                else:
                    timestamps = itertools.repeat(None)
            # if not one is enough
            else:
                timestamp,_ = self.getTimeStamp(filename)
                timestamps = itertools.repeat(timestamp)
        else:  # create an iterator from the timestamp
            timestamps = itertools.repeat(timestamp)
        # add an entry for every frame in the image container
        # prepare a list of dictionaries for a bulk insert
        data = []
        entry = dict(filename=filename, ext=extension, external_id=external_id, timestamp=timestamp, path=path.id)
        for i, time in zip(range(frames), timestamps):
            current_entry = entry.copy()
            current_entry["frame"] = i
            current_entry["timestamp"] = time
            current_entry["sort_index"] = self.next_sort_index+i
            data.append(current_entry)

        if commit is True:
            self.add_bulk(data)
        self.next_sort_index += frames
        if commit is False:
            return data

    def add_bulk(self, data):
        if len(data) == 0:
            return
        # try to perform the bulk insert
        try:
            # Insert the maximum of allowed rows at a time
            chunk_size = (SQLITE_MAX_VARIABLE_NUMBER // len(data[0])) - 1
            with self.db.atomic():
                for idx in range(0, len(data), chunk_size):
                    self.table_image.insert_many(data[idx:idx + chunk_size]).execute()
        except peewee.IntegrityError:  # this exception is raised when the image and path combination already exists
            return

        if self.image_count is not None:
            self.image_count += len(data)

    def reset_buffer(self):
        self.buffer.reset()

    def resortSortIndex(self):
        self.db.execute_sql("DELETE FROM path WHERE (SELECT COUNT(image.id) FROM image WHERE image.path_id = path.id) = 0")
        self.db.execute_sql("CREATE TEMPORARY TABLE NewIDs (sort_index INTEGER PRIMARY KEY AUTOINCREMENT, id INT UNSIGNED)")
        self.db.execute_sql("INSERT INTO NewIDs (id) SELECT id FROM image ORDER BY filename ASC")
        self.db.execute_sql("UPDATE image SET sort_index = (SELECT sort_index FROM NewIDs WHERE image.id = NewIDs.id)-1")
        self.db.execute_sql("DROP TABLE NewIDs")

        try:
            self.image_count = self.db.execute_sql("SELECT MAX(sort_index) FROM image LIMIT 1;").fetchone()[0] + 1
        except TypeError:
            self.image_count = 0
            self.image = None
        self.next_sort_index = self.image_count

    def get_image_count(self):
        if self.image_count is None:
            try:
                self.image_count = self.db.execute_sql("SELECT MAX(sort_index) FROM image LIMIT 1;").fetchone()[0]+1
            except TypeError:
                self.image_count = 0
        # return the total count of images in the database
        return self.image_count

    def get_current_image(self):
        # return the current image index
        return self.current_image_index

    def load_frame(self, index, threaded):
        # check if frame is already buffered then we don't need to load it
        if self.buffer.get_frame(index) is not None:
            self.signals.loaded.emit(index, threaded)
            return
        # if we are still loading a frame finish first
        if self.thread:
            self.thread.join()
        # query the information on the image to load
        image = self.table_image.get(sort_index=index)
        filename = os.path.join(image.path.path, image.filename)
        # prepare a slot in the buffer
        slots, slot_index, = self.buffer.prepare_slot(index)
        # call buffer_frame in a separate thread or directly
        if threaded:
            self.thread = Thread(target=self.buffer_frame, args=(image, filename, slots, slot_index, index, True, threaded))
            self.thread.start()
        else:
            return self.buffer_frame(image, filename, slots, slot_index, index, threaded=threaded)

    def buffer_frame(self, image, filename, slots, slot_index, index, signal=True, threaded=True):
        # if we have already a reader...
        if self.reader:
            # ... check if it is the right one, if not delete it
            if filename != self.reader.filename:
                del self.reader
                self.reader = None
        # if we don't have a reader, create a new one
        if self.reader is None:
            try:
                self.reader = imageio.get_reader(filename)
                self.reader.filename = filename
            except IOError:
                pass
        # get the data from the reader
        image_data = None
        if self.reader is not None:
            try:
                image_data = self.reader.get_data(image.frame)
            except ValueError:
                pass
        # if the image can't be opened, open a black image instead
        if image_data is None:
            width = image.width if image.width is not None else 640
            height = image.height if image.height is not None else 480
            image_data = np.zeros((height, width))
        # do an automatic contrast enhancement
        if self.config.auto_contrast:
            image_data = image_data-np.amin(image_data)
            image_data = (image_data/np.amax(image_data)*256).astype(np.uint8)
        # scale 12 bit images
        elif 2**8 < np.amax(image_data) < 2**12:
            image_data = (image_data/16).astype(np.uint8)
        # or 16 bit images
        elif 2**12 < np.amax(image_data) < 2**16:
            image_data = (image_data/256).astype(np.uint8)
        # store data in the slot
        if slots is not None:
            slots[slot_index] = image_data
        # notify that the frame has been loaded
        if signal:
            self.signals.loaded.emit(index, threaded)

    def get_image_data(self, index=None):
        if index is None or index == self.current_image_index:
            # get the pixel data from the current image
            return self.buffer.get_frame(self.current_image_index)
        try:
            image = self.table_image.get(sort_index=index)
        except peewee.DoesNotExist:
            return None

        buffer = self.buffer.get_frame(index)
        if buffer is not None:
            return buffer
        filename = os.path.join(image.path.path, image.filename)
        slots, slot_index, = self.buffer.prepare_slot(index)
        self.buffer_frame(image, filename, slots, slot_index, index, signal=False)
        return self.buffer.get_frame(index)

    def get_image(self, index=None):
        if index is None or index == self.current_image_index:
            return self.image

        try:
            image = self.table_image.get(sort_index=index)
        except peewee.DoesNotExist:
            return None
        return image

    def set_image(self, index):
        # the the current image number and retrieve its information from the database
        self.image = self.table_image.get(sort_index=index)
        self.timestamp = self.image.timestamp
        self.current_image_index = index

    def get_offset(self, image=None):
        # if no image is specified, use the current one
        if image is None:
            image = self.image
        # try to get offset data for the image
        try:
            offset = self.table_offset.get(image=image)
            return [offset.x, offset.y]
        except peewee.DoesNotExist:
            return [0, 0]

    def closeEvent(self, QCloseEvent):
        # join the thread on closing
        if self.thread:
            self.thread.join()
        # remove temporary database if there is still one
        if self.temporary_db:
            self.db.close()
            try:
                os.remove(self.temporary_db)
            except:
                pass
            self.temporary_db = None
        pass

    def initTimeStampRegEx(self):
        # extract and compile regexp for timestamp and timestamp2 lists
        for regex in self.config.timestamp_formats:
            # replace strings with regexp
            regex = regex.replace('%Y','(?P<Y>\d{4})',1)
            regex = regex.replace('%y', '(?P<y>\d{2})', 1)
            regex = regex.replace('%m', '(?P<m>\d{2})', 1)
            regex = regex.replace('%d', '(?P<d>\d{2})', 1)
            regex = regex.replace('%H', '(?P<H>\d{2})', 1)
            regex = regex.replace('%M', '(?P<M>\d{2})', 1)
            regex = regex.replace('%S', '(?P<S>\d{2})', 1)
            regex = regex.replace('%f', '(?P<f>\d{1,6})', 1)
            regex = regex.replace('*', '.*')

            self.reg_timestamp.append(re.compile(regex))

        for regex in self.config.timestamp_formats2:
            # replace strings with regexp
            # timestamp 1
            regex = regex.replace('%Y','(?P<Y>\d{4})',1)
            regex = regex.replace('%y', '(?P<y>\d{2})', 1)
            regex = regex.replace('%m', '(?P<m>\d{2})', 1)
            regex = regex.replace('%d', '(?P<d>\d{2})', 1)
            regex = regex.replace('%H', '(?P<H>\d{2})', 1)
            regex = regex.replace('%M', '(?P<M>\d{2})', 1)
            regex = regex.replace('%S', '(?P<S>\d{2})', 1)
            regex = regex.replace('%f', '(?P<f>\d{1,6})', 1)
            # timestamp 2
            regex = regex.replace('%Y','(?P<Y2>\d{4})',1)
            regex = regex.replace('%y', '(?P<y2>\d{2})', 1)
            regex = regex.replace('%m', '(?P<m2>\d{2})', 1)
            regex = regex.replace('%d', '(?P<d2>\d{2})', 1)
            regex = regex.replace('%H', '(?P<H2>\d{2})', 1)
            regex = regex.replace('%M', '(?P<M2>\d{2})', 1)
            regex = regex.replace('%S', '(?P<S2>\d{2})', 1)
            regex = regex.replace('%f', '(?P<f2>\d{1,6})', 1)
            regex = regex.replace('*', '.*')

            self.reg_timestamp2.append(re.compile(regex))

    def getTimeStampQuick(self, file):
        for regex in self.reg_timestamp:
            match = regex.match(file)
            if match:
                d = match.groupdict()
                if "y" in d:
                    if int(d["y"]) > 60:
                        d["Y"] = int(d["y"]) + 1900
                    else:
                        d["Y"] = int(d["y"]) + 2000

                # reassemble datetime object
                dt = datetime(int(d.get("Y", MINYEAR)), int(d.get("m", 1)), int(d.get("d", 1)),
                                       int(d.get("H", 0)), int(d.get("M", 0)), int(d.get("S", 0)))
                # handle sub second timestamps
                if "f" in d:
                    dt = dt.replace(microsecond=int(d["f"]) * 10 ** (6 - len(d["f"])))
                return dt
        return None

    def getTimeStampsQuick(self,file):
        for regex in self.reg_timestamp2:
            match = regex.match(file)
            if match:
                d = match.groupdict()
                # timestamp 1
                if "y" in d:
                    if int(d["y"]) > 60:
                        d["Y"] = int(d["y"]) + 1900
                    else:
                        d["Y"] = int(d["y"]) + 2000

                dt = datetime(int(d.get("Y", MINYEAR)), int(d.get("m", 1)), int(d.get("d", 1)),
                              int(d.get("H", 0)), int(d.get("M", 0)), int(d.get("S", 0)))
                if "f" in d:
                    dt = dt.replace(microsecond=int(d["f"]) * 10 ** (6 - len(d["f"])))

                # timestamp 2
                if "y2" in d:
                    if int(d["y2"]) > 60:
                        d["Y2"] = int(d["y2"]) + 1900
                    else:
                        d["Y2"] = int(d["y2"]) + 2000

                dt2 = datetime(int(d.get("Y2", MINYEAR)), int(d.get("m2", 1)), int(d.get("d2", 1)),
                              int(d.get("H2", 0)), int(d.get("M2", 0)), int(d.get("S2", 0)))
                if "f2" in d:
                    dt2 = dt2.replace(microsecond=int(d["f"]) * 10 ** (6 - len(d["f2"])))

                return dt, dt2
        return None, None

    def getTimeStamp(self, file):
        _, extension = os.path.splitext(file)
        if extension.lower() == ".tif" or extension.lower() == ".tiff":
            dt = self.get_meta(file)
            return dt, dt

        # try for timestamps2
        t1,t2 = self.getTimeStampsQuick(file)
        if not any(elem is None for elem in [t1,t2]):
            return t1,t2

        # try for timestamp
        t1 = self.getTimeStampQuick(file)
        if t1 is not None:
            return t1,t1

        if extension.lower() == ".jpg":
            dt = self.getExifTime(file)
            return dt, dt
        else:
            print("no time", extension)
        return None, None

    def getExifTime(self, path):
        from PIL import Image
        import PIL
        img = Image.open(path)
        try:
            exif = {
                PIL.ExifTags.TAGS[k]: v
                for k, v in img._getexif().items()
                if k in PIL.ExifTags.TAGS
                }
            return datetime.strptime(exif["DateTime"], '%Y:%m:%d %H:%M:%S')
        except (AttributeError, ValueError):
            return None

    def get_meta(self, file):
        import tifffile
        import json
        with tifffile.TiffFile(file) as tif:
            try:
                metadata = tif[0].image_description
            except AttributeError:
                return None
            try:
                t = json.loads(metadata.decode('utf-8'))["Time"]
                return datetime.strptime(t, '%Y%m%d-%H%M%S')
            except (AttributeError, ValueError, KeyError):
                return None
        return None


class FrameBuffer:
    slots = None
    indices = None
    last_index = 0

    def __init__(self, buffer_count):
        self.buffer_count = buffer_count
        self.reset()

    def reset(self):
        self.slots = [[]]*self.buffer_count
        self.indices = [None]*self.buffer_count
        self.last_index = 0

    def add_frame(self, number, image):
        self.slots[self.last_index] = image
        self.indices[self.last_index] = number
        self.last_index = (self.last_index+1) % len(self.slots)

    def prepare_slot(self, number):
        if self.get_slot_index(number) is not None:
            return None, None
        index = self.last_index
        self.last_index = (self.last_index+1) % len(self.slots)
        self.indices[index] = number
        self.slots[index] = None
        return self.slots, index

    def get_slot_index(self, number):
        try:
            return self.indices.index(number)
        except ValueError:
            return None

    def get_frame(self, number):
        try:
            index = self.indices.index(number)
            return self.slots[index]
        except ValueError:
            return None

