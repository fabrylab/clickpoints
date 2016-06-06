from __future__ import division, print_function
import os
import sys
import importlib
import itertools
from datetime import datetime, timedelta
import peewee
from playhouse.reflection import Introspector
try:
    from StringIO import StringIO  # python 2
except ImportError:
    from io import StringIO  # python 3
import imageio
from threading import Thread
from PyQt4 import QtCore
import numpy as np


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


class DataFile:
    def __init__(self, database_filename=None, config=None, storage_path=None):
        self.database_filename = database_filename
        self.exists = os.path.exists(database_filename)
        self.current_version = "6"
        self.config = config
        self.temporary_db = None
        version = None
        if self.exists:
            self.db = peewee.SqliteDatabase(database_filename)
            introspector = Introspector.from_database(self.db)
            models = introspector.generate_models()
            try:
                version = models["meta"].get(models["meta"].key == "version").value
            except (KeyError, peewee.DoesNotExist):
                version = "0"
            print("Open database with version", version)
            if int(version) < int(self.current_version):
                self.migrateDBFrom(version)
            elif int(version) > int(self.current_version):
                print("Warning Database version %d is newer than ClickPoints version %d "
                      "- please get an updated Version!"
                      % (int(version), int(self.current_version)))
                print("Proceeding on own risk!")
            # go to the folder
            if os.path.dirname(database_filename):
                os.chdir(os.path.dirname(database_filename))
        else:
            filename = os.path.join(storage_path, "tmp%d.cdb" % os.getpid())
            if os.path.exists(filename):
                os.remove(filename)
            self.db = peewee.SqliteDatabase(filename)
            self.temporary_db = filename
            #self.db = peewee.SqliteDatabase(":memory:")

        class BaseModel(peewee.Model):
            class Meta:
                database = self.db

        class Meta(BaseModel):
            key = peewee.CharField(unique=True)
            value = peewee.CharField()

        class Paths(BaseModel):
            path = peewee.CharField(unique=True)

        class Images(BaseModel):
            filename = peewee.CharField()
            ext = peewee.CharField(max_length=10)
            frame = peewee.IntegerField(default=0)
            external_id = peewee.IntegerField(null=True)
            timestamp = peewee.DateTimeField(null=True)
            sort_index = peewee.IntegerField(default=0)
            width = peewee.IntegerField(null=True)
            height = peewee.IntegerField(null=True)
            path = peewee.ForeignKeyField(Paths, related_name="images")

            class Meta:
                # image and path in combination have to be unique
                indexes = ((('filename', 'path', 'frame'), True), )

        class Offsets(BaseModel):
            image = peewee.ForeignKeyField(Images, unique=True)
            x = peewee.FloatField()
            y = peewee.FloatField()

        self.tables = [BaseModel, Meta, Paths, Images, Offsets]

        self.base_model = BaseModel
        self.table_meta = Meta
        self.table_paths = Paths
        self.table_images = Images
        self.table_offsets = Offsets

        self.db.connect()
        for table in [self.table_meta, self.table_paths, self.table_images, self.table_offsets]:
            if not table.table_exists():
                table.create_table()
        if not self.exists:
            self.table_meta(key="version", value=self.current_version).save()

        # second migration part which needs the peewee model
        if version is not None and int(version) < int(self.current_version):
            self.migrateDBFrom2(version)

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
                image = self.table_images.get(sort_index=next_frame)
            except peewee.DoesNotExist:
                break
            timestamp, _ = getTimeStamp(image.filename, image.ext)
            if timestamp:
                image.timestamp = timestamp
                image.save()
            self.last_added_timestamp += 1

    def migrateDBFrom(self, version):
        # migrate database from an older version
        nr_new_version = None
        print("Migrating DB from version %s" % version)
        nr_version = int(version)

        if nr_version < 3:
            print("\tto 3")
            # Add text fields for Marker
            self.db.execute_sql("ALTER TABLE marker ADD COLUMN text varchar(255)")
            nr_new_version = 3

        if nr_version < 4:
            print("\tto 4")
            # Add text fields for Tracks
            try:
                self.db.execute_sql("ALTER TABLE tracks ADD COLUMN text varchar(255)")
            except peewee.OperationalError:
                pass
            # Add text fields for Types
            try:
                self.db.execute_sql("ALTER TABLE types ADD COLUMN text varchar(255)")
            except peewee.OperationalError:
                pass
            nr_new_version = 4

        if nr_version < 5:
            print("\tto 5")
            # Add text fields for Tracks
            try:
                self.db.execute_sql("ALTER TABLE images ADD COLUMN frame int")
                self.db.execute_sql("ALTER TABLE images ADD COLUMN sort_index int")
            except peewee.OperationalError:
                pass
            nr_new_version = 5

        if nr_version < 6:
            print("\tto 6")
            # Add text fields for Tracks
            try:
                self.db.execute_sql("ALTER TABLE images ADD COLUMN path_id int")
                self.db.execute_sql("ALTER TABLE images ADD COLUMN width int NULL")
                self.db.execute_sql("ALTER TABLE images ADD COLUMN height int NULL")
            except peewee.OperationalError:
                pass
            nr_new_version = 6

        self.db.execute_sql("INSERT OR REPLACE INTO meta (id,key,value) VALUES ( \
                                            (SELECT id FROM meta WHERE key='version'),'version',%s)" % str(nr_new_version))

    def migrateDBFrom2(self, nr_version):
        nr_version = int(nr_version)
        if nr_version < 5:
            print("second migration step to 5")
            images = self.table_images.select().order_by(self.table_images.filename)
            for index, image in enumerate(images):
                image.sort_index = index
                image.frame = 0
                image.save()
        if nr_version < 6:
            print("second migration step to 6")
            images = self.table_images.select().order_by(self.table_images.filename)
            for image in images:
                path = None
                if os.path.exists(image.filename):
                    path = ""
                else:
                    for root, dirs, files in os.walk("."):
                        if image.filename in files:
                            path = root
                            break
                if path is None:
                    print("ERROR: image not found", image.filename)
                    continue
                try:
                    path_entry = self.table_paths.get(path=path)
                except peewee.DoesNotExist:
                    path_entry = self.table_paths(path=path)
                    path_entry.save()
                image.path = path_entry
                image.save()

    def getFilename(self):
        if not self.exists:
            return "unsaved project"
        return os.path.basename(self.database_filename)

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
                for table in self.tables:
                    table._meta.database = self.db
                self.exists = True
            # rewrite the paths
            if self.database_filename:
                old_directory = os.path.dirname(self.database_filename)
            else:
                old_directory = ""
            new_directory = os.path.dirname(file)
            paths = self.table_paths.select()
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
                for table in self.tables:
                    table._meta.database = self.db
                self.exists = True

            # change the directory to the new database
            os.chdir(new_directory)

    def add_path(self, path):
        if self.database_filename:
            try:
                path = os.path.relpath(path, os.path.dirname(self.database_filename))
            except ValueError:
                path = os.path.abspath(path)
        path = os.path.normpath(path)
        try:
            path = self.table_paths.get(path=path)
        except peewee.DoesNotExist:
            path = self.table_paths(path=path)
            path.save()
        return path

    def add_image(self, filename, extension, external_id, frames, path, timestamp=None, commit=True):
        # if no timestamp is supplied quickly get one from the filename
        if timestamp is None:
            # do we have a video? then we need two timestamps
            if frames > 1:
                timestamp, timestamp2 = getTimeStampsQuick(filename)
                if timestamp is not None:
                    timestamps = date_linspace(timestamp, timestamp2, frames)
                else:
                    timestamps = itertools.repeat(None)
            # if not one is enough
            else:
                timestamp = getTimeStampQuick(filename)
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
            # try to perform the bulk insert
            try:
                # Insert the maximum of allowed rows at a time
                chunk_size = (SQLITE_MAX_VARIABLE_NUMBER // len(data[0])) -1
                with self.db.atomic():
                    for idx in range(0, len(data), chunk_size):
                        self.table_images.insert_many(data[idx:idx+chunk_size]).execute()
            except peewee.IntegrityError:  # this exception is raised when the image and path combination already exists
                return
            # increase sort_index and image_count by the number of added frames
            if self.image_count is not None:
                self.image_count += frames
        self.next_sort_index += frames
        if commit is False:
            return data

    def add_bulk(self, data):
        # try to perform the bulk insert
        try:
            # Insert the maximum of allowed rows at a time
            chunk_size = (SQLITE_MAX_VARIABLE_NUMBER // len(data[0])) - 1
            with self.db.atomic():
                for idx in range(0, len(data), chunk_size):
                    self.table_images.insert_many(data[idx:idx + chunk_size]).execute()
        except peewee.IntegrityError:  # this exception is raised when the image and path combination already exists
            return

        if self.image_count is not None:
            self.image_count += len(data)

    def reset_buffer(self):
        self.buffer.reset()

    def get_image_count(self):
        if self.image_count is None:
            try:
                self.image_count = self.db.execute_sql("SELECT MAX(sort_index) FROM images LIMIT 1;").fetchone()[0]+1
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
        image = self.table_images.get(sort_index=index)
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
        slots[slot_index] = image_data
        # notify that the frame has been loaded
        if signal:
            self.signals.loaded.emit(index, threaded)

    def get_image_data(self, index=None):
        if index is None or index == self.current_image_index:
            # get the pixel data from the current image
            return self.buffer.get_frame(self.current_image_index)
        try:
            image = self.table_images.get(sort_index=index)
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
            image = self.table_images.get(sort_index=index)
        except peewee.DoesNotExist:
            return None
        return image

    def set_image(self, index):
        # the the current image number and retrieve its information from the database
        self.image = self.table_images.get(sort_index=index)
        self.timestamp = self.image.timestamp
        self.current_image_index = index

    def get_offset(self, image=None):
        # if no image is specified, use the current one
        if image is None:
            image = self.image
        # try to get offset data for the image
        try:
            offset = self.table_offsets.get(image=image)
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
            os.remove(self.temporary_db)
            self.temporary_db = None
        pass


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


import re
filename_data_regex = r'.*(?P<timestamp>\d{8}-\d{6})'
filename_data_regex = re.compile(filename_data_regex)
filename_data_regex2 = r'.*(?P<timestamp>\d{8}-\d{6})_(?P<timestamp2>\d{8}-\d{6})'
filename_data_regex2 = re.compile(filename_data_regex2)

def getTimeStampQuick(file):
    global filename_data_regex, filename_data_regex2
    match = filename_data_regex.match(file)
    if match:
        par_dict = match.groupdict()
        return datetime.strptime(par_dict["timestamp"], '%Y%m%d-%H%M%S')
    return None

def getTimeStampsQuick(file):
    global filename_data_regex, filename_data_regex2
    match = filename_data_regex2.match(file)
    if match:
        par_dict = match.groupdict()
        return datetime.strptime(par_dict["timestamp"], '%Y%m%d-%H%M%S'), datetime.strptime(par_dict["timestamp2"], '%Y%m%d-%H%M%S')
    return None, None

def getTimeStamp(file, extension):
    global filename_data_regex

    if extension.lower() == ".tif" or extension.lower() == ".tiff":
        dt = get_meta(file)
        return dt, dt
    match = filename_data_regex.match(file)
    if match:
        match2 = filename_data_regex2.match(file)
        if match2:
            match = match2
        par_dict = match.groupdict()
        if "timestamp" in par_dict:
            dt = datetime.strptime(par_dict["timestamp"], '%Y%m%d-%H%M%S')
            if "timestamp2" in par_dict:
                dt2 = datetime.strptime(par_dict["timestamp2"], '%Y%m%d-%H%M%S')
            else:
                dt2 = dt
            return dt, dt2
    elif extension.lower() == ".jpg":
        dt = getExifTime(file)
        return dt, dt
    else:
        print("no time", extension)
    return None, None


def getExifTime(path):
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


def get_meta(file):
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
