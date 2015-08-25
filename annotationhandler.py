# handler class to assist in data annotation
# a)save notes in txt format, use reference img/frame as file name
# b)FUTURE save note in SQL database
#

from __future__ import division
# default
import os
from PyQt4.QtGui import *
from PyQt4.QtCore import *

class AnnotationHandler(QWidget):
    def __init__(self,filename,outputpath=''):
        QWidget.__init__(self)

        # default settings and parameters
        self.defsuffix='_annot.txt'
        self.reffilename=filename
        self.outputpath=outputpath

        try:
            name,ext=os.path.splitext(filename[1])
        except:
            name=filename[1]

        self.annotfilename= name + self.defsuffix

        # widget layout and ellements
        self.setMinimumWidth(550)
        self.setMinimumHeight(300)
        self.setWindowTitle(self.reffilename[1])
        self.layout = QGridLayout(self)

        self.lbAName = QLabel(self)
        self.lbAName.setText('Annotation File Name:')
        self.layout.addWidget(self.lbAName,0,0)

        self.leAName = QLineEdit(self)
        self.leAName.setText(self.annotfilename)
        self.layout.addWidget(self.leAName,1,0)

        self.pbConfirm = QPushButton(self)
        self.pbConfirm.setText('C&onfirm')
        self.pbConfirm.pressed.connect(self.saveAnnotation)
        self.layout.addWidget(self.pbConfirm,0,1)

        self.pbDiscard = QPushButton(self)
        self.pbDiscard.setText('&Discard')
        self.pbDiscard.pressed.connect(self.discardAnnotation)
        self.layout.addWidget(self.pbDiscard,1,1)

        self.pteAnnotation = QPlainTextEdit(self)
        self.pteAnnotation.setFocus()
        self.layout.addWidget(self.pteAnnotation,2,0,5,2)

        #TODO: check for existing file and read if available
        if (self.outputpath==''):
            f=QFile(os.path.join(self.reffilename[0],self.annotfilename))
            print os.path.join(self.reffilename[0],self.annotfilename)
        else:
            f=QFile(os.path.join(self.outputpath,self.annotfilename))

        if f.exists():
            f.open(QFile.ReadWrite)
            inS = QTextStream(f)
            string=inS.readAll()
            self.pteAnnotation.setPlainText(string)



    def saveAnnotation(self):
        print "SAVE"
        #TODO: error handling
        if (self.outputpath==''):
            f=QFile(os.path.join(self.reffilename[0],self.annotfilename))
            print os.path.join(self.reffilename[0],self.annotfilename)
        else:
            f=QFile(os.path.join(self.outputpath,self.annotfilename))
        f.open(QFile.ReadWrite)
        if not f.isOpen():
            print "WARNING - cant open file"
        out = QTextStream(f)
        out << self.pteAnnotation.toPlainText()
        f.close()
        self.close()


    def discardAnnotation(self):
        print "DISCARD"
        self.close()
        pass
