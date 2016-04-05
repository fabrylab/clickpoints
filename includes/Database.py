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
import imageio
from threading import Thread
from PyQt4 import QtCore

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
            frame = IntegerField(default=0)
            external_id = IntegerField(null=True)
            timestamp = DateTimeField(null=True)

        class Offsets(BaseModel):
            image = ForeignKeyField(Images, unique=True)
            x = FloatField()
            y = FloatField()

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

        self.reader = None
        self.image = None
        self.current_image_index = None
        self.buffer = FrameBuffer(100)#self.config.buffer_size)
        self.thread = None

        class DataFileSignals(QtCore.QObject):
            loaded = QtCore.pyqtSignal(int)
        self.signals = DataFileSignals()

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
            try:
                self.db.execute_sql("ALTER TABLE tracks ADD COLUMN text varchar(255)")
            except OperationalError:
                pass
            # Add text fields for Types
            try:
                self.db.execute_sql("ALTER TABLE types ADD COLUMN text varchar(255)")
            except OperationalError:
                pass
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

    def get_image_count(self):
        return self.table_images.select().count()

    def get_current_image(self):
        return self.current_image_index

    def load_frame(self, index, threaded):
        # check if frame is already buffered then we don't need to load it
        if self.buffer.get_frame(index) is not None:
            self.signals.loaded.emit(index)
            return
        # if we are still loading a frame finish first
        if self.thread:
            self.thread.join()
        # query the information on the image to load
        image = self.table_images.select().limit(1).offset(index)[0]
        # prepare a slot in the buffer
        slots, slot_index, = self.buffer.prepare_slot(index)
        # call buffer_frame in a separate thread or directly
        if threaded:
            self.thread = Thread(target=self.buffer_frame, args=(image, slots, slot_index, index))
            self.thread.start()
        else:
            return self.buffer_frame(image, slots, slot_index, index)

    def buffer_frame(self, image, slots, slot_index, index):
        # if we have already a reader...
        if self.reader:
            # ... check if it is the right one, if not delete it
            if image.filename != self.reader.filename:
                del self.reader
                self.reader = None
        # if we don't have a reader, create a new one
        if self.reader is None:
            self.reader = imageio.get_reader(image.filename)
            self.reader.filename = image.filename
        # get the data from the reader and store it in the slot
        image_data = self.reader.get_data(image.frame)
        slots[slot_index] = image_data
        # notify that the frame has been loaded
        self.signals.loaded.emit(index)

    def get_image_data(self):
        return self.buffer.get_frame(self.current_image_index)

    def add_image(self, filename, extension, external_id, frames):
        for i in range(frames):
            image = self.table_images()
            image.filename = filename
            image.ext = extension
            image.frames = frames
            image.frame = i
            image.external_id = external_id
            image.timestamp = None#file_entry.timestamp
            image.save()

    def set_image(self, index):#file_entry, frame, timestamp):
        self.image = self.table_images.select().limit(1).offset(index)[0]
        self.current_image_index = index
        return
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

    def get_offset(self, image=None):
        if image is None:
            image = self.image
        try:
            offset = self.table_offsets.get(image=image)
            return [offset.x, offset.y]
        except DoesNotExist:
            return [0, 0]

    def closeEvent(self, QCloseEvent):
        pass


class FrameBuffer:
    def __init__(self, buffer_count):
        self.slots = [[]]*buffer_count
        self.indices = [None]*buffer_count
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
