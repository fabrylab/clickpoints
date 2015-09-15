from __future__ import division, print_function
import os
import re
import glob

try:
    from PyQt5 import QtGui, QtCore
    from PyQt5.QtWidgets import QWidget, QTextStream, QGridLayout
    from PyQt5.QtCore import Qt
except ImportError:
    from PyQt4 import QtGui, QtCore
    from PyQt4.QtGui import QWidget, QGridLayout, QLabel, QLineEdit, QComboBox, QPushButton, QPlainTextEdit, QTableWidget, QHeaderView, QTableWidgetItem
    from PyQt4.QtCore import Qt, QTextStream, QFile, QStringList

from abc import abstractmethod

from peewee import *
from datetime import datetime


class systems(Model):
    name = CharField()
    def devices(self):
        return devices.select().where(devices.system == self)


class devices(Model):
    system = ForeignKeyField(systems)
    name = CharField()

class files(Model):
    timestamp = DateTimeField()
    system = ForeignKeyField(systems)
    device = ForeignKeyField(devices)
    basename = CharField()
    path = IntegerField()
    extension = CharField()

class folder(Model):
    parent_id = IntegerField()#ForeignKeyField(folder)
    name = CharField()

class config:
    def __init__(self):
        self.sql_dbname = 'annotation'
        self.sql_host = '131.188.117.100'
        self.sql_port = 3306
        self.sql_user = 'clickpoints'
        self.sql_pwd = '123456'

class Database:
    def __init__(self):
        self.config = config()

        # init db connection
        self.db = MySQLDatabase(self.config.sql_dbname,
                                host=self.config.sql_host,
                                port=self.config.sql_port,
                                user=self.config.sql_user,
                                passwd=self.config.sql_pwd)

        self.db.connect()

        if self.db.is_closed():
            print("Couldn't open connection to DB %s on host %s",self.config.sql_dbname,self.config.sql_host)
            # TODO clean break?
        else:
            print("connection established")

        # generate acess class

        self.SQL_Systems = systems
        self.SQL_Systems._meta.database = self.db
        self.SQL_Devices = devices
        self.SQL_Devices._meta.database = self.db
        self.SQL_Files = files
        self.SQL_Files._meta.database = self.db
        self.SQL_Folder = folder
        self.SQL_Folder._meta.database = self.db

        self.system_dict = {}
        res = self.SQL_Systems.select()
        for item in res:
            self.system_dict[item.name] = item.id

        self.device_dict = {}
        res = self.SQL_Devices.select()
        for item in res:
            self.device_dict[str(item.system.name)+"_"+item.name] = item.id
        print(self.device_dict)

        #self.saveFile()
        #self.SQL_Files.timestamp > datetime(2015,9,11,23,10,55) &
        #res = self.SQL_Files.select(self.SQL_Files.path).where( self.SQL_Files.system == 3)#(self.SQL_Files.timestamp > datetime(2015,9,11,23,10,55)) & (self.SQL_Files.timestamp < datetime(2015,9,11,23,20,55)) )
        #for item in res:
        #    print("Path", item.path)

    def getPath(self, path_id):
        path = []
        while path_id:
            item = self.SQL_Folder.get(self.SQL_Folder.id == path_id)
            path_id = item.parent_id
            path.append(item.name)
        return "\\".join(path[::-1])

    def savePath(self, folder="", parent=""):

        try:
            item = self.SQL_Folder.get(self.SQL_Folder.name == folder, self.SQL_Folder.parent_id == parent)
        except DoesNotExist:
            item = self.SQL_Folder()

            # update values and update db
            item.name = folder
            item.parent_id = parent

            item.save()
        return item.id

    def getSystemId(self, system_name):
        return self.system_dict[system_name]

    def getDeviceId(self, system_name, device_name):
        return self.device_dict[system_name+"_"+device_name]

    def saveFiles(self, files):
        with self.db.atomic():
            self.SQL_Files.insert_many(files).execute()

    def saveFile(self, tstamp=-1, system_name = "AntaviaSpot", device_name = "Camera", basename="", ext=".none", path = r"/folder/10/test10.png"):

        if tstamp == -1:
            tstamp = datetime.today()#1970,1,1,0,0,0)#datetime.strptime(,'%Y%m%d-%H%M%S')

        system_id = self.system_dict[system_name]
        device_id = self.device_dict[system_name+"_"+device_name]

        try:
            item = self.SQL_Files.get(self.SQL_Files.basename == basename)
            #print("entry found")
        except DoesNotExist:
            item = self.SQL_Files()

        # update values and update db
        item.timestamp = tstamp
        item.system = system_id
        item.device = device_id
        item.basename = basename
        item.extension = ext
        item.path = path

        item.save()
        #print('update')

if __name__ == '__main__':
    database = Database()