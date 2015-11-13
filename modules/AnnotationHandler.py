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
    from PyQt4.QtGui import QWidget, QGridLayout, QLabel, QLineEdit, QComboBox, QPushButton, QPlainTextEdit, QTableWidget, QHeaderView, QTableWidgetItem
    from PyQt4.QtCore import Qt, QTextStream, QFile, QStringList

from Tools import BroadCastEvent
from abc import abstractmethod

#TODO conditional export based on config?
from peewee import *
from datetime import datetime


sys.path.append(os.path.join(os.path.dirname(__file__), "..", "database"))
print(os.path.join(os.path.dirname(__file__), "..", "database"))
from databaseAnnotation import *
import database as fileDB

# util
def UpdateDictWith(x, y):
    """Given two dicts, merge them into a new dict as a shallow copy."""

    z = x.copy()
    z.update(y)
    return z


def ReadAnnotation(filename):
    # default values
    results = dict(timestamp='', system='', camera='', tags='', rating=0)
    result_types = dict(timestamp='str', system='str', camera='str', tags='list', rating='int')
    comment = ""

    with open(filename, 'r') as fp:
        # get key value pairs
        section = ""

        for line_raw in fp.readlines():
            line = line_raw.strip()
            if len(line) > 0 and line[0] == '[' and line[-1] == ']':
                section = line[1:-1]
                continue
            if section == "data":
                # extract key value pairs
                if line.find('=') != -1:
                    key, value = line.split("=")

                    if key in result_types.keys():
                        if result_types[key] == 'list':
                            value = [elem.strip() for elem in value.split(",")]
                        if result_types[key] == 'int':
                            value = int(value)

                    results[key] = value
            if section == "comment":
                comment += line_raw

    # backward compatibility for old files
    if results['timestamp'] == '':
        path, fname = os.path.split(filename)
        results['timestamp'] = fname[0:15]
    if comment == '' and results['tags'] == '':
        with open(filename, 'r') as fp:
            comment = fp.read()

    return results, comment

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

        self.pbAdd = QtGui.QPushButton(self)
        self.pbAdd.setText('Add')
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



