from __future__ import print_function, division
import numpy as np
import os
import peewee
from PIL import Image as PILImage
import imageio
import sys
from cStringIO import StringIO

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
        return peewee.binary_construct(value)

    def python_value(self, value):
        if not PY3:
            value = str(value)
        return imageio.imread(StringIO(value), format=".png")

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

def packToDictList(**kwargs):
    import itertools
    max_len = 0
    singles = {}
    for key in kwargs.keys():
        if kwargs[key] is None:
            del kwargs[key]
            continue
        if isinstance(kwargs[key], (tuple, list)):
            if max_len > 1 and max_len != len(kwargs[key]):
                raise IndexError()
            max_len = max(max_len, len(kwargs[key]))
            singles[key] = False
        else:
            max_len = max(max_len, 1)
            singles[key] = True
    dict_list = []
    for i in range(max_len):
        dict_list.append({key: kwargs[key] if singles[key] else kwargs[key][i] for key in kwargs})
    return dict_list

def VerboseDict(dictionary):
    return " and ".join("%s=%s" % (key, dictionary[key]) for key in dictionary)


class DoesNotExit(peewee.DoesNotExist):
    pass

class ImageDoesNotExit(DoesNotExit):
    pass

class MarkerTypeDoesNotExist(DoesNotExit):
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
    reader = None
    _current_version = "14"
    database_filename = None
    next_sort_index = 0

    """ Enumerations """
    TYPE_Normal = 0
    TYPE_Rect = 1
    TYPE_Line = 2
    TYPE_Track = 4

    def __init__(self, database_filename=None, mode='r'):
        if database_filename is None:
            raise TypeError("No database filename supplied.")
        self.database_filename = database_filename

        version = self._current_version
        new_database = True

        # Create a new database
        if mode == "w":
            if os.path.exists(self.database_filename):
                os.remove(self.database_filename)
            self.db = peewee.SqliteDatabase(database_filename, threadlocals=True)
            self.db.get_conn().row_factory = dict_factory
        else:  # or read an existing one
            if not os.path.exists(self.database_filename) and mode != "r+":
                raise Exception("DB %s does not exist!" % os.path.abspath(self.database_filename))
            self.db = peewee.SqliteDatabase(database_filename, threadlocals=True)
            if os.path.exists(self.database_filename):
                self.db.get_conn().row_factory = dict_factory
                version = self._CheckVersion()
                self.next_sort_index = None
                new_database = False
            else:
                self.db.get_conn().row_factory = dict_factory

        """ Basic Tables """

        class BaseModel(peewee.Model):
            class Meta:
                database = self.db

            database_class = self

        class Meta(BaseModel):
            key = peewee.CharField(unique=True)
            value = peewee.CharField()

        class Path(BaseModel):
            path = peewee.CharField(unique=True)

            def __str__(self):
                return "PathObject id%s: path=%s" % (self.id, self.path)

        class Image(BaseModel):
            filename = peewee.CharField()
            ext = peewee.CharField(max_length=10)
            frame = peewee.IntegerField(default=0)
            external_id = peewee.IntegerField(null=True)
            timestamp = peewee.DateTimeField(null=True)
            sort_index = peewee.IntegerField(default=0)
            width = peewee.IntegerField(null=True)
            height = peewee.IntegerField(null=True)
            path = peewee.ForeignKeyField(Path, related_name="images", on_delete='CASCADE')

            class Meta:
                # image and path in combination have to be unique
                indexes = ((('filename', 'path', 'frame'), True),)

            image_data = None

            def get_data(self):
                if self.image_data is None:
                    if self.database_class.reader is None or self.database_class.reader.filename != self.filename:
                        self.database_class.reader = imageio.get_reader(os.path.join(self.path.path, self.filename))
                        self.database_class.reader.filename = self.filename
                    self.image_data = self.database_class.reader.get_data(self.frame)
                return self.image_data

            def __getattr__(self, item):
                if item == "mask":
                    return self.masks[0]
                if item == "data":
                    return self.get_data()

                if item == "annotation":
                    try:
                        return self.annotations[0]
                    except:
                        return None

                if item == "offset":
                    try:
                        return self.offsets[0]
                    except:
                        return None

                if item == "data8":
                    data = self.get_data().copy()
                    if data.dtype == np.uint16:
                        if data.max() < 2 ** 12:
                            data >>= 4
                            return data.astype(np.uint8)
                        data >>= 8
                        return data.astype(np.uint8)
                    return data
                else:
                    return BaseModel(self, item)

            def getShape(self):
                if self.width is not None and self.height is not None:
                    return [self.height, self.width]
                else:
                    return self.data.shape[:2]

            def __str__(self):
                return "ImageObject id%s: filename=%s, ext=%s, frame=%s, external_id=%s, timestamp=%s, sort_index=%s," \
                       " width=%s, height=%s, path=%s" % (self.id, self.filename, self.ext, self.frame, self.external_id,
                        self.timestamp, self.sort_index, self.width, self.height, self.path)

        self.base_model = BaseModel
        self.table_meta = Meta
        self.table_path = Path
        self.table_image = Image
        self.tables = [Meta, Path, Image]

        """ Offset Table """

        class Offset(BaseModel):
            image = peewee.ForeignKeyField(Image, unique=True, related_name="offsets", on_delete='CASCADE')
            x = peewee.FloatField()
            y = peewee.FloatField()

        self.table_offset = Offset
        self.tables.extend([Offset])

        """ Marker Tables """

        class MarkerType(BaseModel):
            name = peewee.CharField(unique=True)
            color = peewee.CharField()
            mode = peewee.IntegerField(default=0)
            style = peewee.CharField(null=True)
            text = peewee.CharField(null=True)

            def __str__(self):
                return "MarkerType Object: id=%d\tname=%s\tcolor=%s\tmode=%s\tstyle=%s\ttext=%s" \
                       % (self.id, self.name, self.color, self.mode, self.style, self.text)

            def details(self):
                print("MarkerType Object:\n"
                      "id:\t\t{0}\n"
                      "name:\t{1}\n"
                      "color:\t{2}\n"
                      "mode:\t{3}\n"
                      "style:\t{4}\n"
                      "text:\t{5}\n"
                      .format(self.id, self.name, self.color, self.mode, self.style, self.text))

        class Track(BaseModel):
            #uid = peewee.CharField() # TODO discard
            style = peewee.CharField(null=True)
            text = peewee.CharField(null=True)
            type = peewee.ForeignKeyField(MarkerType, related_name="tracks", on_delete='CASCADE')

            def __getattr__(self, item):
                if item == "points":
                    return np.array([[point.x, point.y] for point in self.markers])
                if item == "markers":
                    return self.track_markers.join(Image).order_by(Image.sort_index)
                if item == "times":
                    return np.array([point.image.timestamp for point in self.markers])
                if item == "frames":
                    return np.array([point.image.sort_index for point in self.markers])
                return BaseModel(self, item)

        class Marker(BaseModel):
            image = peewee.ForeignKeyField(Image, related_name="markers", on_delete='CASCADE')
            x = peewee.FloatField()
            y = peewee.FloatField()
            type = peewee.ForeignKeyField(MarkerType, related_name="markers", null=True, on_delete='CASCADE')
            processed = peewee.IntegerField(default=0)
            track = peewee.ForeignKeyField(Track, null=True, related_name='track_markers', on_delete='CASCADE')
            style = peewee.CharField(null=True)
            text = peewee.CharField(null=True)

            class Meta:
                indexes = ((('image', 'track'), True),)

            def __getattr__(self, item):
                if item == "correctedXY":
                    return self.correctedXY()
                if item == "pos":
                    return self.pos()
                return BaseModel(self, item)

            def correctedXY(self):
                join_condition = ((Marker.image == Offset.image) & \
                                  (Marker.image_frame == Offset.image_frame))

                querry = Marker.select(Marker.x,
                                       Marker.y,
                                       Offset.x,
                                       Offset.y) \
                    .join(Offset, peewee.JOIN_LEFT_OUTER, on=join_condition) \
                    .where(Marker.id == self.id)

                for q in querry:
                    if not (q.offsets.x is None) or not (q.offsets.y is None):
                        pt = [q.x + q.offsets.x, q.y + q.offsets.y]
                    else:
                        pt = [q.x, q.y]

                return pt

            def pos(self):
                return np.array([self.x, self.y])

        class Line(BaseModel):
            image = peewee.ForeignKeyField(Image, related_name="lines", on_delete='CASCADE')
            x1 = peewee.FloatField()
            y1 = peewee.FloatField()
            x2 = peewee.FloatField()
            y2 = peewee.FloatField()
            type = peewee.ForeignKeyField(MarkerType, related_name="lines", null=True, on_delete='CASCADE')
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

            def __getattr__(self, item):
                if item == "correctedXY":
                    return self.correctedXY()
                if item == "pos":
                    return self.pos()
                if item == "length":
                    return self.length()
                return BaseModel(self, item)

            def correctedXY(self):
                join_condition = ((Marker.image == Offset.image) & \
                                  (Marker.image_frame == Offset.image_frame))

                querry = Marker.select(Marker.x,
                                       Marker.y,
                                       Offset.x,
                                       Offset.y) \
                    .join(Offset, peewee.JOIN_LEFT_OUTER, on=join_condition) \
                    .where(Marker.id == self.id)

                for q in querry:
                    if not (q.offsets.x is None) or not (q.offsets.y is None):
                        pt = [q.x + q.offsets.x, q.y + q.offsets.y]
                    else:
                        pt = [q.x, q.y]

                return pt

            def pos(self):
                return np.array([self.x, self.y])

            def length(self):
                return np.sqrt((self.x1-self.x2)**2 + (self.y1-self.y2)**2)

        class Rectangle(BaseModel):
            image = peewee.ForeignKeyField(Image, related_name="rectangles", on_delete='CASCADE')
            x = peewee.FloatField()
            y = peewee.FloatField()
            width = peewee.FloatField()
            height = peewee.FloatField()
            type = peewee.ForeignKeyField(MarkerType, related_name="rectangles", null=True, on_delete='CASCADE')
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

            def __getattr__(self, item):
                if item == "correctedXY":
                    return self.correctedXY()
                if item == "pos":
                    return self.pos()
                if item == "slice_x":
                    return self.slice_x()
                if item == "slice_y":
                    return self.slice_y()
                if item == "area":
                    return self.area()
                return BaseModel(self, item)

            def correctedXY(self):
                join_condition = ((Marker.image == Offset.image) & \
                                  (Marker.image_frame == Offset.image_frame))

                querry = Marker.select(Marker.x,
                                       Marker.y,
                                       Offset.x,
                                       Offset.y) \
                    .join(Offset, peewee.JOIN_LEFT_OUTER, on=join_condition) \
                    .where(Marker.id == self.id)

                for q in querry:
                    if not (q.offsets.x is None) or not (q.offsets.y is None):
                        pt = [q.x + q.offsets.x, q.y + q.offsets.y]
                    else:
                        pt = [q.x, q.y]

                return pt

            def pos(self):
                return np.array([self.x, self.y])

            def slice_x(self):
                if self.width < 0:
                    return slice(int(self.x+self.width), int(self.x))
                return slice(int(self.x), int(self.x+self.width))

            def slice_y(self):
                if self.height < 0:
                    return slice(int(self.y+self.height), int(self.y))
                return slice(int(self.y), int(self.y + self.height))

            def area(self):
                return self.width * self.height

        self.table_marker = Marker
        self.table_line = Line
        self.table_rectangle = Rectangle
        self.table_track = Track
        self.table_markertype = MarkerType
        self.tables.extend([Marker, Line, Rectangle, Track, MarkerType])

        """ Mask Tables """

        class Mask(BaseModel):
            image = peewee.ForeignKeyField(Image, related_name="masks", on_delete='CASCADE')
            data = ImageField()

            def __str__(self):
                return "MaskObject id%s: image=%s, data=%s" % (self.id, self.image, self.data)

        class MaskType(BaseModel):
            name = peewee.CharField()  # TODO make unique
            color = peewee.CharField()
            index = peewee.IntegerField(unique=True)

            def __str__(self):
                return "MasktypeObject id%s: name=%s, color=%s, index=%s" % (self.id, self.name, self.color, self.index)

        self.table_mask = Mask
        self.table_masktype = MaskType
        self.tables.extend([Mask, MaskType])
        self.mask_path = None

        """ Annotation Tables """

        class Annotation(BaseModel):
            image = peewee.ForeignKeyField(Image, related_name="annotations", on_delete='CASCADE')
            timestamp = peewee.DateTimeField(null=True)
            comment = peewee.TextField(default="")
            rating = peewee.IntegerField(default=0)

            def __getattr__(self, item):
                if item == "tags":
                    return [tagassociations.tag for tagassociations in self.tagassociations]
                else:
                    return BaseModel(self, item)

        class Tag(BaseModel):
            name = peewee.CharField()

            def __getattr__(self, item):
                if item == "annotations":
                    return [tagassociations.annotation for tagassociations in self.tagassociations]
                else:
                    return BaseModel(self, item)

        class TagAssociation(BaseModel):
            annotation = peewee.ForeignKeyField(Annotation, related_name="tagassociations", on_delete='CASCADE')
            tag = peewee.ForeignKeyField(Tag, related_name="tagassociations", on_delete='CASCADE')

        self.table_annotation = Annotation
        self.table_tag = Tag
        self.table_tagassociation = TagAssociation
        self.tables.extend([Annotation, Tag, TagAssociation])

        """ Connect """
        self.db.connect()
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
                self.db.execute_sql("ALTER TABLE images ADD COLUMN frame int")
                self.db.execute_sql("ALTER TABLE images ADD COLUMN sort_index int")
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
            with self.db.transaction():
                # Add text fields for Tracks
                self.db.execute_sql("ALTER TABLE tracks ADD COLUMN text varchar(255)")
                # Add text fields for Types
                self.db.execute_sql("ALTER TABLE types ADD COLUMN text varchar(255)")
            self._SetVersion(7)

        if nr_version < 8:
            print("\tto 8")
            with self.db.transaction():
                self.db.execute_sql("ALTER TABLE paths RENAME TO path")
                self.db.execute_sql("ALTER TABLE images RENAME TO image")
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
                mask_path = self.db.execute_sql("SELECT * FROM meta WHERE key = 'mask_path'").fetchone()[2]
                masks = self.db.execute_sql("SELECT id, image_id, filename FROM mask").fetchall()
                self.migrate_to_10_mask_path = mask_path
                self.migrate_to_10_masks = masks
                self.db.execute_sql("CREATE TABLE `mask_tmp` (`id` INTEGER NOT NULL, `image_id` INTEGER NOT NULL, `data` BLOB NOT NULL, PRIMARY KEY(id), FOREIGN KEY(`image_id`) REFERENCES 'image' ( 'id' ) ON DELETE CASCADE)")
                for mask in masks:
                    tmp_maskpath = os.path.join(self.migrate_to_10_mask_path, mask[2])
                    if os.path.exists(tmp_maskpath):
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
        for table in self.tables:
            table.create_table(fail_silently=True)

    def _processesTypeNameField(self, types):
        def CheckType(type):
            if isinstance(type, basestring):
                type_name = type
                type = self.getMarkerType(type)
                if type is None:
                    raise MarkerTypeDoesNotExist("No marker type with the name \"%s\" exists." % type_name)
            return type

        if isinstance(types, (tuple, list)):
            types = [CheckType(type) for type in types]
        else:
            types = CheckType(types)
        return types

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

    def _processImagesField(self, images, frames, filenames):
        print(images, frames, filenames)
        if images is not None:
            return images

        def CheckImageFrame(frame):
            image = self.getImage(frame=frame)
            if image is None:
                raise ImageDoesNotExit("No image with the frame number %s exists." % frame)
            return image

        def CheckImageFilename(filename):
            image = self.getImage(filename=filename)
            if image is None:
                raise ImageDoesNotExit("No image with the filename \"%s\" exists." % filename)
            return image

        if frames is not None:
            if isinstance(frames, (tuple, list)):
                images = [CheckImageFrame(frame) for frame in frames]
            else:
                images = CheckImageFrame(frames)
        else:
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
            if self.database_filename:
                try:
                    path_string = os.path.relpath(path_string, os.path.dirname(self.database_filename))
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

    def getPaths(self, path_strings=None, base_path=None, ids=None):
        """
        Get all :py:class:`Path` entries from the database, which match the given criteria. If no critera a given, return all paths.

        See also: :py:meth:`~.DataFile.getPath`, :py:meth:`~.DataFile.setPath`, :py:meth:`~.DataFile.deletePaths`

        Parameters
        ----------
        path_strings: string, path_string, optional
            the string/strings specifying the paths.
        base_path: string, optional
            return only paths starting with the base_path string.
        ids: int, array_like, optional
            the id/ids of the paths.

        Returns
        -------
        entries : array_like
            a query object containing all the matching :py:class:`Path` entries in the database file.
        """

        query = self.table_path.select()

        query = addFilter(query, ids, self.table_path.id)
        query = addFilter(query, path_strings, self.table_path.path)
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

    def deletePaths(self, path_strings=None, base_path=None, ids=None):
        """
        Delete all :py:class:`Path` entries with the given criteria.

        See also: :py:meth:`~.DataFile.getPath`, :py:meth:`~.DataFile.getPaths`, :py:meth:`~.DataFile.setPath`

        Parameters
        ----------
        path_strings: string, optional
            the string/strings specifying the paths.
        base_path: string, optional
            return only paths starting with the base_path string.
        ids: int, optional
            the id/ids of the paths.

        Returns
        -------
        rows : int
            the number of affected rows.
        """

        query = self.table_path.delete()

        query = addFilter(query, ids, self.table_path.id)
        query = addFilter(query, path_strings, self.table_path.path)
        if base_path is not None:
            query = query.where(self.table_path.path.startswith(base_path))
        return query.execute()

    def getImage(self, frame=None, filename=None, id=None):
        """
        Returns the :py:class:`Image` entry with the given frame number.

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

        Returns
        -------
        image : :py:class:`Image`
            the image entry.
        """

        kwargs = noNoneDict(sort_index=frame, filename=filename, id=id)
        try:
            return self.table_image.get(**kwargs)
        except peewee.DoesNotExist:
            KeyError("No image with %s found." % VerboseDict(kwargs))

    def getImages(self, frames=None, filenames=None, exts=None, external_ids=None, timestamps=None, widths=None, heights=None, paths=None, order_by="sort_index"):
        """
        Get all :py:class:`Image` entries sorted by sort index. For large databases :py:meth:`~.DataFile.getImageIterator`, should be used
        as it doesn't load all frames at once.

        See also: :py:meth:`~.DataFile.getImage`, :py:meth:`~.DataFile.getImageIterator`, :py:meth:`~.DataFile.setImage`,
        :py:meth:`~.DataFile.deleteImages`.

        Parameters
        ----------
        frames : int, array_like, optional
            the frame/frames of the images
        filenames : string, array_like, optional
            the filename/filenames of the images
        exts : string, array_like, optional
            the extension/extensions of the images
        TODO

        Returns
        -------
        entries : array_like
            a query object containing all the :py:class:`Image` entries in the database file.
        """

        query = self.table_image.select()

        query = addFilter(query, frames, self.table_image.sort_index)
        query = addFilter(query, filenames, self.table_image.filename)
        query = addFilter(query, exts, self.table_image.ext)
        query = addFilter(query, external_ids, self.table_image.external_id)
        query = addFilter(query, timestamps, self.table_image.timestamp)
        query = addFilter(query, widths, self.table_image.width)
        query = addFilter(query, heights, self.table_image.height)
        query = addFilter(query, paths, self.table_image.path)

        if order_by == "sort_index":
            query = query.order_by(self.table_image.sort_index)
        elif order_by == "timestamp":
            query = query.order_by(self.table_image.timestamp)
        else:
            raise Exception("Unknown order_by parameter - use sort_index or timestamp")

        return query

    def getImageIterator(self, start_frame=0, end_frame=None):  #TODO: end_frame
        """
        Get an iterator to iterate over all :py:class:`Image` entries starting from start_frame.

        See also: :py:meth:`~.DataFile.getImage`, :py:meth:`~.DataFile.getImages`, :py:meth:`~.DataFile.setImage`,  :py:meth:`~.DataFile.deleteImages`.

        Parameters
        ----------
        start_frame : int, optional
            start at the image with the number start_frame. Default is 0
        end_frame

        Returns
        -------
        entries : array_like
            a query object containing all the :py:class:`Image` entries in the database file.

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

        frame = start_frame
        while True:
            try:
                image = self.table_image.get(self.table_image.sort_index == frame)
                yield image
            except peewee.DoesNotExist:
                break
            frame += 1

    def setImage(self, filename=None, path=None, frame=None, external_id=None, timestamp=None, width=None, height=None, id=None):

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

        if filename is not None:
            item.filename = os.path.split(filename)[1]
            item.ext = os.path.splitext(filename)[1]
            if path is None:
                item.path = self.getPath(path_string=os.path.split(filename)[0], create=True)
        if isinstance(path, basestring):
            path = self.getPath(path)
        setFields(item, noNoneDict(frame=frame, path=path, external_id=external_id, timestamp=timestamp, width=width, height=height))
        if new_image:
            if self.next_sort_index is None:
                query = self.table_image.select().order_by(-self.table_image.sort_index).limit(1)  # TODO more efficent sort index retrieval
                try:
                    self.next_sort_index = query[0].sort_index + 1
                except IndexError:
                    self.next_sort_index = 0
            item.sort_index = self.next_sort_index
            self.next_sort_index += 1

        item.save()
        return item

    def deleteImages(self, filenames=None, paths=None, frames=None, external_ids=None, timestamps=None, widths=None, heights=None, ids=None):
        """
        Delete all :py:class:`Image` entries with the given criteria.

        See also: :py:meth:`~.DataFile.getImage`, :py:meth:`~.DataFile.getImages`, :py:meth:`~.DataFile.getImageIterator`, :py:meth:`~.DataFile.setImage`.

        Parameters
        ----------
        filenames : string, array_like, optional
            the filename/filenames of the image (including the extension)
        paths : string, int, :py:class:`Path`, array_like optional
            the path string, id or entry of the image to insert
        frames : int, array_like, optional
            the number/numbers of frames the images have
        external_ids : int, array_like, optional
            an external id/ids for the images. Only necessary if the annotation server is used
        timestamps : datetime object, array_like, optional
            the timestamp/timestamps of the images
        widths : int, array_like, optional
            the width/widths of the images
        heights : int, optional
            the height/heights of the images
        ids : int, array_like, optional
            the id/ids of the images

        Returns
        -------
        rows : int
            the number of affected rows.
        """
        query = self.table_image.delete()

        paths = self._processPathNameField(paths)

        query = addFilter(query, ids, self.table_image.id)
        query = addFilter(query, paths, self.table_image.path)
        query = addFilter(query, filenames, self.table_image.filename)
        query = addFilter(query, frames, self.table_image.frame)
        query = addFilter(query, external_ids, self.table_image.external_id)
        query = addFilter(query, timestamps, self.table_image.timestamp)
        query = addFilter(query, widths, self.table_image.width)
        query = addFilter(query, heights, self.table_image.height)
        return query.execute()

    def getTracks(self, types=None, texts=None, ids=None):
        """
        Get all :py:class:`Track` entries, optional filter by type

        See also: :py:meth:`~.DataFile.getTrack`, :py:meth:`~.DataFile.setTrack`, :py:meth:`~.DataFile.setTracks`, :py:meth:`~.DataFile.deleteTracks`.

        Parameters
        ----------
        types: :py:class:`MarkerType`, str, array_like
            the marker type/types or name of the marker type for the track.
        texts :
            the :py:class:`Track` specific text entry
        ids : int, array_like
            the  :py:class:`Track` ID

        Returns
        -------
        entries : array_like
            a query object which contains the requested :py:class:`Track`.
        """
        types = self._processesTypeNameField(types)

        query = self.table_track.select()
        query = addFilter(query, types, self.table_track.type)
        query = addFilter(query, texts, self.table_track.text)
        query = addFilter(query, ids, self.table_track.id)

        return query

    def getTrack(self, id):
        """
        Get a specific :py:class:`Track` entry by its database ID.

        See also: :py:meth:`~.DataFile.getTracks`, :py:meth:`~.DataFile.setTracks`, :py:meth:`~.DataFile.deleteTracks`.

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

    def setTrack(self, type, style=None, text=None, id=None):
        """
        Insert or update a :py:class:`Track` object.

        See also: :py:meth:`~.DataFile.getTrack`, :py:meth:`~.DataFile.getTracks`, :py:meth:`~.DataFile.getTracks`, :py:meth:`~.DataFile.deleteTracks`.


        Parameters
        ----------
        type: :py:class:`MarkerType` or str
            the marker type or name of the marker type for the track.
        style:
            the :py:class:`Track` specific style entry
        texts :
            the :py:class:`Track` specific text entry
        ids : int, array_like
            the  :py:class:`Track` ID


        Returns
        -------
        track : track object
            a new :py:class:`Track` object
        """
        type = self._processesTypeNameField(type)

        item = self.table_track.insert(id=id, type=type, style=style, text=text).upsert().execute()

        return item

    def deleteTacks(self, types=None, texts=None, ids=None):
        """
        Delete a single :py:class:`Track` object specified by id or all :py:class:`Track` object of an type

        See also: :py:meth:`~.DataFile.getTrack`, :py:meth:`~.DataFile.getTracks`, :py:meth:`~.DataFile.setTrack`, :py:meth:`~.DataFile.setTracks`.

        Parameters
        ----------
        types: :py:class:`MarkerType` or str
            the marker type or name of the marker type
        texts :
            the :py:class:`Track` specific text entry
        ids : int, array_like
            the  :py:class:`Track` ID

        Returns
        -------
        rows : int
            the number of affected rows.
        """

        types = self._processesTypeNameField(types)

        query = self.table_track.delete()
        query = addFilter(query, ids, self.table_track.id)
        query = addFilter(query, texts, self.table_track.text)
        query = addFilter(query, types, self.table_track.type)
        return query.execute()

    def getMarkerTypes(self, names=None, colors=None, modes=None, texts=None, ids=None):
        """
        Retreive all :py:class:`MarkerType` objects in the database.

        See also: :py:meth:`~.DataFile.setMarkerType`, :py:meth:`~.DataFile.getMarkerTypes`, :py:meth:`~.DataFile.deleteMarkerType`.

        Parameters
        ----------
        names: str
            the name of the type
        colors: str
            hex code string for rgb color of style "#00ff3f"
        modes: int
            mode of the marker type (marker 0, rect 1, line 2, track 4)
        texts: str
            display text
        ids: int
            id of the :py:class:`MarkerType` object

        Returns
        -------
        entries : array_like
            a query object which contains all :py:class:`MarkerType` entries.
        """
        query = self.table_markertype.select()

        query = addFilter(query, names, self.table_markertype.name)
        query = addFilter(query, colors, self.table_markertype.color)
        query = addFilter(query, modes, self.table_markertype.mode)
        query = addFilter(query, texts, self.table_markertype.text)
        query = addFilter(query, ids, self.table_markertype.id)

        return query

    def getMarkerType(self, name=None, id=None):
        """
        Retrieve an :py:class:`MarkerType` object from the database.

        See also: :py:meth:`~.DataFile.setMarkerType`, :py:meth:`~.DataFile.getMarkerTypes`, :py:meth:`~.DataFile.deleteMarkerType`.

        Parameters
        ----------
        name: str
            the name of the desired type
        id: int
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

    def setMarkerType(self, name=None, color=None, mode=None, style=None, text=None, id=None):
        """
        Insert or update an :py:class:`MarkerType` object in the database.

        See also: :py:meth:`~.DataFile.getMarkerType`, :py:meth:`~.DataFile.getMarkerTypes`, :py:meth:`~.DataFile.deleteMarkerType`.

        Parameters
        ----------
        name: str
            the name of the type
        color: str
            hex code string for rgb color of style "#00ff3f"
        mode: int
            mode of the marker type (marker 0, rect 1, line 2, track 4)
        style: str
            style string
        text: str
            display text
        id: int
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
        setFields(item, dict(name=name, color=color, mode=mode, style=style, text=text))
        item.save()
        return item

    def deleteMarkerTypes(self, names=None, colors=None, modes=None, texts=None, ids=None):
        """
        Delete all :py:class:`MarkerType` entries from the database, which match the given criteria.

        See also: :py:meth:`~.DataFile.getMarkerType`, :py:meth:`~.DataFile.getMarkerTypes`, :py:meth:`~.DataFile.setMarkerType`.

        Parameters
        ----------
        names: str
            the name of the type
        colors: str
            hex code string for rgb color of style "#00ff3f"
        modes: int
            mode of the marker type (marker 0, rect 1, line 2, track 4)
        texts: str
            display text
        ids: int
            id of the :py:class:`MarkerType` object

        Returns
        -------
        entries : int
            nr of deleted entries
        """
        query = self.table_markertype.delete()

        query = addFilter(query, names, self.table_markertype.name)
        query = addFilter(query, colors, self.table_markertype.color)
        query = addFilter(query, modes, self.table_markertype.mode)
        query = addFilter(query, texts, self.table_markertype.text)
        query = addFilter(query, ids, self.table_markertype.id)

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

    def getMaskTypes(self, names=None, colors=None, indices=None, ids=None):
        """
        Get all :py:class:`MaskType` entries from the database, which match the given criteria. If no criteria a given,
        return all mask types.

        See also: :py:meth:`~.DataFile.getMaskType`, :py:meth:`~.DataFile.setMaskType`,
        :py:meth:`~.DataFile.deleteMaskTypes`.

        Parameters
        ----------
        names : string, array_like, optional
            the name/names of the mask types.
        colors : string, array_like, optional
            the color/colors of the mask types.
        indices : int, array_like, optional
            the index/indices of the mask types, which is used for painting this mask types.
        ids : int, array_like, optional
            the id/ids of the mask types.

        Returns
        -------
        entries : array_like
            a query object containing all the matching :py:class:`MaskType` entries in the database file.
        """

        query = self.table_masktype.select()

        if colors:
            colors = NormalizeColor(colors)

        query = addFilter(query, ids, self.table_masktype.id)
        query = addFilter(query, names, self.table_masktype.name)
        query = addFilter(query, colors, self.table_masktype.color)
        query = addFilter(query, indices, self.table_masktype.index)
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
            free_idxs = list(set(range(1,254)) - set(index_list))
            index = free_idxs[0]

        try:
            # only use id if multiple unique fields are specified
            if id:
                mask_type = self.table_masktype.get(id=id)
            else:
                mask_type = self.table_masktype.get(**noNoneDict(id=id, name=name, color=color, index=index))
        except peewee.DoesNotExist:
            mask_type = self.table_masktype()

        setFields(mask_type, dict(name=name, color=color, index=index))
        mask_type.save()

        return mask_type

    def deleteMaskTypes(self, names=None, colors=None, indices=None, ids=None):
        """
        Delete all :py:class:`MaskType` entries from the database, which match the given criteria.

        See also: :py:meth:`~.DataFile.getMaskType`, :py:meth:`~.DataFile.getMaskTypes`, :py:meth:`~.DataFile.setMaskType`.

        Parameters
        ----------
        names : string, array_like, optional
            the name/names of the mask types.
        colors : string, array_like, optional
            the color/colors of the mask types.
        indices : int, array_like, optional
            the index/indices of the mask types, which is used for painting this mask types.
        ids : int, array_like, optional
            the id/ids of the mask types.
        """

        query = self.table_masktype.delete()

        # normalize and check color values
        if colors:
            colors = NormalizeColor(colors)

        query = addFilter(query, ids, self.table_masktype.id)
        query = addFilter(query, names, self.table_masktype.name)
        query = addFilter(query, colors, self.table_masktype.color)
        query = addFilter(query, indices, self.table_masktype.index)
        query.execute()

    def getMask(self, image=None, frame=None, filename=None, id=None, create=False):
        """
        Get the :py:class:`Mask` entry for the given image frame number or filename.

        See also: :py:meth:`~.DataFile.getMasks`, :py:meth:`~.DataFile.setMask`, :py:meth:`~.DataFile.deleteMask`.

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

        Returns
        -------
        entries : :py:class:`Mask`
            the desired :py:class:`Mask` entry.
        """
        # check input
        assert sum(e is not None for e in [id, image, frame, filename]) == 1, \
            "Exactly one of image, frame or filename should be specified or should be referenced by it's id."

        query = self.table_mask.select(self.table_mask, self.table_image).join(self.table_image)

        query = addFilter(query, id, self.table_mask.id)
        query = addFilter(query, frame, self.table_image.sort_index)
        query = addFilter(query, filename, self.table_image.filename)
        query.limit(1)

        try:
            return query[0]
        except IndexError:
            if create is True:
                image = self.getImage(frame, filename)
                data = np.zeros(image.getShape())  # TODO exception if image can't be loaded
                mask = self.table_mask.get(image=image, data=data)
                mask.save()
                return mask
            return None

    def getMasks(self, images=None, frames=None, filenames=None, ids=None):
        """
        Get all :py:class:`Mask` entries from the database, which match the given criteria. If no criteria a given, return all masks.

        See also: :py:meth:`~.DataFile.getMask`, :py:meth:`~.DataFile.setMask`, :py:meth:`~.DataFile.deleteMask`.

        Parameters
        ----------
        images : int, :py:class:`Image`, array_like, optional
            the image/images for which the mask should be retrieved. If omitted, frame numbers or filenames should be specified instead.
        frames: int, array_like, optional
            frame number/numbers of the images, which masks should be returned. If omitted, images or filenames should be specified instead.
        filenames: string, array_like, optional
            filename of the image/images, which masks should be returned. If omitted, images or frame numbers should be specified instead.
        ids : int, array_like, optional
            id/ids of the masks.

        Returns
        -------
        entries : :py:class:`Mask`
            a query object containing all the matching :py:class:`Mask` entries in the database file.
        """
        # check input
        assert sum(e is not None for e in [images, frames, filenames]) == 1, \
            "Exactly one of images, frames or filenames should be specified"

        query = self.table_mask.select(self.table_mask, self.table_image).join(self.table_image)

        query = addFilter(query, ids, self.table_mask.id)
        query = addFilter(query, images, self.table_mask.image)
        query = addFilter(query, frames, self.table_image.sort_index)
        query = addFilter(query, filenames, self.table_image.filename)

        return query

    def setMask(self, image=None, frame=None, filename=None, data=None, id=None):
        """
        Update or create new :py:class:`Mask` entry with the given parameters.

        See also: :py:meth:`~.DataFile.getMask`, :py:meth:`~.DataFile.getMasks`, :py:meth:`~.DataFile.deleteMask`.

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

        Returns
        -------
        mask : :py:class:`Mask`
            the changed or created :py:class:`Mask` entry.
        """
        # check input
        assert sum(e is not None for e in [id, image, frame, filename]) == 1, \
            "Exactly one of image, frame or filename should be specified or an id"

        # TODO check data shape and datatype warn if it couldn't be checked

        mask = self.getMask(image=image, frame=frame, filename=filename, id=id)

        if not mask:
            print("entering exception")
            if data is None:
                image = self.getImage(frame, filename)
                dir(image)
                data = np.zeros(image.getShape())  # TODO raise if dimensions cant be retrieved
            mask = self.table_mask(image=image, data=data)

        print(mask)
        setFields(mask, dict(data=data, image=image))
        if frame is not None or filename is not None:
            mask.image = self.getImage(frame=frame, filename=filename)
        mask.save()

        return mask

    def deleteMasks(self, images=None, frames=None, filenames=None, ids=None):
        """
        Delete all :py:class:`Mask` entries with the given criteria.

        See also: :py:meth:`~.DataFile.getMask`, :py:meth:`~.DataFile.getMasks`, :py:meth:`~.DataFile.setMask`.

        Parameters
        ----------
        images : int, :py:class:`Image`, array_like, optional
            the image/images for which the mask should be deleted. If omitted, frame numbers or filenames should be specified instead.
        frames: int, array_like, optional
            frame number/numbers of the images, which masks should be deleted. If omitted, images or filenames should be specified instead.
        filenames: string, array_like, optional
            filename of the image/images, which masks should be deleted. If omitted, images or frame numbers should be specified instead.
        ids : int, array_like, optional
            id/ids of the masks.
        """
        # check input
        assert sum(e is not None for e in [images, frames, filenames]) == 1, \
            "Exactly one of images, frames or filenames should be specified"

        # TODO test if join is possible

        query = self.table_mask.delete(self.table_mask, self.table_image).join(self.table_image)

        query = addFilter(query, ids, self.table_mask.id)
        query = addFilter(query, images, self.table_mask.image)
        query = addFilter(query, frames, self.table_image.sort_index)
        query = addFilter(query, filenames, self.table_image.filename)
        query.execute()




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

    def getMarkers(self, images=None, frames=None, filenames=None, xs=None, ys=None, types=None, processed=None, tracks=None, texts=None, ids=None):
        """
        Get all :py:class:`Marker` entries with the given criteria.

        See also: :py:meth:`~.DataFile.getMarker`, :py:meth:`~.DataFile.getMarkers`, :py:meth:`~.DataFile.setMarker`, :py:meth:`~.DataFile.setMarkers`, :py:meth:`~.DataFile.deleteMarkers`.

        Parameters
        ----------
        images : int, :py:class:`Image`, array_like, optional
            the image/s of the markers.
        frames : int, array_like, optional
            the frame/s of the images of the markers.
        filenames : string, array_like, optional
            the filename/s of the images of the markers.
        xs : int, array_like, optional
            the x coordinate/s of the markers.
        ys : int, array_like, optional
            the y coordinate/s of the markers.
        types : string, :py:class:`MarkerType`, array_like, optional
            the marker type/s (or name/s) of the markers.
        processed : int, array_like, optional
            the processed flag/s of the markers.
        tracks : int, :py:class:`Track`, array_like, optional
            the track id/s or instance/s of the markers.
        texts : string, array_like, optional
            the text/s of the markers.
        ids : int, array_like, optional
            the id/s of the markers.

        Returns
        -------
        entries : array_like
            a query object which contains all :py:class:`Marker` entries.
        """
        types = self._processesTypeNameField(types)

        query = self.table_marker.select(self.table_marker, self.table_image).join(self.table_image)

        query = addFilter(query, ids, self.table_marker.id)
        query = addFilter(query, images, self.table_marker.image)
        query = addFilter(query, frames, self.table_image.sort_index)
        query = addFilter(query, filenames, self.table_image.filename)
        query = addFilter(query, xs, self.table_marker.x)
        query = addFilter(query, ys, self.table_marker.y)
        query = addFilter(query, types, self.table_marker.type)
        query = addFilter(query, processed, self.table_marker.processed)
        query = addFilter(query, tracks, self.table_marker.track)
        query = addFilter(query, texts, self.table_marker.text)

        return query

    def setMarker(self, image=None, frame=None, filename=None, x=None, y=None, type=None, processed=None, track=None, style=None, text=None, id=None):
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

        type = self._processesTypeNameField(type)
        image = self._processImagesField(image, frame, filename)

        setFields(item, dict(image=image, x=x, y=y, type=type, processed=processed, track=track, style=style, text=text))
        item.save()
        return item

    def setMarkers(self, images=None, frames=None, filenames=None, xs=None, ys=None, types=None, processed=None,
                   tracks=None, styles=None, texts=None, ids=None):
        """
        Insert or update multiple :py:class:`Marker` objects in the database.

        See also: :py:meth:`~.DataFile.getMarker`, :py:meth:`~.DataFile.getMarkers`, :py:meth:`~.DataFile.setMarker`,
         :py:meth:`~.DataFile.deleteMarkers`.

        Parameters
        ----------
        images : int, :py:class:`Image`, array_like, optional
            the image/s of the markers.
        frames : int, array_like, optional
            the frame/s of the images of the markers.
        filenames : string, array_like, optional
            the filename/s of the images of the markers.
        xs : int, array_like, optional
            the x coordinate/s of the markers.
        ys : int, array_like, optional
            the y coordinate/s of the markers.
        types : string, :py:class:`MarkerType`, array_like, optional
            the marker type/s (or name/s) of the markers.
        processed : int, array_like, optional
            the processed flag/s of the markers.
        tracks : int, :py:class:`Track`, array_like, optional
            the track id/s or instance/s of the markers.
        texts : string, array_like, optional
            the text/s of the markers.
        ids : int, array_like, optional
            the id/s of the markers.

        Returns
        -------
        success : bool
            it the inserting was successful.
        """
        types = self._processesTypeNameField(types)
        images = self._processImagesField(images, frames, filenames)

        data = packToDictList(id=ids, image=images, x=xs, y=ys, processed=processed, type=types, track=tracks,
                              style=styles, text=texts)
        return self.table_marker.insert_many(data).upsert().execute()

    def deleteMarkers(self, images=None, frames=None, filenames=None, xs=None, ys=None, types=None, processed=None,
                      tracks=None, texts=None, ids=None):
        """
        Delete all :py:class:`Marker` entries with the given criteria.

        See also: :py:meth:`~.DataFile.getMarker`, :py:meth:`~.DataFile.getMarkers`, :py:meth:`~.DataFile.setMarker`,
        :py:meth:`~.DataFile.setMarkers`.

        Parameters
        ----------
        images : int, :py:class:`Image`, array_like, optional
            the image/s of the markers.
        frames : int, array_like, optional
            the frame/s of the images of the markers.
        filenames : string, array_like, optional
            the filename/s of the images of the markers.
        xs : int, array_like, optional
            the x coordinate/s of the markers.
        ys : int, array_like, optional
            the y coordinate/s of the markers.
        types : string, :py:class:`MarkerType`, array_like, optional
            the marker type/s (or name/s) of the markers.
        processed : int, array_like, optional
            the processed flag/s of the markers.
        tracks : int, :py:class:`Track`, array_like, optional
            the track id/s or instance/s of the markers.
        texts : string, array_like, optional
            the text/s of the markers.
        ids : int, array_like, optional
            the id/s of the markers.

        Returns
        -------
        rows : int
            the number of affected rows.
        """
        types = self._processesTypeNameField(types)

        query = self.table_marker.delete()

        if images is None:
            images = self.table_image.select()
            images = addFilter(images, frames, self.table_image.sort_index)
            images = addFilter(images, filenames, self.table_image.filename)
            query = query.where(self.table_marker.image.in_(images))
        else:
            query = addFilter(query, images, self.table_mask.image)

        query = addFilter(query, ids, self.table_marker.id)
        query = addFilter(query, xs, self.table_marker.x)
        query = addFilter(query, ys, self.table_marker.y)
        query = addFilter(query, types, self.table_marker.type)
        query = addFilter(query, processed, self.table_marker.processed)
        query = addFilter(query, tracks, self.table_marker.track)
        query = addFilter(query, texts, self.table_marker.text)

        return query.execute()



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

    def getLines(self, images=None, frames=None, filenames=None, xs1=None, ys1=None, xs2=None, ys2=None, types=None,
                 processed=None, texts=None, ids=None):
        """
        Get all :py:class:`Line` entries with the given criteria.

        See also: :py:meth:`~.DataFile.getLine`, :py:meth:`~.DataFile.setLine`, :py:meth:`~.DataFile.setLines`,
        :py:meth:`~.DataFile.deleteLines`.

        Parameters
        ----------
        images : int, :py:class:`Image`, array_like, optional
            the image/s of the lines.
        frames : int, array_like, optional
            the frame/s of the images of the lines.
        filenames : string, array_like, optional
            the filename/s of the images of the lines.
        xs1 : int, array_like, optional
            the x coordinate/s of the lines start.
        ys1 : int, array_like, optional
            the y coordinate/s of the lines start.
        xs2 : int, array_like, optional
            the x coordinate/s of the lines end.
        ys2 : int, array_like, optional
            the y coordinate/s of the lines end.
        types : string, :py:class:`MarkerType`, array_like, optional
            the marker type/s (or name/s) of the lines.
        processed : int, array_like, optional
            the processed flag/s of the lines.
        texts : string, array_like, optional
            the text/s of the lines.
        ids : int, array_like, optional
            the id/s of the lines.

        Returns
        -------
        entries : array_like
            a query object which contains all :py:class:`Line` entries.
        """
        types = self._processesTypeNameField(types)

        query = self.table_line.select(self.table_line, self.table_image).join(self.table_image)

        query = addFilter(query, ids, self.table_line.id)
        query = addFilter(query, images, self.table_line.image)
        query = addFilter(query, frames, self.table_image.sort_index)
        query = addFilter(query, filenames, self.table_image.filename)
        query = addFilter(query, xs1, self.table_line.x1)
        query = addFilter(query, ys1, self.table_line.y1)
        query = addFilter(query, xs2, self.table_line.x2)
        query = addFilter(query, ys2, self.table_line.y2)
        query = addFilter(query, types, self.table_line.type)
        query = addFilter(query, processed, self.table_line.processed)
        query = addFilter(query, texts, self.table_line.text)

        return query

    def setLine(self, image=None, frame=None, filename=None, x1=None, y1=None, x2=None, y2=None, type=None, processed=None, style=None, text=None, id=None):
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

        type = self._processesTypeNameField(type)
        image = self._processImagesField(image, frame, filename)

        setFields(item, dict(image=image, x1=x1, y1=y1, x2=x2, y2=y2, type=type, processed=processed, style=style, text=text))
        item.save()
        return item

    def setLines(self, images=None, frames=None, filenames=None, xs1=None, ys1=None, xs2=None, ys2=None, types=None,
                 processed=None, styles=None, texts=None, ids=None):
        """
        Insert or update multiple :py:class:`Line` objects in the database.

        See also: :py:meth:`~.DataFile.getLine`, :py:meth:`~.DataFile.getLines`, :py:meth:`~.DataFile.setLine`,
        :py:meth:`~.DataFile.deleteLines`.

        Parameters
        ----------
        images : int, :py:class:`Image`, array_like, optional
            the image/s of the lines.
        frames : int, array_like, optional
            the frame/s of the images of the lines.
        filenames : string, array_like, optional
            the filename/s of the images of the lines.
        xs1 : int, array_like, optional
            the x coordinate/s of the start of the lines.
        ys1 : int, array_like, optional
            the y coordinate/s of the start of the lines.
        xs2 : int, array_like, optional
            the x coordinate/s of the end of the lines.
        ys2 : int, array_like, optional
            the y coordinate/s of the end of the lines.
        types : string, :py:class:`MarkerType`, array_like, optional
            the marker type/s (or name/s) of the lines.
        processed : int, array_like, optional
            the processed flag/s of the lines.
        tracks : int, :py:class:`Track`, array_like, optional
            the track id/s or instance/s of the lines.
        texts : string, array_like, optional
            the text/s of the lines.
        ids : int, array_like, optional
            the id/s of the lines.

        Returns
        -------
        success : bool
            it the inserting was successful.
        """
        types = self._processesTypeNameField(types)
        images = self._processImagesField(images, frames, filenames)

        data = packToDictList(id=ids, image=images, x1=xs1, y1=ys1, x2=xs2, y2=ys2, processed=processed, type=types,
                              style=styles, text=texts)
        return self.table_line.insert_many(data).upsert().execute()

    def deleteLines(self, images=None, frames=None, filenames=None, xs1=None, ys1=None, xs2=None, ys2=None, types=None,
                    processed=None, texts=None, ids=None):
        """
        Delete all :py:class:`Marker` entries with the given criteria.

        See also: :py:meth:`~.DataFile.getLine`, :py:meth:`~.DataFile.getLines`, :py:meth:`~.DataFile.setLine`,
        :py:meth:`~.DataFile.setLines`.

        Parameters
        ----------
        images : int, :py:class:`Image`, array_like, optional
            the image/s of the lines.
        frames : int, array_like, optional
            the frame/s of the images of the lines.
        filenames : string, array_like, optional
            the filename/s of the images of the lines.
        xs1 : int, array_like, optional
            the x coordinate/s of the start of the lines.
        ys1 : int, array_like, optional
            the y coordinate/s of the start of the lines.
        xs2 : int, array_like, optional
            the x coordinate/s of the end of the lines.
        ys2 : int, array_like, optional
            the y coordinate/s of the end of the lines.
        types : string, :py:class:`MarkerType`, array_like, optional
            the marker type/s (or name/s) of the lines.
        processed : int, array_like, optional
            the processed flag/s of the lines.
        texts : string, array_like, optional
            the text/s of the lines.
        ids : int, array_like, optional
            the id/s of the lines.

        Returns
        -------
        rows : int
            the number of affected rows.
        """
        types = self._processesTypeNameField(types)

        query = self.table_line.delete()

        if images is None:
            images = self.table_image.select()
            images = addFilter(images, frames, self.table_image.sort_index)
            images = addFilter(images, filenames, self.table_image.filename)
            query = query.where(self.table_line.image.in_(images))
        else:
            query = addFilter(query, images, self.table_mask.image)

        query = addFilter(query, ids, self.table_line.id)
        query = addFilter(query, xs1, self.table_line.x1)
        query = addFilter(query, ys1, self.table_line.y1)
        query = addFilter(query, xs2, self.table_line.x2)
        query = addFilter(query, ys2, self.table_line.y2)
        query = addFilter(query, types, self.table_line.type)
        query = addFilter(query, processed, self.table_line.processed)
        query = addFilter(query, texts, self.table_line.text)

        return query.execute()


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

    def getRectangles(self, images=None, frames=None, filenames=None, xs=None, ys=None, widths=None, heights=None, types=None,
                 processed=None, texts=None, ids=None):
        """
        Get all :py:class:`Rectangle` entries with the given criteria.

        See also: :py:meth:`~.DataFile.getRectangle`, :py:meth:`~.DataFile.setRectangle`,
        :py:meth:`~.DataFile.setRectangles`, :py:meth:`~.DataFile.deleteRectangles`.

        Parameters
        ----------
        images : int, :py:class:`Image`, array_like, optional
            the image/s of the rectangles.
        frames : int, array_like, optional
            the frame/s of the images of the rectangles.
        filenames : string, array_like, optional
            the filename/s of the images of the rectangles.
        xs : int, array_like, optional
            the x coordinate/s of the upper left corner/s of the rectangles.
        ys : int, array_like, optional
            the y coordinate/s of the upper left corner/s of the rectangles.
        widths : int, array_like, optional
            the width/s of the rectangles.
        heights : int, array_like, optional
            the height/s of the rectangles.
        types : string, :py:class:`MarkerType`, array_like, optional
            the marker type/s (or name/s) of the rectangles.
        processed : int, array_like, optional
            the processed flag/s of the rectangles.
        texts : string, array_like, optional
            the text/s of the rectangles.
        ids : int, array_like, optional
            the id/s of the rectangles.

        Returns
        -------
        entries : array_like
            a query object which contains all :py:class:`Rectangle` entries.
        """
        types = self._processesTypeNameField(types)

        query = self.table_rectangle.select(self.table_rectangle, self.table_image).join(self.table_image)

        query = addFilter(query, ids, self.table_rectangle.id)
        query = addFilter(query, images, self.table_rectangle.image)
        query = addFilter(query, frames, self.table_image.sort_index)
        query = addFilter(query, filenames, self.table_image.filename)
        query = addFilter(query, xs, self.table_rectangle.x)
        query = addFilter(query, ys, self.table_rectangle.y)
        query = addFilter(query, heights, self.table_rectangle.height)
        query = addFilter(query, widths, self.table_rectangle.width)
        query = addFilter(query, types, self.table_rectangle.type)
        query = addFilter(query, processed, self.table_rectangle.processed)
        query = addFilter(query, texts, self.table_rectangle.text)

        return query

    def setRectangle(self, image=None, frame=None, filename=None, x=None, y=None, width=None, height=None, type=None,
                     processed=None, style=None, text=None, id=None):
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
            the y coordinate of the upper left of the rectangle.
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

        type = self._processesTypeNameField(type)
        image = self._processImagesField(image, frame, filename)

        setFields(item, dict(image=image, x=x, y=y, width=width, height=height, type=type, processed=processed, style=style, text=text))
        item.save()
        return item

    def setRectangles(self, images=None, frames=None, filenames=None, xs=None, ys=None, widths=None, heights=None, types=None,
                 processed=None, styles=None, texts=None, ids=None):
        """
        Insert or update multiple :py:class:`Rectangle` objects in the database.

        See also: :py:meth:`~.DataFile.getRectangle`, :py:meth:`~.DataFile.getRectangles`,
        :py:meth:`~.DataFile.setRectangle`, :py:meth:`~.DataFile.deleteRectangles`.

        Parameters
        ----------
        images : int, :py:class:`Image`, array_like, optional
            the image/s of the rectangles.
        frames : int, array_like, optional
            the frame/s of the images of the rectangles.
        filenames : string, array_like, optional
            the filename/s of the images of the rectangles.
        xs : int, array_like, optional
            the x coordinate/s of the upper left corner/s of the rectangles.
        ys : int, array_like, optional
         the y coordinate/s of the upper left corner/s of the rectangles.
        widths : int, array_like, optional
            the width/s of the rectangles.
        heights : int, array_like, optional
            the height/s of the rectangles.
        types : string, :py:class:`MarkerType`, array_like, optional
            the marker type/s (or name/s) of the rectangles.
        processed : int, array_like, optional
            the processed flag/s of the rectangles.
        tracks : int, :py:class:`Track`, array_like, optional
            the track id/s or instance/s of the rectangles.
        texts : string, array_like, optional
            the text/s of the rectangles.
        ids : int, array_like, optional
            the id/s of the rectangles.

        Returns
        -------
        success : bool
            it the inserting was successful.
        """
        types = self._processesTypeNameField(types)
        images = self._processImagesField(images, frames, filenames)

        data = packToDictList(id=ids, image=images, x=xs, y=ys, width=widths, height=heights, processed=processed, type=types,
                              style=styles, text=texts)
        return self.table_rectangle.insert_many(data).upsert().execute()

    def deleteRectangles(self, images=None, frames=None, filenames=None, xs=None, ys=None, widths=None, heights=None, types=None,
                    processed=None, texts=None, ids=None):
        """
        Delete all :py:class:`Rectangle` entries with the given criteria.

        See also: :py:meth:`~.DataFile.getRectangle`, :py:meth:`~.DataFile.getRectangles`,
        :py:meth:`~.DataFile.setRectangle`, :py:meth:`~.DataFile.setRectangles`.

        Parameters
        ----------
        images : int, :py:class:`Image`, array_like, optional
            the image/s of the rectangles.
        frames : int, array_like, optional
            the frame/s of the images of the rectangles.
        filenames : string, array_like, optional
            the filename/s of the images of the rectangles.
        xs : int, array_like, optional
            the x coordinate/s of the upper left corner/s of the rectangles.
        ys : int, array_like, optional
            the y coordinate/s of the upper left corner/s of the rectangles.
        widths : int, array_like, optional
            the width/s of the rectangles.
        heights : int, array_like, optional
            the height/s of the rectangles.
        types : string, :py:class:`MarkerType`, array_like, optional
            the marker type/s (or name/s) of the rectangles.
        processed : int, array_like, optional
            the processed flag/s of the rectangles.
        texts : string, array_like, optional
            the text/s of the rectangles.
        ids : int, array_like, optional
            the id/s of the rectangles.

        Returns
        -------
        rows : int
            the number of affected rows.
        """
        types = self._processesTypeNameField(types)

        query = self.table_rectangle.delete()

        if images is None:
            images = self.table_image.select()
            images = addFilter(images, frames, self.table_image.sort_index)
            images = addFilter(images, filenames, self.table_image.filename)
            query = query.where(self.table_rectangle.image.in_(images))
        else:
            query = addFilter(query, images, self.table_mask.image)

        query = addFilter(query, ids, self.table_rectangle.id)
        query = addFilter(query, xs, self.table_rectangle.x)
        query = addFilter(query, ys, self.table_rectangle.y)
        query = addFilter(query, widths, self.table_rectangle.width)
        query = addFilter(query, heights, self.table_rectangle.height)
        query = addFilter(query, types, self.table_rectangle.type)
        query = addFilter(query, processed, self.table_rectangle.processed)
        query = addFilter(query, texts, self.table_rectangle.text)

        return query.execute()
