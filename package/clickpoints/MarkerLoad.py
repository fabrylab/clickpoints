from __future__ import print_function, division
import numpy as np
import re
from peewee import *
import peewee
from playhouse import apsw_ext
from playhouse.apsw_ext import apsw
import time

class DataFile:
    def __init__(self, database_filename='clickpoints.db'):
        self.database_filename = database_filename
        self.db = apsw_ext.APSWDatabase(database_filename)

        """ Basic Tables """
        class BaseModel(Model):
            class Meta:
                database = self.db

        class Images(BaseModel):
            filename = CharField()
            ext = CharField()
            frames = IntegerField(default=0)
            external_id = IntegerField(null=True)
            timestamp = DateTimeField(null=True)

        self.base_model = BaseModel
        self.table_images = Images
        self.tables = [BaseModel, Images]

        """ Marker Tables """
        class Tracks(BaseModel):
            uid = peewee.CharField()

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
                indexes = ( (('image', 'image_frame', 'track'), True), )

        self.table_marker = Marker
        self.table_tracks = Tracks
        self.table_types = Types
        self.tables.extend([Marker, Tracks, Types])

        """ Connect """
        self.db.connect()

database = DataFile()

def GetMarker(image=None, image_frame=None, processed=None, type=None, track=None):
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
        #print(data_sets)
    query = "INSERT OR REPLACE INTO marker (id, image_id, image_frame, x, y, processed, partner_id, type_id, track_id)\n VALUES (\n"
    query += "),\n (".join(data_sets)
    query += ");"
    #print(query)
    while 1:
        try:
            database.db.execute_sql(query)
        except apsw.BusyError:
            time.sleep(0.01)
            continue
        else:
            break
    #print(database.table_marker.raw(query).execute())
    #print(database.table_marker.raw(query))

def ReadTypeDict(string):
    dictionary = {}
    matches = re.findall(
        r"(\d*):\s*\[\s*\'([^']*?)\',\s*\[\s*([\d.]*)\s*,\s*([\d.]*)\s*,\s*([\d.]*)\s*\]\s*,\s*([\d.]*)\s*\]", string)
    for match in matches:
        dictionary[int(match[0])] = [match[1], map(float, match[2:5]), int(match[5])]
    return dictionary

def LoadLog(logname):
    global types
    points = []
    types = {}
    with open(logname) as fp:
        for index, line in enumerate(fp.readlines()):
            line = line.strip()
            if line[:7] == "#@types":
                type_string = line[7:].strip()
                if type_string[0] == "{":
                    try:
                        types = ReadTypeDict(line[7:])
                    except:
                        print("ERROR: Type specification in %s broken, use types from config instead" % logname)
                    continue
            if line[0] == '#':
                continue
            line = line.split(" ")
            x = float(line[0])
            y = float(line[1])
            marker_type = int(line[2])
            if marker_type not in types.keys():
                np.random.seed(marker_type)
                types[marker_type] = ["id%d" % marker_type, np.random.randint(0, 255, 3), 0]
            if len(line) == 3:
                points.append(dict(x=x, y=y, type=marker_type))
                continue
            processed = int(line[3])
            if marker_type == -1:
                continue
            marker_id = line[4]
            partner_id = None
            if len(line) >= 6:
                partner_id = line[5]
            points.append(dict(x=x, y=y, type=marker_type, id=marker_id, partner_id=partner_id, processed=processed))
    return points, types

def LoadLogIDindexed(logname):
    points, types = LoadLog(logname)
    points2 = {point["id"]: point for point in points}
    return points2, types

def SaveLog(filename, points, types={}):
    if isinstance(points, dict):
        points = [points[id] for id in points]
    data = ["%f %f %d %d %s %s\n" % (point["x"], point["y"], point["type"], point["processed"], point["id"], point["partner_id"]) for point in points]
    with open(filename, 'w') as fp:
        fp.write("#@types " + str(types) + "\n")
        for line in data:
            fp.write(line)