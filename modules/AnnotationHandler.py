from __future__ import division, print_function
import os
import sys
import re
import glob

try:
    from PyQt5 import QtGui, QtCore
    from PyQt5.QtWidgets import QWidget, QTextStream, QGridLayout
    from PyQt5.QtCore import Qt
except ImportError:
    from PyQt4 import QtGui, QtCore
    from PyQt4.QtGui import QWidget, QDialog, QGridLayout, QHBoxLayout, QVBoxLayout,QSizePolicy, QLabel, QLineEdit, QComboBox, QPushButton, QPlainTextEdit, QTableWidget, QHeaderView, QTableWidgetItem, QRadioButton
    from PyQt4.QtCore import Qt, QTextStream, QFile, QStringList

from Tools import BroadCastEvent
from abc import abstractmethod

#TODO conditional export based on config?
from peewee import *
import peewee
from datetime import datetime


sys.path.append(os.path.join(os.path.dirname(__file__), "..", "database"))
print(os.path.join(os.path.dirname(__file__), "..", "database"))
from databaseAnnotation import *
import databaseFiles as fileDB

# util
def UpdateDictWith(x, y):
    """Given two dicts, merge them into a new dict as a shallow copy."""

    z = x.copy()
    z.update(y)
    return z


class AnnotationFile:
    def __init__(self, datafile):
        self.data_file = datafile

        class Annotation(datafile.base_model):
            image = peewee.ForeignKeyField(datafile.table_images)
            image_frame = peewee.IntegerField()
            comment = peewee.TextField(default="")
            rating = peewee.IntegerField(default=0)

        class Tags(datafile.base_model):
            name = peewee.CharField()

        class Tagassociation(datafile.base_model):
            annotation = peewee.ForeignKeyField(Annotation)
            tag = peewee.ForeignKeyField(Tags)

        self.table_annotation = Annotation
        self.table_tags = Tags
        self.table_tagassociation = Tagassociation

        for table in [self.table_annotation, self.table_tags, self.table_tagassociation]:
            if not table.table_exists():
                table.create_table()

        self.annotation = None

    def add_annotation(self, **kwargs):
        kwargs.update(dict(image=self.data_file.image, image_frame=self.data_file.image_frame))
        self.annotation = self.table_annotation(**kwargs)
        return self.annotation

    def getAnnotation(self):
        try:
            self.annotation = self.table_annotation.get(self.table_annotation.image == self.data_file.image.id, self.table_annotation.image_frame == self.data_file.image_frame)
        except peewee.DoesNotExist:
            self.annotation = None
        return self.annotation

    def getTagList(self):
        return [tag.name for tag in self.table_tags.select()]

    def getTagsFromAnnotation(self):
        return [tag.name for tag in self.table_tags.select().join(self.table_tagassociation).join(self.table_annotation).where(self.table_annotation.id == self.annotation)]

    def setTags(self, tags):
        ids = []
        for tag in tags:
            try:
                tag_entry = self.table_tags.get(self.table_tags.name == tag)
            except peewee.DoesNotExist:
                tag_entry = self.table_tags(name=tag)
                tag_entry.save()
            ids.append(tag_entry.id)
        current_associations = self.table_tagassociation.select().join(self.table_annotation).where(self.table_annotation.id == self.annotation)
        for association in current_associations:
            if association.tag_id in ids:
                ids.remove(association.tag_id)
            else:
                association.delete_instance()
        for id in ids:
            association = self.table_tagassociation(tag=id, annotation=self.annotation.id)
            association.save()

    def get_annotation_frames(self):
        return self.table_annotation.select().group_by(self.table_annotation.image.concat(self.table_annotation.image_frame))

    def getAnnotationsByIds(self, id_list):
        return self.table_annotation.select(SQL("*"), SQL("GROUP_CONCAT(t3.name, ', ') as tags")).where(self.table_annotation.id << id_list).join(self.table_tagassociation, join_type="LEFT JOIN").join(self.table_tags, join_type="LEFT JOIN").group_by(self.table_annotation.id)

