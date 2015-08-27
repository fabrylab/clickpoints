# handler class to assist in data annotation
# a)save notes in txt format, use reference img/frame as file name
# b)FUTURE save note in SQL database
#

from __future__ import division
# default
import os
import re
from PyQt4.QtGui import *
from PyQt4.QtCore import *

from Tools import *

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

    return results,comment

class AnnotationHandler(QWidget):
    def __init__(self,filename,outputpath=''):
        QWidget.__init__(self)

        # default settings and parameters
        self.defsuffix='_annot.txt'
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

        # regexp
        self.regFromFNameString=r'.*(?P<timestamp>\d{8}-\d{6})_(?P<system>.+?[^_])_(?P<camera>.+)'
        self.regFromFName = re.compile(self.regFromFNameString)

        try:
            name,ext=os.path.splitext(filename[1])
        except:
            name=filename[1]

        self.annotfilename= name + self.defsuffix

        # widget layout and ellements
        self.setMinimumWidth(650)
        self.setMinimumHeight(400)
        self.setWindowTitle(self.reffilename[1])
        self.layout = QGridLayout(self)

        self.lbAName = QLabel(self)
        self.lbAName.setText('AFile Name:')
        self.layout.addWidget(self.lbAName,0,0)
        self.leAName = QLineEdit(self)
        self.leAName.setText(self.annotfilename)
        self.leAName.setEnabled(False)
        self.layout.addWidget(self.leAName,0,1,1,3)

        self.lbTStamp = QLabel(self)
        self.lbTStamp.setText('Time:')
        self.layout.addWidget(self.lbTStamp,1,0)
        self.leTStamp = QLineEdit(self)
        self.leTStamp.setText('uninit')
        self.leTStamp.setEnabled(False)
        self.layout.addWidget(self.leTStamp,1,1)

        self.lbSystem = QLabel(self)
        self.lbSystem.setText('System:')
        self.layout.addWidget(self.lbSystem,3,0)
        self.leSystem = QLineEdit(self)
        self.leSystem.setText('uninit')
        self.leSystem.setEnabled(False)
        self.layout.addWidget(self.leSystem,3,1)

        self.lbCamera = QLabel(self)
        self.lbCamera.setText('Camera:')
        self.layout.addWidget(self.lbCamera,3,2)
        self.leCamera = QLineEdit(self)
        self.leCamera.setText('uninit')
        self.leCamera.setEnabled(False)
        self.layout.addWidget(self.leCamera,3,3)

        self.lbTag = QLabel(self)
        self.lbTag.setText('Tag:')
        self.layout.addWidget(self.lbTag,4,0)
        self.leTag = QLineEdit(self)
        self.leTag.setText('uninit')
        self.layout.addWidget(self.leTag,4,1)

        self.lbRating = QLabel(self)
        self.lbRating.setText('Rating:')
        self.layout.addWidget(self.lbRating,4,2)
        self.leRating = QComboBox(self)
        self.leRating.insertItem(0,'0 - none')
        self.leRating.insertItem(1,'1 - bad')
        self.leRating.insertItem(2,'2')
        self.leRating.insertItem(3,'3')
        self.leRating.insertItem(4,'4')
        self.leRating.insertItem(5,'5 - good')
        self.leRating.setCurrentIndex(0)
        self.leRating.setInsertPolicy(QComboBox.NoInsert)
        self.layout.addWidget(self.leRating,4,3)

        self.pbConfirm = QPushButton(self)
        self.pbConfirm.setText('C&onfirm')
        self.pbConfirm.pressed.connect(self.saveAnnotation)
        self.layout.addWidget(self.pbConfirm,0,4)

        self.pbDiscard = QPushButton(self)
        self.pbDiscard.setText('&Discard')
        self.pbDiscard.pressed.connect(self.discardAnnotation)
        self.layout.addWidget(self.pbDiscard,1,4)

        self.pteAnnotation = QPlainTextEdit(self)
        self.pteAnnotation.setFocus()
        self.layout.addWidget(self.pteAnnotation,5,0,5,4)


        if (self.outputpath==''):
            fname=os.path.join(self.reffilename[0],self.annotfilename)
        else:
            fname=os.path.join(self.outputpath,self.annotfilename)

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

    def discardAnnotation(self):
        print "DISCARD"
        self.close()

