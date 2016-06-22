from __future__ import print_function, division
import numpy as np
import os
import peewee
from playhouse.reflection import Introspector
import time
from PIL import Image
import imageio
import sys


def isstring(object):
    PY3 = sys.version_info[0] == 3

    if PY3:
        return isinstance(object, str)
    else:
        return isinstance(object, basestring)


def CheckValidColor(color):
    class NoValidColor(Exception):
        pass

    if isstring(color):
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

        self.current_version = "9"
        version = self.current_version
        self.next_sort_index = 0
        new_database = True

        # Create a new database
        if mode == "w":
            if os.path.exists(self.database_filename):
                os.remove(self.database_filename)
            self.db = peewee.SqliteDatabase(database_filename)
        else:  # or read an existing one
            if not os.path.exists(self.database_filename) and mode != "r+":
                raise Exception("DB %s does not exist!" % os.path.abspath(self.database_filename))
            self.db = peewee.SqliteDatabase(database_filename)
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
            filename = peewee.CharField(unique=True)
            ext = peewee.CharField(max_length=10)
            frame = peewee.IntegerField(default=0)
            external_id = peewee.IntegerField(null=True)
            timestamp = peewee.DateTimeField(null=True)
            sort_index = peewee.IntegerField(default=0)
            width = peewee.IntegerField(null=True)
            height = peewee.IntegerField(null=True)
            path = peewee.ForeignKeyField(Path, related_name="images")

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
        self.tables = [BaseModel, Meta, Path, Image]

        """ Offset Table """

        class Offset(BaseModel):
            image = peewee.ForeignKeyField(Image, unique=True, related_name="offsets")
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
            type = peewee.ForeignKeyField(MarkerType, related_name="tracks")

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
            image = peewee.ForeignKeyField(Image, related_name="markers")
            x = peewee.FloatField()
            y = peewee.FloatField()
            type = peewee.ForeignKeyField(MarkerType, related_name="markers", null=True)
            processed = peewee.IntegerField(default=0)
            partner = peewee.ForeignKeyField('self', null=True, related_name='partner2')
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
            image = peewee.ForeignKeyField(Image, related_name="masks")
            filename = peewee.CharField()

            mask_data = None

            def get_data(self):
                if self.mask_data is None:
                    im = np.asarray(Image.open(os.path.join(self.database_class._GetMaskPath(), self.filename)))
                    im.setflags(write=True)
                    self.mask_data = im
                return self.mask_data

            def __getattr__(self, item):
                if item == "data":
                    return self.get_data()
                else:
                    return BaseModel(self, item)

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
            image = peewee.ForeignKeyField(Image, related_name="annotations")
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
            annotation = peewee.ForeignKeyField(Annotation, related_name="tagassociations")
            tag = peewee.ForeignKeyField(Tag, related_name="tagassociations")

        self.table_annotation = Annotation
        self.table_tag = Tag
        self.table_tagassociation = TagAssociation
        self.tables.extend([Annotation, Tag, TagAssociation])

        """ Connect """
        self.db.connect()
        self._CreateTables()

        if new_database:
            self.table_meta(key="version", value=self.current_version).save()

        # second migration part which needs the peewee model
        print(version, int(self.current_version), int(version) < int(self.current_version))
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

        if nr_version < 7:
            print("\tto 7")
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
            nr_new_version = 7

        if nr_version < 8:
            print("\tto 8")
            try:
                self.db.execute_sql("ALTER TABLE paths RENAME TO path")
            except peewee.OperationalError:
                pass
            try:
                self.db.execute_sql("ALTER TABLE images RENAME TO image")
            except peewee.OperationalError:
                pass
            try:
                self.db.execute_sql("ALTER TABLE offsets RENAME TO offset")
            except peewee.OperationalError:
                pass
            try:
                self.db.execute_sql("ALTER TABLE tracks RENAME TO track")
            except peewee.OperationalError:
                pass
            try:
                self.db.execute_sql("ALTER TABLE types RENAME TO markertype")
            except peewee.OperationalError:
                pass
            try:
                self.db.execute_sql("ALTER TABLE masktypes RENAME TO masktype")
            except peewee.OperationalError:
                pass
            try:
                self.db.execute_sql("ALTER TABLE tags RENAME TO tag")
            except peewee.OperationalError:
                pass
            nr_new_version = 8

        if nr_version < 9:
            print("\tto 9")
            # Add type fields for Track
            try:
                self.db.execute_sql("ALTER TABLE track ADD COLUMN type_id int")
            except peewee.OperationalError:
                pass
            nr_new_version = 9

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
        if nr_version < 9:
            print("second migration step to 9")
            tracks = self.table_track.select()
            with self.db.atomic():
                for track in tracks:
                    track.type = track.markers[0].type
                    track.save()

    def _GetMaskPath(self):
        if self.mask_path:
            return self.mask_path
        try:
            outputpath_mask = self.table_meta.get(key="mask_path").value
        except peewee.DoesNotExist:
            outputpath_mask = "mask"  # default value
            self.table_meta(key="mask_path", value=outputpath_mask).save()
        self.mask_path = os.path.join(os.path.dirname(self.database_filename), outputpath_mask)
        if not os.path.exists(self.mask_path):
            os.mkdir(self.mask_path)
        return self.mask_path

    def _CreateTables(self):
        for table in self.tables:
            if not table.table_exists():
                self.db.create_table(table)

        try:
            item = self.table_meta.get(self.table_meta.key == "version")
        except peewee.DoesNotExist:
            item = self.table_meta()

            item.key = "version"
            item.value = self.current_version

            item.save()

        return item.get_id()

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

    def GetMarker(self, image=None, image_filename=None, processed=None, type=None, type_name=None, track=None):
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
        return query

    def GetRectangles(self, image=None, image_filename=None, processed=None, type=None, type_name=None, track=None):
        """
        See GetMarkers, but it already merges all connected markers to rectangles. Single markers are omitted.

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
        try:
            # Test if mask already exists in database
            mask_entry = self.table_mask.get(self.table_mask.image == image)
            # Load it
            im = np.asarray(Image.open(os.path.join(self._GetMaskPath(), mask_entry.filename)))
            im.setflags(write=True)
            return im
        except (peewee.DoesNotExist, IOError):
            # Create new mask according to image size
            image_entry = self.table_image.get(self.table_image.id == image)
            pil_image = Image.open(image_entry.filename)
            im = np.zeros(pil_image.size, dtype=np.uint8)
            return im

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
            filename = os.path.join(self._GetMaskPath(), mask_entry.filename)
        except peewee.DoesNotExist:
            # Create new entry
            mask_entry = self.table_mask(image=image)
            # Get mask image name
            image_entry = self.table_image.get(id=image)
            if image_entry.frames > 1:  # TODO
                number = "_" + ("%" + "%d" % np.ceil(np.log10(image_entry.frames)) + "d") % image_frame
            else:
                number = ""
            basename, ext = os.path.splitext(image_entry.filename)
            directory, basename = os.path.split(basename)
            current_maskname = basename + "_" + ext[1:] + number + "_mask.png"
            filename = os.path.join(self._GetMaskPath(), current_maskname)
            # Save entry
            mask_entry.filename = current_maskname
            mask_entry.save()

        # Create image
        pil_image = Image.fromarray(mask)
        # Create color palette
        lut = np.zeros(3 * 256, np.uint8)
        for draw_type in self.table_masktype.select():
            index = draw_type.index
            lut[index * 3:(index + 1) * 3] = [int("0x" + draw_type.color[i:i + 2], 16) for i in [1, 3, 5]]
        pil_image.putpalette(lut)
        # Save mask
        pil_image.save(filename)

    def AddMaskFile(self, image_id, filename):
        try:
            item = self.table_mask.get(self.table_mask.image == image_id)
        except peewee.DoesNotExist:
            item = self.table_mask()

        item.image = image_id
        item.filename = filename

        item.save()
        return item.get_id()
