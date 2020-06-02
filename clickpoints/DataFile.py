#!/usr/bin/env python
# -*- coding: utf-8 -*-
# DataFile.py

# Copyright (c) 2015-2020, Richard Gerum, Sebastian Richter, Alexander Winterl
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ClickPoints. If not, see <http://www.gnu.org/licenses/>

from __future__ import print_function, division
import numpy as np
import os
import peewee
import imageio
import sys
import platform
try:
    from cStringIO import StringIO
except ImportError:
    try:
        from StringIO import StringIO
    except ImportError:
        import io

PY3 = sys.version_info[0] == 3
if PY3:
    basestring = str


# to get query results as dictionaries
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
        d[idx] = row[idx]
    return d


class ImageField(peewee.BlobField):
    """ A database field, that """
    def db_value(self, value):
        value = imageio.imwrite(imageio.RETURN_BYTES, value, format=".png")
        if PY3:
            return value
        return peewee.binary_construct(value)

    def python_value(self, value):
        if not PY3:
            return imageio.imread(StringIO(str(value)), format=".png")
        return imageio.imread(io.BytesIO(value), format=".png")

def CheckValidColor(color):
    class NoValidColor(Exception):
        pass

    if isinstance(color, basestring):
        if color[0] == "#":
            color = color[1:]
        for c in color:
            if not "0" <= c.upper() <= "F":
                raise NoValidColor(color + " is no valid color")
        if len(color) != 6 and len(color) != 8:
            raise NoValidColor(color + " is no valid color")
        return "#" + color
    color_string = ""
    for value in color:
        if not 0 <= value <= 255:
            raise NoValidColor(str(color) + " is no valid color")
        color_string += "%02x" % value
    if len(color_string) != 6 and len(color_string) != 8:
        raise NoValidColor(str(color) + " is no valid color")
    return "#" + color_string

def NormalizeColor(color):
    # if color is a string
    if isinstance(color, basestring):
        color = str(color).upper()

        CheckValidColor(color)
        return color

    # if color is a list
    color = [CheckValidColor(col.upper()) for col in color]
    return color

def HTMLColorToRGB(colorstring):
    """ convert #RRGGBB to an (R, G, B) tuple """
    colorstring = str(colorstring).strip()
    if colorstring[0] == '#': colorstring = colorstring[1:]
    if len(colorstring) != 6 and len(colorstring) != 8:
        raise (ValueError, "input #%s is not in #RRGGBB format" % colorstring)
    return [int(colorstring[i*2:i*2+2], 16) for i in range(int(len(colorstring)/2))]

def addFilter(query, parameter, field):
    if parameter is None:
        return query
    if isinstance(parameter, (tuple, list)):
        return query.where(field << parameter)
    if isinstance(parameter, slice):
        if parameter.start is None:
            return query.where(field < parameter.stop)
        elif parameter.stop is None:
            return query.where(field >= parameter.start)
        else:
            return query.where( field.between(parameter.start, parameter.stop))
    else:
        return query.where(field == parameter)

def noNoneDict(**kwargs):
    new_dict = {}
    for key in kwargs:
        if kwargs[key] is not None:
            new_dict[key] = kwargs[key]
    return new_dict

def setFields(entry, dict):
    for key in dict:
        if dict[key] is not None:
            setattr(entry, key, dict[key])

def packToDictList(table, **kwargs):
    import itertools
    max_len = 0
    singles = {}
    def WrapSingle(key, i):
        return kwargs[key]
    def WrapMultiple(key, i):
        return kwargs[key][i]
    def WrapNoneID(key, i):
        field = getattr(table, key)
        if field.default is not None:
            result = table.select(peewee.fn.COALESCE(peewee.fn.MAX(field)).where(table.id == singles["id"](i)))
        else:
            result = table.select(field).where(table.id == singles["id"](i))
        return result
    def WrapNoneImageTrack(key, i):
        field = getattr(table, key)
        if field.default is not None:
            # if the field has no default value, the SELECT query would return an empty list if the element does not exist
            # this would throw a not-null constraint exception and it would ignore the default value
            # therefore we have to use the default value, if no entry is found
            # MAX "convertes" the empy query to a NULL and COALESCE converts the NULL to the default value
            result = table.select(peewee.fn.COALESCE(peewee.fn.MAX(field), field.default)).where(table.image == singles["image"](i), table.track == singles["track"](i))
        else:
            result = table.select(field).where(table.image == singles["image"](i), table.track == singles["track"](i))
        return result
    for key in list(kwargs.keys()):
        if kwargs[key] is None:
            if "id" in kwargs and kwargs["id"] is not None:
                singles[key] = lambda i, key=key: WrapNoneID(key, i)
            elif ("image" in kwargs and kwargs["image"] is not None) and ("track" in kwargs and kwargs["track"] is not None):
                singles[key] = lambda i, key=key: WrapNoneImageTrack(key, i)
            else:
                del kwargs[key]
            continue
        if isinstance(kwargs[key], (tuple, list, np.ndarray)):
            if max_len > 1 and max_len != len(kwargs[key]):
                raise IndexError()
            max_len = max(max_len, len(kwargs[key]))
            singles[key] = lambda i, key=key: WrapMultiple(key, i)
        else:
            max_len = max(max_len, 1)
            singles[key] = lambda i, key=key: WrapSingle(key, i)
    dict_list = []
    for i in range(max_len):
        dict_list.append({key: singles[key](i) for key in kwargs})
    return dict_list

class Option:
    key = ""
    display_name = ""
    value = None
    default = ""
    value_type = ""
    value_count = 1
    min_value = None
    max_value = None
    decimals = None
    unit = None
    category = ""
    hidden = False
    tooltip = ""

    def __init__(self, **kwargs):
        for key in kwargs:
            setattr(self, key, kwargs[key])

class OptionAccess(object):
    def __init__(self, data_file):
        self.data_file = data_file

    def __getattr__(self, key):
        if key != "data_file":
            return self.data_file.getOption(key)
        return object.__getattr__(self, key)

    def __setattr__(self, key, value):
        if key != "data_file":
            return self.data_file.setOption(key, value)
        return object.__setattr__(self, key, value)

def VerboseDict(dictionary):
    return " and ".join("%s=%s" % (key, dictionary[key]) for key in dictionary)


class DoesNotExist(peewee.DoesNotExist):
    pass


class ImageDoesNotExist(DoesNotExist):
    pass


class MaskDimensionMismatch(DoesNotExist):
    pass


class MaskDtypeMismatch(DoesNotExist):
    pass


class MaskDimensionUnknown(DoesNotExist):
    pass


class MarkerTypeDoesNotExist(DoesNotExist):
    pass


class TrackDoesNotExist(DoesNotExist):
    pass


def GetCommandLineArgs():
    """
    Parse the command line arguments for the information provided by ClickPoints, if the script is invoked from within
    ClickPoints. The arguments are --start_frame --database and --port.

    Returns
    -------
    start_frame : int
        the frame ClickPoints was in when invoking the script. Probably the evaluation should start here
    database : string
        the filename of the database where the current ClickPoints project is stored. Should be used with
        clickpoints.DataFile
    port : int
        the port of the socket connection to communicate with the ClickPoints instance. Should be used with
        clickpoints.Commands
    """
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", dest='database', help='specify which database file to use')
    parser.add_argument("--start_frame", type=int, default=0, dest='start_frame',
                        help='specify at which frame to start')
    parser.add_argument("--port", type=int, dest='port', help='from which port to communicate with ClickPoints')
    args, unknown = parser.parse_known_args()
    return args.start_frame, args.database, args.port


def getLine(image, line, width=None):
    # get the start and end position of the line
    line = np.array(line)
    x1, y1 = line[0]
    x2, y2 = line[1]

    # the width and height of the line
    w = x2 - x1
    h = y2 - y1
    # the length
    length = np.sqrt(w ** 2 + h ** 2)
    # and the normed normal vector
    w2 = h / length
    h2 = -w / length

    # apply an optional offset if the image is a ClickPoints image with an offset
    offset = getattr(image, "offset", None)
    if offset is not None:
        offx, offy = offset.x, offset.y
    else:
        offx, offy = 0, 0
    x1 -= offx
    y1 -= offy

    # get the image data (if the image is a ClickPoints image, if not it is a numpy array)
    data = getattr(image, "data", None)
    image = data if data is not None else image

    # width None is a line with width of 1 and the result is returned as a 1D array
    if width is None:
        width = 1
        return_1d = True
    else:
        return_1d = False

    datas = []
    # iterate over the different image slices to get the width of the cut
    for j in np.arange(0, width) - width / 2. + 0.5:
        data = []
        # iterate over all pixels of the length
        for i in np.linspace(0, 1, np.ceil(length)):
            # get the position along the line
            x = x1 + w * i + w2 * j
            y = y1 + h * i + h2 * j
            # get the rounding percentage
            xp = x - np.floor(x)
            yp = y - np.floor(y)
            x, y = int(x), int(y)
            # and interpolate the 4 surrounding pixels according to the rounding percentage
            v = np.array([[1 - yp, yp]]).T @ np.array([[1 - xp, xp]])
            # for multi channel images (color images)
            if len(image.shape) == 3:
                data.append(np.sum(image[y:y + 2, x:x + 2, :] * v[:, :, None], axis=(0, 1),
                                   dtype=image.dtype))
            # and for single channel images
            else:
                data.append(np.sum(image[y:y + 2, x:x + 2] * v, dtype=image.dtype))
        datas.append(data)

    if return_1d:
        return np.array(datas[0])
    return np.array(datas)[::-1, :]

