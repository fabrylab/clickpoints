from __future__ import division, print_function
import os
import re
import glob

# try:
#     from PyQt5 import QtGui, QtCore
#     from PyQt5.QtWidgets import QWidget, QTextStream, QGridLayout
#     from PyQt5.QtCore import Qt
# except ImportError:
#     from PyQt4 import QtGui, QtCore
#     from PyQt4.QtGui import QWidget, QGridLayout, QLabel, QLineEdit, QComboBox, QPushButton, QPlainTextEdit, QTableWidget, QHeaderView, QTableWidgetItem
#     from PyQt4.QtCore import Qt, QTextStream, QFile, QStringList

from abc import abstractmethod

from peewee import *
from datetime import datetime


class systems(Model):
    name = CharField()
    def devices(self):
        return devices.select().where(devices.system == self)

class systemalias(Model):
    name = CharField()
    system_id = IntegerField()

class devices(Model):
    system = ForeignKeyField(systems)
    name = CharField()

class devicealias(Model):
    name = CharField()
    device_id = IntegerField()

class files(Model):
    timestamp = DateTimeField()
    timestamp2 = DateTimeField()
    frames = IntegerField()
    system = ForeignKeyField(systems)
    device = ForeignKeyField(devices)
    basename = CharField()
    path = IntegerField()
    extension = CharField()
    annotation_id = IntegerField()


class folder(Model):
    parent_id = IntegerField()#ForeignKeyField(folder)
    name = CharField()

class SQLAnnotation(Model):
    timestamp = DateTimeField()
    tag_type = CharField()
    rating = IntegerField()
    reffilename = CharField()
    reffileext = CharField()
    comment = TextField()
    file = ForeignKeyField(files)

class tags(Model):
    name = CharField()

class tagassociation(Model):
    annotation = ForeignKeyField(SQLAnnotation)
    tag = ForeignKeyField(tags)

# TODO: make sure this doesn't overwrite actual config!
class config:
    def __init__(self):
        self.sql_dbname = 'annotation'
        self.sql_host = '131.188.117.94'
        self.sql_port = 3306
        self.sql_user = 'clickpoints'
        self.sql_pwd = '123456'

