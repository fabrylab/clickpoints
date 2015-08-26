# handler class to list annotations / remakrs
# FUTURE: jump to annotation

from __future__ import division
# default
import os
from PyQt4.QtGui import *
from PyQt4.QtCore import *

import glob
from natsort import natsorted

class AnnotationOverview(QWidget):
    def __init__(self,window,mediahandler,outputpath=''):
        QWidget.__init__(self)

        # default settings and parameters
        self.defsuffix='_annot.txt'
        self.outputpath=outputpath
        self.window=window
        self.mh=mediahandler

        # get list of files
        input = self.outputpath + '*' + self.defsuffix
        self.filelist = natsorted(glob.glob(input))
        print self.filelist


        # widget layout and ellements
        self.setMinimumWidth(550)
        self.setMinimumHeight(300)
        self.setWindowTitle('Annotations')
        self.layout = QGridLayout(self)

        self.table= QTableWidget(self)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setColumnCount(2)
        self.table.setRowCount(0)
        self.table.setHorizontalHeaderLabels(QStringList(['Date','Comment']))
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().hide()
        self.layout.addWidget(self.table)

        self.table.doubleClicked.connect(self.JumpToAnnotation)

        for i,file in enumerate(self.filelist):
            # extract date
            path,fname=os.path.split(file)
            date = fname[0:15]

            #extract content
            f=QFile(file)
            f.open(QFile.ReadWrite)
            inS = QTextStream(f)
            comment=inS.readAll()
            f.close()


            # populate table
            ti = QTableWidgetItem()
            ti.setText(date)
            self.table.insertRow(self.table.rowCount())
            self.table.setItem(i,0,ti)

            ti = QTableWidgetItem()
            ti.setText(comment)
            self.table.insertRow(self.table.rowCount())
            self.table.setItem(i,1,ti)


        # fit column to context
        self.table.resizeColumnToContents(0)


    def JumpToAnnotation(self,idx):
        #print "double clicked"
        #print idx.row()
        timestamp= self.table.item(idx.row(),0).text()

        # find match in mh file list
        jtidx=[]
        for i,file in enumerate(self.mh.filelist):
            path,fname=os.path.split(file)
            if fname[0:15]==timestamp:
                jtidx=i
                break
        if jtidx==[]:
            print 'no matching file found for ts: %s'%timestamp
        else:
            print 'got to file: %s'% self.mh.filelist[jtidx]
            self.window.JumpToFrame(jtidx)