class DataFile:
    """
    The DataFile class provides access to the .cdb file format in which ClickPoints stores the data for a project.

    Parameters
    ----------
    database_filename : string
        the filename to open
    mode : string, optional
        can be 'r' (default) to open an existing database and append data to it or 'w' to create a new database. If the mode is 'w' and the
        database already exists, it will be deleted and a new database will be created.
    """
    db = None
    _reader = None
    _current_version = "22"
    _database_filename = None
    _next_sort_index = 0
    _SQLITE_MAX_VARIABLE_NUMBER = None
    _config = None
    _buffer = None

    """ Enumerations """
    TYPE_Normal = 0
    TYPE_Rect = 1
    TYPE_Line = 2
    TYPE_Track = 4
    TYPE_Ellipse = 8
    TYPE_Polygon = 16

    def max_sql_variables(self):
        """Get the maximum number of arguments allowed in a query by the current
        sqlite3 implementation.

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

    def saveReplaceMany(self, table, data):
        if self._SQLITE_MAX_VARIABLE_NUMBER is None:
            self._SQLITE_MAX_VARIABLE_NUMBER = self.max_sql_variables()
        chunk_size = ((self._SQLITE_MAX_VARIABLE_NUMBER // len(data[0])) - 1) // 2
        with self.db.atomic():
            for idx in range(0, len(data), chunk_size):
                table.replace_many(data[idx:idx + chunk_size]).execute()

    def __init__(self, database_filename=None, mode='r'):
        if database_filename is None:
            raise TypeError("No database filename supplied.")
        self._database_filename = database_filename
        print("path", self._database_filename)

        version = self._current_version
        new_database = True

        # Create a new database
        if mode == "w":
            if os.path.exists(self._database_filename):
                os.remove(self._database_filename)
            self.db = peewee.SqliteDatabase(database_filename)
            self.db.connect()
        else:  # or read an existing one
            if not os.path.exists(self._database_filename) and mode != "r+":
                raise Exception("DB %s does not exist!" % os.path.abspath(self._database_filename))
            exists = os.path.exists(self._database_filename)
            self.db = peewee.SqliteDatabase(database_filename)
            self.db.connect()
            if exists:
                version = self._CheckVersion()
                self._next_sort_index = None
                new_database = False

        """ Basic Tables """

        class BaseModel(peewee.Model):
            class Meta:
                database = self.db

            database_class = self

        class Meta(BaseModel):
            key = peewee.CharField(unique=True)
            value = peewee.CharField()

        class Option(BaseModel):
            key = peewee.CharField(unique=True)
            value = peewee.CharField(null=True)

        class Path(BaseModel):
            path = peewee.CharField(unique=True)

            def __str__(self):
                return "PathObject id%s: path=%s" % (self.id, self.path)

        """ Layer Table """

        class Layer(BaseModel):
            name = peewee.CharField(unique=True)
            base_layer = peewee.ForeignKeyField('self', related_name='dependent_layers')

            def __str__(self):
                return "LayerObject id%s:\tname=%s" \
                       % (self.id, self.name)

            def print_details(self):
                print("LayerObject:\n"
                      "id:\t\t{0}\n"
                      "name:\t{1}\n"
                      .format(self.id, self.name))

        class Image(BaseModel):
            filename = peewee.CharField()
            ext = peewee.CharField(max_length=10)
            frame = peewee.IntegerField(default=0)
            external_id = peewee.IntegerField(null=True)
            timestamp = peewee.DateTimeField(null=True)
            sort_index = peewee.IntegerField(default=0)
            width = peewee.IntegerField(null=True)
            height = peewee.IntegerField(null=True)
            path = peewee.ForeignKeyField(Path, backref="images", on_delete='CASCADE')
            layer = peewee.ForeignKeyField(Layer, backref="images", on_delete='CASCADE')

            class Meta:
                # image and path in combination have to be unique
                indexes = ((('filename', 'path', 'frame'), True),)

            def __array__(self):
                return self.get_data()

            def get_data(self):
                # if we have a buffer
                if self.database_class._buffer is not None:
                    # we try to get the image from the buffer to speed up the loading
                    image = self.database_class.get_image_data(self.sort_index, self.layer)
                    # if for some reason the buffer returns None, we have to load the image from the file
                    if image is not None:
                        return image
                # only if we don't have the file already open (which in case for videos is important)
                if self.database_class._reader is None or self.database_class._reader.filename != self.filename:
                    # compose the path
                    if platform.system() == 'Linux' and self.path.path.startswith("\\\\"):
                        # replace samba path for linux
                        path = os.path.join("/mnt", self.path.path[2:], self.filename).replace("\\", "/")
                    else:
                        path = os.path.join(os.path.dirname(self.database_class._database_filename), self.path.path, self.filename)
                    # get the reader (open the file)
                    self.database_class._reader = imageio.get_reader(path)
                    self.database_class._reader.filename = self.filename
                # return the image
                return self.database_class._reader.get_data(self.frame)

            def get_full_filename(self):
                filename = os.path.join(self.path.path, self.filename)
                # replace samba path for linux
                if platform.system() == 'Linux' and filename.startswith("\\\\"):
                    filename = "/mnt/" + filename[2:].replace("\\", "/")
                # apply replace pattern
                if self.database_class.replace is not None:
                    filename = filename.replace(self.database_class.replace[0], self.database_class.replace[1])
                return filename

            @property
            def mask(self):
                try:
                    return self.masks[0]
                except IndexError:
                    return None

            @property
            def annotation(self):
                try:
                    return self.annotations[0]
                except IndexError:
                    return None

            @property
            def offset(self):
                try:
                    return self.offsets[0]
                except IndexError:
                    return None

            @property
            def data(self):
                return self.get_data()

            @property
            def data8(self):
                data = self.get_data().copy()
                if data.dtype == np.uint16:
                    if data.max() < 2 ** 12:
                        data >>= 4
                        return data.astype(np.uint8)
                    data >>= 8
                    return data.astype(np.uint8)
                return data

            def __array__(self):
                return self.get_data()

            def getShape(self):
                if self.width is not None and self.height is not None:
                    return (self.height, self.width)
                else:
                    try:
                        return self.data.shape[:2]
                    except:
                        raise IOError("Can't retrieve image dimensions for %s" % self.filename)

            def __str__(self):
                return f"ImageObject id{self.id}:\tfilename={self.filename}\text={self.ext}\tframe={self.frame}" \
                       f"texternal_id={self.external_id}\ttimestamp={self.timestamp}\tsort_index={self.sort_index}," \
                       f" width={self.width}\theight={self.height}\tpath={self.path}\tlayer={self.layer}"

            def print_details(self):
                print("ImageObject:\n"
                      f"id:\t\t{self.id}\n"
                      f"filename:\t{self.filename}\n"
                      f"ext:\t{self.ext}\n"
                      f"frame:\t{self.frame}\n"
                      f"external_id:\t{self.external_id}\n"
                      f"timestamp:\t{self.timestamp}\n"
                      f"sort_index:\t{self.sort_index}\n"
                      f"widht:\t{self.width}\n"
                      f"height:\t{self.height}\n"
                      f"path:\t{self.path}\n"
                      f"layer:\t{self.layer}")

        self.base_model = BaseModel
        self.table_meta = Meta
        self.table_path = Path
        self.table_layer = Layer
        self.table_image = Image
        self.table_option = Option
        self._tables = [Meta, Path, Layer, Image, Option]

        """ Offset Table """

        class Offset(BaseModel):
            image = peewee.ForeignKeyField(Image, unique=True, backref="offsets", on_delete='CASCADE')
            x = peewee.FloatField()
            y = peewee.FloatField()

            def __str__(self):
                return "OffsetObject id%s:\tx=%s\ty=%s\timage=%s" \
                        % (self.id, self.x, self.y, self.image)

            def print_details(self):
                print("OffsetObject:\n"
                      "id:\t\t{0}\n"
                      "x:\t{1}\n"
                      "y:\t{2}\n"
                      "image:\t{3}\n"
                      .format(self.id, self.x, self.y, self.image))

            def __add__(self, other):
                try:
                    return np.array([self.x, self.y]) + other
                except TypeError:
                    return np.array([self.x, self.y]) + np.array([other.x, other.y])

            def __sub__(self, other):
                try:
                    return np.array([self.x, self.y]) - other
                except TypeError:
                    return np.array([self.x, self.y]) - np.array([other.x, other.y])

            def __array__(self):
                return np.array([self.x, self.y])

        self.table_offset = Offset
        self._tables.extend([Offset])

        """ Marker Tables """

        class MarkerType(BaseModel):
            name = peewee.CharField(unique=True)
            color = peewee.CharField()
            mode = peewee.IntegerField(default=0)
            style = peewee.CharField(null=True)
            text = peewee.CharField(null=True)
            hidden = peewee.BooleanField(default=False)

            def __str__(self):
                return "MarkerTypeObject id%s:\tname=%s\tcolor=%s\tmode=%s\tstyle=%s\ttext=%s\thidden=%s" \
                       % (self.id, self.name, self.color, self.mode, self.style, self.text, self.hidden)

            def print_details(self):
                print("MarkerTypeObject:\n"
                      "id:\t\t{0}\n"
                      "name:\t{1}\n"
                      "color:\t{2}\n"
                      "mode:\t{3}\n"
                      "style:\t{4}\n"
                      "text:\t{5}\n"
                      "hidden:\t{6}\n"
                      .format(self.id, self.name, self.color, self.mode, self.style, self.text, self.hidden))

            def getColorRGB(self):
                return HTMLColorToRGB(self.color)

        class Track(BaseModel):
            style = peewee.CharField(null=True)
            text = peewee.CharField(null=True)
            type = peewee.ForeignKeyField(MarkerType, backref="tracks", on_delete='CASCADE')
            hidden = peewee.BooleanField(default=False)

            def __getattribute__(self, item):
                if item == "points":
                    return np.array([[point.x, point.y] for point in self.markers])
                if item == "points_corrected":
                    return np.array([point.correctedXY() for point in self.markers])
                if item == "markers":
                    return self.track_markers.join(Image).order_by(Image.sort_index)
                if item == "times":
                    return np.array([point.image.timestamp for point in self.markers])
                if item == "frames":
                    return np.array([point.image.sort_index for point in self.markers])
                if item == "image_ids":
                    return np.array([point.image.id for point in self.markers])
                return BaseModel.__getattribute__(self, item)

            def __str__(self):
                return "TrackObject id%s:\ttype=%s\ttext=%s\tstyle=%s\thidden=%s" \
                       % (self.id, self.type, self.style, self.text, self.hidden)

            def print_details(self):
                print("TrackObject:\n"
                      "id:\t\t{0}\n"
                      "type:\t{1}\n"
                      "style:\t{2}\n"
                      "text:\t{3}\n"
                      "hidden:\t{4}\n"
                      .format(self.id, self.type, self.style, self.text, self.hidden))

            def split(self, marker):
                # if we are not given a marker entry..
                if not isinstance(marker, Marker):
                    # we try to get it over its id
                    marker = Marker.get(id=marker)
                    # if not complain
                    if marker is None:
                        raise ValueError("No valid marker given.")
                # get the markers after the given marker
                markers = self.markers.where(Image.sort_index > marker.image.sort_index)
                # create a new track as a copy of this track
                new_track = Track(style=self.style, text=self.text, type=self.type, hidden=self.hidden)
                new_track.save(force_insert=True)
                # move the markers after the given marker to the new track
                Marker.update(track=new_track.id).where(Marker.id << markers).execute()
                # return the new track
                return new_track

            def removeAfter(self, marker):
                # if we are not given a marker entry..
                if not isinstance(marker, Marker):
                    # we try to get it over its id
                    marker = Marker.get(id=marker)
                    # if not complain
                    if marker is None:
                        raise ValueError("No valid marker given.")
                # get the markers after the given marker
                markers = self.markers.where(Image.sort_index > marker.image.sort_index)
                # and delete them
                return Marker.delete().where(Marker.id << markers).execute()

            def changeType(self, new_type):
                # if we are not given a MarkerType entry..
                if not isinstance(new_type, MarkerType):
                    # we try to get it by its id
                    if isinstance(new_type, int):
                        new_type = MarkerType.get(id=new_type)
                    # or by its name
                    else:
                        new_type = MarkerType.get(name=new_type)
                    # if we don't find anything, complain
                    if new_type is None:
                        raise ValueError("No valid marker type given.")
                # ensure that the mode is correct
                if new_type.mode != self.database_class.TYPE_Track:
                    raise ValueError("Given type has not the mode TYPE_Track")
                # change the type and save
                self.type = new_type
                self.save()

                # and change the type of the markers
                #TODO: figure out why peewee ignores the where condition on some systems - works with raw query
                # q = self.database_class.table_marker.update(type=new_type).where(self.database_class.table_marker.track_id == self.id)
                count = self.database_class.db.execute_sql("UPDATE marker SET type_id = %d WHERE track_id = %d" % (new_type.id, self.id))
                return count

            def merge(self, track, mode=None):
                # if we are not given a track..
                if not isinstance(track, Track):
                    # interpret it as a track id and get the track entry
                    track = Track.get(id=track)
                    # if we don't get it, complain
                    if track is None:
                        raise ValueError("No valid track given.")
                # find the image ids from this track and the other track
                my_image_ids = [m.image_id for m in self.markers]
                other_image_ids = [m.image_id for m in track.markers]
                # test if they share any image ids
                if set(my_image_ids) & set(other_image_ids):
                    if mode == "average":
                        # the temporary table generates the averaged track, every point of this temporary table is
                        # upserted in the original track
                        self.database_class.db.execute_sql("WITH bla as (SELECT id, image_id, AVG(x) as x, AVG(y) as y, ? as track_id, type_id, processed, style, text FROM marker WHERE track_id in (?, ?) GROUP BY image_id);"
                                                           "INSERT OR REPLACE INTO marker(image_id, x, y, track_id, type_id, processed, style, text) SELECT image_id, x, y, track_id, type_id, processed, style, text from bla", [self.id, self.id, track.id])
                        # than we can delete the second track
                        track.delete_instance()
                    else:
                        # they are not allowed to share any images
                        image_list = set(my_image_ids) & set(other_image_ids)
                        # list first 10 images with a conflict
                        if len(image_list) < 10:
                            image_list = ", ".join("#%d" % i for i in image_list)
                        else:
                            image_list = ", ".join(["#%d" % i for i in image_list][:10]) + ", ..."
                        # raise an exception
                        raise ValueError(
                            "Can't merge track #%d with #%d, because they have markers in the same images.\n(images %s)" % (
                            self.id, track.id, image_list))
                else:
                # elif set(my_image_ids) & set(other_image_ids) and force:
                    #     if len(set(my_image_ids) & set(other_image_ids))>1:
                    #         self.database_class.db.execute_sql('update marker set track_id = ? where id in (select min(id) as id from marker where track_id in (?,?) group by image_id)',[self.id, self.id, track.id])
                    #         self.database_class.db.execute_sql('delete from marker where track_id=?',[track.id])
                    # move the markers from the other track to this track
                    count = Marker.update(track=self.id, type=self.type).where(Marker.id << track.markers).execute()
                    # and delete the other track
                    track.delete_instance()
                    return count

        class Marker(BaseModel):
            image = peewee.ForeignKeyField(Image, backref="markers", on_delete='CASCADE')
            x = peewee.FloatField()
            y = peewee.FloatField()
            type = peewee.ForeignKeyField(MarkerType, backref="markers", null=True, on_delete='CASCADE')
            processed = peewee.IntegerField(default=0)
            track = peewee.ForeignKeyField(Track, null=True, backref='track_markers', on_delete='CASCADE')
            style = peewee.CharField(null=True)
            text = peewee.CharField(null=True)

            class Meta:
                indexes = ((('image', 'track'), True),)

            def __str__(self):
                return "Marker Object: id=%s\timage=#%s\tx=%s\tx=%s\ttype=%s\tprocessed=%s\ttrack=#%s\tstyle=%s\ttext=%s" \
                       % (self.id, self.image_id, self.x, self.y, self.type, self.processed, self.track_id, self.style, self.text)

            def details(self):
                print("Marker Object:\n"
                      "id:\t\t{0}\n"
                      "image:\t{1}\n"
                      "x:\t{2}\n"
                      "y:\t{3}\n"
                      "type:\t{4}\n"
                      "processed:\t{5}\n"
                      "track:\t{5}\n"
                      "style:\t{5}\n"
                      "text:\t{5}\n"
                      .format(self.id, self.image, self.x, self.y, self.type, self.processed, self.track, self.style, self.text))

            def correctedXY(self):
                return np.array(self.database_class.db.execute_sql(
                    "SELECT m.x - IFNULL(o.x, 0), m.y - IFNULL(o.y, 0) FROM marker m LEFT JOIN image i ON m.image_id == i.id LEFT JOIN offset o ON i.id == o.image_id WHERE m.id == ?",
                    [self.id]).fetchone())

            def pos(self):
                return np.array([self.x, self.y])

            def __add__(self, other):
                try:
                    return np.array([self.x, self.y]) + other
                except TypeError:
                    return np.array([self.x, self.y]) + np.array([other.x, other.y])

            def __sub__(self, other):
                try:
                    return np.array([self.x, self.y]) - other
                except TypeError:
                    return np.array([self.x, self.y]) - np.array([other.x, other.y])

            def __array__(self):
                return np.array([self.x, self.y])

            def changeType(self, new_type):
                # if we are not given a MarkerType entry..
                if not isinstance(new_type, MarkerType):
                    # we try to get it by its id
                    if isinstance(new_type, int):
                        new_type = MarkerType.get(id=new_type)
                    # or by its name
                    else:
                        new_type = MarkerType.get(name=new_type)
                    # if we don't find anything, complain
                    if new_type is None:
                        raise ValueError("No valid marker type given.")
                if self.type.mode == self.database_class.TYPE_Normal:
                    # ensure that the mode is correct
                    if new_type.mode != self.database_class.TYPE_Normal:
                        raise ValueError("Given type has not the mode TYPE_Normal")
                elif self.type.mode == self.database_class.TYPE_Track:
                    # ensure that the mode is correct
                    if new_type.mode != self.database_class.TYPE_Track:
                        raise ValueError("Given type has not the mode TYPE_Track")
                # change the type and save
                self.type = new_type
                return self.save()

        class Line(BaseModel):
            image = peewee.ForeignKeyField(Image, backref="lines", on_delete='CASCADE')
            x1 = peewee.FloatField()
            y1 = peewee.FloatField()
            x2 = peewee.FloatField()
            y2 = peewee.FloatField()
            type = peewee.ForeignKeyField(MarkerType, backref="lines", null=True, on_delete='CASCADE')
            processed = peewee.IntegerField(default=0)
            style = peewee.CharField(null=True)
            text = peewee.CharField(null=True)

            def setPos1(self, x, y):
                self.x1 = x
                self.y1 = y

            def setPos2(self, x, y):
                self.x2 = x
                self.y2 = y

            def getPos(self):
                return [self.x1, self.y1, self.x2, self.y2]

            def getPos1(self):
                return [self.x1, self.y1]

            def getPos2(self):
                return [self.x2, self.y2]

            # def __getattribute__(self, item):
            #     if item == "correctedXY":
            #         return self.correctedXY()
            #     if item == "pos":
            #         return self.pos()
            #     if item == "length":
            #         return self.length()
            #     return BaseModel.__getattribute__(self, item)

            def correctedXY(self):
                join_condition = (Marker.image == Offset.image)

                querry = Marker.select(Marker.x,
                                       Marker.y,
                                       Offset.x,
                                       Offset.y) \
                    .join(Offset, peewee.JOIN_LEFT_OUTER, on=(join_condition).alias('offset')) \
                    .where(Marker.id == self.id)

                for q in querry:
                    if not (q.offset.x is None) or not (q.offset.y is None):
                        pt = [q.x + q.offset.x, q.y + q.offset.y]
                    else:
                        pt = [q.x, q.y]

                return pt

            def pos(self):
                return np.array([self.x, self.y])

            def length(self):
                return np.sqrt((self.x1-self.x2)**2 + (self.y1-self.y2)**2)

            def angle(self):
                return np.arctan2(self.y1 - self.y2, self.x1 - self.x2)

            def cropImage(self, image=None, width=None):
                # if no image is given take the image of the line
                if image is None:
                    image = self.image
                return getLine(image, self, width)

            def __str__(self):
                return "LineObject id%s:\timage=%s\tx1=%s\ty1=%s\tx2=%s\ty2=%s\ttype=%s\tprocessed=%s\tstyle=%s\ttext=%s" \
                       % (self.id, self.image, self.x1, self.y1, self.x2, self.y2, self.type, self.processed, self.style,
                          self.text)

            def print_details(self):
                print("LineObject:\n"
                      "id:\t\t{0}\n"
                      "image:\t{1}\n"
                      "x1:\t{2}\n"
                      "y1:\t{3}\n"
                      "x2:\t{4}\n"
                      "y2:\t{5}\n"
                      "type:\t{6}\n"
                      "processed:\t{7}\n"
                      "style:\t{8}\n"
                      "text:\t{9}"
                      .format(self.id, self.image, self.x1, self.y1, self.x2, self.y2, self.type, self.processed,
                              self.style,
                              self.text))

            def changeType(self, new_type):
                # if we are not given a MarkerType entry..
                if not isinstance(new_type, MarkerType):
                    # we try to get it by its id
                    if isinstance(new_type, int):
                        new_type = MarkerType.get(id=new_type)
                    # or by its name
                    else:
                        new_type = MarkerType.get(name=new_type)
                    # if we don't find anything, complain
                    if new_type is None:
                        raise ValueError("No valid marker type given.")
                # ensure that the mode is correct
                if new_type.mode != self.database_class.TYPE_Line:
                    raise ValueError("Given type has not the mode TYPE_Line")
                # change the type and save
                self.type = new_type
                return self.save()

            def __array__(self):
                return np.array([[self.x1, self.y1], [self.x2, self.y2]])

        class Rectangle(BaseModel):
            image = peewee.ForeignKeyField(Image, backref="rectangles", on_delete='CASCADE')
            x = peewee.FloatField()
            y = peewee.FloatField()
            width = peewee.FloatField()
            height = peewee.FloatField()
            type = peewee.ForeignKeyField(MarkerType, backref="rectangles", null=True, on_delete='CASCADE')
            processed = peewee.IntegerField(default=0)
            style = peewee.CharField(null=True)
            text = peewee.CharField(null=True)

            def setPos1(self, x, y):
                self.x = x
                self.y = y

            #def setPos2(self, x, y):
            #    self.x = x
            #    self.y = y

            def getRect(self):
                return [self.x, self.y, self.width, self.height]

            def getPos1(self):
                return [self.x, self.y]

            def getPos2(self):
                return [self.x+self.width, self.y]

            def getPos3(self):
                return [self.x+self.width, self.y+self.height]

            def getPos4(self):
                return [self.x, self.y+self.height]

            def correctedXY(self):
                return np.array(self.database_class.db.execute_sql(
                    "SELECT r.x - IFNULL(o.x, 0), r.y - IFNULL(o.y, 0) FROM rectangle r LEFT JOIN image i ON r.image_id == i.id LEFT JOIN offset o ON i.id == o.image_id WHERE r.id == ?",
                    [self.id]).fetchone())
            
                join_condition = (Marker.image == Offset.image)

                querry = Marker.select(Marker.x,
                                       Marker.y,
                                       Offset.x,
                                       Offset.y) \
                    .join(Offset, peewee.JOIN_LEFT_OUTER, on=(join_condition).alias('offset')) \
                    .where(Marker.id == self.id)

                for q in querry:
                    if not (q.offset.x is None) or not (q.offset.y is None):
                        pt = [q.x + q.offset.x, q.y + q.offset.y]
                    else:
                        pt = [q.x, q.y]

                return pt

            def pos(self):
                return np.array([self.x, self.y])

            def slice_x(self, border=0):
                if self.width < 0:
                    return slice(int(self.x+self.width-border), int(self.x+border))
                return slice(int(self.x-border), int(self.x+self.width+border))

            def slice_y(self, border=0):
                if self.height < 0:
                    return slice(int(self.y+self.height-border), int(self.y + border))
                return slice(int(self.y-border), int(self.y + self.height + border))

            def slice(self, border=0):
                try:
                    border_y, border_x = border
                except TypeError:
                    border_y = border
                    border_x = border
                return (self.slice_y(border_y), self.slice_x(border_x))

            def cropImage(self, image=None, with_offset=True, with_subpixel=False, border=0):
                # if no image is given take the image of the rectangle
                if image is None:
                    image = self.image
                # get the date from the image if it is a database entry
                if isinstance(image, Image):
                    image_data = image.data
                # if not, assume it is a numpy array
                else:
                    image_data = image

                try:
                    border_y, border_x = border
                except TypeError:
                    border_y = border
                    border_x = border

                # the start of the rectangle
                start = np.array([self.x-border_x, self.y-border_y])
                # the dimensions of the rectangle (needs to be integers)
                extent = np.array([self.width+border_x*2, self.height+border_y*2]).astype("int")

                # check if some dimensions are negative
                if self.width < 0:
                    extent[0] = -extent[0]
                    start[0] = start[0] - extent[0]
                if self.height < 0:
                    extent[1] = -extent[1]
                    start[1] = start[1] - extent[1]

                # subtract the offset from the image
                if with_offset:
                    # try to get the offset from the image (fails if image is already a numpy array)
                    try:
                        # get the offset from the rectangle's image
                        offset0 = self.image.offset
                        # get the offset from the target image
                        offset = image.offset
                        # try to calculate the difference
                        if offset0 is not None:
                            if offset is not None:
                                offset = offset - offset0
                            else:
                                offset = -np.array([offset0.x, offset0.y])
                    # image is a numpy array, it has no offset information
                    except AttributeError:
                        offset = None
                    # apply the offset, if we found one
                    if offset is not None:
                        start -= offset

                # split offsets in integer and decimal part
                start_int = start.astype("int")
                start_float = start - start_int

                # get the cropped image
                crop = image_data[start_int[1]:start_int[1]+extent[1], start_int[0]:start_int[0]+extent[0]]

                # apply the subpixel decimal shift
                if with_subpixel and (start_float[0] or start_float[1]):
                    from scipy.ndimage import shift
                    if len(crop.shape) == 2:  # bw image
                        crop = shift(crop, [start_float[1], start_float[0]])
                    else:  # color image
                        crop = shift(crop, [start_float[1], start_float[0], 0])

                # return the cropped image
                return crop

            def area(self):
                return self.width * self.height

            def __str__(self):
                return "RectangleObject id%s:\timage=%s\tx=%s\ty=%s\twidth=%s\theight=%s\ttype=%s\tprocessed=%s\tstyle=%s\ttext=%s" \
                       % (
                           self.id, self.image, self.x, self.y, self.width, self.height, self.type, self.processed,
                           self.style,
                           self.text)

            def print_details(self):
                print("RectangleObject:\n"
                      "id:\t\t{0}\n"
                      "image:\t{1}\n"
                      "x:\t{2}\n"
                      "y:\t{3}\n"
                      "width:\t{4}\n"
                      "height:\t{5}\n"
                      "type:\t{6}\n"
                      "processed:\t{7}\n"
                      "style:\t{8}\n"
                      "text:\t{9}"
                      .format(self.id, self.image, self.x, self.y, self.width, self.height, self.type, self.processed,
                              self.style,
                              self.text))

            def changeType(self, new_type):
                # if we are not given a MarkerType entry..
                if not isinstance(new_type, MarkerType):
                    # we try to get it by its id
                    if isinstance(new_type, int):
                        new_type = MarkerType.get(id=new_type)
                    # or by its name
                    else:
                        new_type = MarkerType.get(name=new_type)
                    # if we don't find anything, complain
                    if new_type is None:
                        raise ValueError("No valid marker type given.")
                # ensure that the mode is correct
                if new_type.mode != self.database_class.TYPE_Rect:
                    raise ValueError("Given type has not the mode TYPE_Rect")
                # change the type and save
                self.type = new_type
                return self.save()

        class Ellipse(BaseModel):
            image = peewee.ForeignKeyField(Image, backref="ellipses", on_delete='CASCADE')
            x = peewee.FloatField()
            y = peewee.FloatField()
            width = peewee.FloatField()
            height = peewee.FloatField()
            angle = peewee.FloatField()
            type = peewee.ForeignKeyField(MarkerType, backref="ellipses", null=True, on_delete='CASCADE')
            processed = peewee.IntegerField(default=0)
            style = peewee.CharField(null=True)
            text = peewee.CharField(null=True)

            @property
            def center(self):
                return np.array([self.x, self.y])

            @property
            def area(self):
                return np.pi * self.width / 2 * self.height / 2

            def __str__(self):
                return f"EllipseObject id{self.id}:\timage={self.image}\tx={self.x}\ty={self.y}\twidth={self.width}\theight={self.height}\tangle={self.angle}\ttype={self.type}\tprocessed={self.processed}\tstyle={self.style}\ttext={self.text}"

            def print_details(self):
                print("EllipseObject:\n"
                      f"id:\t\t{self.id}\n"
                      f"image:\t{self.image}\n"
                      f"x:\t{self.x}\n"
                      f"y:\t{self.y}\n"
                      f"width:\t{self.width}\n"
                      f"height:\t{self.height}\n"
                      f"angle:\t{self.angle}\n"
                      f"type:\t{self.type}\n"
                      f"processed:\t{self.processed}\n"
                      f"style:\t{self.style}\n"
                      f"text:\t{self.text}")

            def changeType(self, new_type):
                # if we are not given a MarkerType entry..
                if not isinstance(new_type, MarkerType):
                    # we try to get it by its id
                    if isinstance(new_type, int):
                        new_type = MarkerType.get(id=new_type)
                    # or by its name
                    else:
                        new_type = MarkerType.get(name=new_type)
                    # if we don't find anything, complain
                    if new_type is None:
                        raise ValueError("No valid marker type given.")
                # ensure that the mode is correct
                if new_type.mode != self.database_class.TYPE_Ellipse:
                    raise ValueError("Given type has not the mode TYPE_Ellipse")
                # change the type and save
                self.type = new_type
                return self.save()

        this = self
        class Polygon(BaseModel):
            image = peewee.ForeignKeyField(Image, backref="polygons", on_delete='CASCADE')
            type = peewee.ForeignKeyField(MarkerType, backref="polygons", null=True, on_delete='CASCADE')
            closed = peewee.BooleanField(default=0)
            processed = peewee.IntegerField(default=0)
            style = peewee.CharField(null=True)
            text = peewee.CharField(null=True)

            def __array__(self):
                return self.points

            @property
            def points(self):
                if getattr(self, "cached_points", None) is None:
                    self.cached_points = np.array(self.points_raw.select(this.table_polygon_point.x, this.table_polygon_point.y)
                                                .order_by(this.table_polygon_point.index).tuples(), dtype=float).ravel().reshape(-1, 2)
                return self.cached_points

            @points.setter
            def points(self, points):
                # store the points
                self.cached_points = np.asarray(points)
                # remember that this "points" "field" is dirty (e.g. is not synchronous with the database)
                setattr(self, "points_dirty", True)

            @property
            def area(self):
                x, y = self.points.T
                # the shoelace formula for the area of a polygon
                return 0.5 * np.abs(x @ np.roll(y, 1) - y @ np.roll(x, 1))

            @property
            def center(self):
                # the center is the mean of all points
                return np.mean(np.asarray(self.points), axis=0)

            @property
            def perimeter(self):
                p = np.asarray(self.points)
                # if it is closed, include the distance form the last to the first
                if self.closed:
                    return np.sum(np.linalg.norm(p - np.roll(p, axis=0), axis=1))
                else:
                    # if not, it is just the sum of the distances between subsequent points
                    return np.sum(np.linalg.norm(p[:-1] - p[1:], axis=1))

            def save(self, *args, **kwargs):
                BaseModel.save(self, *args, **kwargs)
                if getattr(self, "points_dirty", False) is True:
                    # remove unnecessary points
                    this.db.execute_sql(f"DELETE FROM polygonpoint WHERE polygon_id = {self.id} AND 'index' >= {len(self.cached_points)};")
                    # update the points
                    data = []
                    for index, point in enumerate(self.cached_points):
                        data.append(dict(polygon=self.id, x=point[0], y=point[1], index=index))
                    this.saveReplaceMany(this.table_polygon_point, data)

            def is_dirty(self):
                return BaseModel.is_dirty(self) or getattr(self, "points_dirty", False)

            def __str__(self):
                return f"PolygonObject id{self.id}:\timage={self.image}\ttype={self.type}\tprocessed={self.processed}\tstyle={self.style}\ttext={self.text}"

            def print_details(self):
                print("PolygonObject:\n"
                      f"id:\t\t{self.id}\n"
                      f"image:\t{self.image}\n"
                      f"type:\t{self.type}\n"
                      f"processed:\t{self.processed}\n"
                      f"style:\t{self.style}\n"
                      f"text:\t{self.text}")

            def changeType(self, new_type):
                # if we are not given a MarkerType entry..
                if not isinstance(new_type, MarkerType):
                    # we try to get it by its id
                    if isinstance(new_type, int):
                        new_type = MarkerType.get(id=new_type)
                    # or by its name
                    else:
                        new_type = MarkerType.get(name=new_type)
                    # if we don't find anything, complain
                    if new_type is None:
                        raise ValueError("No valid marker type given.")
                # ensure that the mode is correct
                if new_type.mode != self.database_class.TYPE_Polygon:
                    raise ValueError("Given type has not the mode TYPE_Polygon")
                # change the type and save
                self.type = new_type
                return self.save()

        class PolygonPoint(BaseModel):
            polygon = peewee.ForeignKeyField(Polygon, backref="points_raw", on_delete='CASCADE')
            x = peewee.FloatField()
            y = peewee.FloatField()
            index = peewee.IntegerField()

            class Meta:
                # image and path in combination have to be unique
                indexes = ((('polygon', 'index'), True),)

            def pos(self):
                return np.array([self.x, self.y])

        self.table_marker = Marker
        self.table_line = Line
        self.table_rectangle = Rectangle
        self.table_ellipse = Ellipse
        self.table_polygon = Polygon
        self.table_polygon_point = PolygonPoint
        self.table_track = Track
        self.table_markertype = MarkerType
        self._tables.extend([Marker, Line, Rectangle, Ellipse, Polygon, PolygonPoint, Track, MarkerType])

        """ Mask Tables """

        class Mask(BaseModel):
            image = peewee.ForeignKeyField(Image, backref="masks", on_delete='CASCADE')
            data = ImageField()
            
            def __array__(self):
                return self.data

            def __str__(self):
                return "MaskObject id%s: image=%s, data=%s" % (self.id, self.image, self.data)

        class MaskType(BaseModel):
            name = peewee.CharField(unique=True)
            color = peewee.CharField()
            index = peewee.IntegerField(unique=True)

            def __str__(self):
                return "MasktypeObject id%s: name=%s, color=%s, index=%s" % (self.id, self.name, self.color, self.index)

            def getColorRGB(self):
                return HTMLColorToRGB(self.color)

        self.table_mask = Mask
        self.table_masktype = MaskType
        self._tables.extend([Mask, MaskType])

        """ Annotation Tables """

        class Annotation(BaseModel):
            image = peewee.ForeignKeyField(Image, unique=True, backref="annotations", on_delete='CASCADE')
            timestamp = peewee.DateTimeField(null=True)
            comment = peewee.TextField(default="")
            rating = peewee.IntegerField(default=0)

            def __getattribute__(self, item):
                if item == "tags":
                    return [tagassociations.tag for tagassociations in self.tagassociations]
                return BaseModel.__getattribute__(self, item)

            def __str__(self):
                return "AnnotationObject id%s:\timage=%s\ttimestamp=%s\tcomment=%s\trating=%s" \
                       % (self.id, self.image, self.timestamp, self.comment, self.rating)

            def print_details(self):
                print("AnnotationObject:\n"
                      "id:\t\t{0}\n"
                      "image:\t{1}\n"
                      "timestamp:\t{2}\n"
                      "comment:\t{3}\n"
                      "rating:\t{4}\n"
                      .format(self.id, self.image, self.timestamp, self.comment, self.rating))

        class Tag(BaseModel):
            name = peewee.CharField()

            def __getattribute__(self, item):
                if item == "annotations":
                    return [tagassociations.annotation for tagassociations in self.tagassociations]
                return BaseModel.__getattribute__(self, item)

            def __str__(self):
                return "TagObject id%s:\timage=%s" \
                       % (self.id, self.name)

            def print_details(self):
                print("TagObject:\n"
                      "id:\t\t{0}\n"
                      "name:\t{1}\n"
                      .format(self.id, self.name))

        class TagAssociation(BaseModel):
            annotation = peewee.ForeignKeyField(Annotation, backref="tagassociations", on_delete='CASCADE')
            tag = peewee.ForeignKeyField(Tag, backref="tagassociations", on_delete='CASCADE')

            def __str__(self):
                return "TagAssociationObject id%s:\tannotation=%s\ttag=%s" \
                       % (self.id, self.annotation, self.tag)

            def print_details(self):
                print("TagAssociationObject:\n"
                      "id:\t\t{0}\n"
                      "annotation:\t{1}\n"
                      "tag:\t{2}\n"
                      .format(self.id, self.annotation, self.tag))

        self.table_annotation = Annotation
        self.table_tag = Tag
        self.table_tagassociation = TagAssociation
        self._tables.extend([Annotation, Tag, TagAssociation])

        """ Connect """
        try:
            self.db.connect()
        except peewee.OperationalError:
            pass
        self._CreateTables()
        self.db.execute_sql("PRAGMA foreign_keys = ON")
        self.db.execute_sql("PRAGMA journal_mode = WAL")
        if new_database:
            self.db.execute_sql("CREATE TRIGGER no_empty_tracks\
                                AFTER DELETE ON marker\
                                BEGIN\
                                  DELETE FROM track WHERE id = OLD.track_id AND (SELECT COUNT(marker.id) FROM marker WHERE marker.track_id = track.id) = 0;\
                                END;")

        if new_database:
            self.table_meta(key="version", value=self._current_version).save()

        # second migration part which needs the peewee model
        if version is not None and int(version) < int(self._current_version):
            self._migrateDBFrom2(version)

        self._InitOptions()

    def __del__(self):
        if self.db:
            self.db.close()

    def _InitOptions(self):
        self._options = {}
        self._options_by_key = {}
        self._last_category = "General"
        self._AddOption(key="jumps", display_name="Frame Jumps", default=[-1, +1, -10, +10, -100, +100, -1000, +1000], value_type="int", value_count=8,
                        tooltip="How many frames to jump\n"
                                "for the keys on the numpad:\n"
                                "2, 3, 5, 6, 8, 9, /, *")

        self._AddOption(key="auto_contrast", display_name="Auto Contrast", default=False, value_type="bool")
        self._AddOption(key="rotation", default=0, value_type="int", hidden=True)
        self._AddOption(key="rotation_steps", default=90, value_type="int", hidden=True)
        self._AddOption(key="hide_interfaces", default=True, value_type="bool", hidden=True)
        self._AddOption(key="timestamp_formats", default="['%Y%m%d-%H%M%S-%f', '%Y%m%d-%H%M%S']", value_type="string", hidden=True)
        self._AddOption(key="timestamp_formats2", default="['%Y%m%d-%H%M%S_%Y%m%d-%H%M%S']", value_type="string", hidden=True)
        self._AddOption(key="max_image_size", default=2**14, value_type="int", hidden=True)
        self._AddOption(key="threaded_image_load", display_name="Thread image load", default=True, value_type="bool",
                        tooltip="Whether to do image loading\n"
                                "in a separate thread.\n"
                                "Should only be altered if threading\n"
                                "causes issues.")
        self._AddOption(key="threaded_image_display", display_name="Thread image display", default=True,
                        value_type="bool",
                        tooltip="Whether to do image display\n"
                                "preparation in a separate thread.")
        self._AddOption(key="buffer_mode", display_name="Buffer Mode", default=2,
                        value_type="choice", values=["No Buffer", "Limit Buffer by Frames", "Limit Buffer by Memory"])
        self._AddOption(key="buffer_size", display_name="Buffer Frame Count", default=300, value_type="int", min_value=1,
                        tooltip="How many frames to keep in buffer.\n"
                                "The buffer should be only as big as the\n"
                                "RAM has space to prevent swapping.")
        self._AddOption(key="buffer_memory", display_name="Buffer Memory Amount", default=500, value_type="int",
                        min_value=1, unit="MB",
                        tooltip="How big the buffer is allowed to grow in MB.\n"
                                "This is no hard limit, the buffer can grow\n"
                                "one image bigger than the allowed memory size.\n"
                                "The buffer should be only as big as the\n"
                                "RAM has space to prevent swapping.")

        self._last_category = "Script Launcher"
        self._AddOption(key="scripts", hidden=True, default=[], value_type="array")

        self._last_category = "Contrast Adjust"
        self._AddOption(key="contrast_interface_hidden", default=True, value_type="bool", hidden=True)
        self._AddOption(key="contrast", default=None, value_type="dict", hidden=True)

        self._last_category = "Marker"
        self._AddOption(key="types", default={0: ["marker", [255, 0, 0], self.TYPE_Normal]}, value_type="dict", hidden=True)
        self._AddOption(key="selected_marker_type", default=-1, value_type="int", hidden=True)
        self._AddOption(key="marker_interface_hidden", default=True, value_type="bool", hidden=True)
        self._AddOption(key="tracking_connect_nearest", display_name="Track Auto-Connect", default=False, value_type="bool",
                        tooltip="When Auto-Connect is turned on,\n"
                                "clicking in the image will always\n"
                                "move the current point of the nearest track\n"
                                "instead of starting a new track.\n"
                                "To start a new track while Auto-Connect\n"
                                "is turned on, hold down the 'alt' key")
        self._AddOption(key="tracking_show_trailing", display_name="Track show trailing", default=20, value_type="int", min_value=-1,
                        tooltip="Nr of track markers displayed\n"
                                "before the current frame (past).\n"
                                "-1 for all.")
        self._AddOption(key="tracking_show_leading", display_name="Track show leading", default=0, value_type="int", min_value=-1,
                        tooltip="Nr of track markers displayed\n"
                                "after the current frame (future).\n"
                                "-1 for all.")
        self._AddOption(key="tracking_hide_trailing", display_name="Track hide trailing", default=2, value_type="int", min_value=0,
                        tooltip="Nr of frames before the first track marker\n"
                                "until which the track is hidden.")
        self._AddOption(key="tracking_hide_leading", display_name="Track hide leading", default=2, value_type="int", min_value=0,
                        tooltip="Nr of frames after the last track marker\n"
                                "until the the track is hidden")

        self._last_category = "Mask"
        self._AddOption(key="draw_types", default=[[1, [124, 124, 255], "mask"]], value_type="list", hidden=True)
        self._AddOption(key="selected_draw_type", default=-1, value_type="int", hidden=True)
        self._AddOption(key="mask_opacity", default=0.5, value_type="float", hidden=True)
        self._AddOption(key="mask_brush_size", default=10, value_type="int", hidden=True)
        self._AddOption(key="mask_interface_hidden", default=True, value_type="bool", hidden=True)
        self._AddOption(key="auto_mask_update", display_name="Auto Mask Update", default=True, value_type="bool",
                        tooltip="When turned on, mask changes\n"
                                "are directly displayed as the mask\n"
                                "if not, it is first displayed\n"
                                "separately to increase speed.")

        self._last_category = "Info Hud"
        self._AddOption(key="info_hud_string", display_name="Info Text", default="", value_type="string",
                        tooltip="Can display extra information of the image.\n"
                                "Supports the following types:\n"
                                "exif[] exit information from jpeg files.\n"
                                "regex[] information from the filename.\n"
                                "meta[] meta information from tiff images.")
        self._AddOption(key="filename_data_regex", display_name="Filename Regex", default="", value_type="string",
                        tooltip="Can display extra information of the image.\n"
                                "Supports the following types:\n"
                                "exif[] exit information from jpeg files.\n"
                                "regex[] information from the filename.\n"
                                "meta[] meta information from tiff images.")
        self._AddOption(key="infohud_interface_hidden", default=True, value_type="bool", hidden=True)

        self._last_category = "Timeline"
        self._AddOption(key="fps", default=0, value_type="float", hidden=True)
        self._AddOption(key="skip", default=1, value_type="int", hidden=True)
        self._AddOption(key="play_start", default=0.0, value_type="float", hidden=True)
        self._AddOption(key="play_end", default=1.0, value_type="float", hidden=True)
        self._AddOption(key="playing", default=False, value_type="bool", hidden=True)
        self._AddOption(key="timeline_hide", default=False, value_type="bool", hidden=True)
        self._AddOption(key="datetimeline_show", display_name="Show Datetimeline", default=True, value_type="bool",
                        tooltip="Whether to display the slider with dates.\n"
                                "Changes are only displayed after restart.")
        self._AddOption(key="display_timeformat", display_name="Timeformat for Display", default=r'%Y-%m-%d %H:%M:%S.%2f', value_type="string",
                        tooltip="How the time of the current frame\n"
                                "should be displayed.\n"
                                "Use %Y for year\n"
                                "%m for month\n"
                                "%d for day\n"
                                "%H for hour\n"
                                "%M for minute\n"
                                "%S for second\n"
                                "%2f for milliseconds\n"
                                "%6f for nanoseconds")

        self._last_category = "Video Exporter"
        self._AddOption(key="export_video_filename", default="export/export.mp4", value_type="string", hidden=True)
        self._AddOption(key="export_image_filename", default="export/images%d.jpg", value_type="string", hidden=True)
        self._AddOption(key="export_single_image_filename", default="export/images%d.jpg", value_type="string", hidden=True)
        self._AddOption(key="export_gif_filename", default="export/export.gif", value_type="string", hidden=True)
        self._AddOption(key="export_type", default=0, value_type="int", hidden=True)
        self._AddOption(key="video_codec", default="libx264", value_type="string", hidden=True)
        self._AddOption(key="video_quality", default=5, value_type="int", hidden=True)
        self._AddOption(key="export_display_time", default=True, value_type="bool", hidden=True)
        self._AddOption(key="export_time_from_zero", default=True, value_type="bool", hidden=True)
        self._AddOption(key="export_time_font_size", default=50, value_type="int", hidden=True)
        self._AddOption(key="export_time_font_color", default="#FFFFFF", value_type="string", hidden=True)
        self._AddOption(key="export_time_format", default="%Y-%m-%d %H:%M:%S", value_type="string", hidden=True)
        self._AddOption(key="export_timedelta_format", default="%H:%M:%S", value_type="string", hidden=True)

        self._AddOption(key="export_custom_time", default=False, value_type="bool", hidden=True)
        self._AddOption(key="export_custom_time_delta", default=1.0, value_type="float", hidden=True)

        self._AddOption(key="export_image_scale", default=1.0, value_type="float", hidden=True)
        self._AddOption(key="export_marker_scale", default=1.0, value_type="float", hidden=True)

        self._last_category = "Annotations"
        self._AddOption(key="server_annotations", default=False, value_type="bool", hidden=True)
        self._AddOption(key="sql_dbname", default='', value_type="string", hidden=True)
        self._AddOption(key="sql_host", default='', value_type="string", hidden=True)
        self._AddOption(key="sql_port", default=3306, value_type="int", hidden=True)
        self._AddOption(key="sql_user", default='', value_type="string", hidden=True)
        self._AddOption(key="sql_pwd", default='', value_type="string", hidden=True)

    def _AddOption(self, **kwargs):
        category = kwargs["category"] if "category" in kwargs else self._last_category
        if "display_name" not in kwargs:
            kwargs["display_name"] = kwargs["key"]
        option = Option(**kwargs)
        if category not in self._options:
            self._options[category] = []
        try:
            entry = self.table_option.get(key=option.key)
            entry_found = True
            if option.value_type == "int":
                if option.value_count > 1:
                    option.value = self._stringToList(entry.value)
                else:
                    option.value = int(entry.value)
            if option.value_type == "dict" or option.value_type == "list":
                import ast
                option.value = ast.literal_eval(entry.value)
            if option.value_type == "choice":
                option.value = int(entry.value)
            if option.value_type == "choice_string":
                option.value = str(entry.value)
            if option.value_type == "float":
                option.value = float(entry.value)
            if option.value_type == "bool":
                option.value = (entry.value == "True") or (entry.value == True)
            if option.value_type == "string":
                option.value = str(entry.value)
            if option.value_type == "color":
                option.value = str(entry.value)
            if option.value_type == "array":
                option.value = [value.strip()[1:-1] if value.strip()[0] != "u" else value.strip()[2:-1] for value in entry.value[1:-1].split(",")]
        except peewee.DoesNotExist:
            entry_found = False
        self._options[category].append(option)
        self._options_by_key[option.key] = option
        if self._config is not None and option.key in self._config and not entry_found:
            self.setOption(option.key, self._config[option.key])
            #print("Config", option.key, self._config[option.key])
            #print("Config", option.key, self._config[option.key])

    def _stringToList(self, value):
        value = value.strip()
        if (value.startswith("(") and value.endswith(")")) or (value.startswith("[") and value.endswith("]")):
            value = value[1:-1].strip()
        if value.endswith(","):
            value[:-1].strip()
        try:
            value = [int(v) for v in value.split(",")]
        except ValueError:
            raise ValueError()
        return value

    def setOption(self, key, value):
        option = self._options_by_key[key]
        option.value = value
        value = str(value)
        if str(option.default) == value:
            try:
                self.table_option.get(key=option.key).delete_instance()
            except peewee.DoesNotExist:
                return
        else:
            try:
                entry = self.table_option.get(key=option.key)
                entry.value = value
                entry.save()
            except peewee.DoesNotExist:
                self.table_option(key=option.key, value=value).save(force_insert=True)

    def getOption(self, key):
        option = self._options_by_key[key]
        if option.value is None:
            if isinstance(option.default, (dict, list)):
                return option.default.copy()
            return option.default
        return option.value

    def getOptionAccess(self):
        return OptionAccess(self)

    def _CheckVersion(self):
        try:
            version = self.db.execute_sql('SELECT value FROM meta WHERE key = "version"').fetchone()[0]
        except (KeyError, peewee.DoesNotExist):
            version = "0"
        print("Open database with version", version)
        if int(version) < int(self._current_version):
            self._migrateDBFrom(version)
        elif int(version) > int(self._current_version):
            print("Warning Database version %d is newer than ClickPoints version %d "
                  "- please get an updated Version!"
                  % (int(version), int(self._current_version)))
            print("Proceeding on own risk!")
        return version

    def _migrateDBFrom(self, version):
        # migrate database from an older version
        print("Migrating DB from version %s" % version)
        nr_version = int(version)
        self.db.connection().row_factory = dict_factory

        if nr_version < 3:
            print("\tto 3")
            with self.db.transaction():
                # Add text fields for Marker
                self.db.execute_sql("ALTER TABLE marker ADD COLUMN text varchar(255)")
            self._SetVersion(3)

        if nr_version < 4:
            print("\tto 4")
            with self.db.transaction():
                # Add text fields for Tracks
                self.db.execute_sql("ALTER TABLE tracks ADD COLUMN text varchar(255)")
                # Add text fields for Types
                self.db.execute_sql("ALTER TABLE types ADD COLUMN text varchar(255)")
            self._SetVersion(4)

        if nr_version < 5:
            print("\tto 5")
            with self.db.transaction():
                # Add text fields for Tracks
                self.db.execute_sql("ALTER TABLE images ADD COLUMN frame int DEFAULT 0")
                self.db.execute_sql("ALTER TABLE images ADD COLUMN sort_index int")
            with self.db.transaction():
                self.db.execute_sql(
                    "CREATE TEMPORARY TABLE NewIDs (sort_index INTEGER PRIMARY KEY AUTOINCREMENT, id INT UNSIGNED)")
                self.db.execute_sql("INSERT INTO NewIDs (id) SELECT id FROM images ORDER BY filename ASC")
                self.db.execute_sql(
                    "UPDATE images SET sort_index = (SELECT sort_index FROM NewIDs WHERE images.id = NewIDs.id)-1")
                self.db.execute_sql("DROP TABLE NewIDs")
            self._SetVersion(5)

        if nr_version < 6:
            print("\tto 6")
            with self.db.transaction():
                # Add text fields for Tracks
                self.db.execute_sql("ALTER TABLE images ADD COLUMN path_id int")
                self.db.execute_sql("ALTER TABLE images ADD COLUMN width int NULL")
                self.db.execute_sql("ALTER TABLE images ADD COLUMN height int NULL")
            self._SetVersion(6)

        if nr_version < 7:
            print("\tto 7")
            # fix migration for old branched databases
            if nr_version < 4:  # version before start of migration
                try:
                    # Add text fields for Tracks
                    self.db.execute_sql("ALTER TABLE tracks ADD COLUMN text varchar(255)")
                except peewee.OperationalError:
                    pass
                try:
                    # Add text fields for Types
                    self.db.execute_sql("ALTER TABLE types ADD COLUMN text varchar(255)")
                except peewee.OperationalError:
                    pass
            self._SetVersion(7)

        if nr_version < 8:
            print("\tto 8")
            with self.db.transaction():
                # fix for DB migration with missing paths table
                self.db.execute_sql('CREATE TABLE IF NOT EXISTS "paths" ("id" INTEGER NOT NULL PRIMARY KEY, "path" VARCHAR (255) NOT NULL);')
                self.db.execute_sql("ALTER TABLE paths RENAME TO path")
                self.db.execute_sql("ALTER TABLE images RENAME TO image")
                self.db.execute_sql('INSERT INTO path (id, path) VALUES(1, "")')
                self.db.execute_sql("UPDATE image SET path_id = 1")
                # fix for DB migration with missing paths table
                self.db.execute_sql('CREATE TABLE IF NOT EXISTS "offsets" ("id" INTEGER NOT NULL PRIMARY KEY, "image_id" INTEGER NOT NULL,"x" REAL NOT NULL,"y" REAL NOT NULL, FOREIGN KEY ("image_id") REFERENCES "image" ("id") ON DELETE CASCADE);')
                self.db.execute_sql("ALTER TABLE offsets RENAME TO offset")
                self.db.execute_sql("ALTER TABLE tracks RENAME TO track")
                self.db.execute_sql("ALTER TABLE types RENAME TO markertype")
                self.db.execute_sql("ALTER TABLE masktypes RENAME TO masktype")
                self.db.execute_sql("ALTER TABLE tags RENAME TO tag")
            self._SetVersion(8)

        if nr_version < 9:
            print("\tto 9")
            with self.db.transaction():
                # Add type fields for Track
                self.db.execute_sql("ALTER TABLE track ADD COLUMN type_id int")
                self.db.execute_sql("UPDATE track SET type_id = (SELECT type_id FROM marker WHERE track_id = track.id LIMIT 1)")
                self.db.execute_sql("DELETE FROM track WHERE type_id IS NULL")
            self._SetVersion(9)

        if nr_version < 10:
            print("\tto 10")
            with self.db.transaction():
                # store mask_path and all masks
                self.db.execute_sql("PRAGMA foreign_keys = OFF")
                try:
                    mask_path = self.db.execute_sql("SELECT * FROM meta WHERE key = 'mask_path'").fetchone()[2]
                except TypeError:
                    mask_path = ""
                masks = self.db.execute_sql("SELECT id, image_id, filename FROM mask").fetchall()
                self.migrate_to_10_mask_path = mask_path
                self.migrate_to_10_masks = masks
                self.db.execute_sql("CREATE TABLE `mask_tmp` (`id` INTEGER NOT NULL, `image_id` INTEGER NOT NULL, `data` BLOB NOT NULL, PRIMARY KEY(id), FOREIGN KEY(`image_id`) REFERENCES 'image' ( 'id' ) ON DELETE CASCADE)")
                for mask in masks:
                    tmp_maskpath = os.path.join(self.migrate_to_10_mask_path, mask[2])
                    if os.path.exists(tmp_maskpath):
                        from PIL import Image as PILImage
                        im = np.asarray(PILImage.open(tmp_maskpath))
                        value = imageio.imwrite(imageio.RETURN_BYTES, im, format=".png")
                        value = peewee.binary_construct(value)
                        self.db.execute_sql("INSERT INTO mask_tmp VALUES (?, ?, ?)", [mask[0], mask[1], value])
                self.db.execute_sql("DROP TABLE mask")
                self.db.execute_sql("ALTER TABLE mask_tmp RENAME TO mask")
                self.db.execute_sql("PRAGMA foreign_keys = ON")
            self._SetVersion(10)

        if nr_version < 11:
            print("\tto 11")
            with self.db.transaction():
                self.db.execute_sql("PRAGMA foreign_keys = OFF")
                self.db.execute_sql('CREATE TABLE "annotation_tmp" ("id" INTEGER NOT NULL PRIMARY KEY, "image_id" INTEGER NOT NULL, "timestamp" DATETIME, "comment" TEXT NOT NULL, "rating" INTEGER NOT NULL, FOREIGN KEY ("image_id") REFERENCES "image" ("id") ON DELETE CASCADE)')
                self.db.execute_sql('INSERT INTO annotation_tmp SELECT id, image_id, timestamp, comment, rating FROM annotation')
                self.db.execute_sql("DROP TABLE annotation")
                self.db.execute_sql("ALTER TABLE annotation_tmp RENAME TO annotation")

                self.db.execute_sql('CREATE TABLE "tagassociation_tmp" ("id" INTEGER NOT NULL PRIMARY KEY, "annotation_id" INTEGER NOT NULL, "tag_id" INTEGER NOT NULL, FOREIGN KEY ("annotation_id") REFERENCES "annotation" ("id") ON DELETE CASCADE, FOREIGN KEY ("tag_id") REFERENCES "tag" ("id") ON DELETE CASCADE);')
                self.db.execute_sql('INSERT INTO tagassociation_tmp SELECT id, annotation_id, tag_id FROM tagassociation')
                self.db.execute_sql("DROP TABLE tagassociation")
                self.db.execute_sql("ALTER TABLE tagassociation_tmp RENAME TO tagassociation")

                self.db.execute_sql("DROP TABLE IF EXISTS basemodel")

                self.db.execute_sql('CREATE TABLE "image_tmp" ("id" INTEGER NOT NULL PRIMARY KEY, "filename" VARCHAR(255) NOT NULL, "ext" VARCHAR(10) NOT NULL, "frame" INTEGER, "external_id" INTEGER, "timestamp" DATETIME, "sort_index" INTEGER, "width" INTEGER, "height" INTEGER, "path_id" INTEGER, FOREIGN KEY ("path_id") REFERENCES "path" ("id") ON DELETE CASCADE);')
                self.db.execute_sql('INSERT INTO image_tmp SELECT id, filename, ext, frame, external_id, timestamp, sort_index, width, height, path_id FROM image')
                self.db.execute_sql("DROP TABLE image")
                self.db.execute_sql("ALTER TABLE image_tmp RENAME TO image")

                self.db.execute_sql('CREATE TABLE "marker_tmp" ("id" INTEGER NOT NULL PRIMARY KEY, "image_id" INTEGER NOT NULL, "x" REAL NOT NULL, "y" REAL NOT NULL, "type_id" INTEGER, "processed" INTEGER NOT NULL, "partner_id" INTEGER, "track_id" INTEGER, "style" VARCHAR(255), "text" VARCHAR(255), FOREIGN KEY ("image_id") REFERENCES "image" ("id") ON DELETE CASCADE, FOREIGN KEY ("type_id") REFERENCES "markertype" ("id") ON DELETE CASCADE, FOREIGN KEY ("partner_id") REFERENCES "marker" ("id") ON DELETE SET NULL, FOREIGN KEY ("track_id") REFERENCES "track" ("id"));')
                self.db.execute_sql('INSERT INTO marker_tmp SELECT id, image_id, x, y, type_id, processed, partner_id, track_id, style, text FROM marker')
                self.db.execute_sql("DROP TABLE marker")
                self.db.execute_sql("ALTER TABLE marker_tmp RENAME TO marker")

                self.db.execute_sql('CREATE TABLE "offset_tmp" ("id" INTEGER NOT NULL PRIMARY KEY, "image_id" INTEGER NOT NULL, "x" REAL NOT NULL, "y" REAL NOT NULL, FOREIGN KEY ("image_id") REFERENCES "image" ("id") ON DELETE CASCADE);')
                self.db.execute_sql('INSERT INTO offset_tmp SELECT id, image_id, x, y FROM offset')
                self.db.execute_sql("DROP TABLE offset")
                self.db.execute_sql("ALTER TABLE offset_tmp RENAME TO offset")

                self.db.execute_sql('CREATE TABLE "track_tmp" ("id" INTEGER NOT NULL PRIMARY KEY, "uid" VARCHAR(255) NOT NULL, "style" VARCHAR(255), "text" VARCHAR(255), "type_id" INTEGER NOT NULL, FOREIGN KEY ("type_id") REFERENCES "markertype" ("id") ON DELETE CASCADE);')
                self.db.execute_sql('INSERT INTO track_tmp SELECT id, uid, style, text, type_id FROM track')
                self.db.execute_sql("DROP TABLE track")
                self.db.execute_sql("ALTER TABLE track_tmp RENAME TO track")

            self._SetVersion(11)

        if nr_version < 12:
            print("\tto 12")
            with self.db.transaction():
                self.db.execute_sql("DELETE FROM meta WHERE key = 'version'")
                indexes = ['CREATE UNIQUE INDEX IF NOT EXISTS "image_filename_path_id_frame" ON "image" ("filename", "path_id", "frame");',
                            'CREATE UNIQUE INDEX IF NOT EXISTS "marker_image_id_track_id" ON "marker" ("image_id", "track_id");',
                            'CREATE INDEX IF NOT EXISTS "track_type_id" ON "track" ("type_id");',
                            'CREATE INDEX IF NOT EXISTS "marker_track_id" ON "marker" ("track_id");',
                            'CREATE INDEX IF NOT EXISTS "marker_type_id" ON "marker" ("type_id");',
                            'CREATE UNIQUE INDEX IF NOT EXISTS "markertype_name" ON "markertype" ("name");',
                            'CREATE UNIQUE INDEX IF NOT EXISTS "path_path" ON "path" ("path");',
                            'CREATE INDEX IF NOT EXISTS "image_path_id" ON "image" ("path_id");',
                            'CREATE INDEX IF NOT EXISTS "marker_image_id" ON "marker" ("image_id");',
                            'CREATE INDEX IF NOT EXISTS "tagassociation_tag_id" ON "tagassociation" ("tag_id");',
                            'CREATE UNIQUE INDEX IF NOT EXISTS "meta_key" ON "meta" ("key");',
                            'CREATE INDEX IF NOT EXISTS "marker_partner_id" ON "marker" ("partner_id");',
                            'CREATE INDEX IF NOT EXISTS "mask_image_id" ON "mask" ("image_id");',
                            'CREATE INDEX IF NOT EXISTS "tagassociation_annotation_id" ON "tagassociation" ("annotation_id");',
                            'CREATE UNIQUE INDEX IF NOT EXISTS "masktype_index" ON "masktype" ("index");',
                            'CREATE UNIQUE INDEX IF NOT EXISTS "offset_image_id" ON "offset" ("image_id");',
                            'CREATE INDEX IF NOT EXISTS "annotation_image_id" ON "annotation" ("image_id");']
                for index in indexes:
                    self.db.execute_sql(index)
            self._SetVersion(12)

        if nr_version < 13:
            print("\tto 13")
            with self.db.transaction():
                self.db.execute_sql('CREATE TABLE "marker_tmp" ("id" INTEGER NOT NULL PRIMARY KEY, "image_id" INTEGER NOT NULL, "x" REAL NOT NULL, "y" REAL NOT NULL, "type_id" INTEGER, "processed" INTEGER NOT NULL, "partner_id" INTEGER, "track_id" INTEGER, "style" VARCHAR(255), "text" VARCHAR(255), FOREIGN KEY ("image_id") REFERENCES "image" ("id") ON DELETE CASCADE, FOREIGN KEY ("type_id") REFERENCES "markertype" ("id") ON DELETE CASCADE, FOREIGN KEY ("partner_id") REFERENCES "marker" ("id") ON DELETE SET NULL, FOREIGN KEY ("track_id") REFERENCES "track" ("id") ON DELETE CASCADE);')
                self.db.execute_sql('INSERT INTO marker_tmp SELECT id, image_id, x, y, type_id, processed, partner_id, track_id, style, text FROM marker')
                self.db.execute_sql("DROP TABLE marker")
                self.db.execute_sql("ALTER TABLE marker_tmp RENAME TO marker")
                self.db.execute_sql('CREATE INDEX "marker_image_id" ON "marker" ("image_id")')
                self.db.execute_sql('CREATE UNIQUE INDEX "marker_image_id_track_id" ON "marker" ("image_id", "track_id")')
                self.db.execute_sql('CREATE INDEX "marker_partner_id" ON "marker" ("partner_id")')
                self.db.execute_sql('CREATE INDEX "marker_track_id" ON "marker" ("track_id")')
                self.db.execute_sql('CREATE INDEX "marker_type_id" ON "marker" ("type_id")')
                self.db.execute_sql('CREATE TRIGGER no_empty_tracks\
                                    AFTER DELETE ON marker\
                                    BEGIN\
                                        DELETE FROM track WHERE id = OLD.track_id AND (SELECT COUNT(marker.id) FROM marker WHERE marker.track_id = track.id) = 0;\
                                    END;')
            self._SetVersion(13)

        if nr_version < 14:
            print("\tto 14")
            with self.db.transaction():
                # create new table line
                self.db.execute_sql('CREATE TABLE "line" ("id" INTEGER NOT NULL PRIMARY KEY, "image_id" INTEGER NOT NULL, "x1" REAL NOT NULL, "y1" REAL NOT NULL, "x2" REAL NOT NULL, "y2" REAL NOT NULL, "type_id" INTEGER, "processed" INTEGER NOT NULL, "style" VARCHAR(255), "text" VARCHAR(255), FOREIGN KEY ("image_id") REFERENCES "image" ("id") ON DELETE CASCADE, FOREIGN KEY ("type_id") REFERENCES "markertype" ("id") ON DELETE CASCADE);')
                self.db.execute_sql('CREATE INDEX "line_image_id" ON "line" ("image_id");')
                self.db.execute_sql('CREATE INDEX "line_type_id" ON "line" ("type_id");')

                # migrate line marker to line
                self.db.execute_sql('INSERT INTO line SELECT m1.id, m1.image_id, m1.x AS x1, m1.y AS y1, m2.x AS x2, m2.y AS y2, m1.type_id, m1.processed, m1.style, m1.text FROM marker AS m1 JOIN markertype ON m1.type_id = markertype.id JOIN marker AS m2 ON m1.partner_id = m2.id WHERE m1.partner_id > m1.id AND mode == 2')
                self.db.execute_sql('DELETE FROM marker WHERE marker.id IN (SELECT marker.id FROM marker JOIN markertype ON marker.type_id = markertype.id WHERE mode == 2)')

                # create table rectangle
                self.db.execute_sql('CREATE TABLE "rectangle" ("id" INTEGER NOT NULL PRIMARY KEY, "image_id" INTEGER NOT NULL, "x" REAL NOT NULL, "y" REAL NOT NULL, "width" REAL NOT NULL, "height" REAL NOT NULL, "type_id" INTEGER, "processed" INTEGER NOT NULL, "style" VARCHAR(255), "text" VARCHAR(255), FOREIGN KEY ("image_id") REFERENCES "image" ("id") ON DELETE CASCADE, FOREIGN KEY ("type_id") REFERENCES "markertype" ("id") ON DELETE CASCADE);')
                self.db.execute_sql('CREATE INDEX "rectangle_image_id" ON "rectangle" ("image_id");')
                self.db.execute_sql('CREATE INDEX "rectangle_type_id" ON "rectangle" ("type_id");')

                # migrate rectangle marker to rectangle
                self.db.execute_sql('INSERT INTO rectangle SELECT m1.id, m1.image_id, m1.x, m1.y, (m2.x-m1.x) AS width, (m2.y-m1.y) AS height, m1.type_id, m1.processed, m1.style, m1.text FROM marker AS m1 JOIN markertype ON m1.type_id = markertype.id JOIN marker AS m2 ON m1.partner_id = m2.id WHERE m1.partner_id > m1.id AND mode == 1')
                self.db.execute_sql('DELETE FROM marker WHERE marker.id IN (SELECT marker.id FROM marker JOIN markertype ON marker.type_id = markertype.id WHERE mode == 1)')
            self._SetVersion(14)

        if nr_version < 15:
            print("\tto 15")
            with self.db.transaction():
                # remove uid from tracks
                self.db.execute_sql('CREATE TABLE "track_tmp" ("id" INTEGER NOT NULL PRIMARY KEY, "style" VARCHAR(255), "text" VARCHAR(255), "type_id" INTEGER NOT NULL, FOREIGN KEY ("type_id") REFERENCES "markertype" ("id") ON DELETE CASCADE);')
                self.db.execute_sql('INSERT INTO track_tmp SELECT id, style, text, type_id FROM track')
                self.db.execute_sql("DROP TABLE track")
                self.db.execute_sql("ALTER TABLE track_tmp RENAME TO track")
                self.db.execute_sql('CREATE INDEX "track_type_id" ON "track" ("type_id")')

                # make masktype unique
                self.db.execute_sql('CREATE TABLE "masktype_tmp" ("id" INTEGER NOT NULL PRIMARY KEY, "name" VARCHAR(255) NOT NULL, "color" VARCHAR(255) NOT NULL, "index" INTEGER NOT NULL)')
                self.db.execute_sql('CREATE UNIQUE INDEX "masktype_tmp_index" ON "masktype_tmp" ("index");')
                self.db.execute_sql('CREATE UNIQUE INDEX "masktype_tmp_name" ON "masktype_tmp" ("name");')
                mask_types = self.db.execute_sql('SELECT * from masktype').fetchall()
                for mask_type in mask_types:
                    i = 1
                    name = mask_type["name"]
                    while True:
                        try:
                            self.db.execute_sql('INSERT INTO masktype_tmp ("id", "name", "color", "index") VALUES(?, ?, ?, ?)', [mask_type["id"], name, mask_type["color"], mask_type["index"]])
                            break
                        except peewee.IntegrityError:
                            i += 1
                            name = "%s%d" % (mask_type["name"], i)
                self.db.execute_sql("DROP TABLE masktype")
                self.db.execute_sql("ALTER TABLE masktype_tmp RENAME TO masktype")
                self.db.execute_sql('DROP INDEX "masktype_tmp_index"')
                self.db.execute_sql('DROP INDEX "masktype_tmp_name"')
                self.db.execute_sql('CREATE UNIQUE INDEX "masktype_index" ON "masktype" ("index");')
                self.db.execute_sql('CREATE UNIQUE INDEX "masktype_name" ON "masktype" ("name");')

                # make annotations unique
                self.db.execute_sql('DROP INDEX IF EXISTS "annotation_image_id"')
                self.db.execute_sql('CREATE UNIQUE INDEX "annotation_image_id" ON "annotation" ("image_id");')
            self._SetVersion(15)

        if nr_version < 16:
            print("\tto 16")
            with self.db.transaction():
                try:
                    self.db.execute_sql(
                        'CREATE TABLE "option" ("id" INTEGER NOT NULL PRIMARY KEY, "key" VARCHAR(255) NOT NULL, "value" VARCHAR(255))')
                    self.db.execute_sql('CREATE UNIQUE INDEX "option_key" ON "option" ("key")')
                except peewee.OperationalError:
                    pass
            self._SetVersion(16)

        if nr_version < 17:
            print("\tto 17")
            with self.db.transaction():
                try:
                    self.db.execute_sql(
                        'CREATE TABLE "markertype_tmp" ("id" INTEGER NOT NULL PRIMARY KEY, "name" VARCHAR(255) NOT NULL, "color" VARCHAR(255) NOT NULL, "mode" INTEGER NOT NULL, "style" VARCHAR(255), "text" VARCHAR(255), "hidden" INTEGER NOT NULL);')
                    self.db.execute_sql(
                        'INSERT INTO markertype_tmp SELECT id, name, color, mode, style, text, "0" FROM markertype')
                    self.db.execute_sql("DROP TABLE markertype")
                    self.db.execute_sql("ALTER TABLE markertype_tmp RENAME TO markertype")
                    self.db.execute_sql('CREATE UNIQUE INDEX "markertype_name" ON "markertype" ("name");')

                    self.db.execute_sql(
                        'CREATE TABLE "track_tmp" ("id" INTEGER NOT NULL PRIMARY KEY, "style" VARCHAR(255), "text" VARCHAR(255), "type_id" INTEGER NOT NULL, "hidden" INTEGER NOT NULL, FOREIGN KEY ("type_id") REFERENCES "markertype" ("id") ON DELETE CASCADE);')
                    self.db.execute_sql(
                        'INSERT INTO track_tmp SELECT id, style, text, type_id, "0" FROM track')
                    self.db.execute_sql("DROP TABLE track")
                    self.db.execute_sql("ALTER TABLE track_tmp RENAME TO track")
                    self.db.execute_sql('CREATE INDEX "track_type_id" ON "track" ("type_id");')
                except peewee.OperationalError:
                    raise
                    pass
            self._SetVersion(17)

        if nr_version < 18:
            print("\tto 18")
            with self.db.transaction():
                try:
                    self.db.execute_sql(
                        'CREATE TABLE "image_tmp" ("id" INTEGER NOT NULL PRIMARY KEY, "filename" VARCHAR(255) NOT NULL, "ext" VARCHAR(10) NOT NULL, "frame" INTEGER DEFAULT 0, "external_id" INTEGER, "timestamp" DATETIME, "sort_index" INTEGER NOT NULL, "width" INTEGER, "height" INTEGER, "path_id" INTEGER NOT NULL, "layer" INTEGER NOT NULL, FOREIGN KEY ("path_id") REFERENCES "path" ("id") ON DELETE CASCADE);')
                    self.db.execute_sql(
                        'INSERT INTO image_tmp SELECT id, filename, ext, frame, external_id, timestamp, sort_index, width, height, path_id, "0" FROM image')
                    self.db.execute_sql('DROP TABLE image')
                    self.db.execute_sql('ALTER TABLE image_tmp RENAME TO image')
                    self.db.execute_sql('CREATE INDEX "image_path_id" ON "image" ("path_id");')
                except peewee.OperationalError:
                    raise
                pass
            self._SetVersion(18)

        if nr_version < 19:
            print("\tto 19")

            with self.db.transaction():
                # crete a new table for the layers
                self.db.execute_sql(
                    'CREATE TABLE "layer" ("id" INTEGER NOT NULL PRIMARY KEY, "name" VARCHAR(255) NOT NULL);')
                self.db.execute_sql('CREATE UNIQUE INDEX "layer_name" ON "layer" ("name")')
                # increase the layer index of every image (should now start with layer 1 instead of layer 0)
                self.db.execute_sql('UPDATE image SET layer = layer+1')
                # add layer entries for each layer referenced in the image table
                self.db.execute_sql('INSERT INTO layer SELECT DISTINCT layer, "layer " || layer FROM image')

                # convert the layer field to a foreign key field
                self.db.execute_sql('CREATE TABLE "image_tmp" ("id" INTEGER NOT NULL PRIMARY KEY, "filename" VARCHAR(255) NOT NULL, "ext" VARCHAR(10) NOT NULL, "frame" INTEGER NOT NULL, "external_id" INTEGER, "timestamp" DATETIME, "sort_index" INTEGER NOT NULL, "width" INTEGER, "height" INTEGER, "path_id" INTEGER NOT NULL, "layer_id" INTEGER, FOREIGN KEY ("path_id") REFERENCES "path" ("id") ON DELETE CASCADE, FOREIGN KEY ("layer_id") REFERENCES "layer" ("id") ON DELETE CASCADE);')
                self.db.execute_sql('INSERT INTO image_tmp SELECT * FROM image')
                self.db.execute_sql("DROP TABLE image")
                self.db.execute_sql("ALTER TABLE image_tmp RENAME TO image")

                # rename the first layer to "default"
                self.db.execute_sql('UPDATE layer SET name="default" WHERE id = 1')

            self._SetVersion(19)

        if nr_version < 20:
            print("\tto 20")

            with self.db.transaction():
                # create a new tmp table with base_layer_id added as a foreign key field
                self.db.execute_sql('CREATE TABLE "layer_tmp" ("id" INTEGER NOT NULL PRIMARY KEY, "name" VARCHAR(255) NOT NULL, "base_layer_id" INTEGER NOT NULL, FOREIGN KEY ("base_layer_id") REFERENCES "layer" ("id"));')
                self.db.execute_sql('INSERT INTO layer_tmp SELECT id, name, (SELECT id FROM layer ORDER BY id LIMIT 1) FROM layer')
                self.db.execute_sql("DROP TABLE layer")
                self.db.execute_sql("ALTER TABLE layer_tmp RENAME TO layer")

                self.db.execute_sql('CREATE UNIQUE INDEX "layer_name" ON "layer" ("name");')

            self._SetVersion(20)

        if nr_version < 21:
            print("\tto 21")

            with self.db.transaction():
                # create a new table for the ellipses
                self.db.execute_sql("""CREATE TABLE ellipse (
                                                            id        INTEGER       NOT NULL
                                                                                    PRIMARY KEY,
                                                            image_id  INTEGER       NOT NULL,
                                                            x         REAL          NOT NULL,
                                                            y         REAL          NOT NULL,
                                                            width     REAL          NOT NULL,
                                                            height    REAL          NOT NULL,
                                                            angle     REAL          NOT NULL,
                                                            type_id   INTEGER,
                                                            processed INTEGER       NOT NULL,
                                                            style     VARCHAR (255),
                                                            text      VARCHAR (255),
                                                            FOREIGN KEY (
                                                                image_id
                                                            )
                                                            REFERENCES image (id) ON DELETE CASCADE,
                                                            FOREIGN KEY (
                                                                type_id
                                                            )
                                                            REFERENCES markertype (id) ON DELETE CASCADE
                                                        );

                """)
            self._SetVersion(21)

        if nr_version < 22:
            print("\tto 22")

            with self.db.transaction():
                # create a new table for the polygons
                self.db.execute_sql("""CREATE TABLE polygon (
                                                                id        INTEGER       NOT NULL
                                                                                        PRIMARY KEY,
                                                                image_id  INTEGER       NOT NULL,
                                                                type_id   INTEGER,
                                                                closed    INTEGER       NOT NULL,
                                                                processed INTEGER       NOT NULL,
                                                                style     VARCHAR (255),
                                                                text      VARCHAR (255),
                                                                FOREIGN KEY (
                                                                    image_id
                                                                )
                                                                REFERENCES image (id) ON DELETE CASCADE,
                                                                FOREIGN KEY (
                                                                    type_id
                                                                )
                                                                REFERENCES markertype (id) ON DELETE CASCADE
                                                            );
                """)
                self.db.execute_sql("""CREATE TABLE polygonpoint (
                                                                    id         INTEGER NOT NULL
                                                                                       PRIMARY KEY,
                                                                    polygon_id INTEGER NOT NULL,
                                                                    x          REAL    NOT NULL,
                                                                    y          REAL    NOT NULL,
                                                                    [index]    INTEGER NOT NULL,
                                                                    FOREIGN KEY (
                                                                        polygon_id
                                                                    )
                                                                    REFERENCES polygon (id) ON DELETE CASCADE
                                                                );
                """)
                self.db.execute_sql("""CREATE UNIQUE INDEX polygonpoint_polygon_id_index ON polygonpoint (
                                        polygon_id,
                                        "index"
                                    );
                """)
            self._SetVersion(22)

        self.db.connection().row_factory = None

    def _SetVersion(self, nr_new_version):
        self.db.execute_sql("INSERT OR REPLACE INTO meta (id,key,value) VALUES ( \
                                            (SELECT id FROM meta WHERE key='version'),'version',%s)" % str(
            nr_new_version))

    def _migrateDBFrom2(self, nr_version):
        nr_version = int(nr_version)
        if nr_version < 5:
            print("second migration step to 5")
            images = self.table_image.select().order_by(self.table_image.filename)
            for index, image in enumerate(images):
                image.sort_index = index
                image.frame = 0
                image.save()
        if nr_version < 6:
            print("second migration step to 6")
            images = self.table_image.select().order_by(self.table_image.filename)
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
                    path_entry = self.table_path.get(path=path)
                except peewee.DoesNotExist:
                    path_entry = self.table_path(path=path)
                    path_entry.save()
                image.path = path_entry
                image.save()

    def _CreateTables(self):
        for table in self._tables:
            table.create_table(fail_silently=True)

    def _checkTrackField(self, tracks):
        if not isinstance(tracks, (tuple, list)):
            tracks = [tracks]
        tracks = list(set([t for t in tracks if t is not None]))
        if len(tracks) == 0:
            return
        if self._SQLITE_MAX_VARIABLE_NUMBER is None:
            self._SQLITE_MAX_VARIABLE_NUMBER = self.max_sql_variables()
        chunk_size = (self._SQLITE_MAX_VARIABLE_NUMBER - 1) // 2
        c=0
        with self.db.atomic():
            for idx in range(0, len(tracks), chunk_size):
                c += self.table_track.select().where(self.table_track.id << tracks[idx:idx + chunk_size]).count()
        if c != len(set(tracks)):
            raise TrackDoesNotExist("One or more tracks from the list {0} does not exist.".format(tracks))

    def _processesTypeNameField(self, types, modes):
        mode_list = []
        for mode in modes:
            mode_list.append(getattr(self, mode))

        def CheckType(type):
            if isinstance(type, basestring):
                type_name = type
                type = self.getMarkerType(type)
                if type is None:
                    raise MarkerTypeDoesNotExist("No marker type with the name \"%s\" exists." % type_name)

            if type is not None and type.mode not in mode_list:
                raise ValueError("Marker type \"%s\" is not a marker type with mode (allowed modes here: %s)" % (type.name, ", ".join(modes)))
            return type

        if isinstance(types, (tuple, list)):
            types = [CheckType(type) for type in types]
        else:
            types = CheckType(types)
        return types

    def _processLayerNameField(self, layers):
        def CheckLayer(layer):
            if isinstance(layer, basestring):
                layer_entry = self.getLayer(layer)
                if layer_entry is None:
                    raise peewee.DoesNotExist("Layer with name \"%s\" does not exist" % layer)
                return layer_entry
            return layer

        if isinstance(layers, (tuple, list)):
            layers = [CheckLayer(layer) for layer in layers]
        else:
            layers = CheckLayer(layers)
        return layers

    def _processPathNameField(self, paths):
        def CheckPath(path):
            if isinstance(path, basestring):
                return self.getPath(path)
            return path

        if isinstance(paths, (tuple, list)):
            paths = [CheckPath(path) for path in paths]
        else:
            paths = CheckPath(paths)
        return paths

    def _processImagesField(self, images, frames, filenames, layer):
        if images is not None:
            if not isinstance(frames, (tuple, list)):
                # if a number is provided, than it is the id of an image in the database
                if isinstance(images, int):
                    return self.getImage(id=images)
                # if not, it should be an image entry object
                return self.getImage(frame=images.sort_index, layer=images.layer.base_layer)
            new_images = []
            for image in images:
                new_images.append(self.getImage(frame=image.sort_index, layer=image.layer.base_layer))
            return new_images

        def CheckImageFrame(frame, layer):
            image = self.getImage(frame=frame, layer=layer)
            if image is None:
                raise ImageDoesNotExist("No image with the frame number %s exists." % frame)
            return image

        def CheckImageFilename(filename):
            image = self.getImage(filename=filename)
            if image is None:
                raise ImageDoesNotExist("No image with the filename \"%s\" exists." % filename)
            return image

        if frames is not None:
            if isinstance(frames, (tuple, list)):
                images = [CheckImageFrame(frame, layer) for frame in frames]
            else:
                images = CheckImageFrame(frames, layer)
        elif filenames is not None:
            if isinstance(filenames, (tuple, list)):
                images = [CheckImageFilename(filename) for filename in filenames]
            else:
                images = CheckImageFilename(filenames)
        return images

    def getDbVersion(self):
        """
        Returns the version of the currently opened database file.

        Returns
        -------
        version : string
            the version of the database

        """
        return self._current_version

    def getPath(self, path_string=None, id=None, create=False):
        """
        Get a :py:class:`Path` entry from the database.

        See also: :py:meth:`~.DataFile.getPaths`, :py:meth:`~.DataFile.setPath`, :py:meth:`~.DataFile.deletePaths`

        Parameters
        ----------
        path_string: string, optional
            the string specifying the path.
        id: int, optional
            the id of the path.
        create: bool, optional
            whether the path should be created if it does not exist. (default: False)

        Returns
        -------
        path : :py:class:`Path`
            the created/requested :py:class:`Path` entry.
        """
        # check input
        assert any(e is not None for e in [id, path_string]), "Path and ID may not be both None"

        # collect arguments
        kwargs = {}
        # normalize the path, making it relative to the database file
        if path_string is not None:
            if self._database_filename:
                try:
                    path_string = os.path.relpath(path_string, os.path.dirname(self._database_filename))
                except ValueError:
                    path_string = os.path.abspath(path_string)
            path_string = os.path.normpath(path_string)
            kwargs["path"] = path_string
        # add the id
        if id:
            kwargs["id"] = id

        # try to get the path
        try:
            path = self.table_path.get(**kwargs)
        # if not create it
        except peewee.DoesNotExist as err:
            if create:
                path = self.table_path(**kwargs)
                path.save()
            else:
                return None
        # return the path
        return path

    def getPaths(self, path_string=None, base_path=None, id=None):
        """
        Get all :py:class:`Path` entries from the database, which match the given criteria. If no critera a given, return all paths.

        See also: :py:meth:`~.DataFile.getPath`, :py:meth:`~.DataFile.setPath`, :py:meth:`~.DataFile.deletePaths`

        Parameters
        ----------
        path_string : string, path_string, optional
            the string/s specifying the path/s.
        base_path : string, optional
            return only paths starting with the base_path string.
        id: int, array_like, optional
            the id/s of the path/s.

        Returns
        -------
        entries : array_like
            a query object containing all the matching :py:class:`Path` entries in the database file.
        """

        query = self.table_path.select()

        query = addFilter(query, id, self.table_path.id)
        query = addFilter(query, path_string, self.table_path.path)
        if base_path is not None:
            query = query.where(self.table_path.path.startswith(base_path))

        return query

    def setPath(self, path_string=None, id=None):
        """
        Update or create a new :py:class:`Path` entry with the given parameters.

        See also: :py:meth:`~.DataFile.getPath`, :py:meth:`~.DataFile.getPaths`, :py:meth:`~.DataFile.deletePaths`

        Parameters
        ----------
        path_string: string, optional
            the string specifying the path.
        id: int, optional
            the id of the paths.

        Returns
        -------
        entries : :py:class:`Path`
            the changed or created :py:class:`Path` entry.
        """

        try:
            path = self.table_path.get(**noNoneDict(id=id, path=path_string))
        except peewee.DoesNotExist:
            path = self.table_path()

        setFields(path, dict(path=path_string))
        path.save()

        return path

    def deletePaths(self, path_string=None, base_path=None, id=None):
        """
        Delete all :py:class:`Path` entries with the given criteria.

        See also: :py:meth:`~.DataFile.getPath`, :py:meth:`~.DataFile.getPaths`, :py:meth:`~.DataFile.setPath`

        Parameters
        ----------
        path_string: string, optional
            the string/s specifying the paths.
        base_path: string, optional
            return only paths starting with the base_path string.
        id: int, optional
            the id/s of the paths.

        Returns
        -------
        rows : int
            the number of affected rows.
        """

        query = self.table_path.delete()

        query = addFilter(query, id, self.table_path.id)
        query = addFilter(query, path_string, self.table_path.path)
        if base_path is not None:
            query = query.where(self.table_path.path.startswith(base_path))
        return query.execute()

    def getLayer(self, layer_name=None, base_layer=None, id=None, create=False):
        """
        Get a :py:class:`Layer` entry from the database.

        See also: :py:meth:`~.DataFile.getLayers`, :py:meth:`~.DataFile.setLayer`, :py:meth:`~.DataFile.deleteLayers`

        Parameters
        ----------
        layer_name: string, optional
            the string specifying the layers name.
        base_layer : int, :py:class:`Layer`, optional
            the base layer to which this layer should reference.
        id: int, optional
            the id of the layer.
        create: bool, optional
            whether the layer should be created if it does not exist. (default: False)

        Returns
        -------
        path : :py:class:`Layer`
            the created/requested :py:class:`Layer` entry.
        """
        # check input
        assert any(e is not None for e in [id, layer_name]), "Name and ID may not be both None"

        # collect arguments
        kwargs = {}
        # normalize the path, making it relative to the database file
        if layer_name is not None:
            kwargs["name"] = layer_name
        # add the id
        if id:
            kwargs["id"] = id
        if base_layer is not None:
            kwargs["base_layer"] = base_layer

        # try to get the path
        try:
            layer = self.table_layer.get(**kwargs)
        # if not create it
        except peewee.DoesNotExist as err:
            if create:
                layer = self.table_layer(**kwargs)
                # if the base_layer is None, we want to create a self-referential entry, but as we don't know the id
                # of the new entry, we have to assign it later. So for now we just guess a valid id for a base_layer
                # reference
                if base_layer is None:
                    # it is not possible to
                    try_base_layer_id = 1
                    while True:
                        try:
                            layer.base_layer = try_base_layer_id
                        except peewee.IntegrityError:
                            pass
                        else:
                            break
                        try_base_layer_id += 1
                layer.save()
                # now the layer has been created and we can assign the self reference
                if base_layer is None:
                    layer.base_layer = layer
                    layer.save()
            else:
                return None
        # return the path
        return layer

    def getLayers(self, layer_name=None, base_layer=None, id=None):
        """
        Get all :py:class:`Layer` entries from the database, which match the given criteria. If no critera a given, return all layers.

        See also: :py:meth:`~.DataFile.getLayer`, :py:meth:`~.DataFile.setLayer`, :py:meth:`~.DataFile.deleteLayers`

        Parameters
        ----------
        layer_name : string, optional
            the string/s specifying the layer name/s.
        base_layer : int, :py:class:`Layer`, optional
            the base layer to which this layer should reference.
        id: int, array_like, optional
            the id/s of the layer/s.

        Returns
        -------
        entries : array_like
            a query object containing all the matching :py:class:`Layer` entries in the database file.
        """

        query = self.table_layer.select()

        query = addFilter(query, id, self.table_layer.id)
        query = addFilter(query, layer_name, self.table_layer.name)
        query = addFilter(query, base_layer, self.table_layer.base_layer)

        return query

    def setLayer(self, layer_name=None, base_layer=None, id=None):
        """
        Update or create a new :py:class:`Layer` entry with the given parameters.

        See also: :py:meth:`~.DataFile.getLayer`, :py:meth:`~.DataFile.getLayers`, :py:meth:`~.DataFile.deleteLayers`

        Parameters
        ----------
        layer_name: string, optional
            the string specifying the name of the layer.
        base_layer: int, :py:class:`Layer`, optional
            the base layer to which this layer should reference.
        id: int, optional
            the id of the layers.

        Returns
        -------
        entries : :py:class:`Layer`
            the changed or created :py:class:`Layer` entry.
        """

        base_layer = self._processLayerNameField(base_layer)

        try:
            layer = self.table_layer.get(**noNoneDict(id=id, name=layer_name, base_layer=base_layer))
        except peewee.DoesNotExist:
            return self.getLayer(layer_name=layer_name, base_layer=base_layer, id=id, create=True)

        setFields(layer, dict(name=layer_name, base_layer=base_layer))
        layer.save()

        return layer

    def deleteLayers(self, layer_name=None, base_layer=None, id=None):
        """
        Delete all :py:class:`Layer` entries with the given criteria.

        See also: :py:meth:`~.DataFile.getLayer`, :py:meth:`~.DataFile.getLayers`, :py:meth:`~.DataFile.setLayer`

        Parameters
        ----------
        layer_name: string, optional
            the string/s specifying the name/s of the layer/s.
        base_layer: int, :py:class:`Layer`, optional
            the base layer to which this layer should reference.
        id: int, optional
            the id/s of the layers.

        Returns
        -------
        rows : int
            the number of affected rows.
        """

        query = self.table_layer.delete()

        query = addFilter(query, id, self.table_layer.id)
        query = addFilter(query, layer_name, self.table_layer.name)
        query = addFilter(query, base_layer, self.table_layer.base_layer)

        return query.execute()

    def getImageCount(self):
        """
        Returns the number of images in the database.
        
        Returns
        -------
        count : int
            the number of images.
        """
        return self.db.execute_sql("SELECT MAX(sort_index) FROM image LIMIT 1;").fetchone()[0] + 1

    def getImage(self, frame=None, filename=None, id=None, layer=None):
        """
        Returns the :py:class:`Image` entry with the given frame number and layer.

        See also: :py:meth:`~.DataFile.getImages`, :py:meth:`~.DataFile.getImageIterator`, :py:meth:`~.DataFile.setImage`,
        :py:meth:`~.DataFile.deleteImages`.

        Parameters
        ----------
        frame : int, optional
            the frame number of the desired image, as displayed in ClickPoints.
        filename : string, optional
            the filename of the desired image.
        id : int, optional
            the id of the image.
        layer : int, string, optional
            the layer_id or name of the layer of the image.

        Returns
        -------
        image : :py:class:`Image`
            the image entry.
        """

        layer = self._processLayerNameField(layer)

        kwargs = noNoneDict(sort_index=frame, filename=filename, id=id, layer=layer)
        try:
            return self.table_image.get(**kwargs)
        except peewee.DoesNotExist:
            KeyError("No image with %s found." % VerboseDict(kwargs))

    def getImages(self, frame=None, filename=None, ext=None, external_id=None, timestamp=None, width=None, height=None, path=None, layer=None, order_by="sort_index"):
        """
        Get all :py:class:`Image` entries sorted by sort index. For large databases
        :py:meth:`~.DataFile.getImageIterator`, should be used as it doesn't load all frames at once.

        See also: :py:meth:`~.DataFile.getImage`, :py:meth:`~.DataFile.getImageIterator`, :py:meth:`~.DataFile.setImage`,
        :py:meth:`~.DataFile.deleteImages`.

        Parameters
        ----------
        frame : int, array_like, optional
            the frame number/s of the image/s as displayed in ClickPoints (sort_index in the database).
        filename : string, array_like, optional
            the filename/s of the image/s.
        ext : string, array_like, optional
            the extension/s of the image/s.
        external_id : int, array_like, optional
            the external id/s of the image/s.
        timestamp : datetime, array_like, optional
            the timestamp/s of the image/s.
        width : int, array_like, optional
            the width/s of the image/s.
        height : int, array_like, optional
            the height/s of the image/s
        path : int, :py:class:`Path`, array_like, optional
            the path/s (or path id/s) of the image/s
        layer : int, string, array_like, optional
            the layer/s of the image/s
        order_by : string, optional
            sort by either 'sort_index' (default) or 'timestamp'.

        Returns
        -------
        entries : array_like
            a query object containing all the :py:class:`Image` entries in the database file.
        """

        layer = self._processLayerNameField(layer)

        query = self.table_image.select()

        query = addFilter(query, frame, self.table_image.sort_index)
        query = addFilter(query, filename, self.table_image.filename)
        query = addFilter(query, ext, self.table_image.ext)
        query = addFilter(query, external_id, self.table_image.external_id)
        query = addFilter(query, timestamp, self.table_image.timestamp)
        query = addFilter(query, width, self.table_image.width)
        query = addFilter(query, height, self.table_image.height)
        query = addFilter(query, path, self.table_image.path)
        query = addFilter(query, layer, self.table_image.layer)

        if order_by == "sort_index":
            query = query.order_by(self.table_image.sort_index)
        elif order_by == "timestamp":
            query = query.order_by(self.table_image.timestamp)
        else:
            raise Exception("Unknown order_by parameter - use sort_index or timestamp")

        return query

    def getImageIterator(self, start_frame=0, end_frame=None, skip=1, layer=1):
        """
        Get an iterator to iterate over all :py:class:`Image` entries starting from start_frame.

        See also: :py:meth:`~.DataFile.getImage`, :py:meth:`~.DataFile.getImages`, :py:meth:`~.DataFile.setImage`,  :py:meth:`~.DataFile.deleteImages`.

        Parameters
        ----------
        start_frame : int, optional
            start at the image with the number start_frame. Default is 0
        end_frame : int, optional
            the last frame of the iteration (excluded). Default is None, the iteration stops when no more images are present.
        skip : int, optional
            how many frames to jump. Default is 1
        layer : int, string, optional
            layer of frames, over which should be iterated.

        Returns
        -------
        image_iterator : iterator
            an iterator object to iterate over :py:class:`Image` entries.

        Examples
        --------
        .. code-block:: python
            :linenos:

            import clickpoints

            # open the database "data.cdb"
            db = clickpoints.DataFile("data.cdb")

            # iterate over all images and print the filename
            for image in db.GetImageIterator():
                print(image.filename)
        """

        layer = self._processLayerNameField(layer)

        frame = start_frame
        while True:
            if frame == end_frame:
                break
            try:
                image = self.table_image.get(self.table_image.sort_index == frame, self.table_image.layer == layer)
                yield image
            except peewee.DoesNotExist:
                break
            frame += skip

    def setImage(self, filename=None, path=None, frame=None, external_id=None, timestamp=None, width=None, height=None, id=None, layer="default", sort_index=None):

        """
        Update or create new :py:class:`Image` entry with the given parameters.

        See also: :py:meth:`~.DataFile.getImage`, :py:meth:`~.DataFile.getImages`, :py:meth:`~.DataFile.getImageIterator`, :py:meth:`~.DataFile.deleteImages`.

        Parameters
        ----------
        filename : string, optional
            the filename of the image (including the extension)
        path : string, int, :py:class:`Path`, optional
            the path string, id or entry of the image to insert
        frame : int, optional
            the frame number if the image is part of a video
        external_id : int, optional
            an external id for the image. Only necessary if the annotation server is used
        timestamp : datetime object, optional
            the timestamp of the image
        width : int, optional
            the width of the image
        height : int, optional
            the height of the image
        id : int, optional
            the id of the image
        layer : int, string, optional
            the layer_id of the image, always use with sort_index
        sort_index: int, only use with layer
            the sort index (position in the time line) if not in layer 0

        Returns
        -------
        image : :py:class:`Image`
            the changed or created :py:class:`Image` entry
        """
        try:
            item = self.table_image.get(id=id, filename=filename)
            new_image = False
        except peewee.DoesNotExist:
            item = self.table_image()
            new_image = True

        if isinstance(layer, basestring):
            layer = self.getLayer(layer, create=True)

        if filename is not None:
            item.filename = os.path.split(filename)[1]
            item.ext = os.path.splitext(filename)[1]
            if path is None:
                item.path = self.getPath(path_string=os.path.split(filename)[0], create=True)
        if isinstance(path, basestring):
            path = self.getPath(path)
        setFields(item, noNoneDict(frame=frame, path=path, external_id=external_id, timestamp=timestamp, width=width, height=height, layer=layer, sort_index=sort_index))
        if new_image:
            if sort_index is None:
                if self._next_sort_index is None:
                    try:
                        self._next_sort_index = self.db.execute_sql("SELECT MAX(sort_index) FROM image LIMIT 1;").fetchone()[0] + 1
                    except IndexError:
                        self._next_sort_index = 0
                item.sort_index = self._next_sort_index
                self._next_sort_index += 1
        item.save()
        return item

    def deleteImages(self, filename=None, path=None, frame=None, external_id=None, timestamp=None, width=None, height=None, id=None, layer=None):
        """
        Delete all :py:class:`Image` entries with the given criteria.

        See also: :py:meth:`~.DataFile.getImage`, :py:meth:`~.DataFile.getImages`, :py:meth:`~.DataFile.getImageIterator`, :py:meth:`~.DataFile.setImage`.

        Parameters
        ----------
        filename : string, array_like, optional
            the filename/filenames of the image (including the extension)
        path : string, int, :py:class:`Path`, array_like optional
            the path string, id or entry of the image to insert
        frame : int, array_like, optional
            the number/numbers of frames the images have
        external_id : int, array_like, optional
            an external id/ids for the images. Only necessary if the annotation server is used
        timestamp : datetime object, array_like, optional
            the timestamp/timestamps of the images
        width : int, array_like, optional
            the width/widths of the images
        height : int, optional
            the height/heights of the images
        id : int, array_like, optional
            the id/ids of the images
        layer: int, array_like, optional
            the layer/layers of the images

        Returns
        -------
        rows : int
            the number of affected rows.
        """
        query = self.table_image.delete()

        layer = self._processLayerNameField(layer)
        path = self._processPathNameField(path)

        query = addFilter(query, id, self.table_image.id)
        query = addFilter(query, path, self.table_image.path)
        query = addFilter(query, filename, self.table_image.filename)
        query = addFilter(query, frame, self.table_image.frame)
        query = addFilter(query, external_id, self.table_image.external_id)
        query = addFilter(query, timestamp, self.table_image.timestamp)
        query = addFilter(query, width, self.table_image.width)
        query = addFilter(query, height, self.table_image.height)
        query = addFilter(query, layer, self.table_image.layer)
        return query.execute()

    def getTracks(self, type=None, text=None, hidden=None, id=None):
        """
        Get all :py:class:`Track` entries, optional filter by type

        See also: :py:meth:`~.DataFile.getTrack`, :py:meth:`~.DataFile.setTrack`, :py:meth:`~.DataFile.deleteTracks`, :py:meth:`~.DataFile.getTracksNanPadded`.

        Parameters
        ----------
        type: :py:class:`MarkerType`, str, array_like, optional
            the marker type/types or name of the marker type for the track.
        text : str, array_like, optional
            the :py:class:`Track` specific text entry
        hidden : bool, array_like, optional
            whether the tracks should be displayed in ClickPoints
        id : int, array_like, optional
            the  :py:class:`Track` ID

        Returns
        -------
        entries : array_like
            a query object which contains the requested :py:class:`Track`.
        """
        type = self._processesTypeNameField(type, ["TYPE_Track"])

        query = self.table_track.select()
        query = addFilter(query, type, self.table_track.type)
        query = addFilter(query, text, self.table_track.text)
        query = addFilter(query, hidden, self.table_track.hidden)
        query = addFilter(query, id, self.table_track.id)

        return query

    def getTrack(self, id):
        """
        Get a specific :py:class:`Track` entry by its database ID.

        See also: :py:meth:`~.DataFile.getTracks`, :py:meth:`~.DataFile.deleteTracks`, :py:meth:`~.DataFile.getTracksNanPadded`.

        Parameters
        ----------
        id: int
            id of the track

        Returns
        -------
        entries : :py:class:`Track`
            requested object of class :py:class:`Track` or None
        """
        try:
            return self.table_track.get(id=id)
        except peewee.DoesNotExist:
            return None

    def setTrack(self, type, style=None, text=None, hidden=None, id=None, uid=None):
        """
        Insert or update a :py:class:`Track` object.

        See also: :py:meth:`~.DataFile.getTrack`, :py:meth:`~.DataFile.getTracks`, :py:meth:`~.DataFile.deleteTracks`, :py:meth:`~.DataFile.getTracksNanPadded`.


        Parameters
        ----------
        type: :py:class:`MarkerType`, str
            the marker type or name of the marker type for the track.
        style:
            the :py:class:`Track` specific style entry
        text :
            the :py:class:`Track` specific text entry
        hidden :
            wether the track should be displayed in ClickPoints
        id : int, array_like
            the  :py:class:`Track` ID


        Returns
        -------
        track : track object
            a new :py:class:`Track` object
        """
        type = self._processesTypeNameField(type, ["TYPE_Track"])

        # gather all the parameters that are not none
        parameters = locals()
        parameters = {key: parameters[key] for key in ["id", "type", "style", "text", "hidden"] if parameters[key] is not None}
        # insert and item with the given parameters
        item = self.table_track.replace(**parameters).execute()
        item = self.table_track.get(id=item)

        return item

    def deleteTracks(self, type=None, text=None, hidden=None, id=None):
        """
        Delete a single :py:class:`Track` object specified by id or all :py:class:`Track` object of an type

        See also: :py:meth:`~.DataFile.getTrack`, :py:meth:`~.DataFile.getTracks`, :py:meth:`~.DataFile.setTrack`, :py:meth:`~.DataFile.getTracksNanPadded`.

        Parameters
        ----------
        type: :py:class:`MarkerType`, str, array_like, optional
            the marker type or name of the marker type
        text : str, array_like, optional
            the :py:class:`Track` specific text entry
        hidden : bool, array_like, optional
            whether the tracks should be displayed in ClickPoints
        id : int, array_like, array_like, optional
            the  :py:class:`Track` ID

        Returns
        -------
        rows : int
            the number of affected rows.
        """

        type = self._processesTypeNameField(type, ["TYPE_Track"])

        query = self.table_track.delete()
        query = addFilter(query, id, self.table_track.id)
        query = addFilter(query, text, self.table_track.text)
        query = addFilter(query, hidden, self.table_track.hidden)
        query = addFilter(query, type, self.table_track.type)
        return query.execute()

    def getMarkerTypes(self, name=None, color=None, mode=None, text=None, hidden=None, id=None):
        """
        Retreive all :py:class:`MarkerType` objects in the database.

        See also: :py:meth:`~.DataFile.getMarkerType`, :py:meth:`~.DataFile.setMarkerType`, :py:meth:`~.DataFile.deleteMarkerTypes`.

        Parameters
        ----------
        name: str, array_like, optional
            the name of the type
        color: str, array_like, optional
            hex code string for rgb color of style "#00ff3f"
        mode: int, array_like, optional
            mode of the marker type (marker 0, rect 1, line 2, track 4)
        text: str, array_like, optional
            display text
        hidden: bool, array_like, optional
            whether the types should be displayed in ClickPoints
        id: int, array_like, optional
            id of the :py:class:`MarkerType` object

        Returns
        -------
        entries : array_like
            a query object which contains all :py:class:`MarkerType` entries.
        """
        query = self.table_markertype.select()

        query = addFilter(query, name, self.table_markertype.name)
        query = addFilter(query, color, self.table_markertype.color)
        query = addFilter(query, mode, self.table_markertype.mode)
        query = addFilter(query, text, self.table_markertype.text)
        query = addFilter(query, hidden, self.table_markertype.hidden)
        query = addFilter(query, id, self.table_markertype.id)

        return query

    def getMarkerType(self, name=None, id=None):
        """
        Retrieve an :py:class:`MarkerType` object from the database.

        See also: :py:meth:`~.DataFile.getMarkerTypes`, :py:meth:`~.DataFile.setMarkerType`, :py:meth:`~.DataFile.deleteMarkerTypes`.

        Parameters
        ----------
        name: str, optional
            the name of the desired type
        id: int, optional
            id of the :py:class:`MarkerType` object

        Returns
        -------
        entries : array_like
            the :py:class:`MarkerType` with the desired name or None.
        """
        try:
            return self.table_markertype.get(**noNoneDict(name=name, id=id))
        except peewee.DoesNotExist:
            return None

    def setMarkerType(self, name=None, color=None, mode=None, style=None, text=None, hidden=None, id=None):
        """
        Insert or update an :py:class:`MarkerType` object in the database.

        See also: :py:meth:`~.DataFile.getMarkerType`, :py:meth:`~.DataFile.getMarkerTypes`, :py:meth:`~.DataFile.deleteMarkerTypes`.

        Parameters
        ----------
        name: str, optional
            the name of the type
        color: str, optional
            hex code string for rgb color of style "#00ff3f"
        mode: int, optional
            mode of the marker type (marker 0, rect 1, line 2, track 4)
        style: str, optional
            style string
        text: str, optional
            display text
        hidden: bool, optional
            whether the type should be displayed in ClickPoints
        id: int, optional
            id of the :py:class:`MarkerType` object

        Returns
        -------
        entries : object
            the created :py:class:`MarkerType` with the desired name or None.
        """
        try:
            item = self.table_markertype.get(**noNoneDict(id=id, name=name))
        except peewee.DoesNotExist:
            item = self.table_markertype()

        if color is not None:
            color = CheckValidColor(color)
        setFields(item, dict(name=name, color=color, mode=mode, style=style, text=text, hidden=hidden))
        item.save()
        return item

    def deleteMarkerTypes(self, name=None, color=None, mode=None, text=None, hidden=None, id=None):
        """
        Delete all :py:class:`MarkerType` entries from the database, which match the given criteria.

        See also: :py:meth:`~.DataFile.getMarkerType`, :py:meth:`~.DataFile.getMarkerTypes`, :py:meth:`~.DataFile.setMarkerType`.

        Parameters
        ----------
        name: str, array_like, optional
            the name of the type
        color: str, array_like, optional
            hex code string for rgb color of style "#00ff3f"
        mode: int, array_like, optional
            mode of the marker type (marker 0, rect 1, line 2, track 4)
        text: str, array_like, optional
            display text
        hidden: bool, array_like, optional
            whether the types should be displayed in ClickPoints
        id: int, array_like, optional
            id of the :py:class:`MarkerType` object

        Returns
        -------
        entries : int
            nr of deleted entries
        """
        query = self.table_markertype.delete()

        query = addFilter(query, name, self.table_markertype.name)
        query = addFilter(query, color, self.table_markertype.color)
        query = addFilter(query, mode, self.table_markertype.mode)
        query = addFilter(query, text, self.table_markertype.text)
        query = addFilter(query, hidden, self.table_markertype.hidden)
        query = addFilter(query, id, self.table_markertype.id)

        return query.execute()

    def getMaskType(self, name=None, color=None, index=None, id=None):
        """
        Get a :py:class:`MaskType` from the database.

        See also: :py:meth:`~.DataFile.getMaskTypes`, :py:meth:`~.DataFile.setMaskType`, :py:meth:`~.DataFile.deleteMaskTypes`.

        Parameters
        ----------
        name : string, optional
            the name of the mask type.
        color : string, optional
            the color of the mask type.
        index : int, optional
            the index of the mask type, which is used for painting this mask type.
        id : int, optional
            the id of the mask type.

        Returns
        -------
        entries : :py:class:`MaskType`
            the created/requested :py:class:`MaskType` entry.
        """
        # check input
        assert any(e is not None for e in [id, name, color, index]), "Path, ID, color and index may not be all None"

        if color:
            color = NormalizeColor(color)

        # try to get the path
        try:
            return self.table_masktype.get(**noNoneDict(id=id, name=name, color=color, index=index))
        # if not create it
        except peewee.DoesNotExist:
            return None

    def getMaskTypes(self, name=None, color=None, index=None, id=None):
        """
        Get all :py:class:`MaskType` entries from the database, which match the given criteria. If no criteria a given,
        return all mask types.

        See also: :py:meth:`~.DataFile.getMaskType`, :py:meth:`~.DataFile.setMaskType`,
        :py:meth:`~.DataFile.deleteMaskTypes`.

        Parameters
        ----------
        name : string, array_like, optional
            the name/names of the mask types.
        color : string, array_like, optional
            the color/colors of the mask types.
        index : int, array_like, optional
            the index/indices of the mask types, which is used for painting this mask types.
        id : int, array_like, optional
            the id/ids of the mask types.

        Returns
        -------
        entries : array_like
            a query object containing all the matching :py:class:`MaskType` entries in the database file.
        """

        query = self.table_masktype.select()

        if color:
            color = NormalizeColor(color)

        query = addFilter(query, id, self.table_masktype.id)
        query = addFilter(query, name, self.table_masktype.name)
        query = addFilter(query, color, self.table_masktype.color)
        query = addFilter(query, index, self.table_masktype.index)
        return query

    def setMaskType(self, name=None, color=None, index=None, id=None):
        """
        Update or create a new a :py:class:`MaskType` entry with the given parameters.

        See also: :py:meth:`~.DataFile.getMaskType`, :py:meth:`~.DataFile.getMaskTypes`, :py:meth:`~.DataFile.setMaskType`, :py:meth:`~.DataFile.deleteMaskTypes`.

        Parameters
        ----------
        name : string, optional
            the name of the mask type.
        color : string, optional
            the color of the mask type.
        index : int, optional
            the index of the mask type, which is used for painting this mask type.
        id : int, optional
            the id of the mask type.

        Returns
        -------
        entries : :py:class:`MaskType`
            the changed or created :py:class:`MaskType` entry.
        """

        # normalizer and check color values
        if color:
            color = NormalizeColor(color)

        # get lowest free index is not specified by user
        if not index:
            index_list = [l.index for l in self.table_masktype.select().order_by(self.table_masktype.index)]
            free_idxs = list(set(range(1, 254)) - set(index_list))
            new_index = free_idxs[0]
        else:
            new_index = index

        try:
            # only use id if multiple unique fields are specified
            if id:
                mask_type = self.table_masktype.get(id=id)
            elif name:
                mask_type = self.table_masktype.get(name=name)
            else:
                raise peewee.DoesNotExist
            # if no desired index is provided keep the existing index
            if index is None or mask_type.index is not None:
                new_index = mask_type.index
        except peewee.DoesNotExist:
            mask_type = self.table_masktype()

        setFields(mask_type, dict(name=name, color=color, index=new_index))
        mask_type.save()

        return mask_type

    def deleteMaskTypes(self, name=None, color=None, index=None, id=None):
        """
        Delete all :py:class:`MaskType` entries from the database, which match the given criteria.

        See also: :py:meth:`~.DataFile.getMaskType`, :py:meth:`~.DataFile.getMaskTypes`, :py:meth:`~.DataFile.setMaskType`.

        Parameters
        ----------
        name : string, array_like, optional
            the name/names of the mask types.
        color : string, array_like, optional
            the color/colors of the mask types.
        index : int, array_like, optional
            the index/indices of the mask types, which is used for painting this mask types.
        id : int, array_like, optional
            the id/ids of the mask types.
        """

        query = self.table_masktype.delete()

        # normalize and check color values
        if color:
            color = NormalizeColor(color)

        query = addFilter(query, id, self.table_masktype.id)
        query = addFilter(query, name, self.table_masktype.name)
        query = addFilter(query, color, self.table_masktype.color)
        query = addFilter(query, index, self.table_masktype.index)
        query.execute()

    """ Masks """

    def getMask(self, image=None, frame=None, filename=None, id=None, layer=None, create=False):
        """
        Get the :py:class:`Mask` entry for the given image frame number or filename.

        See also: :py:meth:`~.DataFile.getMasks`, :py:meth:`~.DataFile.setMask`, :py:meth:`~.DataFile.deleteMasks`.

        Parameters
        ----------
        image : int, :py:class:`Image`, optional
            the image for which the mask should be retrieved. If omitted, frame number or filename should be specified instead.
        frame : int, optional
            frame number of the image, which mask should be returned. If omitted, image or filename should be specified instead.
        filename : string, optional
            filename of the image, which mask should be returned. If omitted, image or frame number should be specified instead.
        id : int, optional
            id of the mask entry.
        create : bool, optional
            whether the mask should be created if it does not exist. (default: False)
        layer: int, optional
            layer of the image, which mask should be returned. Always use with frame.

        Returns
        -------
        mask : :py:class:`Mask`
            the desired :py:class:`Mask` entry.
        """
        # check input
        # assert sum(e is not None for e in [id, image, frame, filename]) == 1, \
        #     "Exactly one of image, frame or filename should be specified or should be referenced by it's id."
        assert sum(e is not None for e in [id, image, frame, filename]) == 1, \
            "Image, frame (with layer) or filename should be specified or should be referenced by it's id."

        image = self._processImagesField(image, frame, filename, layer)

        query = self.table_mask.select(self.table_mask, self.table_image).join(self.table_image)

        query = addFilter(query, id, self.table_mask.id)
        query = addFilter(query, image, self.table_mask.image)
        query = addFilter(query, frame, self.table_image.sort_index)
        query = addFilter(query, filename, self.table_image.filename)
        query = addFilter(query, layer, self.table_image.layer)
        query.limit(1)

        try:
            return query[0]
        except IndexError:
            if create is True:
                if not image:
                    image = self.getImage(frame=frame, filename=filename, layer=layer)
                    if not image:
                        raise ImageDoesNotExist("No parent image found ")
                try:
                    data = np.zeros(image.getShape())
                except IOError:
                    raise MaskDimensionUnknown("Can't retrieve dimensions for mask from image %s " % image.filename)
                mask = self.table_mask(image=image, data=data)
                mask.save()
                return mask
            return None

    def getMasks(self, image=None, frame=None, filename=None, id=None, layer=None, order_by="sort_index"):
        """
        Get all :py:class:`Mask` entries from the database, which match the given criteria. If no criteria a given, return all masks.

        See also: :py:meth:`~.DataFile.getMask`, :py:meth:`~.DataFile.setMask`, :py:meth:`~.DataFile.deleteMasks`.

        Parameters
        ----------
        image : int, :py:class:`Image`, array_like, optional
            the image/images for which the mask should be retrieved. If omitted, frame numbers or filenames should be specified instead.
        frame: int, array_like, optional
            frame number/numbers of the images, which masks should be returned. If omitted, images or filenames should be specified instead.
        filename: string, array_like, optional
            filename of the image/images, which masks should be returned. If omitted, images or frame numbers should be specified instead.
        id : int, array_like, optional
            id/ids of the masks.
        layer :  int, optional
            layer of the images, which masks should be returned. Always use with frame.
        order_by: string, optional
            sorts the result according to sort paramter ('sort_index' or 'timestamp')

        Returns
        -------
        entries : :py:class:`Mask`
            a query object containing all the matching :py:class:`Mask` entries in the database file.
        """
        # check input
        assert sum(e is not None for e in [image, frame, filename]) <= 1, \
            "Exactly one of images, frames or filenames should be specified"

        if layer is not None:
            assert frame is not None, \
                "Frame should be specified, if layer is given."

        image = self._processImagesField(image, frame, filename, layer)

        query = self.table_mask.select(self.table_mask, self.table_image).join(self.table_image)

        query = addFilter(query, id, self.table_mask.id)
        query = addFilter(query, image, self.table_mask.image)
        query = addFilter(query, frame, self.table_image.sort_index)
        query = addFilter(query, filename, self.table_image.filename)
        query = addFilter(query, layer, self.table_image.layer)

        if order_by == "sort_index":
            query = query.order_by(self.table_image.sort_index)
        elif order_by == "timestamp":
            query = query.order_by(self.table_image.timestamp)
        else:
            raise Exception("Unknown order_by parameter - use sort_index or timestamp")

        class QuerySelector(type(query)):
            def __iter__(self):
                return self.iterator()
        query.__class__ = QuerySelector

        return query

    def setMask(self, image=None, frame=None, filename=None, data=None, id=None, layer=None):
        """
        Update or create new :py:class:`Mask` entry with the given parameters.

        See also: :py:meth:`~.DataFile.getMask`, :py:meth:`~.DataFile.getMasks`, :py:meth:`~.DataFile.deleteMasks`.

        Parameters
        ----------
        image : int, :py:class:`Image`, optional
            the image for which the mask should be set. If omitted, frame number or filename should be specified instead.
        frame: int, optional
            frame number of the images, which masks should be set. If omitted, image or filename should be specified instead.
        filename: string, optional
            filename of the image, which masks should be set. If omitted, image or frame number should be specified instead.
        data: ndarray, optional
            the mask data of the mask to set. Must have the same dimensions as the corresponding image, but only
            one channel, and it should be using the data type uint8.
        id : int, optional
            id of the mask entry.
        layer: int, optional
            the layer of the image, which masks should be set. always use with frame.

        Returns
        -------
        mask : :py:class:`Mask`
            the changed or created :py:class:`Mask` entry.
        """
        # check input
        assert sum(e is not None for e in [id, image, frame, filename]) == 1, \
            "Exactly one of image, frame or filename should be specified or an id"
        if layer is not None:
            assert frame is not None, \
                "Frame should be specified, if layer is given."

        image = self._processImagesField(image, frame, filename, layer)

        mask = self.getMask(image=image, filename=filename, id=id)

        # get image object
        if not image:
            image = self.getImage(frame=frame, filename=filename, layer=layer)
            if not image:
                raise ImageDoesNotExist("No matching parent image found (%s)" % filename)


        # verify data
        if data is not None:
            if not data.dtype == np.uint8:
                raise MaskDtypeMismatch("mask.data dtype is not of type uint8")
            try:
                if not tuple(data.shape) == image.getShape():
                    raise MaskDimensionMismatch("mask.data shape doesn't match image dimensions!")
            except IOError:
                UserWarning("Couldn't retrieve image dimension - shape verification not possible ")

        # create mask element
        if not mask:
            # create and verify data
            if data is None:
                try:
                    data = np.zeros(image.getShape())
                except IOError:
                    raise MaskDimensionUnknown("Can't retreive dimensions for mask from image %s " % image.filename)
            else:
                if not data.dtype == np.uint8:
                    raise MaskDtypeMismatch("mask.data dtype is not of type uint8")
                try:
                    if not tuple(data.shape) == image.getShape():
                        raise MaskDimensionMismatch("mask.data shape doesn't match image dimensions!")
                except IOError:
                    UserWarning("Couldn't retrieve image dimension - shape verification not possible ")
            mask = self.table_mask(image=image, data=data)

        setFields(mask, dict(data=data, image=image))
        if frame is not None or filename is not None:
            mask.image = self.getImage(frame=frame, filename=filename, layer=layer)
        mask.save()

        return mask

    def deleteMasks(self, image=None, frame=None, filename=None, id=None, layer=None):
        """
        Delete all :py:class:`Mask` entries with the given criteria.

        See also: :py:meth:`~.DataFile.getMask`, :py:meth:`~.DataFile.getMasks`, :py:meth:`~.DataFile.setMask`.

        Parameters
        ----------
        image : int, :py:class:`Image`, array_like, optional
            the image/images for which the mask should be deleted. If omitted, frame numbers or filenames should be specified instead.
        frame: int, array_like, optional
            frame number/numbers of the images, which masks should be deleted. If omitted, images or filenames should be specified instead.
        filename: string, array_like, optional
            filename of the image/images, which masks should be deleted. If omitted, images or frame numbers should be specified instead.
        id : int, array_like, optional
            id/ids of the masks.
        layer: int, array_like, optional
            layer/layers of the images, which masks should be deleted. Always use with frame!
        """
        # check input
        assert sum(e is not None for e in [image, frame, filename]) <= 1, \
            "Exactly one of images, frames or filenames should be specified"

        if layer is not None:
            assert frame is not None, \
                "Frame should be specified, if layer is given."

        query = self.table_mask.delete()

        if image is None:
            images = self.table_image.select()
            images = addFilter(images, frame, self.table_image.sort_index)
            images = addFilter(images, filename, self.table_image.filename)
            images = addFilter(images, layer, self.table_image.layer)
            query = query.where(self.table_mask.image.in_(images))
        else:
            query = addFilter(query, image, self.table_mask.image)

        query = addFilter(query, id, self.table_mask.id)
        query.execute()

    """ Markers """

    def getMarker(self, id):
        """
        Retrieve an :py:class:`Marker` object from the database.

        See also: :py:meth:`~.DataFile.getMarkers`, :py:meth:`~.DataFile.setMarker`, :py:meth:`~.DataFile.setMarkers`,
        :py:meth:`~.DataFile.deleteMarkers`.

        Parameters
        ----------
        id: int
            the id of the marker

        Returns
        -------
        marker : :py:class:`Marker`
            the :py:class:`Marker` with the desired id or None.
        """
        try:
            return self.table_marker.get(id=id)
        except peewee.DoesNotExist:
            return None

    def getMarkers(self, image=None, frame=None, filename=None, x=None, y=None, type=None, processed=None, track=None, text=None, id=None, layer=None):
        """
        Get all :py:class:`Marker` entries with the given criteria.

        See also: :py:meth:`~.DataFile.getMarker`, :py:meth:`~.DataFile.getMarkers`, :py:meth:`~.DataFile.setMarker`, :py:meth:`~.DataFile.setMarkers`, :py:meth:`~.DataFile.deleteMarkers`.

        Parameters
        ----------
        image : int, :py:class:`Image`, array_like, optional
            the image/s of the markers.
        frame : int, array_like, optional
            the frame/s of the images of the markers.
        filename : string, array_like, optional
            the filename/s of the images of the markers.
        x : int, array_like, optional
            the x coordinate/s of the markers.
        y : int, array_like, optional
            the y coordinate/s of the markers.
        type : string, :py:class:`MarkerType`, array_like, optional
            the marker type/s (or name/s) of the markers.
        processed : int, array_like, optional
            the processed flag/s of the markers.
        track : int, :py:class:`Track`, array_like, optional
            the track id/s or instance/s of the markers.
        text : string, array_like, optional
            the text/s of the markers.
        id : int, array_like, optional
            the id/s of the markers.
        layer : int, optional
            the layer of the markers

        Returns
        -------
        entries : array_like
            a query object which contains all :py:class:`Marker` entries.
        """
        type = self._processesTypeNameField(type, ["TYPE_Normal", "TYPE_Track"])

        query = self.table_marker.select(self.table_marker, self.table_image).join(self.table_image)

        image = self._processImagesField(image, frame, filename, layer)

        query = addFilter(query, id, self.table_marker.id)
        query = addFilter(query, image, self.table_marker.image)
        query = addFilter(query, frame, self.table_image.sort_index)
        query = addFilter(query, layer, self.table_image.layer)
        query = addFilter(query, filename, self.table_image.filename)
        query = addFilter(query, x, self.table_marker.x)
        query = addFilter(query, y, self.table_marker.y)
        query = addFilter(query, type, self.table_marker.type)
        query = addFilter(query, processed, self.table_marker.processed)
        query = addFilter(query, track, self.table_marker.track)
        query = addFilter(query, text, self.table_marker.text)

        # define the __array__ method of the query to make np.array(db.getMarkers()) possible
        query.__array__ = lambda: np.array([p.pos() for p in query])

        return query

    def setMarker(self, image=None, frame=None, filename=None, x=None, y=None, type=None, processed=None, track=None, style=None, text=None, id=None, layer=None):
        """
        Insert or update an :py:class:`Marker` object in the database.

        See also: :py:meth:`~.DataFile.getMarker`, :py:meth:`~.DataFile.getMarkers`, :py:meth:`~.DataFile.setMarkers`,
        :py:meth:`~.DataFile.deleteMarkers`.

        Parameters
        ----------
        image : int, :py:class:`Image`, optional
            the image of the marker.
        frame : int, optional
            the frame of the images of the marker.
        filename : string, optional
            the filename of the image of the marker.
        x : int, optional
            the x coordinate of the marker.
        y : int, optional
            the y coordinate of the marker.
        type : string, :py:class:`MarkerType`, optional
            the marker type (or name) of the marker.
        processed : int, optional
            the processed flag of the marker.
        track : int, :py:class:`Track`, optional
            the track id or instance of the marker.
        text : string, optional
            the text of the marker.
        id : int, optional
            the id of the marker.
        layer: int, optional
            the layer of the image of the marker

        Returns
        -------
        marker : :py:class:`Marker`
            the created or changed :py:class:`Marker` item.
        """
        assert not (id is None and type is None and track is None), "Marker must either have a type or a track or be referenced by it's id."
        assert not (id is None and image is None and frame is None and filename is None), "Marker must have an image, frame or filename given or be referenced by it's id."

        try:
            item = self.table_marker.get(id=id)
        except peewee.DoesNotExist:
            item = self.table_marker()

        type = self._processesTypeNameField(type, ["TYPE_Normal", "TYPE_Track"])
        if track is not None:
            self._checkTrackField(track)
        image = self._processImagesField(image, frame, filename, layer)

        setFields(item, dict(image=image, x=x, y=y, type=type, processed=processed, track=track, style=style, text=text))
        item.save()
        return item

    def setMarkers(self, image=None, frame=None, filename=None, x=None, y=None, type=None, processed=None,
                   track=None, style=None, text=None, id=None, layer=None):
        """
        Insert or update multiple :py:class:`Marker` objects in the database.

        See also: :py:meth:`~.DataFile.getMarker`, :py:meth:`~.DataFile.getMarkers`, :py:meth:`~.DataFile.setMarker`,
        :py:meth:`~.DataFile.deleteMarkers`.

        Parameters
        ----------
        image : int, :py:class:`Image`, array_like, optional
            the image/s of the markers.
        frame : int, array_like, optional
            the frame/s of the images of the markers.
        filename : string, array_like, optional
            the filename/s of the images of the markers.
        x : int, array_like, optional
            the x coordinate/s of the markers.
        y : int, array_like, optional
            the y coordinate/s of the markers.
        type : string, :py:class:`MarkerType`, array_like, optional
            the marker type/s (or name/s) of the markers.
        processed : int, array_like, optional
            the processed flag/s of the markers.
        track : int, :py:class:`Track`, array_like, optional
            the track id/s or instance/s of the markers.
        text : string, array_like, optional
            the text/s of the markers.
        id : int, array_like, optional
            the id/s of the markers.
        layer: int, optional
            the layer of the images

        Returns
        -------
        success : bool
            it the inserting was successful.
        """
        type = self._processesTypeNameField(type, ["TYPE_Normal", "TYPE_Track"])
        if track is not None:
            self._checkTrackField(track)
        image = self._processImagesField(image, frame, filename, layer)

        data = packToDictList(self.table_marker, id=id, image=image, x=x, y=y, processed=processed, type=type, track=track,
                              style=style, text=text)
        return self.saveReplaceMany(self.table_marker, data)

    def deleteMarkers(self, image=None, frame=None, filename=None, x=None, y=None, type=None, processed=None,
                      track=None, text=None, id=None, layer=None):
        """
        Delete all :py:class:`Marker` entries with the given criteria.

        See also: :py:meth:`~.DataFile.getMarker`, :py:meth:`~.DataFile.getMarkers`, :py:meth:`~.DataFile.setMarker`,
        :py:meth:`~.DataFile.setMarkers`.

        Parameters
        ----------
        image : int, :py:class:`Image`, array_like, optional
            the image/s of the markers.
        frame : int, array_like, optional
            the frame/s of the images of the markers.
        filename : string, array_like, optional
            the filename/s of the images of the markers.
        x : int, array_like, optional
            the x coordinate/s of the markers.
        y : int, array_like, optional
            the y coordinate/s of the markers.
        type : string, :py:class:`MarkerType`, array_like, optional
            the marker type/s (or name/s) of the markers.
        processed : int, array_like, optional
            the processed flag/s of the markers.
        track : int, :py:class:`Track`, array_like, optional
            the track id/s or instance/s of the markers.
        text : string, array_like, optional
            the text/s of the markers.
        id : int, array_like, optional
            the id/s of the markers.

        Returns
        -------
        rows : int
            the number of affected rows.
        """
        type = self._processesTypeNameField(type, ["TYPE_Normal", "TYPE_Track"])

        query = self.table_marker.delete()

        image = self._processImagesField(image, frame, filename, layer)

        if image is None and (frame is not None or filename is not None):
            images = self.table_image.select(self.table_image.id)
            images = addFilter(images, frame, self.table_image.sort_index)
            images = addFilter(images, filename, self.table_image.filename)
            query = query.where(self.table_marker.image.in_(images))
        else:
            query = addFilter(query, image, self.table_marker.image)

        query = addFilter(query, id, self.table_marker.id)
        query = addFilter(query, x, self.table_marker.x)
        query = addFilter(query, y, self.table_marker.y)
        query = addFilter(query, type, self.table_marker.type)
        query = addFilter(query, processed, self.table_marker.processed)
        query = addFilter(query, track, self.table_marker.track)
        query = addFilter(query, text, self.table_marker.text)

        return query.execute()

    """ Lines """

    def getLine(self, id):
        """
        Retrieve an :py:class:`Line` object from the database.

        See also: :py:meth:`~.DataFile.getLines`, :py:meth:`~.DataFile.setLine`, :py:meth:`~.DataFile.setLines`,
        :py:meth:`~.DataFile.deleteLines`.

        Parameters
        ----------
        id: int
            the id of the line

        Returns
        -------
        line : :py:class:`Line`
            the :py:class:`Line` with the desired id or None.
        """
        try:
            return self.table_line.get(id=id)
        except peewee.DoesNotExist:
            return None

    def getLines(self, image=None, frame=None, filename=None, x1=None, y1=None, x2=None, y2=None, type=None,
                 processed=None, text=None, id=None):
        """
        Get all :py:class:`Line` entries with the given criteria.

        See also: :py:meth:`~.DataFile.getLine`, :py:meth:`~.DataFile.setLine`, :py:meth:`~.DataFile.setLines`,
        :py:meth:`~.DataFile.deleteLines`.

        Parameters
        ----------
        image : int, :py:class:`Image`, array_like, optional
            the image/s of the lines.
        frame : int, array_like, optional
            the frame/s of the images of the lines.
        filename : string, array_like, optional
            the filename/s of the images of the lines.
        x1 : int, array_like, optional
            the x coordinate/s of the lines start.
        y1 : int, array_like, optional
            the y coordinate/s of the lines start.
        x2 : int, array_like, optional
            the x coordinate/s of the lines end.
        y2 : int, array_like, optional
            the y coordinate/s of the lines end.
        type : string, :py:class:`MarkerType`, array_like, optional
            the marker type/s (or name/s) of the lines.
        processed : int, array_like, optional
            the processed flag/s of the lines.
        text : string, array_like, optional
            the text/s of the lines.
        id : int, array_like, optional
            the id/s of the lines.

        Returns
        -------
        entries : array_like
            a query object which contains all :py:class:`Line` entries.
        """
        type = self._processesTypeNameField(type, ["TYPE_Line"])

        query = self.table_line.select(self.table_line, self.table_image).join(self.table_image)

        query = addFilter(query, id, self.table_line.id)
        query = addFilter(query, image, self.table_line.image)
        query = addFilter(query, frame, self.table_image.sort_index)
        query = addFilter(query, filename, self.table_image.filename)
        query = addFilter(query, x1, self.table_line.x1)
        query = addFilter(query, y1, self.table_line.y1)
        query = addFilter(query, x2, self.table_line.x2)
        query = addFilter(query, y2, self.table_line.y2)
        query = addFilter(query, type, self.table_line.type)
        query = addFilter(query, processed, self.table_line.processed)
        query = addFilter(query, text, self.table_line.text)

        # define the __array__ method of the query to make np.array(db.getLines()) possible
        query.__array__ = lambda:  np.array([[[l.x1, l.y1], [l.x2, l.y2]] for l in query])

        return query

    def setLine(self, image=None, frame=None, filename=None, x1=None, y1=None, x2=None, y2=None, type=None, processed=None, style=None, text=None, id=None, layer=None):
        """
        Insert or update an :py:class:`Line` object in the database.

        See also: :py:meth:`~.DataFile.getLine`, :py:meth:`~.DataFile.getLines`, :py:meth:`~.DataFile.setLines`,
        :py:meth:`~.DataFile.deleteLines`.

        Parameters
        ----------
        image : int, :py:class:`Image`, optional
            the image of the line.
        frame : int, optional
            the frame of the images of the line.
        filename : string, optional
            the filename of the image of the line.
        x1 : int, optional
            the x coordinate of the start of the line.
        y1 : int, optional
            the y coordinate of the start of the line.
        x2 : int, optional
            the x coordinate of the end of the line.
        y2 : int, optional
            the y coordinate of the end of the line.
        type : string, :py:class:`MarkerType`, optional
            the marker type (or name) of the line.
        processed : int, optional
            the processed flag of the line.
        text : string, optional
            the text of the line.
        id : int, optional
            the id of the line.
        layer : int, optional
            the layer of the image of the line

        Returns
        -------
        line : :py:class:`Line`
            the created or changed :py:class:`Line` item.
        """
        assert not (id is None and type is None), "Line must either have a type or be referenced by it's id."
        assert not (id is None and image is None and frame is None and filename is None), "Line must have an image, frame or filename given or be referenced by it's id."

        try:
            item = self.table_line.get(id=id)
        except peewee.DoesNotExist:
            item = self.table_line()

        type = self._processesTypeNameField(type, ["TYPE_Line"])
        image = self._processImagesField(image, frame, filename, layer)

        setFields(item, dict(image=image, x1=x1, y1=y1, x2=x2, y2=y2, type=type, processed=processed, style=style, text=text))
        item.save()
        return item

    def setLines(self, image=None, frame=None, filename=None, x1=None, y1=None, x2=None, y2=None, type=None,
                 processed=None, style=None, text=None, id=None, layer=None):
        """
        Insert or update multiple :py:class:`Line` objects in the database.

        See also: :py:meth:`~.DataFile.getLine`, :py:meth:`~.DataFile.getLines`, :py:meth:`~.DataFile.setLine`,
        :py:meth:`~.DataFile.deleteLines`.

        Parameters
        ----------
        image : int, :py:class:`Image`, array_like, optional
            the image/s of the lines.
        frame : int, array_like, optional
            the frame/s of the images of the lines.
        filename : string, array_like, optional
            the filename/s of the images of the lines.
        x1 : int, array_like, optional
            the x coordinate/s of the start of the lines.
        y1 : int, array_like, optional
            the y coordinate/s of the start of the lines.
        x2 : int, array_like, optional
            the x coordinate/s of the end of the lines.
        y2 : int, array_like, optional
            the y coordinate/s of the end of the lines.
        type : string, :py:class:`MarkerType`, array_like, optional
            the marker type/s (or name/s) of the lines.
        processed : int, array_like, optional
            the processed flag/s of the lines.
        track : int, :py:class:`Track`, array_like, optional
            the track id/s or instance/s of the lines.
        text : string, array_like, optional
            the text/s of the lines.
        id : int, array_like, optional
            the id/s of the lines.
        layer: int, optional
            the layer of the images of the lines

        Returns
        -------
        success : bool
            it the inserting was successful.
        """
        type = self._processesTypeNameField(type, ["TYPE_Line"])
        image = self._processImagesField(image, frame, filename, layer)

        data = packToDictList(self.table_line, id=id, image=image, x1=x1, y1=y1, x2=x2, y2=y2, processed=processed, type=type,
                              style=style, text=text)
        return self.saveReplaceMany(self.table_line, data)

    def deleteLines(self, image=None, frame=None, filename=None, x1=None, y1=None, x2=None, y2=None, type=None,
                    processed=None, text=None, id=None):
        """
        Delete all :py:class:`Line` entries with the given criteria.

        See also: :py:meth:`~.DataFile.getLine`, :py:meth:`~.DataFile.getLines`, :py:meth:`~.DataFile.setLine`,
        :py:meth:`~.DataFile.setLines`.

        Parameters
        ----------
        image : int, :py:class:`Image`, array_like, optional
            the image/s of the lines.
        frame : int, array_like, optional
            the frame/s of the images of the lines.
        filename : string, array_like, optional
            the filename/s of the images of the lines.
        x1 : int, array_like, optional
            the x coordinate/s of the start of the lines.
        y1 : int, array_like, optional
            the y coordinate/s of the start of the lines.
        x2 : int, array_like, optional
            the x coordinate/s of the end of the lines.
        y2 : int, array_like, optional
            the y coordinate/s of the end of the lines.
        type : string, :py:class:`MarkerType`, array_like, optional
            the marker type/s (or name/s) of the lines.
        processed : int, array_like, optional
            the processed flag/s of the lines.
        text : string, array_like, optional
            the text/s of the lines.
        id : int, array_like, optional
            the id/s of the lines.

        Returns
        -------
        rows : int
            the number of affected rows.
        """
        type = self._processesTypeNameField(type, ["TYPE_Line"])

        query = self.table_line.delete()

        if image is None and (frame is not None or filename is not None):
            images = self.table_image.select(self.table_image.id)
            images = addFilter(images, frame, self.table_image.sort_index)
            images = addFilter(images, filename, self.table_image.filename)
            query = query.where(self.table_line.image.in_(images))
        else:
            query = addFilter(query, image, self.table_line.image)

        query = addFilter(query, id, self.table_line.id)
        query = addFilter(query, x1, self.table_line.x1)
        query = addFilter(query, y1, self.table_line.y1)
        query = addFilter(query, x2, self.table_line.x2)
        query = addFilter(query, y2, self.table_line.y2)
        query = addFilter(query, type, self.table_line.type)
        query = addFilter(query, processed, self.table_line.processed)
        query = addFilter(query, text, self.table_line.text)

        return query.execute()

    """ Rectangles """

    def getRectangle(self, id):
        """
        Retrieve an :py:class:`Rectangle` object from the database.

        See also: :py:meth:`~.DataFile.getRectangles`, :py:meth:`~.DataFile.setRectangle`,
        :py:meth:`~.DataFile.setRectangles`, :py:meth:`~.DataFile.deleteRectangles`.

        Parameters
        ----------
        id: int
            the id of the rectangle.

        Returns
        -------
        rectangle : :py:class:`Rectangle`
            the :py:class:`Rectangle` with the desired id or None.
        """
        try:
            return self.table_rectangle.get(id=id)
        except peewee.DoesNotExist:
            return None

    def getRectangles(self, image=None, frame=None, filename=None, x=None, y=None, width=None, height=None, type=None,
                 processed=None, text=None, id=None, layer=None):
        """
        Get all :py:class:`Rectangle` entries with the given criteria.

        See also: :py:meth:`~.DataFile.getRectangle`, :py:meth:`~.DataFile.setRectangle`,
        :py:meth:`~.DataFile.setRectangles`, :py:meth:`~.DataFile.deleteRectangles`.

        Parameters
        ----------
        image : int, :py:class:`Image`, array_like, optional
            the image/s of the rectangles.
        frame : int, array_like, optional
            the frame/s of the images of the rectangles.
        filename : string, array_like, optional
            the filename/s of the images of the rectangles.
        x : int, array_like, optional
            the x coordinate/s of the upper left corner/s of the rectangles.
        y : int, array_like, optional
            the y coordinate/s of the upper left corner/s of the rectangles.
        width : int, array_like, optional
            the width/s of the rectangles.
        height : int, array_like, optional
            the height/s of the rectangles.
        type : string, :py:class:`MarkerType`, array_like, optional
            the marker type/s (or name/s) of the rectangles.
        processed : int, array_like, optional
            the processed flag/s of the rectangles.
        text : string, array_like, optional
            the text/s of the rectangles.
        id : int, array_like, optional
            the id/s of the rectangles.
        layer : int, optional
            the id of the image of the rectangle

        Returns
        -------
        entries : array_like
            a query object which contains all :py:class:`Rectangle` entries.
        """
        type = self._processesTypeNameField(type, ["TYPE_Rect"])

        query = self.table_rectangle.select(self.table_rectangle, self.table_image).join(self.table_image)

        image = self._processImagesField(image, frame, filename, layer)

        query = addFilter(query, id, self.table_rectangle.id)
        query = addFilter(query, image, self.table_rectangle.image)
        query = addFilter(query, frame, self.table_image.sort_index)
        query = addFilter(query, filename, self.table_image.filename)
        query = addFilter(query, x, self.table_rectangle.x)
        query = addFilter(query, y, self.table_rectangle.y)
        query = addFilter(query, height, self.table_rectangle.height)
        query = addFilter(query, width, self.table_rectangle.width)
        query = addFilter(query, type, self.table_rectangle.type)
        query = addFilter(query, processed, self.table_rectangle.processed)
        query = addFilter(query, text, self.table_rectangle.text)

        return query

    def setRectangle(self, image=None, frame=None, filename=None, x=None, y=None, width=None, height=None, type=None,
                     processed=None, style=None, text=None, id=None, layer=None):
        """
        Insert or update an :py:class:`Rectangle` object in the database.

        See also: :py:meth:`~.DataFile.getRectangle`, :py:meth:`~.DataFile.getRectangles`,
        :py:meth:`~.DataFile.setRectangles`, :py:meth:`~.DataFile.deleteRectangles`.

        Parameters
        ----------
        image : int, :py:class:`Image`, optional
            the image of the rectangle.
        frame : int, optional
            the frame of the images of the rectangle.
        filename : string, optional
            the filename of the image of the rectangle.
        x : int, optional
            the x coordinate of the upper left corner of the rectangle.
        y : int, optional
            the y coordinate of the upper left corner of the rectangle.
        width : int, optional
            the width of the rectangle.
        height : int, optional
            the height of the rectangle.
        type : string, :py:class:`MarkerType`, optional
            the marker type (or name) of the rectangle.
        processed : int, optional
            the processed flag of the rectangle.
        text : string, optional
            the text of the rectangle.
        id : int, optional
            the id of the rectangle.
        layer : int, optional
            the id of the image of the rectangle

        Returns
        -------
        rectangle : :py:class:`Rectangle`
            the created or changed :py:class:`Rectangle` item.
        """
        assert not (id is None and type is None), "Rectangle must either have a type or be referenced by it's id."
        assert not (id is None and image is None and frame is None and filename is None), "Rectangle must have an image, frame or filename given or be referenced by it's id."

        try:
            item = self.table_rectangle.get(id=id)
        except peewee.DoesNotExist:
            item = self.table_rectangle()

        type = self._processesTypeNameField(type, ["TYPE_Rect"])
        image = self._processImagesField(image, frame, filename, layer)

        setFields(item, dict(image=image, x=x, y=y, width=width, height=height, type=type, processed=processed, style=style, text=text))
        item.save()
        return item

    def setRectangles(self, image=None, frame=None, filename=None, x=None, y=None, width=None, height=None, type=None,
                 processed=None, style=None, text=None, id=None, layer=None):
        """
        Insert or update multiple :py:class:`Rectangle` objects in the database.

        See also: :py:meth:`~.DataFile.getRectangle`, :py:meth:`~.DataFile.getRectangles`,
        :py:meth:`~.DataFile.setRectangle`, :py:meth:`~.DataFile.deleteRectangles`.

        Parameters
        ----------
        image : int, :py:class:`Image`, array_like, optional
            the image/s of the rectangles.
        frame : int, array_like, optional
            the frame/s of the images of the rectangles.
        filename : string, array_like, optional
            the filename/s of the images of the rectangles.
        x : int, array_like, optional
            the x coordinate/s of the upper left corner/s of the rectangles.
        y : int, array_like, optional
         the y coordinate/s of the upper left corner/s of the rectangles.
        width : int, array_like, optional
            the width/s of the rectangles.
        height : int, array_like, optional
            the height/s of the rectangles.
        type : string, :py:class:`MarkerType`, array_like, optional
            the marker type/s (or name/s) of the rectangles.
        processed : int, array_like, optional
            the processed flag/s of the rectangles.
        text : string, array_like, optional
            the text/s of the rectangles.
        id : int, array_like, optional
            the id/s of the rectangles.
        layer : int, optional
            the layer of the images of the rectangles

        Returns
        -------
        success : bool
            it the inserting was successful.
        """
        type = self._processesTypeNameField(type, ["TYPE_Rect"])
        image = self._processImagesField(image, frame, filename, layer)

        data = packToDictList(self.table_rectangle, id=id, image=image, x=x, y=y, width=width, height=height, processed=processed, type=type,
                              style=style, text=text)
        return self.saveReplaceMany(self.table_rectangle, data)

    def deleteRectangles(self, image=None, frame=None, filename=None, x=None, y=None, width=None, height=None, type=None,
                    processed=None, text=None, id=None, layer=None):
        """
        Delete all :py:class:`Rectangle` entries with the given criteria.

        See also: :py:meth:`~.DataFile.getRectangle`, :py:meth:`~.DataFile.getRectangles`,
        :py:meth:`~.DataFile.setRectangle`, :py:meth:`~.DataFile.setRectangles`.

        Parameters
        ----------
        image : int, :py:class:`Image`, array_like, optional
            the image/s of the rectangles.
        frame : int, array_like, optional
            the frame/s of the images of the rectangles.
        filename : string, array_like, optional
            the filename/s of the images of the rectangles.
        x : int, array_like, optional
            the x coordinate/s of the upper left corner/s of the rectangles.
        y : int, array_like, optional
            the y coordinate/s of the upper left corner/s of the rectangles.
        width : int, array_like, optional
            the width/s of the rectangles.
        height : int, array_like, optional
            the height/s of the rectangles.
        type : string, :py:class:`MarkerType`, array_like, optional
            the marker type/s (or name/s) of the rectangles.
        processed : int, array_like, optional
            the processed flag/s of the rectangles.
        text : string, array_like, optional
            the text/s of the rectangles.
        id : int, array_like, optional
            the id/s of the rectangles.

        Returns
        -------
        rows : int
            the number of affected rows.
        """
        type = self._processesTypeNameField(type, ["TYPE_Rect"])
        image = self._processImagesField(image, frame, filename, layer)

        query = self.table_rectangle.delete()

        if image is None and (frame is not None or filename is not None):
            images = self.table_image.select(self.table_image.id)
            images = addFilter(images, frame, self.table_image.sort_index)
            images = addFilter(images, filename, self.table_image.filename)
            query = query.where(self.table_rectangle.image.in_(images))
        else:
            query = addFilter(query, image, self.table_rectangle.image)

        query = addFilter(query, id, self.table_rectangle.id)
        query = addFilter(query, x, self.table_rectangle.x)
        query = addFilter(query, y, self.table_rectangle.y)
        query = addFilter(query, width, self.table_rectangle.width)
        query = addFilter(query, height, self.table_rectangle.height)
        query = addFilter(query, type, self.table_rectangle.type)
        query = addFilter(query, processed, self.table_rectangle.processed)
        query = addFilter(query, text, self.table_rectangle.text)

        return query.execute()

    """ Ellipses """

    def getEllipse(self, id):
        """
        Retrieve an :py:class:`Ellipse` object from the database.

        See also: :py:meth:`~.DataFile.getEllipses`, :py:meth:`~.DataFile.setEllipse`,
        :py:meth:`~.DataFile.setEllipses`, :py:meth:`~.DataFile.deleteEllipses`.

        Parameters
        ----------
        id: int
            the id of the ellipse.

        Returns
        -------
        ellipse : :py:class:`Ellipse`
            the :py:class:`Ellipse` with the desired id or None.
        """
        try:
            return self.table_ellipse.get(id=id)
        except peewee.DoesNotExist:
            return None

    def getEllipses(self, image=None, frame=None, filename=None, x=None, y=None, width=None, height=None, angle=None,
                    type=None, processed=None, text=None, id=None, layer=None):
        """
        Get all :py:class:`Ellipse` entries with the given criteria.

        See also: :py:meth:`~.DataFile.getEllipse`, :py:meth:`~.DataFile.setEllipse`,
        :py:meth:`~.DataFile.setEllipses`, :py:meth:`~.DataFile.deleteEllipses`.

        Parameters
        ----------
        image : int, :py:class:`Image`, array_like, optional
            the image/s of the ellipses.
        frame : int, array_like, optional
            the frame/s of the images of the ellipses.
        filename : string, array_like, optional
            the filename/s of the images of the ellipses.
        x : int, array_like, optional
            the x coordinate/s of the center/s of the ellipses.
        y : int, array_like, optional
            the y coordinate/s of the center/s of the ellipses.
        width : int, array_like, optional
            the width/s of the ellipses.
        height : int, array_like, optional
            the height/s of the ellipses.
        angle : float, array_like, optional
            the angle/s of the rectangles in ellipses.
        type : string, :py:class:`MarkerType`, array_like, optional
            the marker type/s (or name/s) of the ellipses.
        processed : int, array_like, optional
            the processed flag/s of the ellipses.
        text : string, array_like, optional
            the text/s of the ellipses.
        id : int, array_like, optional
            the id/s of the ellipses.
        layer : int, optional
            the id of the image of the ellipses.

        Returns
        -------
        entries : array_like
            a query object which contains all :py:class:`Ellipse` entries.
        """
        type = self._processesTypeNameField(type, ["TYPE_Ellipse"])

        query = self.table_ellipse.select(self.table_ellipse, self.table_image).join(self.table_image)

        image = self._processImagesField(image, frame, filename, layer)

        query = addFilter(query, id, self.table_ellipse.id)
        query = addFilter(query, image, self.table_ellipse.image)
        query = addFilter(query, frame, self.table_image.sort_index)
        query = addFilter(query, filename, self.table_image.filename)
        query = addFilter(query, x, self.table_ellipse.x)
        query = addFilter(query, y, self.table_ellipse.y)
        query = addFilter(query, height, self.table_ellipse.height)
        query = addFilter(query, width, self.table_ellipse.width)
        query = addFilter(query, angle, self.table_ellipse.angle)
        query = addFilter(query, type, self.table_ellipse.type)
        query = addFilter(query, processed, self.table_ellipse.processed)
        query = addFilter(query, text, self.table_ellipse.text)

        return query

    def setEllipse(self, image=None, frame=None, filename=None, x=None, y=None, width=None, height=None, angle=None,
                   type=None, processed=None, style=None, text=None, id=None, layer=None):
        """
        Insert or update an :py:class:`Ellipse` object in the database.

        See also: :py:meth:`~.DataFile.getEllipse`, :py:meth:`~.DataFile.getEllipses`,
        :py:meth:`~.DataFile.setEllipses`, :py:meth:`~.DataFile.deleteEllipses`.

        Parameters
        ----------
        image : int, :py:class:`Image`, optional
            the image of the ellipse.
        frame : int, optional
            the frame of the images of the ellipse.
        filename : string, optional
            the filename of the image of the ellipse.
        x : int, optional
            the x coordinate of the center of the ellipse.
        y : int, optional
            the y coordinate of the center of the ellipse.
        width : int, optional
            the width of the ellipse.
        height : int, optional
            the height of the ellipse.
        angle : float, optional
            the angle of the ellipse in degrees.
        type : string, :py:class:`MarkerType`, optional
            the marker type (or name) of the ellipse.
        processed : int, optional
            the processed flag of the ellipse.
        text : string, optional
            the text of the ellipse.
        id : int, optional
            the id of the ellipse.
        layer : int, optional
            the id of the image of the ellipse.

        Returns
        -------
        ellipse : :py:class:`Ellipse`
            the created or changed :py:class:`Ellipse` item.
        """
        assert not (id is None and type is None), "Ellipse must either have a type or be referenced by it's id."
        assert not (id is None and image is None and frame is None and filename is None), "Ellipse must have an image, frame or filename given or be referenced by it's id."

        try:
            item = self.table_ellipse.get(id=id)
        except peewee.DoesNotExist:
            item = self.table_ellipse()

        type = self._processesTypeNameField(type, ["TYPE_Ellipse"])
        image = self._processImagesField(image, frame, filename, layer)

        setFields(item, dict(image=image, x=x, y=y, width=width, height=height, angle=angle, type=type, processed=processed, style=style, text=text))
        item.save()
        return item

    def setEllipses(self, image=None, frame=None, filename=None, x=None, y=None, width=None, height=None, angle=None,
                    type=None, processed=None, style=None, text=None, id=None, layer=None):
        """
        Insert or update multiple :py:class:`Ellipse` objects in the database.

        See also: :py:meth:`~.DataFile.getEllipse`, :py:meth:`~.DataFile.getEllipses`,
        :py:meth:`~.DataFile.setEllipse`, :py:meth:`~.DataFile.deleteEllipses`.

        Parameters
        ----------
        image : int, :py:class:`Image`, array_like, optional
            the image/s of the ellipses.
        frame : int, array_like, optional
            the frame/s of the images of the ellipses.
        filename : string, array_like, optional
            the filename/s of the images of the ellipses.
        x : int, array_like, optional
            the x coordinate/s of the center/s of the ellipses.
        y : int, array_like, optional
         the y coordinate/s of the center/s of the ellipses.
        width : int, array_like, optional
            the width/s of the ellipses.
        height : int, array_like, optional
            the height/s of the ellipses.
        angle : int, array_like, optional
            the angle/s of the ellipses.
        type : string, :py:class:`MarkerType`, array_like, optional
            the marker type/s (or name/s) of the ellipses.
        processed : int, array_like, optional
            the processed flag/s of the ellipses.
        text : string, array_like, optional
            the text/s of the ellipses.
        id : int, array_like, optional
            the id/s of the ellipses.
        layer : int, optional
            the layer of the images of the ellipses.

        Returns
        -------
        success : bool
            it the inserting was successful.
        """
        type = self._processesTypeNameField(type, ["TYPE_Ellipse"])
        image = self._processImagesField(image, frame, filename, layer)

        data = packToDictList(self.table_ellipse, id=id, image=image, x=x, y=y, width=width, height=height, angle=angle,
                              processed=processed, type=type, style=style, text=text)
        return self.saveReplaceMany(self.table_ellipse, data)

    def deleteEllipses(self, image=None, frame=None, filename=None, x=None, y=None, width=None, height=None, angle=None,
                       type=None, processed=None, text=None, id=None, layer=None):
        """
        Delete all :py:class:`Ellipse` entries with the given criteria.

        See also: :py:meth:`~.DataFile.getEllipse`, :py:meth:`~.DataFile.getEllipses`,
        :py:meth:`~.DataFile.setEllipse`, :py:meth:`~.DataFile.setEllipses`.

        Parameters
        ----------
        image : int, :py:class:`Image`, array_like, optional
            the image/s of the ellipses.
        frame : int, array_like, optional
            the frame/s of the images of the ellipses.
        filename : string, array_like, optional
            the filename/s of the images of the ellipses.
        x : int, array_like, optional
            the x coordinate/s of the center/s of the ellipses.
        y : int, array_like, optional
            the y coordinate/s of the center/s of the ellipses.
        width : int, array_like, optional
            the width/s of the ellipses.
        height : int, array_like, optional
            the height/s of the ellipses.
        angle : int, array_like, optional
            the angle/s of the ellipses in degrees.
        type : string, :py:class:`MarkerType`, array_like, optional
            the marker type/s (or name/s) of the ellipses.
        processed : int, array_like, optional
            the processed flag/s of the ellipses.
        text : string, array_like, optional
            the text/s of the ellipses.
        id : int, array_like, optional
            the id/s of the ellipses.

        Returns
        -------
        rows : int
            the number of affected rows.
        """
        type = self._processesTypeNameField(type, ["TYPE_Ellipse"])
        image = self._processImagesField(image, frame, filename, layer)

        query = self.table_ellipse.delete()

        if image is None and (frame is not None or filename is not None):
            images = self.table_image.select(self.table_image.id)
            images = addFilter(images, frame, self.table_image.sort_index)
            images = addFilter(images, filename, self.table_image.filename)
            query = query.where(self.table_ellipse.image.in_(images))
        else:
            query = addFilter(query, image, self.table_ellipse.image)

        query = addFilter(query, id, self.table_ellipse.id)
        query = addFilter(query, x, self.table_ellipse.x)
        query = addFilter(query, y, self.table_ellipse.y)
        query = addFilter(query, width, self.table_ellipse.width)
        query = addFilter(query, height, self.table_ellipse.height)
        query = addFilter(query, angle, self.table_ellipse.angle)
        query = addFilter(query, type, self.table_ellipse.type)
        query = addFilter(query, processed, self.table_ellipse.processed)
        query = addFilter(query, text, self.table_ellipse.text)

        return query.execute()

    """ Polygons """

    def getPolygon(self, id):
        """
        Retrieve an :py:class:`Polygon` object from the database.

        See also: :py:meth:`~.DataFile.getPolygons`, :py:meth:`~.DataFile.setPolygon`,
        :py:meth:`~.DataFile.setPolygons`, :py:meth:`~.DataFile.deletePolygons`.

        Parameters
        ----------
        id: int
            the id of the polygon.

        Returns
        -------
        polygon : :py:class:`Polygon`
            the :py:class:`Polygon` with the desired id or None.
        """
        try:
            return self.table_polygon.get(id=id)
        except peewee.DoesNotExist:
            return None

    def getPolygons(self, image=None, frame=None, filename=None, type=None, processed=None, text=None, id=None, layer=None):
        """
        Get all :py:class:`Polygon` entries with the given criteria.

        See also: :py:meth:`~.DataFile.getPolygon`, :py:meth:`~.DataFile.setPolygon`,
        :py:meth:`~.DataFile.setPolygons`, :py:meth:`~.DataFile.deletePolygons`.

        Parameters
        ----------
        image : int, :py:class:`Image`, array_like, optional
            the image/s of the polygons.
        frame : int, array_like, optional
            the frame/s of the images of the polygons.
        filename : string, array_like, optional
            the filename/s of the images of the polygons.
        type : string, :py:class:`MarkerType`, array_like, optional
            the marker type/s (or name/s) of the polygons.
        processed : int, array_like, optional
            the processed flag/s of the polygons.
        text : string, array_like, optional
            the text/s of the polygons.
        id : int, array_like, optional
            the id/s of the polygons.
        layer : int, optional
            the id of the image of the polygons.

        Returns
        -------
        entries : array_like
            a query object which contains all :py:class:`Polygon` entries.
        """
        type = self._processesTypeNameField(type, ["TYPE_Polygon"])

        query = self.table_polygon.select(self.table_polygon, self.table_image).join(self.table_image)

        image = self._processImagesField(image, frame, filename, layer)

        query = addFilter(query, id, self.table_polygon.id)
        query = addFilter(query, image, self.table_polygon.image)
        query = addFilter(query, frame, self.table_image.sort_index)
        query = addFilter(query, filename, self.table_image.filename)
        query = addFilter(query, type, self.table_polygon.type)
        query = addFilter(query, processed, self.table_polygon.processed)
        query = addFilter(query, text, self.table_polygon.text)

        return query

    def setPolygon(self, image=None, frame=None, filename=None, points=None, type=None, processed=None, style=None,
                   text=None, id=None, layer=None):
        """
        Insert or update an :py:class:`Polygon` object in the database.

        See also: :py:meth:`~.DataFile.getPolygon`, :py:meth:`~.DataFile.getPolygons`,
        :py:meth:`~.DataFile.setPolygons`, :py:meth:`~.DataFile.deletePolygons`.

        Parameters
        ----------
        image : int, :py:class:`Image`, optional
            the image of the polygon.
        frame : int, optional
            the frame of the images of the polygon.
        filename : string, optional
            the filename of the image of the polygon.
        points : array, optional
            the points of the vertices of the polygon.
        type : string, :py:class:`MarkerType`, optional
            the marker type (or name) of the polygon.
        processed : int, optional
            the processed flag of the polygon.
        text : string, optional
            the text of the polygon.
        id : int, optional
            the id of the polygon.
        layer : int, optional
            the id of the image of the polygon.

        Returns
        -------
        polygon : :py:class:`Polygon`
            the created or changed :py:class:`Polygon` item.
        """
        assert not (id is None and type is None), "Polygon must either have a type or be referenced by it's id."
        assert not (id is None and image is None and frame is None and filename is None), "Polygon must have an image, frame or filename given or be referenced by it's id."

        try:
            item = self.table_polygon.get(id=id)
        except peewee.DoesNotExist:
            item = self.table_polygon()

        type = self._processesTypeNameField(type, ["TYPE_Polygon"])
        image = self._processImagesField(image, frame, filename, layer)

        setFields(item, dict(image=image, points=points, type=type, processed=processed, style=style, text=text))
        item.save()
        return item

    def setPolygons(self, image=None, frame=None, filename=None, points=None, type=None, processed=None, style=None,
                    text=None, id=None, layer=None):
        raise NotImplemented("Use multiple calls to setPolygon() instead.")

    def deletePolygons(self, image=None, frame=None, filename=None,
                       type=None, processed=None, text=None, id=None, layer=None):
        """
        Delete all :py:class:`Polygon` entries with the given criteria.

        See also: :py:meth:`~.DataFile.getPolygon`, :py:meth:`~.DataFile.getPolygons`,
        :py:meth:`~.DataFile.setPolygon`, :py:meth:`~.DataFile.setPolygons`.

        Parameters
        ----------
        image : int, :py:class:`Image`, array_like, optional
            the image/s of the polygons.
        frame : int, array_like, optional
            the frame/s of the images of the polygons.
        filename : string, array_like, optional
            the filename/s of the images of the polygons.
        type : string, :py:class:`MarkerType`, array_like, optional
            the marker type/s (or name/s) of the polygons.
        processed : int, array_like, optional
            the processed flag/s of the polygons.
        text : string, array_like, optional
            the text/s of the polygons.
        id : int, array_like, optional
            the id/s of the polygons.

        Returns
        -------
        rows : int
            the number of affected rows.
        """
        type = self._processesTypeNameField(type, ["TYPE_Polygon"])
        image = self._processImagesField(image, frame, filename, layer)

        query = self.table_polygon.delete()

        if image is None and (frame is not None or filename is not None):
            images = self.table_image.select(self.table_image.id)
            images = addFilter(images, frame, self.table_image.sort_index)
            images = addFilter(images, filename, self.table_image.filename)
            query = query.where(self.table_ellipse.image.in_(images))
        else:
            query = addFilter(query, image, self.table_ellipse.image)

        query = addFilter(query, id, self.table_polygon.id)
        query = addFilter(query, type, self.table_polygon.type)
        query = addFilter(query, processed, self.table_polygon.processed)
        query = addFilter(query, text, self.table_polygon.text)

        return query.execute()

    """ Offset """

    def setOffset(self, image, x, y):
        """
        Set an :py:class:`Offset` entry for a given image.

        See also: :py:meth:`~.DataFile.deleteOffsets`.

        Parameters
        ----------
        image : int, :py:class:`Image`
            the image for which the offset should be given.
        x : int
            the x coordinate of the offset.
        y : int
            the y coordinate of the offset.

        Returns
        -------
        entries : :py:class:`Offset`
            object of class :py:class:`Offset`
        """

        try:
            offset = self.table_offset.get(image=image)
        except peewee.DoesNotExist:
            offset = self.table_offset()

        setFields(offset, dict(image=image, x=x, y=y))
        offset.save()

        return offset

    def deleteOffsets(self, image=None):
        """
        Delete all :py:class:`Offset` entries from the database, which match the given criteria. If no criteria a given,
        delete all.

        See also: :py:meth:`~.DataFile.setOffset`.

        Parameters
        ----------
        image : int, :py:class:`Image`, array_like, optional
            the image/s for which the offset should be deleted.

        Returns
        -------
        rows : int
            number of rows deleted
        """

        query = self.table_offset.delete()

        query = addFilter(query, image, self.table_offset.image)

        return query.execute()

    def setTag(self, name=None, id=None):
        """
        Set a specific :py:class:`Tag` entry by its name or database ID

        See also: :py:meth:`~.DataFile.getTag`, :py:meth:`~.DataFile.getTags`, :py:meth:`~.DataFile.deleteTags`.

        Parameters
        ----------
        name: str
            name of the tag
        id: int
            id of :py:class:`Tag` entry

        Returns
        -------
        entries : :py:class:`Tag`
            object of class :py:class:`Tag`
        """

        # check input
        assert any(e is not None for e in [id, name]), "Name and ID may not be all None"

        try:
            if id:
                tag = self.table_tag.get(id=id)
            else:
                tag = self.table_tag.get(name=name)
        except peewee.DoesNotExist:
            tag = self.table_tag()

        setFields(tag, dict(name=name))
        tag.save()

        return tag

    def getTag(self, name=None, id=None):
        """
        Get a specific :py:class:`Tag` entry by its name or database ID

        See also: :py:meth:`~.DataFile.getTags`, :py:meth:`~.DataFile.setTag`, :py:meth:`~.DataFile.deleteTags`.

        Parameters
        ----------
        name: str
            name of the tag
        id: int
            id of :py:class:`Tag` entry


        Returns
        -------
        entries : :py:class:`Tag`
            requested object of class :py:class:`Tag` or None
        """

        # check input
        assert any(e is not None for e in [id, name]), "Name and ID may not be all None"

        try:
            return self.table_tag.get(**noNoneDict(name=name, id=id))
        except:
            return None


    def getTags(self,name=None,id=None):
        """
        Get all :py:class:`Tag` entries from the database, which match the given criteria. If no criteria a given,
        return all.

        See also: :py:meth:`~.DataFile.getTag`, :py:meth:`~.DataFile.setTag`,
        :py:meth:`~.DataFile.deleteTags`.

        Parameters
        ----------
        name : string, array_like, optional
            the name/names of the :py:class:`Tag`.
        id : int, array_like, optional
            the id/ids of the :py:class:`Tag`.

        Returns
        -------
        entries : array_like
            a query object containing all the matching :py:class:`Tag` entries in the database file.
        """

        query = self.table_tag.select()

        query = addFilter(query, name, self.table_tag.name)
        query = addFilter(query, id, self.table_tag.id)

        return query

    def deleteTags(self, name=None, id=None):
        """
        Delete all :py:class:`Tag` entries from the database, which match the given criteria. If no criteria a given,
        delete all.

        See also: :py:meth:`~.DataFile.getTag`, :py:meth:`~.DataFile.getTags`, :py:meth:`~.DataFile.setTag`.

        Parameters
        ----------
        name : string, array_like, optional
            the name/names of the :py:class:`Tag`.
        id : int, array_like, optional
            the id/ids of the :py:class:`Tag`.

        Returns
        -------
        rows : int
            number of rows deleted
        """

        query = self.table_tag.delete()

        query = addFilter(query, name, self.table_tag.name)
        query = addFilter(query, id, self.table_tag.id)

        return query.execute()

    def getAnnotation(self, image=None, frame=None, filename=None, id=None, create=False):
        """
        Get the :py:class:`Annotation` entry for the given image frame number or filename.

        See also: :py:meth:`~.DataFile.getAnnotations`, :py:meth:`~.DataFile.setAnnotation`, :py:meth:`~.DataFile.deleteAnnotations`.

        Parameters
        ----------
        image : int, :py:class:`Image`, optional
            the image for which the annotation should be retrieved. If omitted, frame number or filename should be specified instead.
        frame : int, optional
            frame number of the image, which annotation should be returned. If omitted, image or filename should be specified instead.
        filename : string, optional
            filename of the image, which annotation should be returned. If omitted, image or frame number should be specified instead.
        id : int, optional
            id of the annotation entry.
        create : bool, optional
            whether the annotation should be created if it does not exist. (default: False)

        Returns
        -------
        annotation : :py:class:`Annotation`
            the desired :py:class:`Annotation` entry.
        """
        # check input
        assert sum(e is not None for e in [id, image, frame, filename]) == 1, \
            "Exactly one of image, frame or filename should be specified or should be referenced by it's id."

        query = self.table_annotation.select(self.table_annotation, self.table_image).join(self.table_image)

        query = addFilter(query, id, self.table_annotation.id)
        query = addFilter(query, image, self.table_annotation.image)
        query = addFilter(query, frame, self.table_image.sort_index)
        query = addFilter(query, filename, self.table_image.filename)
        query.limit(1)

        try:
            return query[0]
        except IndexError:
            if create is True:
                if not image:
                    image = self.getImage(frame, filename)
                    if not image:
                        raise ImageDoesNotExist("No parent image found ")
                annotation = self.table_annotation(image=image, timestamp=image.timestamp, comment="", rating=None)
                annotation.save()
                return annotation
            return None

    def getAnnotations(self, image=None, frame=None, filename=None, timestamp=None, tag=None, comment=None, rating=None, id=None):
        """
        Get all :py:class:`Annotation` entries from the database, which match the given criteria. If no criteria a given, return all masks.

        See also: :py:meth:`~.DataFile.getAnnotation`, :py:meth:`~.DataFile.setAnnotation`, :py:meth:`~.DataFile.deleteAnnotations`.

        Parameters
        ----------
        image : int, :py:class:`Image`, array_like, optional
            the image/images for which the annotations should be retrieved. If omitted, frame numbers or filenames should be specified instead.
        frame: int, array_like, optional
            frame number/numbers of the images, which annotations should be returned. If omitted, images or filenames should be specified instead.
        filename: string, array_like, optional
            filename of the image/images, which annotations should be returned. If omitted, images or frame numbers should be specified instead.
        timestamp : datetime, array_like, optional
            timestamp/s of the annotations.
        tag : string, array_like, optional
            the tag/s of the annotations to load.
        comment : string, array_like, optional
            the comment/s of the annotations.
        rating : int, array_like, optional
            the rating/s of the annotations.
        id : int, array_like, optional
            id/ids of the annotations.

        Returns
        -------
        entries : :py:class:`Annotation`
            a query object containing all the matching :py:class:`Annotation` entries in the database file.
        """
        # check input
        assert sum(e is not None for e in [image, frame, filename]) <= 1, \
            "Exactly one of images, frames or filenames should be specified"

        query = self.table_annotation.select(self.table_annotation, self.table_image).join(self.table_image)
        if tag is not None:
            query = query.switch(self.table_annotation).join(self.table_tagassociation).join(self.table_tag)

        query = addFilter(query, id, self.table_annotation.id)
        query = addFilter(query, image, self.table_annotation.image)
        query = addFilter(query, frame, self.table_image.sort_index)
        query = addFilter(query, filename, self.table_image.filename)
        query = addFilter(query, timestamp, self.table_annotation.timestamp)
        query = addFilter(query, comment, self.table_annotation.comment)
        query = addFilter(query, rating, self.table_annotation.rating)
        if tag:
            query = addFilter(query, tag, self.table_tag.name)
            query = query.group_by(self.table_annotation.id)

        return query

    def setAnnotation(self, image=None, frame=None, filename=None, timestamp=None, comment=None, rating=None, id=None, layer=None):
        """
        Insert or update an :py:class:`Annotation` object in the database.

        See also: :py:meth:`~.DataFile.getAnnotation`, :py:meth:`~.DataFile.getAnnotations`, :py:meth:`~.DataFile.deleteAnnotations`.

        Parameters
        ----------
        image : int, :py:class:`Image`, optional
            the image of the annotation.
        frame : int, optional
            the frame of the images of the annotation.
        filename : string, optional
            the filename of the image of the annotation.
        timestamp : datetime, optional
            the timestamp of the annotation.
        comment : string, optional
            the text of the annotation.
        rating : int, optional
            the rating of the annotation.
        id : int, optional
            the id of the annotation.

        Returns
        -------
        annotation : :py:class:`Annotation`
            the created or changed :py:class:`Annotation` item.
        """
        assert not (id is None and image is None and frame is None and filename is None), "Annotations must have an image, frame or filename given or be referenced by it's id."

        image = self._processImagesField(image, frame, filename, layer)

        try:
            item = self.table_annotation.get(**noNoneDict(id=id, image=image))
        except peewee.DoesNotExist:
            item = self.table_annotation()

        setFields(item, dict(image=image, timestamp=timestamp, comment=comment, rating=rating))
        item.save()
        return item

    def deleteAnnotations(self, image=None, frame=None, filename=None, timestamp=None, comment=None, rating=None, id=None):
        """
        Delete all :py:class:`Annotation` entries with the given criteria.

        See also: :py:meth:`~.DataFile.getAnnotation`, :py:meth:`~.DataFile.getAnnotations`, :py:meth:`~.DataFile.setAnnotation`.

        Parameters
        ----------
        image : int, :py:class:`Image`, array_like, optional
            the image/images for which the annotations should be retrieved. If omitted, frame numbers or filenames should be specified instead.
        frame: int, array_like, optional
            frame number/numbers of the images, which annotations should be returned. If omitted, images or filenames should be specified instead.
        filename: string, array_like, optional
            filename of the image/images, which annotations should be returned. If omitted, images or frame numbers should be specified instead.
        timestamp : datetime, array_like, optional
            timestamp/s of the annotations.
        comment : string, array_like, optional
            the comment/s of the annotations.
        rating : int, array_like, optional
            the rating/s of the annotations.
        id : int, array_like, optional
            id/ids of the annotations.

        Returns
        -------
        rows : int
            the number of affected rows.
        """

        query = self.table_annotation.delete()

        if image is None and (frame is not None or filename is not None):
            images = self.table_image.select(self.table_image.id)
            images = addFilter(images, frame, self.table_image.sort_index)
            images = addFilter(images, filename, self.table_image.filename)
            query = query.where(self.table_annotation.image.in_(images))
        else:
            query = addFilter(query, image, self.table_annotation.image)

        query = addFilter(query, id, self.table_annotation.id)
        query = addFilter(query, image, self.table_annotation.image)
        query = addFilter(query, timestamp, self.table_annotation.timestamp)
        query = addFilter(query, comment, self.table_annotation.comment)
        query = addFilter(query, rating, self.table_annotation.rating)

        return query.execute()

    def mergeWith(self, other_db):
        my_marker_types = {t.name: t.id for t in self.getMarkerTypes()}
        other_marker_types = {t.name: t.id for t in other_db.getMarkerTypes()}
        marker_translation = {}
        marker_type_attributes = ["name", "color", "mode", "style", "text", "hidden"]
        for other_marker_type in other_db.getMarkerTypes():
            if other_marker_type.name in my_marker_types:
                marker_translation[other_marker_type.id] = my_marker_types[other_marker_type.name]
            else:
                kwargs = {name: getattr(other_marker_type, name) for name in marker_type_attributes}
                marker_type = self.setMarkerType(**kwargs)
                marker_translation[other_marker_type.id] = marker_type.id

        image_attributes = ["filename", "frame", "external_id", "timestamp", "width", "height", "layer"]
        marker_attributes = ["image", "x", "y", "type", "processed", "track", "style", "text"]
        line_attributes = ["image", "x1", "x2", "y1", "y2", "type", "processed", "style", "text"]
        annotation_attributes = ["image", "timestamp", "comment", "rating"]
        for image_other in other_db.getImages():
            kwargs = {name: getattr(image_other, name) for name in image_attributes}
            image = self.setImage(**kwargs)
            for marker in image_other.markers:
                kwargs = {name: getattr(marker, name) for name in marker_attributes}
                kwargs["type"] = kwargs["type"].name
                kwargs["image"] = image
                self.setMarker(**kwargs)
            for line in image_other.lines:
                kwargs = {name: getattr(line, name) for name in line_attributes}
                kwargs["type"] = kwargs["type"].name
                kwargs["image"] = image
                self.setLine(**kwargs)
            for annotation in image_other.annotations:
                kwargs = {name: getattr(annotation, name) for name in annotation_attributes}
                kwargs["image"] = image
                self.setAnnotation(**kwargs)

    def getTracksNanPadded(self, type=None, id=None, start_frame=None, end_frame=None, skip=None, layer=0, apply_offset=False):
        """
        Return an array of all track points with the given filters. The array has the shape of [n_tracks, n_images, pos],
        where pos is the 2D position of the markers.

        See also: :py:meth:`~.DataFile.getTrack`, :py:meth:`~.DataFile.setTrack`, :py:meth:`~.DataFile.deleteTracks`, :py:meth:`~.DataFile.getTracks`.

        Parameters
        ----------
        type: :py:class:`MarkerType`, str, array_like, optional
            the marker type/types or name of the marker type for the track.
        id : int, array_like, optional
            the  :py:class:`Track` ID
        start_frame : int, optional
            the frame where to begin the array. Default: first frame.
        end_frame : int, optional
            the frame where to end the array. Default: last frame.
        skip : int, optional
            skip every nth frame. Default: don't skip frames.
        layer : int, optional
            which layer to use for the images.
        apply_offset : bool, optional
            whether to apply the image offsets to the marker positions. Default: False.

        Returns
        -------
        nan_padded_array : ndarray
            the array which contains all the track marker positions.
        """

        layer_count = self.table_layer.select().count()

        """ image conditions """
        where_condition_image = []

        # get the filter condition (only filter if it is necessary, e.g. if we have more than one layer)
        if layer is not None and layer_count != 1:
            if layer == 0:
                layer = self.table_layer.select().where(self.table_layer.id == self.table_layer.base_layer).limit(1)[0]
            else:
                layer = self.table_layer.select().where(self.table_layer.id == layer).limit(1)[0]
            where_condition_image.append("layer_id = %d" % layer.base_layer_id)

        # if a start frame is given, only export marker from images >= the given frame
        if start_frame is not None:
            where_condition_image.append("i.sort_index >= %d" % start_frame)
        # if a end frame is given, only export marker from images < the given frame
        if end_frame is not None:
            where_condition_image.append("i.sort_index < %d" % end_frame)
        # skip every nth frame
        if skip is not None:
            where_condition_image.append("i.sort_index %% %d = 0" % skip)

        # append sorting by sort index
        if len(where_condition_image):
            where_condition_image = " WHERE " + " AND ".join(where_condition_image)
        else:
            where_condition_image = ""

        # get the image ids according to the conditions
        image_ids = self.db.execute_sql("SELECT id FROM image i "+where_condition_image+" ORDER BY sort_index;").fetchall()
        image_count = len(image_ids)

        """ track conditions """
        where_condition_tracks = []

        if type is not None:
            type = self._processesTypeNameField(type, ["TYPE_Track"])
            if not isinstance(type, list):
                where_condition_tracks.append("t.type_id = %d" % type.id)
            else:
                where_condition_tracks.append("t.type_id in " % str([t.id for t in type]))

        if id is not None:
            where_condition_tracks.append("t.id = %d" % id)

        # append sorting by sort index
        if len(where_condition_tracks):
            where_condition_tracks = " WHERE " + " AND ".join(where_condition_tracks)
        else:
            where_condition_tracks = ""

        track_ids = self.db.execute_sql("SELECT id FROM track t "+where_condition_tracks+";").fetchall()
        track_count = len(track_ids)

        # create empty array to be filled by the queries
        pos = np.zeros((track_count, image_count, 2), "float")

        # iterate either over images or over tracks
        # for some reasons it is better to iterate over the images even if the number of tracks is lower
        if image_count < track_count * 100:
            # iterate over all images
            for index, (id,) in enumerate(image_ids):
                # get the tracks for this image
                q = self.db.execute_sql(
                    "SELECT x, y FROM track t LEFT JOIN marker m ON m.track_id = t.id AND m.image_id = ? "+where_condition_tracks+" ORDER BY t.id",
                    (id,))
                # store the result in the array
                pos[:, index] = q.fetchall()
        else:
            # iterate over all tracks
            for index, (id,) in enumerate(track_ids):
                # get the images for this track
                q = self.db.execute_sql(
                    "SELECT x, y FROM image i LEFT JOIN marker m ON m.track_id = ? AND m.image_id = i.id " + where_condition_image + " ORDER BY i.sort_index",
                    (id,))
                # store the result in the array
                pos[index] = q.fetchall()

        # if the offset is required, get the offsets for all images and add them to the marker positions
        if apply_offset:
            query_offset = "SELECT IFNULL(o.x, 0) AS x, IFNULL(o.y, 0) AS y FROM image AS i LEFT JOIN offset o ON i.id = o.image_id"
            offsets = np.array(self.db.execute_sql(query_offset + where_condition_image + " ORDER BY sort_index;").fetchall()).astype(float)
            pos += offsets

        return pos
