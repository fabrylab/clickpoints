# handler class to assist in data annotation
# a)save notes in txt format, use reference img/frame as file name
# b)FUTURE save note in SQL database
#

from __future__ import division
# default
import os
import re
import glob
from PyQt4.QtGui import *
from PyQt4.QtCore import *

# util
def UpdateDictwith(x, y):
    '''Given two dicts, merge them into a new dict as a shallow copy.'''

    z = x.copy()
    z.update(y)
    return z

def ReadAnnotation(filename):
    #default values
    results= dict({ 'timestamp': '',
                        'system': '',
                        'camera':'',
                        'tags':'',
                        'rating':0
                        })
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
                #extract key value pairs
                if line.find('=') != -1:
                    key, value = line.split("=")

                    if key in result_types.keys():
                        if result_types[key] == 'list':
                            value = [elem.strip() for elem in value.split(",")]
                        if result_types[key] == 'int':
                            value = int(value)

                    results[key]=value
            if section == "comment":
                comment += line_raw

    # backward compatibility for old files
    if results['timestamp']=='':
        path, fname = os.path.split(filename)
        results['timestamp'] = fname[0:15]
    if comment=='' and results['tags']=='':
        with open(filename, 'r') as fp:
            comment = fp.read()

    return results,comment

class AnnotationEditor(QWidget):
    def __init__(self,filename,outputpath='',modules=[],config=None):
        QWidget.__init__(self)

        # default settings and parameters
        self.reffilename=filename
        self.outputpath=outputpath
        # init default values
        self.results= dict({ 'timestamp': '',
                        'system': '',
                        'camera':'',
                        'tags':'',
                        'rating':0
                        })
        self.comment=''
        self.modules = modules
        self.config = config

        # regexp
        self.regFromFNameString=self.config.filename_data_regex
        self.regFromFName = re.compile(self.regFromFNameString)

        try:
            name,ext=os.path.splitext(filename[1])
        except:
            name=filename[1]

        self.annotfilename = name + self.config.annotation_tag

        if (self.outputpath==''):
            fname=os.path.join(self.reffilename[0],self.annotfilename)
        else:
            fname=os.path.join(self.outputpath,self.annotfilename)

        # widget layout and ellements
        self.setMinimumWidth(650)
        self.setMinimumHeight(400)
        self.setWindowTitle(self.reffilename[1])
        self.layout = QGridLayout(self)

        self.layout.addWidget(QLabel('AFile Name:'),0,0)
        self.leAName = QLineEdit(self.annotfilename, self)
        self.leAName.setEnabled(False)
        self.layout.addWidget(self.leAName,0,1,1,3)

        self.layout.addWidget(QLabel('Time:', self),1,0)
        self.leTStamp = QLineEdit('uninit', self)
        self.leTStamp.setEnabled(False)
        self.layout.addWidget(self.leTStamp,1,1)

        self.layout.addWidget(QLabel('System:', self),3,0)
        self.leSystem = QLineEdit('uninit', self)
        self.leSystem.setEnabled(False)
        self.layout.addWidget(self.leSystem,3,1)

        self.layout.addWidget(QLabel('Camera:', self),3,2)
        self.leCamera = QLineEdit('uninit', self)
        self.leCamera.setEnabled(False)
        self.layout.addWidget(self.leCamera,3,3)

        self.layout.addWidget(QLabel('Tag:', self),4,0)
        self.leTag = QLineEdit('uninit', self)
        self.layout.addWidget(self.leTag,4,1)

        self.layout.addWidget(QLabel('Rating:', self),4,2)
        self.leRating = QComboBox(self)
        for index, name in enumerate(['0 - none', '1 - bad', '2', '3', '4', '5 - good']):
            self.leRating.insertItem(index, name)
        self.leRating.setInsertPolicy(QComboBox.NoInsert)
        self.layout.addWidget(self.leRating,4,3)

        self.pbConfirm = QPushButton('C&onfirm', self)
        self.pbConfirm.pressed.connect(self.saveAnnotation)
        self.layout.addWidget(self.pbConfirm,0,4)

        self.pbDiscard = QPushButton('&Discard', self)
        self.pbDiscard.pressed.connect(self.discardAnnotation)
        self.layout.addWidget(self.pbDiscard,1,4)

        if os.path.exists(fname):
            self.pbRemove = QPushButton('&Remove', self)
            self.pbRemove.pressed.connect(self.removeAnnotation)
            self.layout.addWidget(self.pbRemove,2,4)

        self.pteAnnotation = QPlainTextEdit(self)
        self.pteAnnotation.setFocus()
        self.layout.addWidget(self.pteAnnotation,5,0,5,4)

        f = QFile(fname)
        # read values from exisiting file
        if f.exists():
            self.results,self.comment = ReadAnnotation(fname)
        # extract values from filename
        else:
            # extract relevant values, store in dict
            fname,ext=os.path.splitext(self.reffilename[1])
            match = self.regFromFName.match(fname)
            if not match:
                print 'warning - no match for regexp'
            else:
                re_dict = match.groupdict()

                # update results
                self.results=UpdateDictwith(self.results,re_dict)
                print self.results

        # update gui
        # update meta
        self.leTStamp.setText(self.results['timestamp'])
        self.leSystem.setText(self.results['system'])
        self.leCamera.setText(self.results['camera'])
        self.leTag.setText(", ".join(self.results['tags']))
        self.leRating.setCurrentIndex(int(self.results['rating']))

        # update comment
        self.pteAnnotation.setPlainText(self.comment)

    def saveAnnotation(self):
        print "SAVE"
        if (self.outputpath==''):
            f=QFile(os.path.join(self.reffilename[0],self.annotfilename))
            print os.path.join(self.reffilename[0],self.annotfilename)
        else:
            f=QFile(os.path.join(self.outputpath,self.annotfilename))
        f.open(QFile.Truncate | QFile.ReadWrite)

        if not f.isOpen():
            print "WARNING - cant open file"
        else:
            # new output format
            # extract relevant values, store in dict
            fname,ext=os.path.splitext(self.reffilename[1])
            match = self.regFromFName.match(fname)
            if not match:
                print 'warning - no match for regexp'
            else:
                re_dict = match.groupdict()

                # update results
                self.results=UpdateDictwith(self.results,re_dict)

            # update with gui changes
            self.results['tags']=self.leTag.text()
            self.results['rating']=self.leRating.currentIndex()

            #write to file
            out = QTextStream(f)
            #write header
            out << '[data]\n'
            #write header info
            for field in self.results:
                out << "%s=%s\n" % (field,self.results.get(field))

            # # write data
            out << '\n[comment]\n'
            out << self.pteAnnotation.toPlainText()

            f.close()
            self.close()

            for module in self.modules:
                if "AnnotationAdded" in dir(module):
                    module.AnnotationAdded()

    def removeAnnotation(self):
        if (self.outputpath==''):
            f=os.path.join(self.reffilename[0],self.annotfilename)
            print os.path.join(self.reffilename[0],self.annotfilename)
        else:
            f=os.path.join(self.outputpath,self.annotfilename)
        os.remove(f)
        for module in self.modules:
            if "AnnotationRemoved" in dir(module):
                module.AnnotationRemoved()
        self.close()

    def discardAnnotation(self):
        print "DISCARD"
        self.close()