class AnnotationEditor(QWidget):
    def __init__(self, filename,filenr, outputpath, modules, config):
        QWidget.__init__(self)

        # default settings and parameters
        self.reffilename = filename
        self.outputpath = outputpath
        # init default values
        self.results = dict({'timestamp': '',
                             'system': '',
                             'camera': '',
                             'tags': '',
                             'rating': 0
                             })
        self.comment = ''


        self.fid=0
        if not config.files_id==[]:
            self.fid = config.file_ids[filenr]

        self.modules = modules
        self.config = config

        # regexp
        self.regFromFNameString = self.config.filename_data_regex
        self.regFromFName = re.compile(self.regFromFNameString)

        basename, ext = os.path.splitext(filename[1])
        self.basename = basename
        self.ext = ext

        self.annotfilename = basename + self.config.annotation_tag

        if self.outputpath == '':
            self.fname = os.path.join(self.reffilename[0], self.annotfilename)
        else:
            self.fname = os.path.join(self.outputpath, self.annotfilename)

        # widget layout and ellements
        self.setMinimumWidth(650)
        self.setMinimumHeight(400)
        self.setWindowTitle(self.reffilename[1])
        self.layout = QGridLayout(self)

        self.layout.addWidget(QLabel('AFile Name:'), 0, 0)
        self.leAName = QLineEdit(self.annotfilename, self)
        self.leAName.setEnabled(False)
        self.layout.addWidget(self.leAName, 0, 1, 1, 3)

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
        self.laTag.setContentsMargins(0,4,0,0)
        self.layout.addWidget(self.laTag, 4, 0,Qt.AlignTop)

        self.leTag=[]
        if self.config.sql_annotation==True:
            print("run TagSelector")
            self.leTag = pyQtTagSelector()
            self.layout.addWidget(self.leTag, 4, 1)
        else:
            print("run LineEdit")
            self.leTag = QLineEdit('uninit', self)
            self.layout.addWidget(self.leTag, 4, 1)

        self.laRating = QLabel('Rating:', self)
        self.laRating.setContentsMargins(0,4,0,0)
        self.layout.addWidget(self.laRating, 4, 2, Qt.AlignTop)
        self.leRating = QComboBox(self)
        for index, basename in enumerate(['0 - none', '1 - bad', '2', '3', '4', '5 - good']):
            self.leRating.insertItem(index, basename)
        self.leRating.setInsertPolicy(QComboBox.NoInsert)
        self.leRating.setContentsMargins(0,5,0,0)
        self.layout.addWidget(self.leRating, 4, 3,Qt.AlignTop)

        self.ah=[]
        # check for sql or file mode
        if self.config.sql_annotation==True:
            print('SQL Mode enabled')
            self.ah=AnnotationHandlerSQL(config,self)

        else:
            print('local text mode enabled')
            self.ah=AnnotationHandlerTXT(config,self)


        self.pbConfirm = QPushButton('C&onfirm', self)
        self.pbConfirm.pressed.connect(self.ah.saveAnnotation)
        self.layout.addWidget(self.pbConfirm, 0, 4)

        self.pbDiscard = QPushButton('&Discard', self)
        self.pbDiscard.pressed.connect(self.ah.discardAnnotation)
        self.layout.addWidget(self.pbDiscard, 1, 4)

        if self.ah.annotationExists():
            self.pbRemove = QPushButton('&Remove', self)
            self.pbRemove.pressed.connect(self.ah.removeAnnotation)
            self.layout.addWidget(self.pbRemove, 2, 4)

        self.pteAnnotation = QPlainTextEdit(self)
        self.pteAnnotation.setFocus()
        self.layout.addWidget(self.pteAnnotation, 5, 0, 5, 4)


        if self.ah.annotationExists():
            self.results, self.comment = self.ah.getAnnotation()
        else:
            # extract relevant values, store in dict
            fname, ext = os.path.splitext(self.reffilename[1])
            match = self.regFromFName.match(fname)
            if not match:
                print('warning - no match for regexp')
            else:
                re_dict = match.groupdict()

                # update results
                self.results = UpdateDictWith(self.results, re_dict)

        # update gui
        # update meta
        self.leTStamp.setText(self.results['timestamp'])
        self.leSystem.setText(self.results['system'])
        self.leCamera.setText(self.results['camera'])
        self.leTag.setText(", ".join(self.results['tags']))
        self.leRating.setCurrentIndex(int(self.results['rating']))

        # update comment
        self.pteAnnotation.setPlainText(self.comment)

    # @abstractmethod
    # def annotationExists(self):
    #     pass
    # @abstractmethod
    # def removeAnnotation(self):
    #     pass
    # @abstractmethod
    # def getAnnotation(self):
    #     pass
    # @abstractmethod
    # def saveAnnotation(self):
    #     pass


class AnnotationHandlerSQL:
    def __init__(self,config,parent):
        self.config=config
        self.parent=parent
        # init db connection
        self.db = DatabaseAnnotation(self.config)
        #TODO: add config
        self.dbFiles = fileDB.Database()

        self.parent.leTag.setStringList(self.db.getTagList())

    def saveAnnotation(self):
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
        # update tags
        self.parent.results['tags'] = "SQLTags"


        # check for empty timestamp
        if not self.parent.results['timestamp'] == '':
            tstamp = datetime.strptime(self.parent.results['timestamp'],'%Y%m%d-%H%M%S')
        else:
            tstamp = datetime(1970,1,1,0,0,0)


        item=self.db.SQLAnnotation
        try:
            # load entry from db
            item=self.db.SQLAnnotation.get(self.db.SQLAnnotation.reffilename==self.parent.basename)
            print("entry found")
            found=True
        except DoesNotExist:
            found=False

        if found:
            # update values and update db
            item.timestamp = tstamp
            item.system = self.parent.results['system']
            item.camera = self.parent.results['camera']
            item.tags = self.parent.results['tags']
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
               system = self.parent.results['system'],
               camera = self.parent.results['camera'],
               tags = self.parent.results['tags'],
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
        file_item = self.dbFiles.SQL_Files.get(self.dbFiles.SQL_Files.id==self.parent.fid)
        print(file_item.basename)
        file_item.annotation_id = item.id
        print('update anotation',file_item.id,item.id)
        print(file_item.annotation_id)
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
            tag_associations = self.db.SQLTagAssociation.select().where(self.db.SQLTagAssociation.annotation_id==id)
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
            found = True
        except DoesNotExist:
            found = False
        return found


    def getAnnotation(self):
        # qerry db for matching reffilename
        # path,file = os.path.split(refname)
        # basename,ext = os.path.splitext(file)

        try:
            item=self.db.SQLAnnotation.get(self.db.SQLAnnotation.reffilename==self.parent.basename)
            found = True
            comment=item.comment
            results={}
            results['timestamp']=datetime.strftime(item.timestamp,'%Y%m%d-%H%M%S')
            results['system']=item.system
            results['camera']=item.camera
            #results['tags']=[elem.strip() for elem in item.tags.split(",")]
            results['rating']=item.rating
            results['reffilename']=item.reffilename
            results['feffileext']=item.reffileext

            tag_list=self.db.getTagsForAnnotationID(item.id)
            self.parent.leTag.setActiveTagList(tag_list)
            results['tags']= tag_list
            return results, comment

        except DoesNotExist:
            raise Exception("Can't retrieve annotation details")


    def discardAnnotation(self):
        print("DISCARD")
        self.parent.close()


