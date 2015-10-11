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

from Tools import BroadCastEvent
from abc import abstractmethod

#TODO conditional export based on config?
from peewee import *
from datetime import datetime

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


class SQLAnnotation(Model):
        timestamp = DateTimeField()
        system = CharField()
        camera = CharField()
        tags =  CharField()
        rating = IntegerField()
        reffilename = CharField()
        reffileext = CharField()
        comment = TextField()

        class Meta:
            database = None

class AnnotationEditor(QWidget):
    def __init__(self, filename, outputpath, modules, config):
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
        self.modules = modules
        self.config = config

        # check for sql or file mode
        if self.config.sql_annotation==True:
            print('SQL Mode enabled')

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

            self.SQLAnnotation = SQLAnnotation
            self.SQLAnnotation._meta.database=self.db


            # init for sql
            self.annotationExists = self.SQL_annotationExists
            self.removeAnnotation = self.SQL_removeAnnotation
            self.getAnnotation    = self.SQL_readAnnotation
            self.saveAnnotation   = self.SQL_saveAnnotation

        else:
            print('local text mode enabled')

            # init for txt
            self.annotationExists = self.T_annotationExists
            self.removeAnnotation = self.T_removeAnnotation
            self.getAnnotation    = self.T_getAnnotation
            self.saveAnnotation   = self.T_saveAnnotation

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

        self.layout.addWidget(QLabel('Tag:', self), 4, 0)
        self.leTag = QLineEdit('uninit', self)
        self.layout.addWidget(self.leTag, 4, 1)

        self.layout.addWidget(QLabel('Rating:', self), 4, 2)
        self.leRating = QComboBox(self)
        for index, basename in enumerate(['0 - none', '1 - bad', '2', '3', '4', '5 - good']):
            self.leRating.insertItem(index, basename)
        self.leRating.setInsertPolicy(QComboBox.NoInsert)
        self.layout.addWidget(self.leRating, 4, 3)

        self.pbConfirm = QPushButton('C&onfirm', self)
        self.pbConfirm.pressed.connect(self.saveAnnotation)
        self.layout.addWidget(self.pbConfirm, 0, 4)

        self.pbDiscard = QPushButton('&Discard', self)
        self.pbDiscard.pressed.connect(self.discardAnnotation)
        self.layout.addWidget(self.pbDiscard, 1, 4)

        if self.annotationExists():
            self.pbRemove = QPushButton('&Remove', self)
            self.pbRemove.pressed.connect(self.removeAnnotation)
            self.layout.addWidget(self.pbRemove, 2, 4)

        self.pteAnnotation = QPlainTextEdit(self)
        self.pteAnnotation.setFocus()
        self.layout.addWidget(self.pteAnnotation, 5, 0, 5, 4)


        if self.annotationExists():
            self.results, self.comment = self.getAnnotation(self.basename)
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

    @abstractmethod
    def annotationExists(self):
        pass
    @abstractmethod
    def removeAnnotation(self):
        pass
    @abstractmethod
    def getAnnotation(self):
        pass
    @abstractmethod
    def saveAnnotation(self):
        pass

    ##########################################################################################################
    # mySQL storage version here
    def SQL_saveAnnotation(self):
        # extract relevant values, store in dict
        match = self.regFromFName.match(self.basename)
        if not match:
            print('warning - no match for regexp')
        else:
            re_dict = match.groupdict()

            # update results
            self.results = UpdateDictWith(self.results, re_dict)

        # update with gui changes
        self.results['tags'] = self.leTag.text()
        self.results['rating'] = self.leRating.currentIndex()

        # check for empty timestamp
        if not self.results['timestamp'] == '':
            tstamp = datetime.strptime(self.results['timestamp'],'%Y%m%d-%H%M%S')
        else:
            tstamp = datetime(1970,1,1,0,0,0)


        item=self.SQLAnnotation
        try:
            # load entry from db
            item=self.SQLAnnotation.get(self.SQLAnnotation.reffilename==self.basename)
            print("entry found")
            found=True
        except DoesNotExist:
            found=False

        if found:
            # update values and update db
            item.timestamp = tstamp
            item.system = self.results['system']
            item.camera = self.results['camera']
            item.tags = self.results['tags']
            item.rating = self.results['rating']
            item.comment = self.pteAnnotation.toPlainText()
            item.reffilename=self.basename
            item.reffileext=self.ext

            item.save()
            print('update')
        else:
            # create new entry
            item=self.SQLAnnotation(
               timestamp = tstamp,
               system = self.results['system'],
               camera = self.results['camera'],
               tags = self.results['tags'],
               rating = self.results['rating'],
               comment = self.pteAnnotation.toPlainText(),
               reffilename=self.basename,
               reffileext= self.ext)

            print('tags: ',item.tags)
            print('found: ',found)

            item.save()
            print('save')

        results, comment = self.SQL_readAnnotation(self.reffilename[1])
        BroadCastEvent(self.modules, "AnnotationAdded", self.basename, results, comment)

        # close widget
        self.close()

    def SQL_removeAnnotation(self):
        try:
            item=self.SQLAnnotation.get(self.SQLAnnotation.reffilename==self.basename)
            item.delete_instance()

            BroadCastEvent(self.modules, "AnnotationRemoved", self.basename)
            self.close()
            return True
        except DoesNotExist:
            return False


    def SQL_annotationExists(self):
        # qerry db for matching reffilename
        try:
            self.SQLAnnotation.get(self.SQLAnnotation.reffilename==self.basename)
            found = True
        except DoesNotExist:
            found = False
        return found


    def SQL_readAnnotation(self, refname):
        # qerry db for matching reffilename
        basename,ext = os.path.splitext(refname)
        try:
            item=self.SQLAnnotation.get(self.SQLAnnotation.reffilename==basename)
            found = True
            comment=item.comment
            results={}
            results['timestamp']=datetime.strftime(item.timestamp,'%Y%m%d-%H%M%S')
            results['system']=item.system
            results['camera']=item.camera
            results['tags']=[elem.strip() for elem in item.tags.split(",")]
            results['rating']=item.rating
            results['reffilename']=item.reffilename
            results['feffileext']=item.reffileext

        except DoesNotExist:
            found = False
        return results, comment

    ##########################################################################################################
    # TEXT file storage version here
    def T_saveAnnotation(self):
        print("SAVE")
        if self.outputpath == '':
            filename = os.path.join(self.reffilename[0], self.annotfilename)
            f = QFile(filename)
            print(filename)
        else:
            filename = os.path.join(self.outputpath, self.annotfilename)
            f = QFile(filename)
        f.open(QFile.Truncate | QFile.ReadWrite)

        if not f.isOpen():
            print("WARNING - cant open file")
        else:
            # new output format
            # extract relevant values, store in dict
            fname, ext = os.path.splitext(self.reffilename[1])
            match = self.regFromFName.match(fname)
            if not match:
                print('warning - no match for regexp')
            else:
                re_dict = match.groupdict()

                # update results
                self.results = UpdateDictWith(self.results, re_dict)

            # update with gui changes
            self.results['tags'] = self.leTag.text()
            self.results['rating'] = self.leRating.currentIndex()

            # write to file
            out = QTextStream(f)
            # write header
            out << '[data]\n'
            # write header info
            for field in self.results:
                out << "%s=%s\n" % (field, self.results.get(field))

            # # write data
            comment = self.pteAnnotation.toPlainText()
            out << '\n[comment]\n'
            out << comment

            f.close()
            self.close()

            results, comment = ReadAnnotation(filename)
            BroadCastEvent(self.modules, "AnnotationAdded", self.basename, results, comment)

    def T_removeAnnotation(self):
        if self.outputpath == '':
            f = os.path.join(self.reffilename[0], self.annotfilename)
            print(os.path.join(self.reffilename[0], self.annotfilename))
        else:
            f = os.path.join(self.outputpath, self.annotfilename)
        os.remove(f)
        BroadCastEvent(self.modules, "AnnotationRemoved", self.basename)

        self.close()

    def T_annotationExists(self):
        if os.path.exists(self.fname):
            return True
        else:
            return False

    def T_getAnnotation(self):
        f = QFile(self.fname)
        # read values from exisiting file
        if f.exists():
            self.results, self.comment = ReadAnnotation(self.fname)

    def discardAnnotation(self):
        print("DISCARD")
        self.close()


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


class AnnotationHandler:
    def __init__(self, window, media_handler, modules, config=None):
        self.config = config

        # default settings and parameters
        self.outputpath = config.outputpath
        self.window = window
        self.media_handler = media_handler
        self.config = config
        self.modules = modules

        self.frame_list = self.media_handler.getImgList(extension=False, path=False)

        # get list of files
        annotation_glob_string = os.path.join(self.outputpath, '*' + self.config.annotation_tag)
        self.filelist = glob.glob(annotation_glob_string)

        self.annoations = {}

        for i, file in enumerate(self.filelist):
            # read annotation file
            results, comment = ReadAnnotation(file)

            # get file basename
            filename = os.path.split(file)[1]
            basename = filename[:-len(self.config.annotation_tag)]
            self.annoations[basename] = dict(data=results, comment=comment)

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
