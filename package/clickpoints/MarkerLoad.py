from __future__ import print_function, division
import numpy as np
import os
import peewee
from playhouse import apsw_ext
from playhouse.apsw_ext import apsw
import time
from PIL import Image

class DataFile:
    def __init__(self, database_filename='clickpoints.db'):
        self.database_filename = database_filename
        self.db = apsw_ext.APSWDatabase(database_filename)

        """ Basic Tables """
        class BaseModel(peewee.Model):
            class Meta:
                database = self.db

        class Images(BaseModel):
            filename = peewee.CharField()
            ext = peewee.CharField()
            frames = peewee.IntegerField(default=0)
            external_id = peewee.IntegerField(null=True)
            timestamp = peewee.DateTimeField(null=True)

        self.base_model = BaseModel
        self.table_images = Images
        self.tables = [BaseModel, Images]

        """ Marker Tables """
        class Tracks(BaseModel):
            uid = peewee.CharField()
            def points(self):
                return np.array([[point.x, point.y] for point in self.marker()])
            def marker(self):
                return Marker.select().where(Marker.track == self).join(Images).order_by(Images.filename).order_by(Marker.image_frame)
            def times(self):
                return np.array([point.image.timestamp for point in self.marker()])

        class Types(BaseModel):
            name = peewee.CharField()
            color = peewee.CharField()
            mode = peewee.IntegerField()

        class Marker(BaseModel):
            image = peewee.ForeignKeyField(Images)
            image_frame = peewee.IntegerField()
            x = peewee.FloatField()
            y = peewee.FloatField()
            type = peewee.ForeignKeyField(Types)
            processed = peewee.IntegerField(default=0)
            partner_id = peewee.IntegerField(null=True)
            track = peewee.ForeignKeyField(Tracks, null=True)
            class Meta:
                indexes = ((('image', 'image_frame', 'track'), True), )

        self.table_marker = Marker
        self.table_tracks = Tracks
        self.table_types = Types
        self.tables.extend([Marker, Tracks, Types])

        """ Mask Tables """
        class Mask(BaseModel):
            image = peewee.ForeignKeyField(Images)
            image_frame = peewee.IntegerField()
            filename = peewee.CharField()

        class MaskTypes(BaseModel):
            name = peewee.CharField()
            color = peewee.CharField()
            index = peewee.IntegerField()

        self.table_mask = Mask
        self.table_maskTypes = MaskTypes
        self.tables.extend([Mask, MaskTypes])

        """ Connect """
        self.db.connect()

database = DataFile()

def GetImages():
    """
    Get all images sorted by filename

    Returns
    -------
    entries : array_like
        a query object containing all the images in the database file.
    """
    global database
    query = database.table_images.select()
    query.order_by(database.table_images.filename)
    return query

def GetTracks():
    """
    Get all track entries

    Returns
    -------
    entries : array_like
        a query object which contains the requested tracks.
    """
    global database
    query = database.table_tracks.select()
    return query

def GetMarker(image=None, image_frame=None, processed=None, type=None, track=None):
    """
    Get all the marker entries in the database where the parameters fit. If a parameter is omitted, the column is
    ignored. If it is provided a single value, only database entries matching this value are returned. If a list is
    supplied, any entrie with a value from the list is machted.

    Parameters
    ----------
    image : int, array, optional
        the image id(s) for the markers to be selected.
    image_frame : int, array, optional
        the image frame(s) for the markers to be selected.
    processed : bool, array, optional
        the processed flag(s) for the markers to be selected.
    type : int, array, optional
        the type id(s) for the markers to be selected.
    track : int, array, optional
        the track id(s) for the markers to be selected.

    Returns
    -------
    entries : array_like
        a query object which can be iterated to get the track entries wich where machted by the paremeters provided.
    """
    global database
    query = database.table_marker.select()
    parameter = [image, image_frame, processed, type, track]
    table = database.table_marker
    fields = [table.image, table.image_frame, table.processed, table.type, table.track]
    for field, parameter in zip(fields, parameter):
        if parameter is None:
            continue
        if isinstance(parameter, (tuple, list)):
            query = query.where(field << parameter)
        else:
            query = query.where(field == parameter)
    return query

