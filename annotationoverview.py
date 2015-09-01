# handler class to list annotations / remakrs
# FUTURE: jump to annotation

from __future__ import division
# default
import os
from PyQt4.QtGui import *
from PyQt4.QtCore import *

import glob
from natsort import natsorted

from annotationhandler import *
from ConfigLoad import *

class AnnotationOverview(QWidget):
    def __init__(self,window,mediahandler,outputpath='',frameSlider=None, config=None):
        QWidget.__init__(self)

        # default settings and parameters
        self.outputpath=outputpath
        self.window=window
        self.mh=mediahandler
        self.frameSlider = frameSlider
        self.config = config

        self.frame_list = [os.path.split(file)[1][:-4] for file in self.mh.filelist]

        # get list of files
        input = os.path.join(self.outputpath, '*' + self.config.annotation_tag)
        self.filelist = natsorted(glob.glob(input))

        # widget layout and elements
        self.setMinimumWidth(700)
        self.setMinimumHeight(300)
        self.setWindowTitle('Annotations')
        self.layout = QGridLayout(self)

        self.table= QTableWidget(0, 7, self)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setHorizontalHeaderLabels(QStringList(['Date','Tag','Comment','R','System','Cam','file']))
        self.table.hideColumn(6)
        self.table.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setResizeMode(2,QHeaderView.Stretch)
        self.table.verticalHeader().hide()
        self.layout.addWidget(self.table)

        self.table.doubleClicked.connect(self.JumpToAnnotation)

        for i,file in enumerate(self.filelist):
            # read annotation file
            results, comment = ReadAnnotation(file)

            # get file basename
            filename = os.path.split(file)[1]
            basename = filename[:-len(self.config.annotation_tag)]

            # populate table
            self.table.insertRow(self.table.rowCount())
            self.table.setItem(i,0,QTableWidgetItem(results['timestamp']))
            self.table.setItem(i,1,QTableWidgetItem(", ".join(results['tags'])))
            self.table.setItem(i,2,QTableWidgetItem(comment))
            self.table.setItem(i,3,QTableWidgetItem(str(results['rating'])))
            self.table.setItem(i,4,QTableWidgetItem(results['system']))
            self.table.setItem(i,5,QTableWidgetItem(results['camera']))
            self.table.setItem(i,6,QTableWidgetItem(basename))

        # fit column to context
        self.table.resizeColumnToContents(0)

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