class pyQtTagSelector(QWidget):

    class unCheckBox(QtGui.QCheckBox):
        def __init__(self,parent,name):
            super(QtGui.QCheckBox, self).__init__(parent)
            #self.parent = parent
            self.name = name
            self.parent = parent

            self.setText(self.name)
            self.setChecked(True)
            self.toggled.connect(self.hCB_remove)

            # add to list of currently used tags
            self.parent.list.append(str(name))

            #print(self.parent.list)

        def hCB_remove(self):
            # remove from tag list
            self.parent.list.remove(self.name)

            # DEBUG
            #print(self.parent.list)

            # delete icon
            self.deleteLater()

    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent)


        self.cbTag = QtGui.QComboBox(self)
        self.cbTag.addItems(QStringList(['']))
        self.cbTag.setInsertPolicy(QtGui.QComboBox.InsertAtBottom)
        self.cbTag.setEditable(True)
        sizePolicy = QSizePolicy(QSizePolicy.Preferred,QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(1)
        self.cbTag.setSizePolicy(sizePolicy)
        self.cbTag.activated.connect(self.hPB_add)

        self.pbAdd = QtGui.QPushButton(self)
        self.pbAdd.setText('Add')
        self.pbAdd.setMaximumWidth(30)
        self.pbAdd.released.connect(self.hPB_add)


        self.layout_main = QtGui.QVBoxLayout()
        self.layout_main.setAlignment(Qt.AlignTop)
        self.layout_tag = QtGui.QHBoxLayout()
        self.layout_list = QtGui.QVBoxLayout()
        self.setLayout(self.layout_main)
        self.layout_main.addLayout(self.layout_tag)
        self.layout_main.addLayout(self.layout_list)
        self.layout_tag.addWidget(self.cbTag)
        self.layout_tag.addWidget(self.pbAdd)

        self.layout_main.setContentsMargins(0,0,0,0)

        self.list=[]

    def setText(self,string):
        self.cbTag.setEditText(string)

    def setStringList(self,string_list):
        self.cbTag.addItems(QStringList(string_list))

    def setActiveTagList(self,string_list):
        for tag in string_list:
            # on add create checked checbox
            cb = self.unCheckBox(self,tag)
            self.layout_list.addWidget(cb)

    def getTagList(self):
        return self.list

    def hPB_add(self):
        name = self.cbTag.currentText()
        # check if already in list
        if not name in self.list and not name=='':
            print('add: ',self.cbTag.currentText())

            # on add create checked checbox
            cb = self.unCheckBox(self,self.cbTag.currentText())
            self.layout_list.addWidget(cb)
        else:
            print("Item %s is already in list" % name)

class AddMetaTemplate(QDialog):
    def __init__(self,parent,name,dbFiles):
        QWidget.__init__(self)

        # paramete
        self.db=dbFiles
        self.name=name
        self.system_id=0

        self.setMinimumWidth(400)
        #self.setMinimumHeight(400)
        self.layout = QVBoxLayout(self)

        self.rb_AsType = QRadioButton("Add as Tag")
        self.rb_AsType.toggled.connect(self.h_rbSelect)
        self.rb_AsTypeAliasAndType = QRadioButton("Add as Alias for NEW Tag")
        self.rb_AsTypeAliasAndType.toggled.connect(self.h_rbSelect)



        # sub layouts
        self.layout_AsType= QHBoxLayout()
        self.layout_AsTypeAndAlias= QHBoxLayout()


        self.layout.addWidget(self.rb_AsType)
        self.layout.addLayout(self.layout_AsType)
        self.layout.addWidget(self.rb_AsTypeAliasAndType)
        self.layout.addLayout(self.layout_AsTypeAndAlias)


        self.pb_Confirm = QPushButton("OK")
        self.pb_Confirm.released.connect(self.h_pb_Confirm)
        self.pb_Confirm.setDisabled(True)
        self.pb_Cancel = QPushButton("Cancel")
        self.pb_Cancel.released.connect(self.h_pb_Cancel)

        self.layout_buttons = QHBoxLayout()
        self.layout_buttons.addWidget(self.pb_Confirm)
        self.layout_buttons.addWidget(self.pb_Cancel)
        self.layout.addLayout(self.layout_buttons)

    def h_pb_Confirm(self):
        print("Confirm pressed")
        self.close()

    def h_pb_Cancel(self):
        print("Cancel pressed")
        self.close()

    def h_rbSelect(self):
        self.pb_Confirm.setEnabled(True)


class AddMetaSystem(AddMetaTemplate):
    def __init__(self,parent,name,dbFiles):
        AddMetaTemplate.__init__(self,parent,type,dbFiles)

        self.name=name;

        # set names
        self.setWindowTitle("Add System or SystemAlias")
        self.rb_AsType.setText("Add \"%s\" as new System"%name)
        self.rb_AsTypeAliasAndType.setText("Add \"%s\" as Alias for a System"%name)

        # for add as Alias to new System
        self.layout_AsTypeAndAlias.addSpacing(20)
        self.layout_AsTypeAndAlias.addWidget(QLabel("Add "))
        self.leAlias = QLineEdit()
        self.leAlias.setText(name)
        self.leAlias.setDisabled(True)
        sp = self.leAlias.sizePolicy()
        sp.setHorizontalStretch(1)
        self.leAlias.setSizePolicy(sp)
        self.layout_AsTypeAndAlias.addWidget(self.leAlias)
        self.ComboBoxSystem2 = QComboBox(self)
        self.systems = dbFiles.SQL_Systems.select()
        for index, item in enumerate(self.systems):
            self.ComboBoxSystem2.insertItem(index, item.name)
        self.ComboBoxSystem2.setInsertPolicy(QComboBox.InsertAtBottom and QComboBox.InsertAtBottom)
        self.ComboBoxSystem2.setEditable(True)
        sp =self.ComboBoxSystem2.sizePolicy()
        sp.setHorizontalStretch(1)
        self.ComboBoxSystem2.setSizePolicy(sp)
        self.layout_AsTypeAndAlias.addWidget(self.ComboBoxSystem2)

    def h_pb_Confirm(self):
        print("Confirm pressed")

        # depending on mode:
        if self.rb_AsType.isChecked():
            # add as new System
            system_id=self.db.newSystem(self.name)
            self.system_id= system_id
        elif self.rb_AsTypeAliasAndType.isChecked():
            # check if target system exists
            target_system = str(self.ComboBoxSystem2.currentText())
            if target_system in self.db.system_dict:
                #get system_id
                system_id=self.db.getSystemId(target_system)
            else:
                # add System
                system_id=self.db.newSystem(target_system)

            # add Alias for System
            self.db.newSystemAlias(self.name,target_system)
            self.system_id= system_id

        self.close()

class AddMetaDevice(AddMetaTemplate):
    def __init__(self,parent,name,dbFiles,system_id):
        AddMetaTemplate.__init__(self,parent,type,dbFiles)

        self.name=name
        self.system_id=system_id

        # set names
        self.setWindowTitle("Add Device or DeviceAlias")
        self.rb_AsType.setText("Add \"%s\" as new Device"%name)
        self.rb_AsTypeAliasAndType.setText("Add \"%s\" as Alias for a Device"%name)

        # for add as Alias to new System
        self.layout_AsTypeAndAlias.addSpacing(20)
        self.layout_AsTypeAndAlias.addWidget(QLabel("Add "))
        self.leAlias = QLineEdit()
        self.leAlias.setText(name)
        self.leAlias.setDisabled(True)
        sp = self.leAlias.sizePolicy()
        sp.setHorizontalStretch(1)
        self.leAlias.setSizePolicy(sp)
        self.layout_AsTypeAndAlias.addWidget(self.leAlias)
        self.ComboBoxDevice = QComboBox(self)
        self.systems = dbFiles.SQL_Systems.select()
        self.devices = self.systems[self.system_id-1].devices()
        for index, item in enumerate(self.devices):
            self.ComboBoxDevice.insertItem(index, item.name)
        self.ComboBoxDevice.setInsertPolicy(QComboBox.InsertAtBottom and QComboBox.InsertAtBottom)
        self.ComboBoxDevice.setEditable(True)
        sp =self.ComboBoxDevice.sizePolicy()
        sp.setHorizontalStretch(1)
        self.ComboBoxDevice.setSizePolicy(sp)
        self.layout_AsTypeAndAlias.addWidget(self.ComboBoxDevice)

    def h_pb_Confirm(self):
        print("Confirm pressed")
        # TODO finish up confirm callback and update
        # depending on mode:
        if self.rb_AsType.isChecked():
            # add as new Device
            device_id=self.db.newDevice(self.system_id,self.name)
            self.device_id= device_id
        elif self.rb_AsTypeAliasAndType.isChecked():
            # check if target device exists
            target_device = str(self.ComboBoxDevice.currentText())
            target_system=  self.db.getSystemName(self.system_id)
            print("used names:",target_device,target_system)
            if (target_system+'_'+target_device) in self.db.device_dict:
                #get device_id
                device_id=self.db.getDeviceId(target_system,target_device)
            else:
                # add device
                device_id=self.db.newDevice(self.system_id,target_device)

            # add Alias for device
            self.db.newDeviceAlias(self.name,target_system,target_device)
            self.device_id= device_id

        self.close()


class AnnotationEditor(QWidget):
    def __init__(self, filename, image_frame, filenr, db, modules, config):
        QWidget.__init__(self)

        # default settings and parameters
        self.reffilename = filename
        self.db = db
        self.modules = modules
        self.config = config

        # regexp
        self.regFromFNameString = self.config.filename_data_regex
        self.regFromFName = re.compile(self.regFromFNameString)

        self.annotation = self.db.getAnnotation()
        if self.annotation is None:
            # extract relevant values, store in dict
            match = self.regFromFName.match(filename)
            if not match:
                print('warning - no match for regexp')
                re_dict = {}
            else:
                re_dict = match.groupdict()
            self.annotation = self.db.add_annotation(**re_dict)
            exists = False
        else:
            exists = True

        # widget layout and ellements
        self.setMinimumWidth(650)
        self.setMinimumHeight(400)
        self.setWindowTitle("Annotation")
        self.layout = QGridLayout(self)

        self.layout.addWidget(QLabel('AFile Name:'), 0, 0)
        self.leAName = QLineEdit(self.reffilename, self)
        self.leAName.setEnabled(False)
        self.layout.addWidget(self.leAName, 0, 1, 1, 3)

        if self.config.sql_annotation is True:
            self.layout.addWidget(QLabel('Time:', self), 1, 0)
            self.leTStamp = QLineEdit('uninit', self)
            self.leTStamp.setEnabled(False)
            self.layout.addWidget(self.leTStamp, 1, 1)

            self.layout.addWidget(QLabel('System:', self), 3, 0)
            self.leSystem = QLineEdit('uninit', self)
            self.leSystem.setEnabled(False)
            self.layout.addWidget(self.leSystem, 3, 1)

            self.layout.addWidget(QLabel('Camera:', self), 3, 2)
            self.leCamera = QLineEdit('uninit', self)
            self.leCamera.setEnabled(False)
            self.layout.addWidget(self.leCamera, 3, 3)

        self.laTag = QLabel('Tag:', self)
        self.laTag.setContentsMargins(0, 4, 0, 0)
        self.layout.addWidget(self.laTag, 4, 0, Qt.AlignTop)

        self.leTag = pyQtTagSelector()
        self.layout.addWidget(self.leTag, 4, 1)

        self.laRating = QLabel('Rating:', self)
        self.laRating.setContentsMargins(0, 4, 0, 0)
        self.layout.addWidget(self.laRating, 4, 2, Qt.AlignTop)
        self.leRating = QComboBox(self)
        for index, text in enumerate(['0 - none', '1 - bad', '2', '3', '4', '5 - good']):
            self.leRating.insertItem(index, text)
        self.leRating.setInsertPolicy(QComboBox.NoInsert)
        self.leRating.setContentsMargins(0, 5, 0, 0)
        self.layout.addWidget(self.leRating, 4, 3, Qt.AlignTop)

        self.pbConfirm = QPushButton('C&onfirm', self)
        self.pbConfirm.pressed.connect(self.saveAnnotation)
        self.layout.addWidget(self.pbConfirm, 0, 4)

        self.pbDiscard = QPushButton('&Discard', self)
        self.pbDiscard.pressed.connect(self.close)
        self.layout.addWidget(self.pbDiscard, 1, 4)

        if exists:
            self.pbRemove = QPushButton('&Remove', self)
            self.pbRemove.pressed.connect(self.removeAnnotation)
            self.layout.addWidget(self.pbRemove, 2, 4)

        self.pteAnnotation = QPlainTextEdit(self)
        self.pteAnnotation.setFocus()
        self.layout.addWidget(self.pteAnnotation, 5, 0, 5, 4)

        # fill gui entries
        if self.config.sql_annotations is True:
            self.leTStamp.setText(self.annotation.timestamp)
            self.leSystem.setText(self.annotation.system)
            self.leCamera.setText(self.annotation.camera)
        if self.annotation.rating:
            self.leRating.setCurrentIndex(self.annotation.rating)
        self.leRating.currentIndexChanged.connect(lambda x: setattr(self.annotation, "rating", x))
        if self.annotation.comment:
            self.pteAnnotation.setPlainText(self.annotation.comment)
        self.pteAnnotation.textChanged.connect(lambda: setattr(self.annotation, "comment", self.pteAnnotation.toPlainText()))

        # update active tags
        self.leTag.setStringList(db.getTagList())
        self.leTag.setActiveTagList(db.getTagsFromAnnotation())

    def saveAnnotation(self):
        # save the annotation
        self.db.annotation.save()
        # get table list from selecttag widget
        taglist = self.leTag.getTagList()
        # update tag association table
        self.db.setTags(taglist)
        self.close()

    def removeAnnotation(self):
        self.annotation.delete_instance()
        self.close()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.close()
        if event.key() == QtCore.Qt.Key_S and event.modifiers() & Qt.ControlModifier:
            self.saveAnnotation()


class AnnotationHandlerSQL:
    def __init__(self,config,parent):
        self.config=config
        self.parent=parent
        # init db connection
        self.db = DatabaseAnnotation(self.config)
        #TODO: add config
        self.dbFiles = fileDB.DatabaseFiles(self.config)

        self.parent.leTag.setStringList(self.db.getTagList())

    def saveAnnotation(self):
        ### extract parameters ###
        # extract relevant values, store in dict
        match = self.parent.regFromFName.match(self.parent.basename)
        if not match:
            print('warning - no match for regexp')
        else:
            re_dict = match.groupdict()
            # update results
            self.parent.results = UpdateDictWith(self.parent.results, re_dict)

        # update with gui changes
        self.parent.results['rating'] = self.parent.leRating.currentIndex()
        self.parent.results['tags'] = "SQLTags"

        # check for empty timestamp
        if not self.parent.results['timestamp'] == '':
            tstamp = datetime.strptime(self.parent.results['timestamp'],'%Y%m%d-%H%M%S')
        else:
            tstamp = datetime(1970,1,1,0,0,0)


        #item=self.db.SQLAnnotation
        try:
            # load entry from db
            if self.config.annotation_ids==[]:
                # use basename match
                item=self.db.SQLAnnotation.get(self.db.SQLAnnotation.reffilename==self.parent.basename)
                found=True
            else:
                # use annotationID if available
                if not self.parent.aid==0:
                    item=self.db.SQLAnnotation.get(self.db.SQLAnnotation.id==self.parent.aid)
                    found=True
                else:
                    item=self.db.SQLAnnotation.get(self.db.SQLAnnotation.reffilename==self.parent.basename)
                    found=True

        except DoesNotExist:
            found=False

        # check for system ID
        print("system:",self.parent.results['system'])
        system_id = self.dbFiles.retrieveSystemID(self.parent.results['system'])
        if system_id==False:
            self.popup=AddMetaSystem(self.parent,self.parent.results['system'],self.dbFiles)
            self.popup.exec_()
            system_id = self.popup.system_id
            if system_id==0:
                raise Exception("No System \"%s\" found, please add System or System Alias"%self.parent.results['system'])
        print("SystemID=",system_id)

        # check for device ID
        print("device:",self.parent.results['camera'])
        device_id = self.dbFiles.retrieveDeviceID(self.dbFiles.getSystemName(system_id),self.parent.results['camera'])
        if device_id==False:
            self.popup=AddMetaDevice(self.parent,self.parent.results['camera'],self.dbFiles,system_id)
            self.popup.exec_()
            device_id = self.popup.device_id
        print("DeviceID=",device_id)

        if found:
            # update values and update db
            item.timestamp = tstamp
            item.system = system_id
            item.device = device_id
            item.tag_type = self.parent.results['tags']
            item.rating = self.parent.results['rating']
            item.comment = self.parent.pteAnnotation.toPlainText()
            item.reffilename=self.parent.basename
            item.reffileext=self.parent.ext
            item.fileid=self.parent.fid

            item.save()
            print('update')
        else:
            # create new entry
            item=self.db.SQLAnnotation(
               timestamp = tstamp,
               system = system_id,
               device = device_id,
               tag_type = self.parent.results['tags'],
               rating = self.parent.results['rating'],
               comment = self.parent.pteAnnotation.toPlainText(),
               reffilename=self.parent.basename,
               reffileext= self.parent.ext,
               fileid=self.parent.fid)

            item.save()
            print('save')

        print(item.id)

        # update tags
        self.parent.results['tags'] = "SQLTags"
        # get table list from selecttag widget
        taglist=self.parent.leTag.getTagList()
        # update SQL tag table
        self.db.updateTagTable(taglist)
        # update tag association table
        self.db.setTagsForAnnotationID(item.id,taglist)

        # update file
        if not self.config.file_ids==[]:
            file_item = self.dbFiles.SQL_Files.get(self.dbFiles.SQL_Files.id==self.parent.fid)
            file_item.annotation_id = item.id
            file_item.save()

        results, comment = self.getAnnotation()
        BroadCastEvent(self.parent.modules, "AnnotationAdded", self.parent.basename, results, comment)

        # close widget
        self.parent.close()

    def removeAnnotation(self):
        print('remove annotation')
        try:
            # remove annotation entry
            item=self.db.SQLAnnotation.get(self.db.SQLAnnotation.reffilename==self.parent.basename)
            id=item.id
            file_id=item.fileid
            item.delete_instance()

            # remove tag associations
            tag_associations = self.db.SQLTagAssociation.select().where(self.db.SQLTagAssociation.annotation==id)
            [item.delete_instance() for item in tag_associations]

            # reset annotation_id in files table
            file_item = self.dbFiles.SQL_Files.get(self.dbFiles.SQL_Files.id==file_id)
            file_item.annotation_id=0

            BroadCastEvent(self.parent.modules, "AnnotationRemoved", self.parent.basename)
            self.parent.close()
            return True
        except DoesNotExist:
            return False


    def annotationExists(self):
        # qerry db for matching reffilename
        try:
            self.db.SQLAnnotation.get(self.db.SQLAnnotation.reffilename==self.parent.basename)
            print("Annotation exists TRUE")
            found = True
        except DoesNotExist:
            found = False
        return found


    def getAnnotation(self, filename, file_frame):
        # qerry db for matching reffilename
        # path,file = os.path.split(refname)
        # basename,ext = os.path.splitext(file)

        try:
            print("try get annotation")
            item=self.db.SQLAnnotation.get(self.db.SQLAnnotation.reffilename==self.parent.basename)
            results,comment=self.db.readAnnotation(item)
            return results, comment

        except DoesNotExist:
            raise Exception("Can't retrieve annotation details")


    def discardAnnotation(self):
        print("DISCARD")
        self.parent.close()




class AnnotationOverview(QWidget):
    def __init__(self, window, annoation_ids, db):
        QWidget.__init__(self)

        # widget layout and elements
        self.setMinimumWidth(700)
        self.setMinimumHeight(300)
        self.setWindowTitle('Annotations')
        self.layout = QGridLayout(self)
        self.annoation_ids = annoation_ids
        self.window = window
        self.db = db

        self.table = QTableWidget(0, 8, self)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setHorizontalHeaderLabels(QStringList(['Date', 'Tag', 'Comment', 'R', 'System', 'Cam', 'image', 'image_frame']))
        self.table.hideColumn(6)
        self.table.hideColumn(7)
        self.table.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setResizeMode(2, QHeaderView.Stretch)
        self.table.verticalHeader().hide()
        self.layout.addWidget(self.table)

        self.table.doubleClicked.connect(self.JumpToAnnotation)

        for index, annotation in enumerate(self.db.getAnnotationsByIds(self.annoation_ids)):
            # populate table
            self.UpdateRow(index, annotation.image, annotation, annotation.comment)

        # fit column to context
        self.table.resizeColumnToContents(0)
        self.table.sortByColumn(0, Qt.AscendingOrder)

    def JumpToAnnotation(self, idx):
        # get file basename
        image_name = self.table.item(idx.row(), 6).text()
        image_frame = int(self.table.item(idx.row(), 7).text())

        frame = self.window.media_handler.get_frame_number_by_id(image_name, image_frame)
        if frame is not None:
            self.window.JumpToFrame(frame)

    def UpdateRow(self, row, basename, data, comment, sort_if_new=False):
        new = False
        if self.table.rowCount() <= row:
            self.table.insertRow(self.table.rowCount())
            for j in range(8):
                self.table.setItem(row, j, QTableWidgetItem())
            new = True
        if 0:
            texts = [data['timestamp'], ", ".join(data['tags']), comment, str(data['rating']), data['system'],
                 data['camera'], basename]
        else:
            if data.tags is None:
                data.tags = ""
            texts = ["", data.tags, data.comment, str(data.rating), "", "", str(data.image.filename), str(data.image_frame)]
        for index, text in enumerate(texts):
            print(index, text)
            self.table.item(row, index).setText(text)
        if new and sort_if_new:
            self.table.sortByColumn(0, Qt.AscendingOrder)

    def AnnotationAdded(self, basename, data, comment):
        row = self.table.rowCount()
        for i in range(self.table.rowCount()):
            if self.table.item(i, 6).text() == basename:
                row = i
                break
        self.UpdateRow(row, basename, data, comment, sort_if_new=True)

    def AnnotationRemoved(self, basename):
        for i in range(self.table.rowCount()):
            if self.table.item(i, 6).text() == basename:
                self.table.removeRow(i)
                break


class AnnotationHandler:
    def __init__(self, window, media_handler, modules, datafile, config=None):
        self.config = config

        # default settings and parameters
        self.window = window
        self.media_handler = media_handler
        self.config = config
        self.modules = modules

        #self.frame_list = self.media_handler.getImgList(extension=False, path=False)

        self.annoations = {}
        self.db=[]

        self.annoation_ids = []

        if self.config.sql_annotation==False:  # TODO rename to server_annotation
            self.data_file = datafile
            self.annotation_file = AnnotationFile(datafile)

            # place tick marks for already present masks
            for item in self.annotation_file.get_annotation_frames():
                frame = self.window.media_handler.get_frame_number_by_id(item.image.filename, item.image_frame)
                if frame is not None:
                    BroadCastEvent(self.modules, "AnnotationMarkerAdd", frame)
                    self.annoation_ids.append(item.id)
            self.db = self.annotation_file
        else:
            ## MYSQL version
            # init db connection
            self.db = DatabaseAnnotation(self.config)

            # TODO performance concerns - how to poll the DB in a clever way ?

            if self.config.annotation_ids==[]:
            # brute force version
                print("brute force")
                """
                for file in self.media_handler.filelist:
                    # extract base name
                    path,filename = os.path.split(file)
                    basename,ext = os.path.splitext(filename)

                    results = {}
                    comment=''

                    try:
                        results,comment=self.db.getAnnotationByBasename(basename)
                        self.annoations[basename] = dict(data=results, comment=comment)
                        BroadCastEvent(self.modules, "AnnotationAdded", basename, results, comment)
                    except DoesNotExist:
                        print('no annotation for file:',file)
                        pass
                """

            else:
            # SQL File & Annotation version
                print('annotation ids version')
                for nr,annotation_ID in enumerate(self.config.annotation_ids):
                    if not annotation_ID == 0: # is not empty
                        print(nr,annotation_ID)
                        try:
                            results,comment=self.db.getAnnotationByID(annotation_ID)
                            self.annoations[self.frame_list[nr]] = dict(data=results, comment=comment)
                            BroadCastEvent(self.modules, "AnnotationMarkerAdd", nr)
                            BroadCastEvent(self.modules, "AnnotationAdded", self.frame_list[nr], results, comment)
                        except:
                            print('no annotation for file:',self.frame_list[nr])



        self.AnnotationEditorWindow = None
        self.AnnotationOverviewWindow = None

    def AnnotationAdded(self, basename, data, comment):
        if self.AnnotationOverviewWindow:
            self.AnnotationOverviewWindow.AnnotationAdded(basename, data, comment)

    def AnnotationRemoved(self, basename):
        if self.AnnotationOverviewWindow:
            self.AnnotationOverviewWindow.AnnotationRemoved(basename)

    def keyPressEvent(self, event):
        # @key A: add/edit annotation
        if event.key() == Qt.Key_A:
            self.AnnotationEditorWindow = AnnotationEditor(self.media_handler.get_filename(),
                                                           self.media_handler.get_file_frame(), self.media_handler.get_index(), self.db,
                                                           modules=self.modules, config=self.config)
            self.AnnotationEditorWindow.show()
        # @key Y: show annotation overview
        if event.key() == Qt.Key_Y:
            self.AnnotationOverviewWindow = AnnotationOverview(self.window, self.annoation_ids, self.db)
            self.AnnotationOverviewWindow.show()

    def closeEvent(self, event):
        if self.AnnotationEditorWindow:
            self.AnnotationEditorWindow.close()
        if self.AnnotationOverviewWindow:
            self.AnnotationOverviewWindow.close()

    @staticmethod
    def file():
        return __file__