class AnnotationHandlerTXT:
    def __init__(self,config,parent):
        self.config = config
        self.parent = parent

    def saveAnnotation(self):
        print("SAVE")
        if self.parent.outputpath == '':
            filename = os.path.join(self.parent.reffilename[0], self.parent.annotfilename)
            f = QFile(filename)
            print(filename)
        else:
            filename = os.path.join(self.parent.outputpath, self.parent.annotfilename)
            f = QFile(filename)
        f.open(QFile.Truncate | QFile.ReadWrite)

        if not f.isOpen():
            print("WARNING - cant open file")
        else:
            # new output format
            # extract relevant values, store in dict
            fname, ext = os.path.splitext(self.parent.reffilename[1])
            match = self.parent.regFromFName.match(fname)
            if not match:
                print('warning - no match for regexp')
            else:
                re_dict = match.groupdict()

                # update results
                self.parent.results = UpdateDictWith(self.parent.results, re_dict)

            # update with gui changes
            self.parent.results['tags'] = self.parent.leTag.text()
            self.parent.results['rating'] = self.parent.leRating.currentIndex()

            # write to file
            out = QTextStream(f)
            # write header
            out << '[data]\n'
            # write header info
            for field in self.parent.results:
                out << "%s=%s\n" % (field, self.parent.results.get(field))

            # # write data
            comment = self.parent.pteAnnotation.toPlainText()
            out << '\n[comment]\n'
            out << comment

            f.close()
            self.parent.close()

            results, comment = ReadAnnotation(filename)
            BroadCastEvent(self.parent.modules, "AnnotationAdded", self.parent.basename, results, comment)

    def removeAnnotation(self):
        if self.parent.outputpath == '':
            f = os.path.join(self.parent.reffilename[0], self.parent.annotfilename)
            print(os.path.join(self.parent.reffilename[0], self.parent.annotfilename))
        else:
            f = os.path.join(self.parent.outputpath, self.parent.annotfilename)
        os.remove(f)
        BroadCastEvent(self.parent.modules, "AnnotationRemoved", self.parent.basename)

        self.parent.close()

    def annotationExists(self):
        if os.path.exists(self.parent.fname):
            return True
        else:
            return False

    def getAnnotation(self):
        f = QFile(self.parent.fname)
        # read values from exisiting file
        if f.exists():
            self.parent.results, self.parent.comment = ReadAnnotation(self.parent.fname)

            return self.parent.results,self.parent.comment

    def discardAnnotation(self):
        print("DISCARD")
        self.parent.close()



