from __future__ import division, print_function
import os
import re
import datetime
import numpy as np
from peewee import *
from playhouse.reflection import Introspector
try:
    from StringIO import StringIO  # python 2
except ImportError:
    from io import StringIO  # python 3

def SQLMemoryDBFromFile(filename, *args, **kwargs):

    db_file = SqliteDatabase(filename, *args, **kwargs)

    db_file.connect()
    con = db_file.get_conn()
    tempfile = StringIO()
    for line in con.iterdump():
        tempfile.write('%s\n' % line)
    tempfile.seek(0)

    db_memory = SqliteDatabase(":memory:", *args, **kwargs)
    db_memory.get_conn().cursor().executescript(tempfile.read())
    db_memory.get_conn().commit()
    return db_memory

def SaveDB(db_memory, filename):
    if os.path.exists(filename):
        os.remove(filename)
    db_file = SqliteDatabase(filename)
    con_file = db_file.get_conn()
    con_memory = db_memory.get_conn()

    tempfile = StringIO()
    for line in con_memory.iterdump():
        tempfile.write('%s\n' % line)
    tempfile.seek(0)

    con_file.cursor().executescript(tempfile.read())
    con_file.commit()


def SQLMemoryDBFromFileAPSW(filename):
    from playhouse import apsw_ext
    db_file = apsw_ext.APSWDatabase(filename)
    db_memory = apsw_ext.APSWDatabase(':memory:')
    with db_memory.get_conn().backup("main", db_file.get_conn(), "main") as backup:
        backup.step()  # copy whole database in one go
    return db_memory

def SaveDBAPSW(db_memory, filename):
    from playhouse import apsw_ext
    db_file = apsw_ext.APSWDatabase(filename)
    with db_file.get_conn().backup("main", db_memory.get_conn(), "main") as backup:
        backup.step()  # copy whole database in one go

class DataFile:
    def __init__(self, database_filename='clickpoints.db'):
        self.database_filename = database_filename
        self.exists = os.path.exists(database_filename)
        self.current_version = "4"
        if self.exists:
            self.db = SqliteDatabase(database_filename)
            introspector = Introspector.from_database(self.db)
            models = introspector.generate_models()
            try:
                version = models["meta"].get(models["meta"].key == "version").value
            except (KeyError, DoesNotExist):
                version = "0"
            print("Open database with version", version)
            if int(version) < int(self.current_version):
                self.migrateDBFrom(version)
            elif int(version) > int(self.current_version):
                print("Warning Database version %d is newer than ClickPoints version %d "
                      "- please get an updated Version!"
                      % (int(version), int(self.current_version)))
                print("Proceeding on own risk!")
        else:
            self.db = SqliteDatabase(":memory:")

        class BaseModel(Model):
            class Meta:
                database = self.db

        class Meta(BaseModel):
            key = CharField(unique=True)
            value = CharField()

        class Images(BaseModel):
            filename = CharField()
            ext = CharField()
            frames = IntegerField(default=0)
            external_id = IntegerField(null=True)
            timestamp = DateTimeField(null=True)

        class Offsets(BaseModel):
            image = ForeignKeyField(Images)
            image_frame = IntegerField()
            x = FloatField()
            y = FloatField()
            class Meta:
                indexes = ((('image', 'image_frame'), True), )

        self.tables = [BaseModel, Meta, Images, Offsets]

        self.base_model = BaseModel
        self.table_meta = Meta
        self.table_images = Images
        self.table_offsets = Offsets

        self.db.connect()
        for table in [self.table_meta, self.table_images, self.table_offsets]:
            if not table.table_exists():
                table.create_table()
        if not self.exists:
            self.table_meta(key="version", value=self.current_version).save()

        self.image = None
        self.next_image_index = 1
        query = self.table_images.select().order_by(-self.table_images.id).limit(1)
        for image in query:
            self.next_image_index = image.id+1

        self.image = None
        self.image_frame = 0
        self.timestamp = 0
        self.image_uses = 0
        self.image_saved = True

    def migrateDBFrom(self, version):
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
            self.db.execute_sql("ALTER TABLE tracks ADD COLUMN text varchar(255)")
            # Add text fields for Types
            self.db.execute_sql("ALTER TABLE types ADD COLUMN text varchar(255)")
            nr_new_version = 4

        self.db.execute_sql("INSERT OR REPLACE INTO meta (id,key,value) VALUES ( \
                                            (SELECT id FROM meta WHERE key='version'),'version',%s)" % str(nr_new_version))

    def save_current_image(self):
        if not self.exists:
            SaveDB(self.db, self.database_filename)
            self.db = SqliteDatabase(self.database_filename)
            for table in self.tables:
                table._meta.database = self.db
            self.exists = True
        if self.image.timestamp:
            self.image.timestamp = str(self.image.timestamp)
        self.image.save(force_insert=True)
        self.image_saved = True
        self.next_image_index += 1

    def check_to_save(self):
        if self.image and not self.image_saved:
            if self.image_uses > 0:
                self.save_current_image()

    def set_image(self, file_entry, frame, timestamp):
        self.check_to_save()
        try:
            self.image = self.table_images.get(self.table_images.filename == file_entry.filename)
            self.image_saved = True
        except DoesNotExist:
            self.image = self.table_images(id=self.next_image_index)
            self.image.filename = file_entry.filename
            self.image.ext = file_entry.extension
            self.image.frames = file_entry.frames
            self.image.external_id = file_entry.external_id
            self.image.id = self.next_image_index
            self.image.timestamp = file_entry.timestamp
            self.image_uses = 0
            self.image_saved = False
        self.image_frame = frame
        self.timestamp = timestamp
        return self.image

    def get_image(self, file_entry, frame, timestamp):
        try:
            image = self.table_images.get(self.table_images.filename == file_entry.filename)
        except DoesNotExist:
            if self.image and not self.image_saved:
                self.save_current_image()
            try:
                image = self.table_images.get(self.table_images.filename == file_entry.filename)
            except DoesNotExist:
                image = self.table_images(id=self.next_image_index)
                image.filename = file_entry.filename
                image.ext = file_entry.extension
                image.frames = file_entry.frames
                image.external_id = file_entry.external_id
                image.id = self.next_image_index
                self.next_image_index += 1
                image.save(force_insert=True)
        return image

    def get_offset(self, filename, frame):
        try:
            image = self.table_images.get(filename=filename)
            print("image", image, frame)
            offset = self.table_offsets.get(image=image, image_frame=frame)
            return [offset.x, offset.y]
        except DoesNotExist:
            return [0, 0]

    def get_offset_maxmin(self,round=True):
        try:
            query = self.table_offsets.select( fn.Max(self.table_offsets.x).alias('max_x'),
                                               fn.Min(self.table_offsets.x).alias('min_x'),
                                               fn.Max(self.table_offsets.y).alias('max_y'),
                                               fn.Min(self.table_offsets.y).alias('min_y'))
            for q in query:
                if round:
                    return [np.ceil(q.max_x), np.floor(q.min_x), np.ceil(q.max_y), np.floor(q.min_y)]
                else:
                    return [q.max_x, q.min_x, q.max_y, q.min_y]
        except DoesNotExist:
            return [0,0,0,0]


if __name__ == '__main__':
    db = DataFile(r'C:\Users\fox\Dropbox\PhD\python\CountPenugs\activity\clickpoints.db')