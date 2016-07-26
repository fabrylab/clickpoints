from __future__ import print_function, division
import numpy as np
import os
import peewee
from PIL import Image as PILImage
import imageio
import sys

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
        return imageio.imread(value, format=".png")


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


def addFilter(query, parameter, field):
    if parameter is None:
        return query
    if isinstance(parameter, (tuple, list)):
        return query.where(field << parameter)
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
        if key is not None:
            setattr(entry, key, dict[key])


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
    current_version = "14"
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

        version = self.current_version
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
            mode = peewee.IntegerField()
            style = peewee.CharField(null=True)
            text = peewee.CharField(null=True)

        class Track(BaseModel):
            uid = peewee.CharField()
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
            name = peewee.CharField()
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
            self.table_meta(key="version", value=self.current_version).save()

        # second migration part which needs the peewee model
        if version is not None and int(version) < int(self.current_version):
            self._migrateDBFrom2(version)

    def _CheckVersion(self):
        try:
            version = self.db.execute_sql('SELECT value FROM meta WHERE key = "version"').fetchone()[0]
        except (KeyError, peewee.DoesNotExist):
            version = "0"
        print("Open database with version", version)
        if int(version) < int(self.current_version):
            self._migrateDBFrom(version)
        elif int(version) > int(self.current_version):
            print("Warning Database version %d is newer than ClickPoints version %d "
                  "- please get an updated Version!"
                  % (int(version), int(self.current_version)))
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
                #self.db.execute_sql("ALTER TABLE paths RENAME TO path")
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

    def getDbVersion(self):
        """
        Returns the version of the currently opened database file.

        Returns
        -------
        version : string
            the version of the database

        """
        return self.current_version

    def getPath(self, id=None, path_string=None, create=False):  # TODO
        """
        Get a :py:class:`Path` entry from the database.

        See also: :py:meth:`~.DataFile.getPaths`, :py:meth:`~.DataFile.setPath`, :py:meth:`~.DataFile.deletePaths`

        Parameters
        ----------
        id: int, optional
            the id of the path.
        path_string: string, optional
            the string specifying the path.
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

    def getPaths(self, ids=None, path_strings=None, base_path=None):
        """
        Get all :py:class:`Path` entries from the database, which match the given criteria. If no critera a given, return all paths.

        See also: :py:meth:`~.DataFile.getPath`, :py:meth:`~.DataFile.setPath`, :py:meth:`~.DataFile.deletePaths`

        Parameters
        ----------
        ids: int, array_like, optional
            the id/ids of the paths.
        path_strings: string, path_string, optional
            the string/strings specifying the paths.
        base_path: string, optional
            return only paths starting with the base_path string.

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

    def setPath(self, id=None, path_string=None):
        """
        Update or create a new :py:class:`Path` entry with the given parameters.

        See also: :py:meth:`~.DataFile.getPath`, :py:meth:`~.DataFile.getPaths`, :py:meth:`~.DataFile.deletePaths`

        Parameters
        ----------
        id: int, optional
            the id of the paths.
        path_string: string, optional
            the string specifying the path.

        Returns
        -------
        entries : :py:class:`Path`
            the changed or created :py:class:`Path` entry.
        """

        try:
            path = self.table_path.get(id=id, path=path_string)
        except peewee.DoesNotExist:
            path = self.table_path()

        if id is not None:
            path.id = id
        if path_string is not None:
            path.path = path_string
        path.save()

        return path

    def deletePaths(self, ids=None, path_strings=None, base_path=None):
        """
        Delete all :py:class:`Path` entries with the given criteria.

        See also: :py:meth:`~.DataFile.getPath`, :py:meth:`~.DataFile.getPaths`, :py:meth:`~.DataFile.setPath`

        Parameters
        ----------
        ids: int, optional
            the id/ids of the paths.
        path_strings: string, optional
            the string/strings specifying the paths.
        base_path: string, optional
            return only paths starting with the base_path string.
        """

        query = self.table_path.delete()

        query = addFilter(query, ids, self.table_path.id)
        query = addFilter(query, path_strings, self.table_path.path)
        if base_path is not None:
            query = query.where(self.table_path.path.startswith(base_path))
        query.execute()

    def getImage(self, frame):
        """
        Returns the :py:class:`Image` entry with the given frame number.

        See also: :py:meth:`~.DataFile.getImages`, :py:meth:`~.DataFile.getImageIterator`, :py:meth:`~.DataFile.setImage`,
        :py:meth:`~.DataFile.deleteImages`.

        Parameters
        ----------
        frame : int
            the frame number of the desired image.

        Returns
        -------
        image : :py:class:`Image`
            the image entry.
        """

        return self.table_image.get(sort_index=frame)

    def getImages(self, start_frame=None):
        """
        Get all :py:class:`Image` entries sorted by sort index. For large databases :py:meth:`~.DataFile.getImageIterator`, should be used
        as it doesn't load all frames at once.

        See also: :py:meth:`~.DataFile.getImage`, :py:meth:`~.DataFile.getImageIterator`, :py:meth:`~.DataFile.setImage`,
        :py:meth:`~.DataFile.deleteImages`.

        Parameters
        ----------
        start_frame : int, optional
            only return images with sort_index >= start_frame. Default is 0, which returns all images

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
            for image in db.GetImages():
                print(image.filename)
        """

        query = self.table_image.select()
        if start_frame is not None:
            query = query.where(self.table_image.sort_index >= start_frame)
        query = query.order_by(self.table_image.sort_index)
        return query

    def getImageIterator(self, start_frame=0):
        """
        Get an iterator to iterate over all :py:class:`Image` entries starting from start_frame.

        See also: :py:meth:`~.DataFile.getImage`, :py:meth:`~.DataFile.getImages`, :py:meth:`~.DataFile.setImage`,  :py:meth:`~.DataFile.deleteImages`.

        Parameters
        ----------
        start_frame : int, optional
            start at the image with the number start_frame. Default is 0

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

    def setImage(self, id=None, filename=None, path=None, frames=None, external_id=None, timestamp=None, width=None, height=None):

        """
        Update or create new :py:class:`Image` entry with the given parameters.

        See also: :py:meth:`~.DataFile.getImage`, :py:meth:`~.DataFile.getImages`, :py:meth:`~.DataFile.getImageIterator`, :py:meth:`~.DataFile.deleteImages`.

        Parameters
        ----------
        id : int, optional
            the id of the image
        filename : string, optional
            the filename of the image (including the extension)
        frames : int, optional
            the number of frames the image has
        external_id : int, optional
            an external id for the image. Only necessary if the annotation server is used
        timestamp : datetime object, optional
            the timestamp of the image
        width : int, optional
            the width of the image
        height : int, optional
            the height of the image

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
            item.filename = filename
            item.ext = os.path.splitext(filename)[1]
            item.path = self.getPath(path_string=os.path.split(filename)[0], create=True)
        if frames is not None:
            item.frames = frames
        if external_id is not None:
            item.external_id = external_id
        if timestamp is not None:
            item.timestamp = timestamp
        if width is not None:
            item.width = width
        if height is not None:
            item.height = height
        if new_image:
            if self.next_sort_index is None:
                query = self.table_image.select().order_by(-self.table_image.sort_index).limit(1)
                try:
                    self.next_sort_index = query[0].sort_index + 1
                except IndexError:
                    self.next_sort_index = 0
            item.sort_index = self.next_sort_index
            self.next_sort_index += 1

        item.save()
        return item


    def deleteImages(self, ids=None, filenames=None, frames=None, external_ids=None, timestamps=None, widths=None, heights=None):
        """
        Delete all :py:class:`Image` entries with the given criteria.

        See also: :py:meth:`~.DataFile.getImage`, :py:meth:`~.DataFile.getImages`, :py:meth:`~.DataFile.getImageIterator`, :py:meth:`~.DataFile.setImage`.

        Parameters
        ----------
        ids : int, array_like, optional
            the id/ids of the images
        filenames : string, array_like, optional
            the filename/filenames of the image (including the extension)
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

        Returns
        -------

        """
        query = self.table_image.delete()

        query = addFilter(query, ids, self.table_image.id)
        query = addFilter(query, filenames, self.table_image.filename)
        query = addFilter(query, frames, self.table_image.frame)
        query = addFilter(query, external_ids, self.table_image.external_id)
        query = addFilter(query, timestamps, self.table_image.timestamp)
        query = addFilter(query, widths, self.table_image.width)
        query = addFilter(query, heights, self.table_image.height)
        query.execute()

    def getMaskType(self, id=None, name=None, color=None, index=None, create=False):
        """
        Get a :py:class:`MaskType` from the database.

        See also: :py:meth:`~.DataFile.getMaskTypes`, :py:meth:`~.DataFile.setMaskType`, :py:meth:`~.DataFile.deleteMaskTypes`.

        Parameters
        ----------
        id : int, optional
            the id of the mask type.
        name : string, optional
            the name of the mask type.
        color : string, optional
            the color of the mask type.
        index : int, optional
            the index of the mask type, which is used for painting this mask type.
        create : bool, optional
            whether the mask type should be created if it does not exist. (default: False)

        Returns
        -------
        entries : :py:class:`MaskType`
            the created/requested :py:class:`MaskType` entry.
        """
        # check input
        assert any(e is not None for e in [id, name, color, index]), "Path, ID, color and index may not be all None"

        # collect arguments
        kwargs = noNoneDict(id=id, name=name, color=color, index=index)

        # try to get the path
        try:
            masktype = self.table_masktype.get(**kwargs)
        # if not create it
        except peewee.DoesNotExist as err:
            if create:
                masktype = self.table_masktype(**kwargs)
                masktype.save()
            else:
                return None
        # return the path
        return masktype

    def getMaskTypes(self, ids=None, names=None, colors=None, indices=None):
        """
        Get all :py:class:`MaskType` entries from the database, which match the given criteria. If no criteria a given, return all mask types.

        See also: :py:meth:`~.DataFile.getMaskType`, :py:meth:`~.DataFile.setMaskType`, :py:meth:`~.DataFile.deleteMaskTypes`.

        Parameters
        ----------
        ids : int, array_like, optional
            the id/ids of the mask types.
        names : string, array_like, optional
            the name/names of the mask types.
        colors : string, array_like, optional
            the color/colors of the mask types.
        indices : int, array_like, optional
            the index/indices of the mask types, which is used for painting this mask types.

        Returns
        -------
        entries : array_like
            a query object containing all the matching :py:class:`MaskType` entries in the database file.
        """

        query = self.table_masktype.select()

        query = addFilter(query, ids, self.table_masktype.id)
        query = addFilter(query, names, self.table_masktype.name)
        query = addFilter(query, colors, self.table_masktype.color)
        query = addFilter(query, indices, self.table_masktype.index)
        return query

    def setMaskType(self, id=None, name=None, color=None, index=None):
        """
        Update or create a new a :py:class:`MaskType` entry with the given parameters.

        See also: :py:meth:`~.DataFile.getMaskType`, :py:meth:`~.DataFile.getMaskTypes`, :py:meth:`~.DataFile.setMaskType`, :py:meth:`~.DataFile.deleteMaskTypes`.

        Parameters
        ----------
        id : int, optional
            the id of the mask type.
        name : string, optional
            the name of the mask type.
        color : string, optional
            the color of the mask type.
        index : int, optional
            the index of the mask type, which is used for painting this mask type.

        Returns
        -------
        entries : :py:class:`MaskType`
            the changed or created :py:class:`MaskType` entry.
        """

        try:
            mask_type = self.table_masktype.get(**noNoneDict(id=id, name=name, color=color, index=index))
        except peewee.DoesNotExist:
            mask_type = self.table_masktype()

        setFields(mask_type, dict(id=id, name=name, color=color, index=index))
        mask_type.save()

        return mask_type

    def deleteMaskTypes(self, ids=None, names=None, colors=None, indices=None):
        """
        Delete all :py:class:`MaskType` entries from the database, which match the given criteria.

        See also: :py:meth:`~.DataFile.getMaskType`, :py:meth:`~.DataFile.getMaskTypes`, :py:meth:`~.DataFile.setMaskType`.

        Parameters
        ----------
        ids : int, array_like, optional
            the id/ids of the mask types.
        names : string, array_like, optional
            the name/names of the mask types.
        colors : string, array_like, optional
            the color/colors of the mask types.
        indices : int, array_like, optional
            the index/indices of the mask types, which is used for painting this mask types.
        """

        query = self.table_masktype.delete()

        query = addFilter(query, ids, self.table_masktype.id)
        query = addFilter(query, names, self.table_masktype.name)
        query = addFilter(query, colors, self.table_masktype.color)
        query = addFilter(query, indices, self.table_masktype.index)
        query.execute()

    def GetMasks(self, order_by="sort_index"):
        """
        Get all mask entries

        Parameters
        ----------
        order_by: string ['sort_index','timestamp']
            sort results by sort_index or timestamp (def: sort_index)

        Returns
        -------
        entries : array_like
            a query object which contains all :py:class:`Mask` entries.
        """

        query = self.table_mask.select()
        # order query results by
        if order_by=='sort_index':
            query = query.join(self.table_image).order_by(self.table_image.sort_index)
        elif order_by=='timestamp':
            query = query.join(self.table_image).order_by(self.table_image.timestamp)
        else:
            print("Unknown order_by paramter %s - results not sorted!" % order_by)

        return query

    def GetMask(self, image):
        """
        Get the mask image data for the image with the id `image`. If the database already has an entry the corresponding
        mask will be loaded, otherwise a new empty mask array will be created.
    
        To save the changes on the mask use `SetMask`.
    
        Parameters
        ----------
        image : int
            image id.
    
        Returns
        -------
        mask : ndarray
            mask data for the image.
        """
        # Test if mask already exists in database
        mask_entry = self.table_mask.get(self.table_mask.image == image)
        return mask_entry

    def SetMask(self, mask, image):
        """
        Add or overwrite the mask file for the image with the id `image`
    
        Parameters
        ----------
        mask : array_like
            mask image data.
        image : int
            image id.
        """
        try:
            # Test if mask already exists in database
            mask_entry = self.table_mask.get(self.table_mask.image == image)
            mask_entry.data = image
            mask_entry.save()
        except peewee.DoesNotExist:
            # Create new entry
            mask_entry = self.table_mask(image=image)
            mask_entry.data = image
            mask_entry.save()

    def AddMaskFile(self, image_id, filename):
        try:
            item = self.table_mask.get(self.table_mask.image == image_id)
        except peewee.DoesNotExist:
            item = self.table_mask()

        item.image = image_id
        item.filename = filename

        item.save()
        return item.get_id()