class DatabaseFiles:
    def __init__(self,config):
        self.config = config

        # init db connection
        self.db = MySQLDatabase(self.config.sql_dbname,
                                host=self.config.sql_host,
                                port=self.config.sql_port,
                                user=self.config.sql_user,
                                passwd=self.config.sql_pwd)

        self.db.connect()

        if self.db.is_closed():
            raise Exception("Couldn't open connection to DB %s on host %s" % (self.config.sql_dbname,self.config.sql_host))
        else:
            print("Connection established to fileDB %s on host %s" % (self.config.sql_dbname,self.config.sql_host))

        # generate acess class

        self.SQL_Systems = systems
        self.SQL_Systems._meta.database = self.db
        self.SQL_SystemAlias = systemalias
        self.SQL_SystemAlias._meta.database = self.db
        self.SQL_Devices = devices
        self.SQL_Devices._meta.database = self.db
        self.SQL_DeviceAlias = devicealias
        self.SQL_DeviceAlias._meta.database = self.db
        self.SQL_Files = files
        self.SQL_Files._meta.database = self.db
        self.SQL_Folder = folder
        self.SQL_Folder._meta.database = self.db

        self.SQL_Annotation = SQLAnnotation
        self.SQL_Annotation._meta.database = self.db
        self.SQL_TagAssociation = tagassociation
        self.SQL_TagAssociation._meta.database = self.db
        self.SQL_Tags = tags
        self.SQL_Tags._meta.database = self.db

        self.system_dict = {}
        self.updateSystemDict()
        self.systemalias_dict = {}
        self.updateSystemAliasDict()

        self.device_dict = {}
        self.device_dict_plain = {}
        self.updateDeviceDict()
        self.devicealias_dict = {}
        self.updateDeviceAliasDict()
        #print(self.device_dict)

        #self.saveFile()
        #self.SQL_Files.timestamp > datetime(2015,9,11,23,10,55) &
        #res = self.SQL_Files.select(self.SQL_Files.path).where( self.SQL_Files.system == 3)#(self.SQL_Files.timestamp > datetime(2015,9,11,23,10,55)) & (self.SQL_Files.timestamp < datetime(2015,9,11,23,20,55)) )
        #for item in res:
        #    print("Path", item.path)

        # set all timestamp2 entires to timestamp
        #query = self.SQL_Files.update(timestamp2=self.SQL_Files.timestamp)
        #query.execute()

    ''' SYSTEM functions '''
    def updateSystemDict(self):
        self.system_dict = {}
        res = self.SQL_Systems.select()
        for item in res:
            self.system_dict[item.name] = item.id

    def updateSystemAliasDict(self):
        self.systemalias_dict = {}
        res = self.SQL_SystemAlias.select()
        for item in res:
            self.systemalias_dict[item.name] = item.id

    def getSystemId(self, system_name):
        return self.system_dict[system_name]

    def getSystemName(self, id):
        system_dict_byname = { v:k for k, v in self.system_dict.items()}
        return system_dict_byname[id]

    def getSystemIdByAlias(self,system_name):
        alais_id = self.systemalias_dict[system_name]
        qr = self.SQL_SystemAlias.get(self.SQL_SystemAlias.id==alais_id)
        return qr.system_id

    def retrieveSystemID(self,name):
        self.updateSystemDict()
        try:
            # check for system name in db
            system_id = self.getSystemId(name)
            return system_id
        except KeyError:
            print('System Key=%s not found' % name)
            try:
                # check alias
                system_id = self.getSystemIdByAlias(name)
                return system_id
            except KeyError:
                print('SystemAlias Key=%s not found' % name)
                return False


    def newSystem(self, system_name):
        system_id = self.SQL_Systems.create(name=system_name).id
        self.updateSystemDict()
        return system_id

    def newSystemAlias(self,system_alias,system_name):
        try:
            system_id = self.getSystemId(system_name)
            if not system_alias in self.systemalias_dict:
                system_id = self.SQL_SystemAlias.create(name=system_alias,system_id=system_id).id
                return system_id
        except KeyError:
            raise Exception("The target system %s does not exist!"%system_name)


    ''' DEVICE functions '''
    def updateDeviceDict(self):
        self.device_dict = {}
        res = self.SQL_Devices.select()
        for item in res:
            self.device_dict[str(item.system.name)+"_"+item.name] = item.id
        self.device_dict_plain = {}
        for item in res:
            self.device_dict_plain[item.name] = item.id

    def updateDeviceAliasDict(self):
        self.devicealias_dict = {}
        res = self.SQL_DeviceAlias.select()
        for item in res:
            self.devicealias_dict[item.name] = item.device_id

    def retrieveDeviceID(self,system_name, device_name):
        self.updateDeviceDict()
        try:
            # check for device name in db
            device_id = self.getDeviceId(system_name,device_name)
            return device_id
        except KeyError:
            print('System Key=%s_%s not found' % (system_name,device_name))
            try:
                # check alias
                device_id = self.getDeviceIdByAlias(device_name)
                return device_id
            except KeyError:
                print('SystemAlias Key=%s_%s not found' % (system_name,device_name))
                return False

    def getDeviceId(self, system_name, device_name):
        return self.device_dict[system_name+"_"+device_name]

    def getDeviceName(self, id):
        device_dict_byname = { v:k for k, v in self.device_dict_plain.items()}
        return device_dict_byname[id]

    def getDeviceIdByAlias(self,device_name):
        #device_dict_plain_reverse = { v:k for k, v in self.device_dict_plain.query()}
        return self.devicealias_dict[device_name]

    def newDevice(self, system_id, device_name):
        device_id = self.SQL_Devices.create(name=device_name, system=system_id).id
        self.updateDeviceDict()
        return device_id

    def newDeviceAlias(self,device_alias,system_name,device_name):
        try:
            device_id = self.getDeviceId(system_name,device_name)
            if not device_alias in self.devicealias_dict:
                self.SQL_DeviceAlias.create(name=device_alias,device_id=device_id)
                return device_id
        except KeyError:
            raise Exception("The target device %s does not exist!"%device_name)


    ''' PATH functions '''
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

    def getIdListForPath(self,path):
        # get id based on path
        clean_path = path.strip(os.sep)     # remove trailing/leading seperators '//' '/' '\\' '\' etc
        token = clean_path.split(os.sep)    # tokenize on seperator

        # get base path_id
        path_id_list = [0]
        item = self.SQL_Folder.get(self.SQL_Folder.name == token[0])
        if not item.parent_id == 0:
            raise Exception(" \"%s\" is not a top level path - specified path must be absolute!" % item.name)
        else:
            path_id_list.append(item.id)

        # itterate through tokens and extract paths with correct name and parent_id
        for t in token[1::]:
            try:
                item = self.SQL_Folder.get(self.SQL_Folder.name == t, self.SQL_Folder.parent_id == path_id_list[-1])
                path_id_list.append(item.id)
                # print(item.id,item.name,item.parent_id)
            except:
                raise Exception('Path: \'%s\' in \'%s\' does not exist in the folder table'%(t,path))


        return path_id_list

    def deleteFilesByPathID(self,cpath_id):
        # get list of folders ids included start id
        path_id_list = [cpath_id]   # first path entry is the start path

        done=False
        name_list=[]
        nextsearch_path_id_list = [cpath_id]
        while not done:
            tmp_list = []
            for id in nextsearch_path_id_list:
                print("search children for id:",id)
                try:
                    query = self.SQL_Folder.select().where(self.SQL_Folder.parent_id == id)

                    # add new paths to search for next itteration
                    for item in query:
                        tmp_list.append(item.id)
                        print(id)
                        print(item.id,item.name,item.parent_id)
                        name_list.append(item.name)

                    # found children - add to final list
                    path_id_list.append(id)
                except:
                    # no more children found - add to final list
                    path_id_list.append(id)

            nextsearch_path_id_list = tmp_list

            if nextsearch_path_id_list == []:
                done=True

        # request file list for all files connected to folders in path_id_list
        # DELETE all file entries
        query = self.SQL_Files.delete().where(self.SQL_Files.path.in_(path_id_list))
        print(query.execute(),'files deleted!')

        # DELETE all path entries
        query = self.SQL_Folder.delete().where(self.SQL_Folder.id.in_(path_id_list))
        print(query.execute(),'path segments deleted!')

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
    db = DatabaseFiles(config())


    # test code for folder based wipe
    #
    # path=os.path.normpath(r'\\131.188.117.94\data\microbsCRO\2012')
    #
    #
    # path_id_list=db.getIdListForPath(path)
    # current_path_id = path_id_list[-1]
    #
    # db.deleteFilesByPathID(current_path_id)



