class AnnotationOverview(QWidget):
    def __init__(self,window,annotations,frame_list):
        QWidget.__init__(self)

        # widget layout and elements
        self.setMinimumWidth(700)
        self.setMinimumHeight(300)
        self.setWindowTitle('Annotations')
        self.layout = QGridLayout(self)
        self.annotations = annotations
        self.window = window
        self.frame_list = frame_list

        self.table= QTableWidget(0, 7, self)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setHorizontalHeaderLabels(QStringList(['Date','Tag','Comment','R','System','Cam','file']))
        self.table.hideColumn(6)
        self.table.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setResizeMode(2,QHeaderView.Stretch)
        self.table.verticalHeader().hide()
        self.layout.addWidget(self.table)

        self.table.doubleClicked.connect(self.JumpToAnnotation)

        for i,basename in enumerate(self.annotations):
            # read annotation file
            data = self.annotations[basename]["data"]
            comment = self.annotations[basename]["comment"]

            # populate table
            self.table.insertRow(self.table.rowCount())
            self.table.setItem(i,0,QTableWidgetItem(data['timestamp']))
            self.table.setItem(i,1,QTableWidgetItem(", ".join(data['tags'])))
            self.table.setItem(i,2,QTableWidgetItem(comment))
            self.table.setItem(i,3,QTableWidgetItem(str(data['rating'])))
            self.table.setItem(i,4,QTableWidgetItem(data['system']))
            self.table.setItem(i,5,QTableWidgetItem(data['camera']))
            self.table.setItem(i,6,QTableWidgetItem(basename))

        # fit column to context
        self.table.resizeColumnToContents(0)
        self.table.sortByColumn(0, Qt.AscendingOrder)

    def JumpToAnnotation(self,idx):
        # get file basename
        basename = self.table.item(idx.row(),6).text()

        # find match in file list
        try:
            index = self.frame_list.index(basename)
        except ValueError:
            print('no matching file found for '+basename)
        else:
            self.window.JumpToFrame(index)

class AnnotationHandler:
    def __init__(self, window, MediaHandler, modules, config=None):
        self.config = config

        # default settings and parameters
        self.outputpath=config.outputpath
        self.window=window
        self.mediahandler=MediaHandler
        self.config = config
        self.modules = modules

        self.frame_list = [os.path.split(file)[1][:-4] for file in self.mediahandler.filelist]

        # get list of files
        input = os.path.join(self.outputpath, '*' + self.config.annotation_tag)
        self.filelist = glob.glob(input)

        self.annoations = {}

        for i,file in enumerate(self.filelist):
            # read annotation file
            results, comment = ReadAnnotation(file)

            # get file basename
            filename = os.path.split(file)[1]
            basename = filename[:-len(self.config.annotation_tag)]
            self.annoations[basename] = dict(data=results, comment=comment)

    def getAnnotations(self):
        return self.annoations

    def keyPressEvent(self, event):
        # @key A: add/edit annotation
        if event.key() == Qt.Key_A:
            self.AnnotationEditorWindow = AnnotationEditor(self.mediahandler.getCurrentFilename(nr=self.mediahandler.currentPos),outputpath=self.outputpath, modules=self.modules, config=self.config)
            self.AnnotationEditorWindow.show()
        # @key Y: show annotation overview
        if event.key() == Qt.Key_Y:
            self.AnnotationOverviewWindow = AnnotationOverview(self.window, self.annoations, self.frame_list)
            self.AnnotationOverviewWindow.show()

    @staticmethod
    def file():
        return __file__
