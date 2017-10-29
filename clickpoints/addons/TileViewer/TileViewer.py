#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ExportMarkerCountToXLS.py

# Copyright (c) 2015-2016, Richard Gerum, Sebastian Richter
#
# This file is part of ClickPoints.
#
# ClickPoints is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ClickPoints is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ClickPoints. If not, see <http://www.gnu.org/licenses/>

from __future__ import division, print_function
import clickpoints
from clickpoints.includes.QtShortCuts import AddQOpenFileChoose
import qtawesome as qta
from qtpy import QtCore, QtGui, QtWidgets
import numpy as np
from qimage2ndarray import array2qimage
import json


class Addon(clickpoints.Addon):
    page = 0
    page_item_count = 5
    tile_size = 84

    def __init__(self, *args, **kwargs):
        clickpoints.Addon.__init__(self, *args, **kwargs)
        # set the title and layout
        self.setWindowTitle("TileViewer - ClickPoints")
        self.setWindowIcon(qta.icon("fa.eye"))
        self.layout = QtWidgets.QVBoxLayout(self)

        # inut file chooser
        self.openFile = AddQOpenFileChoose(self.layout, "Input", "", file_type="*.txt")
        self.openFile.textChanged.connect(self.loadFile)

        # the page selector
        self.layout_navigate = QtWidgets.QHBoxLayout()
        self.layout.addLayout(self.layout_navigate)
        self.pushButton_left = QtWidgets.QPushButton(qta.icon("fa.arrow-left"), "")
        self.pushButton_left.clicked.connect(lambda: self.setPage(offset=-1))
        QtWidgets.QShortcut(QtGui.QKeySequence("Left"), self, lambda: self.setPage(offset=-1))
        self.layout_navigate.addWidget(self.pushButton_left)
        self.pushButton_right = QtWidgets.QPushButton(qta.icon("fa.arrow-right"), "")
        self.pushButton_right.clicked.connect(lambda: self.setPage(offset=+1))
        QtWidgets.QShortcut(QtGui.QKeySequence("Right"), self, lambda: self.setPage(offset=1))
        self.layout_navigate.addWidget(self.pushButton_right)
        self.label_index = QtWidgets.QLabel("0/0")
        self.layout_navigate.addWidget(self.label_index)

        # create the table
        self.tableWidget = QtWidgets.QTableWidget(0, 2, self)
        self.layout.addWidget(self.tableWidget)
        self.row_headers = ["Image", "Data"]
        self.tableWidget.setHorizontalHeaderLabels(self.row_headers)
        self.tableWidget.setMinimumHeight(500)
        self.setMinimumWidth(300)
        self.tableWidget.setCurrentCell(0, 0)

        # add a marker type with a square
        self.my_type = self.db.setMarkerType("view", "#ef7fff", self.db.TYPE_Normal, style='{"shape":"rect-o", "scale": %d, "transform":"image"}' % self.tile_size)
        self.cp.reloadTypes()
        # find or create one instance of this marker
        self.my_marker = self.db.getMarkers(type=self.my_type)
        if self.my_marker.count():
            # take an instance if you found one
            self.my_marker = self.my_marker[0]
        else:
            # or create a new one
            self.my_marker = self.db.setMarker(image=1, x=0, y=0, type=self.my_marker)

        # connect the cell clicked event
        self.tableWidget.cellClicked.connect(self.cellSelected)

        # start with an empty table
        self.data = []
        self.setPage(0)

    def setPage(self, index=None, offset=None):
        # set the new page
        if index is None:
            new_page = self.page + offset
        else:
            new_page = index
        # limit it by 0 and max_pages
        max_pages = int(np.ceil(len(self.data)/self.page_item_count))
        self.page = min([max([0, new_page]), max_pages-1])
        # update the label
        self.label_index.setText("%d/%d" % (self.page+1, max_pages))
        # and the table
        self.updateTable()

    def loadFile(self, file):
        # load the data from the file
        with open(file, "r") as fp:
            self.data = json.loads(fp.read())
        # go to the first page
        self.setPage(0)

    def cellSelected(self, row, column):
        # get the data
        data = self.data[row]
        # jump to the frame
        self.cp.jumpToFrame(data[0])
        # center the window on the position
        self.cp.centerOn(data[1], data[2])
        # place the marker at the position
        self.db.setMarker(id=self.my_marker.id, x=data[1], y=data[2], image=self.db.getImage(data[0]))
        self.cp.reloadMarker()

    def setTableText(self, row, column, text):
        # create or get a QTableWidgetItem item
        if column == -1:
            item = self.tableWidget.verticalHeaderItem(row)
            if item is None:
                item = QtWidgets.QTableWidgetItem("")
                self.tableWidget.setVerticalHeaderItem(row, item)
        else:
            item = self.tableWidget.item(row, column)
            if item is None:
                item = QtWidgets.QTableWidgetItem("")
                self.tableWidget.setItem(row, column, item)

        # if we have an array set the image
        if isinstance(text, np.ndarray):
            #item.setIcon(QtGui.QIcon(QtGui.QPixmap(array2qimage(text))))
            # the image is the background if the cell
            try:
                item.setBackground(QtGui.QBrush(array2qimage(text)))
            except ValueError as err:
                pass
            # set the cell size to fit the image
            self.tableWidget.setRowHeight(row, self.tile_size)
            self.tableWidget.setColumnWidth(column, self.tile_size)
            # make it not selectable
            item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            item.setText("")
        # if not set the text
        else:
            item.setBackground(QtGui.QBrush(0))
            item.setText(str(text))

    def updateTable(self):
        # set the row count
        self.tableWidget.setRowCount(self.page_item_count)
        # fill the rows with the data
        idx = -1
        for idx, d in enumerate(self.data[self.page*self.page_item_count:(self.page+1)*self.page_item_count]):
            self.updateRow(idx, idx+self.page*self.page_item_count)
        # set the row count again, to cut out unused rows
        self.tableWidget.setRowCount(idx+1)

    def updateRow(self, row, idx):
        # get the data from the list
        data = self.data[idx]
        # set the id
        self.setTableText(row, -1, "#%d" % idx)
        # set the image
        image = self.db.getImage(data[0])
        im = image.data
        im = im[int(data[2]-self.tile_size/2):int(data[2]+self.tile_size/2), int(data[1]-self.tile_size/2):int(data[1]+self.tile_size/2)]
        self.setTableText(row, 0, im)
        # set the additional data
        self.setTableText(row, 1, "Image: %d\nx: %d\ny: %d" % (data[0], data[1], data[2]))

    def buttonPressedEvent(self):
        # show the addon window when the button in ClickPoints is pressed
        self.show()


if __name__ == "__main__":
    import sys, ctypes
    if sys.platform[:3] == 'win':
        myappid = 'fabrybiophysics.foxviewer'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    app = QtWidgets.QApplication(sys.argv)

    database = clickpoints.DataFile(r"D:\Repositories\ClickPointsExamples\TweezerVideos\001\track.cdb")

    window = Addon(database=database)
    window.show()
    app.exec_()