class AnnotationOverview(QWidget):
    def __init__(self, window, annotations, frame_list):
        QWidget.__init__(self)

        # widget layout and elements
        self.setMinimumWidth(700)
        self.setMinimumHeight(300)
        self.setWindowTitle('Annotations')
        self.layout = QGridLayout(self)
        self.annotations = annotations
        self.window = window
        self.frame_list = frame_list

        self.table = QTableWidget(0, 7, self)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setHorizontalHeaderLabels(QStringList(['Date', 'Tag', 'Comment', 'R', 'System', 'Cam', 'file']))
        self.table.hideColumn(6)
        self.table.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setResizeMode(2, QHeaderView.Stretch)
        self.table.verticalHeader().hide()
        self.layout.addWidget(self.table)

        self.table.doubleClicked.connect(self.JumpToAnnotation)

        for i, basename in enumerate(self.annotations):
            # read annotation file
            data = self.annotations[basename]["data"]
            comment = self.annotations[basename]["comment"]

            # populate table
            self.UpdateRow(i, basename, data, comment)

        # fit column to context
        self.table.resizeColumnToContents(0)
        self.table.sortByColumn(0, Qt.AscendingOrder)

    def JumpToAnnotation(self, idx):
        # get file basename
        basename = self.table.item(idx.row(), 6).text()

        # find match in file list
        try:
            index = self.frame_list.index(basename)
        except ValueError:
            print('no matching file found for ' + basename)
        else:
            self.window.JumpToFrame(index)

    def UpdateRow(self, row, basename, data, comment, sort_if_new=False):
        new = False
        if self.table.rowCount() <= row:
            self.table.insertRow(self.table.rowCount())
            for j in range(7):
                self.table.setItem(row, j, QTableWidgetItem())
            new = True
        texts = [data['timestamp'], ", ".join(data['tags']), comment, str(data['rating']), data['system'],
                 data['camera'], basename]
        for index, text in enumerate(texts):
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


class AnnotationHandler():
    def __init__(self, window, media_handler, modules, config=None):
        self.config = config

        # default settings and parameters
        self.outputpath = config.outputpath
        self.window = window
        self.media_handler = media_handler
        self.config = config
        self.modules = modules

        self.frame_list = self.media_handler.getImgList(extension=False, path=False)

        self.annoations = {}
        self.db=[]

        if self.config.sql_annotation==False:
            ## LOCAL version
            if self.outputpath == '':
                searchpath,fname=os.path.split(self.media_handler.filelist[0])
            else:
                searchpath=self.outputpath
            # TODO: this is a band aid fix for choosing files with the file dialogue, this will break for recursive foulder structures!

            # get list of files
            annotation_glob_string = os.path.join(searchpath, '*' + self.config.annotation_tag)
            self.filelist = glob.glob(annotation_glob_string)

            for i, file in enumerate(self.filelist):
                # read annotation file
                results, comment = ReadAnnotation(file)

                # get file basename
                filename = os.path.split(file)[1]
                basename = filename[:-len(self.config.annotation_tag)]
                self.annoations[basename] = dict(data=results, comment=comment)
        else:
            ## MYSQL version
            # init db connection
            self.db = DatabaseAnnotation(self.config)

            # TODO performance concerns - how to poll the DB in a clever way ?

            if self.config.annotation_ids==[]:
            # brute force version
                print("brute force")
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
        self.annoations[basename] = dict(data=data, comment=comment)
        if self.AnnotationOverviewWindow:
            self.AnnotationOverviewWindow.AnnotationAdded(basename, data, comment)

    def AnnotationRemoved(self, basename):
        del self.annoations[basename]
        if self.AnnotationOverviewWindow:
            self.AnnotationOverviewWindow.AnnotationRemoved(basename)

    def getAnnotations(self):
        return self.annoations

    def keyPressEvent(self, event):
        # @key A: add/edit annotation
        if event.key() == Qt.Key_A:
            self.AnnotationEditorWindow = AnnotationEditor(self.media_handler.getCurrentFilename(),
                                                           self.media_handler.getCurrentPos(),
                                                           outputpath=self.outputpath, modules=self.modules,
                                                           config=self.config)
            self.AnnotationEditorWindow.show()
        # @key Y: show annotation overview
        if event.key() == Qt.Key_Y:
            self.AnnotationOverviewWindow = AnnotationOverview(self.window, self.annoations, self.frame_list)
            self.AnnotationOverviewWindow.show()

    def closeEvent(self, event):
        if self.AnnotationEditorWindow:
            self.AnnotationEditorWindow.close()
        if self.AnnotationOverviewWindow:
            self.AnnotationOverviewWindow.close()

    @staticmethod
    def file():
        return __file__
