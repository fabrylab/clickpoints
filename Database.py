from __future__ import division, print_function
import os
import re
from peewee import *
from playhouse import apsw_ext

class DataFile:
    def __init__(self, database_filename='clickpoints.db'):
        self.exists = os.path.exists(database_filename)
        self.db = apsw_ext.APSWDatabase(database_filename)

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

        self.db.connect()
        if not self.exists:
            self.db.create_tables([self.table_images])

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

    def set_image(self, file_entry, frame, timestamp):
        #if self.image:
        #    use = self.table_marker.select(fn.count(self.table_marker.id).alias('count')).where(self.table_marker.image == self.image)[0]
        #    if use.count == 0:
        #        if self.next_image_index == self.image.id+1:
        #            self.next_image_index -= 1
        #        self.image.delete_instance()
        if self.image and not self.image_saved:
            if self.image_uses > 0:
                self.image.save(force_insert=True)
                self.next_image_index += 1
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
            self.image_uses = 0
            self.image_saved = False
        self.image_frame = frame
        self.timestamp = timestamp
        return self.image
