from __future__ import print_function, division
import numpy as np
import os
import peewee
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
    class NoValidColor(Exception): pass
    if isstring(color):
        if color[0] == "#":
            color = color[1:]
        for c in color:
            if not "0" <= c.upper() <= "F":
                raise NoValidColor(color+" is no valid color")
        if len(color) != 6 and len(color) != 8:
            raise NoValidColor(color+" is no valid color")
        return "#"+color
    color_string = ""
    for value in color:
        if not 0 <= value <= 255:
            raise NoValidColor(str(color)+" is no valid color")
        color_string += "%02x" % value
    if len(color_string) != 6 and len(color_string) != 8:
        raise NoValidColor(str(color)+" is no valid color")
    return "#"+color_string


def GetCommandLineArgs():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", dest='database', help='specify which database file to use')
    parser.add_argument("--start_frame", type=int, default=0, dest='start_frame', help='specify at which frame to start')
    parser.add_argument("--port", type=int, dest='port', help='from which port to communicate with ClickPoints')
    args, unknown = parser.parse_known_args()
    return args.start_frame, args.database, args.port


class DataFile:
    def __init__(self, database_filename=None, mode='r'):
        if database_filename is None:
            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("--database", dest='database', help='specify which database file to use')
            args, unknown = parser.parse_known_args()
            if args.database:
                database_filename = args.database
        if database_filename is None:
            raise TypeError("No database filename supplied. Pass it either as an argument to DataFile or as a command line parameter e.g. --database clickpoints.cdb")
        self.database_filename = database_filename

        self.current_version = "6"

        # Create a new database
        if mode == "w":
            if os.path.exists(self.database_filename):
                os.remove(self.database_filename)
            self.db = peewee.SqliteDatabase(database_filename)
            self.next_sort_index = 0
        else:  # or read an existing one
            if not os.path.exists(self.database_filename):
                raise Exception("DB %s does not exist!" % os.path.abspath(self.database_filename))
            self.db = peewee.SqliteDatabase(database_filename)
            self.next_sort_index = None

        """ Basic Tables """
        class BaseModel(peewee.Model):
            class Meta:
                database = self.db
            database_class = self

        class Meta(BaseModel):
            key = peewee.CharField()
            value = peewee.CharField()

        class Paths(BaseModel):
            path = peewee.CharField(unique=True)

        class Images(BaseModel):
            filename = peewee.CharField(unique=True)
            ext = peewee.CharField()
            frame = peewee.IntegerField(default=0)
            external_id = peewee.IntegerField(null=True)
            timestamp = peewee.DateTimeField(null=True)
            sort_index = peewee.IntegerField(default=0)
            width = peewee.IntegerField(null=True)
            height = peewee.IntegerField(null=True)
            path = peewee.ForeignKeyField(Paths, related_name="images")

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
                if item == "data8":
                    data = self.get_data().copy()
                    if data.dtype == np.uint16:
                        if data.max() < 2**12:
                            data >>= 4
                            return data.astype(np.uint8)
                        data >>= 8
                        return data.astype(np.uint8)
                    return data
                else:
                    return BaseModel(self, item)


        self.base_model = BaseModel
        self.table_meta = Meta
        self.table_paths = Paths
        self.table_images = Images
        self.tables = [BaseModel, Paths, Images]

        """ Offset Table """
        class Offsets(BaseModel):
            image = peewee.ForeignKeyField(Images, unique=True)
            x = peewee.FloatField()
            y = peewee.FloatField()

        self.table_offsets = Offsets
        self.tables.extend([Offsets])

        """ Marker Tables """
        class Tracks(BaseModel):
            uid = peewee.CharField()
            style = peewee.CharField(null=True)
            def points(self):
                return np.array([[point.x, point.y] for point in self.marker()])
            def marker(self):
                return Marker.select().where(Marker.track == self).join(Images).order_by(Images.sort_index)
            def times(self):
                return np.array([point.image.timestamp for point in self.marker()])

        class Types(BaseModel):
            name = peewee.CharField()
            color = peewee.CharField()
            mode = peewee.IntegerField()
            style = peewee.CharField(null=True)

        class Marker(BaseModel):
            image = peewee.ForeignKeyField(Images)
            x = peewee.FloatField()
            y = peewee.FloatField()
            type = peewee.ForeignKeyField(Types)
            processed = peewee.IntegerField(default=0)
            partner = peewee.ForeignKeyField('self', null=True, related_name='partner2')
            style = peewee.CharField(null=True)
            text = peewee.CharField(null=True)
            track = peewee.ForeignKeyField(Tracks, null=True)

            def correctedXY(self):
                join_condition = ((Marker.image == Offsets.image) & \
                                 (Marker.image_frame == Offsets.image_frame))

                querry = Marker.select( Marker.x,
                                        Marker.y,
                                        Offsets.x,
                                        Offsets.y)\
                                .join(  Offsets, peewee.JOIN_LEFT_OUTER, on=join_condition)\
                                .where( Marker.id == self.id)

                for q in querry:
                    if not (q.offsets.x is None) or not (q.offsets.y is None):
                        pt = [q.x + q.offsets.x, q.y + q.offsets.y]
                    else:
                        pt = [q.x, q.y]

                return pt

            class Meta:
                indexes = ((('image', 'image_frame', 'track'), True), )
            def pos(self):
                return np.array([self.x, self.y])

        self.table_marker = Marker
        self.table_tracks = Tracks
        self.table_types = Types
        self.tables.extend([Marker, Tracks, Types])

        """ Mask Tables """
        class Mask(BaseModel):
            image = peewee.ForeignKeyField(Images, related_name="masks")
            filename = peewee.CharField()

            mask_data = None

            def get_data(self):
                if self.mask_data is None:
                    im = np.asarray(Image.open(os.path.join(self.database_class.GetMaskPath(), self.filename)))
                    im.setflags(write=True)
                    self.mask_data = im
                return self.mask_data

            def __getattr__(self, item):
                if item == "data":
                    return self.get_data()
                else:
                    return BaseModel(self, item)

        class MaskTypes(BaseModel):
            name = peewee.CharField()
            color = peewee.CharField()
            index = peewee.IntegerField()

        self.table_mask = Mask
        self.table_maskTypes = MaskTypes
        self.tables.extend([Mask, MaskTypes])
        self.mask_path = None

        """ Connect """
        self.db.connect()
        self.CreateTables()

        """ Enumerations """
        self.TYPE_Normal = 0
        self.TYPE_Rect = 1
        self.TYPE_Line = 2
        self.TYPE_Track = 4

    def GetMaskPath(self):
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

    def CreateTables(self):
        table_list = [self.table_meta,self.table_paths,self.table_images,self.table_marker,self.table_types,self.table_tracks,self.table_mask,self.table_maskTypes]
        for table in table_list:
            if not table.table_exists():
                self.db.create_table(table)

        try:
            item = self.table_meta.get(self.table_meta.key=="version")
        except peewee.DoesNotExist:
            item = self.table_meta()

            item.key="version"
            item.value=self.current_version

            item.save()

        return item.get_id()
    
    def GetImages(self, start_frame=None):
        """
        Get all images sorted by filename
    
        Returns
        -------
        entries : array_like
            a query object containing all the images in the database file.
        """

        query = self.table_images.select()
        if start_frame is not None:
            query = query.where(self.table_images.sort_index >= start_frame)
        query = query.order_by(self.table_images.sort_index)
        return query

    def AddPath(self, path):
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

    def AddImage(self,filename,ext,path,frames=1,external_id=None,timestamp=None,sort_index=None,width=None,height=None):
        """
        Add single image to db

        Parameters
        -----------
        filename : string
            description
        ext : string
            description
        frames : int
            description
        external_id : int
            description
        timestamp : DateTime Object
            description
        Returns
        --------
        index : int
        """
        try:
            item = self.table_images.get(self.table_images.filename==filename)
            new_image = False
        except peewee.DoesNotExist:
            item = self.table_images()
            new_image = True

        item.filename=filename
        item.ext=ext
        item.frames=frames
        item.external_id=external_id
        item.timestamp=timestamp
        item.path = self.AddPath(path)
        if width is not None:
            item.width = width
        if height is not None:
            item.height = height
        if new_image:
            if self.next_sort_index is None:
                query = self.table_images.select().order_by(-self.table_images.sort_index).limit(1)
                try:
                    self.next_sort_index = query[0].sort_index+1
                except IndexError:
                    self.next_sort_index = 0
            item.sort_index = self.next_sort_index
            self.next_sort_index += 1

        item.save()
        return item.get_id()

    def RemoveImage(self,filename):
        try:
            item = self.table_images.get(self.table_images.filename==filename)
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
            a query object which contains the requested tracks.
        """

        query = self.table_tracks.select()
        return query

    def AddTrack(self):
        """
        Add a new track entry

        Returns
        -------
        entry : track object
            a new track object
        """
        import uuid

        item = self.table_tracks(uid=uuid.uuid4().hex)
        item.save()
        return item

    def AddTracks(self, count):
        """
        Add a new tracks

        Parameters
        ----------
        count: int
            how many tracks to create

        Returns
        -------
        tracks : list of track object
            the new track objects
        """

        return [self.AddTrack() for _ in range(count)]
    
    def GetTypes(self):
        """
        Get all type entries
    
        Returns
        -------
        entries : array_like
            a query object which contains all marker types.
        """
        query = self.table_types.select()
        return query

    def AddType(self, name, color, mode=0, style=None):
        try:
            item = self.table_types.get(self.table_types.name == name)
        except peewee.DoesNotExist:
            item = self.table_types()

        item.name = name
        item.color = CheckValidColor(color)
        item.mode = mode
        item.style = style

        item.save()
        return item.get_id()

    def GetType(self, name):
        try:
            return self.table_types.get(self.table_types.name == name)
        except peewee.DoesNotExist:
            return None
    
    def GetMarker(self, image=None, image_filename=None, processed=None, type=None, type_name=None, track=None):
        """
        Get all the marker entries in the database where the parameters fit. If a parameter is omitted, the column is
        ignored. If it is provided a single value, only database entries matching this value are returned. If a list is
        supplied, any entrie with a value from the list is machted.
    
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
            a query object which can be iterated to get the track entries which where matched by the parameters provided.
        """
        # select marker, joined with types and images
        query = (self.table_marker.select(self.table_marker, self.table_types, self.table_images)
                                  .join(self.table_types)
                                  .switch(self.table_marker)
                                  .join(self.table_images)
                 )
        parameter = [image, image_filename, processed, type, type_name, track]
        table = self.table_marker
        fields = [table.image, self.table_images.filename, table.processed, table.type, self.table_types.name, table.track]
        for field, parameter in zip(fields, parameter):
            if parameter is None:
                continue
            if isinstance(parameter, (tuple, list)):
                query = query.where(field << parameter)
            else:
                query = query.where(field == parameter)
        return query
    
    def SetMarker(self, id=None, image=None, x=None, y=None, processed=0, partner=None, type=None, track=None, marker_text=None):
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
        """
        data_sets = []
        table = self.table_marker
        fields = [table.id, table.image, table.x, table.y, table.processed, table.partner_id, table.type, table.text, table.track ]
        names = ["id", "image_id", "x", "y", "processed", "partner_id", "type_id", "text", "track_id"]
        for data in np.broadcast(id, image, x, y, processed, partner, type, marker_text, track):
            data_set = []
            condition_list = ["image_id", "track_id"]
            # TODO: track_id param as position=[-1] is BAD
            condition_param = [data[1], data[-1]]
            condition = "WHERE "
            for idx,cond in enumerate(condition_list):
                if not condition_param[idx] is None:
                    condition += cond + " = " + str(condition_param[idx])
                else:
                    condition += cond + " = NULL"
                if not idx == len(condition_list)-1:
                    condition += " AND "

            # print(condition)

            # condition = "WHERE image_id = %d AND track_id = %d" % (data[1], data[2], data[-1])

            for field, name, value in zip(fields, names, data):
                if value is None:
                    data_set.append("(SELECT "+name+" FROM marker "+condition+")")
                else:
                    # for CharFileds add ticks
                    if (field.__class__.__name__)=='CharField':
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
            a query object which contains all marker types.
        """
        query = self.table_maskTypes.select()
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
            im = np.asarray(Image.open(os.path.join(self.GetMaskPath(), mask_entry.filename)))
            im.setflags(write=True)
            return im
        except (peewee.DoesNotExist, IOError):
            # Create new mask according to image size
            image_entry = self.table_images.get(self.table_images.id == image)
            pil_image = Image.open(image_entry.filename)
            im = np.zeros(pil_image.size, dtype=np.uint8)
            return im
    
    def SetMask(self,mask, image):
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
            filename = os.path.join(self.GetMaskPath(), mask_entry.filename)
        except peewee.DoesNotExist:
            # Create new entry
            mask_entry = self.table_mask(image=image)
            # Get mask image name
            image_entry = self.table_images.get(id=image)
            if image_entry.frames > 1:  # TODO
                number = "_"+("%"+"%d" % np.ceil(np.log10(image_entry.frames))+"d") % image_frame
            else:
                number = ""
            basename, ext = os.path.splitext(image_entry.filename)
            directory, basename = os.path.split(basename)
            current_maskname = basename + "_" + ext[1:] + number + "_mask.png"
            filename = os.path.join(self.GetMaskPath(), current_maskname)
            # Save entry
            mask_entry.filename = current_maskname
            mask_entry.save()
    
        # Create image
        pil_image = Image.fromarray(mask)
        # Create color palette
        lut = np.zeros(3 * 256, np.uint8)
        for draw_type in self.table_maskTypes.select():
            index = draw_type.index
            lut[index * 3:(index + 1) * 3] = [int("0x"+draw_type.color[i:i+2], 16) for i in [1, 3, 5]]
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