def SetMarker(id=None, image=None, image_frame=None, x=None, y=None, processed=None, partner=None, type=None, track=None):
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
    image_frame : int, array, optional
        the image frame(s) for the markers to be inserted.
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
    global database
    data_sets = []
    table = database.table_marker
    fields = [table.id, table.image, table.image_frame, table.x, table.y, table.processed, table.partner_id, table.type, table.track]
    names = ["id", "image_id", "image_frame", "x", "y", "processed", "partner_id", "type_id", "track_id"]
    for data in np.broadcast(id, image, image_frame, x, y, processed, partner, type, track):
        data_set = []
        condition = "WHERE image_id = %d AND image_frame = %d AND track_id = %d" % (data[1], data[2], data[-1])
        for field, name, value in zip(fields, names, data):
            if value is None:
                data_set.append("(SELECT "+name+" FROM marker "+condition+")")
            else:
                data_set.append(str(value))
        data_sets.append(",\n ".join(data_set))
    query = "INSERT OR REPLACE INTO marker (id, image_id, image_frame, x, y, processed, partner_id, type_id, track_id)\n VALUES (\n"
    query += "),\n (".join(data_sets)
    query += ");"
    while 1:
        try:
            database.db.execute_sql(query)
        except apsw.BusyError:
            time.sleep(0.01)
            continue
        else:
            break

def GetMask(image, image_frame=0):
    """
    Get the mask image data for the image with the id `image`. If the database already has an entry the corresponding
    mask will be loaded, otherwise a new empty mask array will be created.

    To save the changes on the mask use `SetMask`.

    Parameters
    ----------
    image : int
        image id.
    image_frame : int, optional
        image frame number (default=0).

    Returns
    -------
    mask : ndarray
        mask data for the image.
    """
    global database
    try:
        # Test if mask already exists in database
        mask_entry = database.table_mask.get(database.table_mask.image == image, database.table_mask.image_frame == image_frame)
        # Load it
        im = np.asarray(Image.open(mask_entry.filename))
        im.setflags(write=True)
        return im
    except peewee.DoesNotExist:
        # Create new mask according to image size
        image_entry = database.table_images.get(database.table_images.id == image)
        pil_image = Image.open(image_entry.filename)
        im = np.zeros(pil_image.size, dtype=np.uint8)
        return im

def SetMask(mask, image, image_frame=0):
    """
    Add or overwrite the mask file for the image with the id `image` and the frame number `image_frame`

    Parameters
    ----------
    mask : array_like
        mask image data.
    image : int
        image id.
    image_frame : int, optional
        image frame number (default=0).
    """
    global database
    try:
        # Test if mask already exists in database
        mask_entry = database.table_mask.get(database.table_mask.image == image, database.table_mask.image_frame == image_frame)
        filename = mask_entry.filename
    except peewee.DoesNotExist:
        # Create new entry
        mask_entry = database.table_mask(image=image, image_frame=image_frame)
        # Get mask image name
        image_entry = database.table_images.get(id=image)
        if image_entry.frames > 1:
            number = "_"+("%"+"%d" % np.ceil(np.log10(image_entry.frames))+"d") % image_frame
        else:
            number = ""
        basename, ext = os.path.splitext(image_entry.filename)
        directory, basename = os.path.split(basename)
        current_maskname = os.path.join(directory, basename + "_" + ext[1:] + number + "_mask.png")
        filename = current_maskname
        # Save entry
        mask_entry.filename = current_maskname
        mask_entry.save()

    # Create image
    pil_image = Image.fromarray(mask)
    # Create color palette
    lut = np.zeros(3 * 256, np.uint8)
    for draw_type in database.table_maskTypes.select():
        index = draw_type.index
        lut[index * 3:(index + 1) * 3] = [int("0x"+draw_type.color[i:i+2], 16) for i in [1, 3, 5]]
    pil_image.putpalette(lut)
    # Save mask
    pil_image.save(filename)
