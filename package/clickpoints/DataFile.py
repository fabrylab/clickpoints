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

class ImageField(peewee.BlobField):

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

    if isinstance(object, basestring):
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

class Rectangle:
    def __init__(self, x1, y1, x2, y2, rect, partner):
        self.x1 = min(x1, x2)
        self.x2 = max(x1, x2)
        self.y1 = min(y1, y2)
        self.y2 = max(y1, y2)
        self.width = self.x2-self.x1
        self.height = self.y2-self.y1
        self.marker1 = rect
        self.marker2 = partner
        self.slice_x = slice(int(self.x1), int(self.x2))
        self.slice_y = slice(int(self.y1), int(self.y2))

class Line:
    def __init__(self, x1, y1, x2, y2, marker1, marker2):
        self.x1 = x1
        self.x2 = x2
        self.y1 = y1
        self.y2 = y2
        self.dx = abs(self.x2-self.x1)
        self.dy = abs(self.y2-self.y1)
        self.length = np.sqrt(self.dx**2 + self.dy**2)
        self.marker1 = marker1
        self.marker2 = marker2

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

    def __init__(self, database_filename=None, mode='r'):
        if database_filename is None:
            raise TypeError("No database filename supplied.")
        self.database_filename = database_filename

        self.current_version = "12"
        version = self.current_version
        self.next_sort_index = 0
        new_database = True

        # Create a new database
        if mode == "w":
            if os.path.exists(self.database_filename):
                os.remove(self.database_filename)
            self.db = peewee.SqliteDatabase(database_filename, threadlocals=True)
        else:  # or read an existing one
            if not os.path.exists(self.database_filename) and mode != "r+":
                raise Exception("DB %s does not exist!" % os.path.abspath(self.database_filename))
            self.db = peewee.SqliteDatabase(database_filename, threadlocals=True)
            if os.path.exists(self.database_filename):
                version = self._CheckVersion()
                self.next_sort_index = None
                new_database = False

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
                    reader = imageio.get_reader(os.path.join(self.path.path, self.filename))
                    self.image_data = reader.get_data(self.frame)
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
            partner = peewee.ForeignKeyField('self', null=True, related_name='partner2', on_delete='SET NULL')
            track = peewee.ForeignKeyField(Track, null=True, related_name='track_markers')
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

        self.table_marker = Marker
        self.table_track = Track
        self.table_markertype = MarkerType
        self.tables.extend([Marker, Track, MarkerType])

        """ Mask Tables """

        class Mask(BaseModel):
            image = peewee.ForeignKeyField(Image, related_name="masks", on_delete='CASCADE')
            data = ImageField()

        class MaskType(BaseModel):
            name = peewee.CharField()
            color = peewee.CharField()
            index = peewee.IntegerField(unique=True)

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
            self.table_meta(key="version", value=self.current_version).save()

        # second migration part which needs the peewee model
        if version is not None and int(version) < int(self.current_version):
            self._migrateDBFrom2(version)

        """ Enumerations """
        self.TYPE_Normal = 0
        self.TYPE_Rect = 1
        self.TYPE_Line = 2
        self.TYPE_Track = 4

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

                self.db.execute_sql('CREATE TABLE "image_tmp" ("id" INTEGER NOT NULL PRIMARY KEY, "filename" VARCHAR(255) NOT NULL, "ext" VARCHAR(10) NOT NULL, "frame" INTEGER NOT NULL, "external_id" INTEGER, "timestamp" DATETIME, "sort_index" INTEGER NOT NULL, "width" INTEGER, "height" INTEGER, "path_id" INTEGER NOT NULL, FOREIGN KEY ("path_id") REFERENCES "path" ("id") ON DELETE CASCADE);')
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

    def GetImages(self, start_frame=None):
        """
        Get all images sorted by sort index.

        Parameters
        ----------
        start_frame : int, optional
            only return images with sort_index >= start_frame. Default is 0, which returns all images

    
        Returns
        -------
        entries : array_like
            a query object containing all the :py:class:`Image` entries in the database file.
        """

        query = self.table_image.select()
        if start_frame is not None:
            query = query.where(self.table_image.sort_index >= start_frame)
        query = query.order_by(self.table_image.sort_index)
        return query

    def GetImageIterator(self, start_frame=0):
        """
        Get an iterator to iterate over all images starting from start_frame.

        Parameters
        ----------
        start_frame : int, optional
            start at the image with the number start_frame. Default is 0


        Returns
        -------
        entries : array_like
            a query object containing all the :py:class:`Image` entries in the database file.
        """

        frame = start_frame
        while True:
            try:
                image = self.table_image.get(self.table_image.sort_index == frame)
                yield image
            except peewee.DoesNotExist:
                break
            frame += 1

    def AddPath(self, path):
        """
        Add a path to the database, or return the path entry if it already exists.

        Returns
        -------
        path : path_entry
            the created/requested :py:class:`Path` entry.
        """

        if self.database_filename:
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

    def AddImage(self, filename, ext, path, frames=1, external_id=None, timestamp=None, sort_index=None, width=None,
                 height=None):
        """
        Add a single image to db

        Parameters
        ----------
        filename : string
            the filename of the image (including the extension)
        ext : string
            the file extension
        path: string
            the path to the filename
        frames : int
            the number of frames the image has
        external_id : int
            an external id for the image. Only necessary if the annotation server is used
        timestamp : datetime object
            the timestamp of the image

        Returns
        -------
        image : image entry
            the created or updated :py:class:`Image` entry
        """
        try:
            item = self.table_image.get(self.table_image.filename == filename)
            new_image = False
        except peewee.DoesNotExist:
            item = self.table_image()
            new_image = True

        item.filename = filename
        item.ext = ext
        item.frames = frames
        item.external_id = external_id
        item.timestamp = timestamp
        item.path = self.AddPath(path)
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

    def RemoveImage(self, filename):
        try:
            item = self.table_image.get(self.table_image.filename == filename)
        except peewee.DoesNotExist:
            print("Image with name: \'%s\' is not in DB", filename)
            return False

        item.delete_instance()

        return True

    def GetTracks(self):
        """
        Get all track entries
    
        Returns
        -------
        entries : array_like
            a query object which contains the requested :py:class:`Track`.
        """

        query = self.table_track.select()
        return query

    def AddTrack(self, type):
        """
        Add a new track entry

        Parameters
        ----------
        type: :py:class:`MarkerType` or str
            the marker type or name of the marker type for the track.

        Returns
        -------
        track : track object
            a new :py:class:`Track` object
        """
        import uuid

        if isinstance(type, basestring):
            type = self.GetType(type)

        item = self.table_track(uid=uuid.uuid4().hex, type=type)
        item.save()
        return item

    def AddTracks(self, count, type):
        """
        Add multiple new tracks

        Parameters
        ----------
        count: int
            how many tracks to create

        type: :py:class:`MarkerType` or str
            the marker type or name of the marker type for the tracks.

        Returns
        -------
        tracks : list of :py:class:`Track`
            the new track objects
        """

        if isinstance(type, basestring):
            type = self.GetType(type)

        return [self.AddTrack(type) for _ in range(count)]

    def GetTypes(self):
        """
        Get all type entries
    
        Returns
        -------
        entries : array_like
            a query object which contains all :py:class:`MarkerType` entries.
        """
        query = self.table_markertype.select()
        return query

    def AddType(self, name, color, mode=0, style=None):
        try:
            item = self.table_markertype.get(self.table_markertype.name == name)
        except peewee.DoesNotExist:
            item = self.table_markertype()

        item.name = name
        item.color = CheckValidColor(color)
        item.mode = mode
        item.style = style

        item.save()
        return item.get_id()

    def GetType(self, name):
        """
        Get the type with the specified name.

        Parameters
        ----------
        name: str
            the name of the desired type

        Returns
        -------
        entries : array_like
            the :py:class:`MarkerType` with the desired name or None.
        """
        try:
            return self.table_markertype.get(self.table_markertype.name == name)
        except peewee.DoesNotExist:
            return None

    def GetMarker(self, image=None, image_filename=None, processed=None, type=None, type_name=None, track=None, order_by='sort_index'):
        """
        Get all the marker entries in the database where the parameters fit. If a parameter is omitted, the column is
        ignored. If it is provided a single value, only database entries matching this value are returned. If a list is
        supplied, any entry with a value from the list is matched.

        Parameters
        ----------
        image : int, array, optional
            the image id(s) for the markers to be selected.
        processed : bool, array, optional
            the processed flag(s) for the markers to be selected.
        type : int, array, optional
            the type id(s) for the markers to be selected.
        track : int, array, optional
            the track id(s) for the markers to be selected.
        order_by: string ['sort_index','timestamp']
            sort results by sort_index or timestamp (def: sort_index)

        Returns
        -------
        entries : array_like
            a query object which can be iterated to get the :py:class:`Tracks` entries which where matched by the parameters provided.
        """
        # select marker, joined with types and images
        query = (self.table_marker.select(self.table_marker, self.table_markertype, self.table_image)
                 .join(self.table_markertype)
                 .switch(self.table_marker)
                 .join(self.table_image)
                 )
        parameter = [image, image_filename, processed, type, type_name, track]
        table = self.table_marker
        fields = [table.image, self.table_image.filename, table.processed, table.type, self.table_markertype.name,
                  table.track]
        for field, parameter in zip(fields, parameter):
            if parameter is None:
                continue
            if isinstance(parameter, (tuple, list)):
                query = query.where(field << parameter)
            else:
                query = query.where(field == parameter)

        # order query results by
        if order_by=='sort_index':
            query = query.order_by(self.table_image.sort_index)
        elif order_by=='timestamp':
            query = query.order_by(self.table_image.timestamp)
        else:
            print("Unknown order_by paramter %s - results not sorted!" % order_by)

        return query

    def GetRectangles(self, image=None, image_filename=None, processed=None, type=None, type_name=None, track=None):
        """
        See GetMarkers, but it already merges all connected markers to rectangles and filters for markers with a
        TYPE_Rect marker type. Single markers are omitted.

        Parameters
        ----------
        image : int, array, optional
            the image id(s) for the markers to be selected.
        processed : bool, array, optional
            the processed flag(s) for the markers to be selected.
        type : int, array, optional
            the type id(s) for the markers to be selected.
        track : int, array, optional
            the track id(s) for the markers to be selected.

        Returns
        -------
        entries : array_like
            a list of rectangle objects.
        """
        # select marker, joined with types and images
        query = (self.table_marker.select(self.table_marker, self.table_markertype, self.table_image)
                 .join(self.table_markertype)
                 .switch(self.table_marker)
                 .join(self.table_image)
                 )
        parameter = [image, image_filename, processed, type, type_name, track]
        table = self.table_marker
        fields = [table.image, self.table_image.filename, table.processed, table.type, self.table_markertype.name,
                  table.track]
        for field, parameter in zip(fields, parameter):
            if parameter is None:
                continue
            if isinstance(parameter, (tuple, list)):
                query = query.where(field << parameter)
            else:
                query = query.where(field == parameter)

        # iterate over markers and merge rectangles
        rects = []
        for rect in query:
            if rect.type.mode & self.TYPE_Rect:
                try:
                    # only if we have a partner and the partner has a smaller id (so that we only get one of each pair)
                    if rect.partner_id and rect.id < rect.partner.id:
                        # create a rectangle item and append it to the lisst
                        rects.append(Rectangle(rect.x, rect.y, rect.partner.x, rect.partner.y, rect, rect.partner))
                # ignore markers where the partner doesn't exist
                except peewee.DoesNotExist:
                    pass
        # return the list
        return rects

    def GetLines(self, image=None, image_filename=None, processed=None, type=None, type_name=None, track=None):
        """
        See GetMarkers, but it already merges all connected markers to lines and filters for markers with a TYPE_Line
        marker type. Single markers are omitted.

        Parameters
        ----------
        image : int, array, optional
            the image id(s) for the markers to be selected.
        processed : bool, array, optional
            the processed flag(s) for the markers to be selected.
        type : int, array, optional
            the type id(s) for the markers to be selected.
        track : int, array, optional
            the track id(s) for the markers to be selected.

        Returns
        -------
        entries : array_like
            a list of rectangle objects.
        """
        # select marker, joined with types and images
        query = (self.table_marker.select(self.table_marker, self.table_markertype, self.table_image)
                 .join(self.table_markertype)
                 .switch(self.table_marker)
                 .join(self.table_image)
                 )
        parameter = [image, image_filename, processed, type, type_name, track]
        table = self.table_marker
        fields = [table.image, self.table_image.filename, table.processed, table.type, self.table_markertype.name,
                  table.track]
        for field, parameter in zip(fields, parameter):
            if parameter is None:
                continue
            if isinstance(parameter, (tuple, list)):
                query = query.where(field << parameter)
            else:
                query = query.where(field == parameter)

        # iterate over markers and merge rectangles
        lines = []
        for line in query:
            if line.type.mode & self.TYPE_Line:
                try:
                    # only if we have a partner and the partner has a smaller id (so that we only get one of each pair)
                    if line.partner_id and line.id < line.partner.id:
                        # create a rectangle item and append it to the lisst
                        lines.append(Line(line.x, line.y, line.partner.x, line.partner.y, line, line.partner))
                # ignore markers where the partner doesn't exist
                except peewee.DoesNotExist:
                    pass
        # return the list
        return lines

    def SetMarker(self, id=None, image=None, x=None, y=None, processed=0, partner=None, type=None, track=None,
                  marker_text=None):
        """
        Insert or update markers in the database file. Every parameter can either be omitted, to use the default value,
        supplied with a single value, to use the same value for all entries, or be supplied with a list of values, to use a
        different value for each entry. If any parameter is a list, multiple entries are inserted, otherwise just a single
        value will be inserted or updated.
    
        Parameters
        ----------
        id : int, array, optional
            the id(s) for the markers to be inserted.
        image : int, array, optional
            the image id(s) for the markers to be inserted.
        x : float, array, optional
            the x coordinate(s) for the markers to be inserted.
        y : float, array, optional
            the y coordinate(s) for the markers to be inserted.
        processed : bool, array, optional
            the processed flag(s) for the markers to be inserted.
        partner : int, array, optional
            the partner id(s) for the markers to be inserted.
        type : int, array, optional
            the type id(s) for the markers to be inserted.
        track : int, array, optional
            the track id(s) for the markers to be inserted.

        Examples
        --------
        >>> points = db.GetMarker(image=image)
        >>> p0 = np.array([[point.x, point.y] for point in points if point.track_id])
        >>> tracking_ids = [point.track_id for point in points if point.track_id]
        >>> types = [point.type_id for point in points if point.track_id]
        >>> db.SetMarker(image=image, x=p0[:, 0]+10, y=p0[:, 1], processed=0, type=types, track=tracking_ids)

        Get all the points of an image and move them 10 pixels to the right.

        """
        # if the variable track is a list of track instances, we need to convert it to track ids
        try:
            if isinstance(track[0], self.table_track):
                track = track[:]
                for i, t in enumerate(track):
                    if isinstance(t, self.table_track):
                        track[i] = t.id
        except TypeError:
            if isinstance(track, self.table_track):
                track = track.id
            pass
        # if the variable image is a list of image instances, we need to convert it to image ids
        try:
            if isinstance(image[0], self.table_image):
                image = image[:]
                for i, img in enumerate(image):
                    if isinstance(img, self.table_image):
                        image[i] = img.id
        except TypeError:
            if isinstance(image, self.table_image):
                image = image.id
            pass
        data_sets = []
        table = self.table_marker
        fields = [table.id, table.image, table.x, table.y, table.processed, table.partner_id, table.type, table.text,
                  table.track]
        names = ["id", "image_id", "x", "y", "processed", "partner_id", "type_id", "text", "track_id"]
        for data in np.broadcast(id, image, x, y, processed, partner, type, marker_text, track):
            data_set = []
            condition_list = ["image_id", "track_id"]
            # TODO: track_id param as position=[-1] is BAD
            condition_param = [data[1], data[-1]]
            condition = "WHERE "
            for idx, cond in enumerate(condition_list):
                if not condition_param[idx] is None:
                    condition += cond + " = " + str(condition_param[idx])
                else:
                    condition += cond + " = NULL"
                if not idx == len(condition_list) - 1:
                    condition += " AND "

            # print(condition)

            # condition = "WHERE image_id = %d AND track_id = %d" % (data[1], data[2], data[-1])

            for field, name, value in zip(fields, names, data):
                if value is None:
                    data_set.append("(SELECT " + name + " FROM marker " + condition + ")")
                else:
                    try:
                        data_set.append(str(value.id))
                    except AttributeError:
                        # for CharFileds add ticks
                        if (field.__class__.__name__) == 'CharField':
                            data_set.append('\'%s\'' % value)
                        else:
                            data_set.append(str(value))
            data_sets.append(",\n ".join(data_set))
        query = "INSERT OR REPLACE INTO marker (id, image_id, x, y, processed, partner_id, type_id, text, track_id)\n VALUES (\n"
        query += "),\n (".join(data_sets)
        query += ");"

        self.db.execute_sql(query)

    def GetMaskTypes(self):
        """
        Get all mask type entries

        Returns
        -------
        entries : array_like
            a query object which contains all :py:class:`MaskType` entries.
        """
        query = self.table_masktype.select()
        return query

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
            a query object which contains all :py:clss:`Mask` entries.
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
