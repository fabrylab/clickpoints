#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ManualClassifier.py

# Copyright (c) 2015-2020, Richard Gerum, Sebastian Richter, Alexander Winterl
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ClickPoints. If not, see <http://www.gnu.org/licenses/>

from __future__ import division, print_function
import sys, os
from qtpy import QtGui, QtCore, QtWidgets
from qimage2ndarray import array2qimage
import qtawesome as qta
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "includes", "qextendedgraphicsview"))
from QExtendedGraphicsView import QExtendedGraphicsView

__icon__ = "fa.tag"

import clickpoints

# Connect to database
start_frame, database, port = clickpoints.GetCommandLineArgs()
db = clickpoints.DataFile(database)
com = clickpoints.Commands(port)

# parameter
marker_type_name = "marker"
marker_type_class0 = "no-bead"
marker_type_class1 = "bead"
view_size = 30

view_o1 = int(view_size/2)
view_o2 = int(view_size/2+0.5)

# Check if the marker type is present
for marker_type in [marker_type_name, marker_type_class0, marker_type_class1]:
    if not db.getMarkerType(marker_type):
        print("ERROR: Marker type %s does not exist" % marker_type)
        sys.exit(-1)

# convert marker back
#markers = db.getMarkers(type=[marker_type_class0, marker_type_class1])
#for m in markers:
#    m.type = db.getMarkerType(marker_type_name)
#    m.save()


class ClassifierWindow(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(QtWidgets.QWidget, self).__init__(parent)
        self.setWindowTitle("ManualClassifier - ClickPoints")
        self.setWindowIcon(qta.icon("fa.tag"))

        # window layout
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        # view/scene setup
        self.view = QExtendedGraphicsView()
        self.local_scene = self.view.scene
        self.origin = self.view.origin
        self.layout.addWidget(self.view)

        # set view to show total image and initialize pixmap
        self.view.setExtend(view_size, view_size)
        self.pixmapItem = QtWidgets.QGraphicsPixmapItem(QtGui.QPixmap(view_size, view_size), self.origin)

        # Get images and template
        self.image_iterator = db.getImageIterator(start_frame=start_frame)
        self.current_image = None
        self.image_data = None
        self.markers = None
        self.current_marker = None

        # start to display first image
        QtCore.QTimer.singleShot(1, self.displayNext)

    def displayNext(self):
        while True:
            # no image?
            if self.current_image is None:
                # try to get next
                try:
                    self.current_image = next(self.image_iterator)
                # if not, close window
                except StopIteration:
                    return self.close()
                # get image pixel data and markers
                self.image_data = self.current_image.data8
                self.markers = (m for m in db.getMarkers(image=self.current_image, type=marker_type_name))
            # get the next marker
            try:
                self.current_marker = next(self.markers)
            # or go to the next image
            except StopIteration:
                self.current_image = None
                continue
            break

        # get marker coordinates and image slice
        x = int(self.current_marker.x)
        y = int(self.current_marker.y)
        # cut out image
        if len(self.image_data.shape) == 3:  # in case of color
            data = self.image_data[y-view_o1:y+view_o2, x-view_o1:x+view_o2, :]
        else:  # in case of black and white
            data = self.image_data[y-view_o1:y+view_o2, x-view_o1:x+view_o2]
        # and feed data to pixmap, this will automatically display the data
        self.pixmapItem.setPixmap(QtGui.QPixmap(array2qimage(data)))

    def keyPressEvent(self, event):

        if event.key() == QtCore.Qt.Key_Escape:
            # @key Escape: close window
            self.close()

        if event.key() == QtCore.Qt.Key_Left:
            # @key Left: set category 0
            print(self.current_image.id, self.current_marker.id, 0)
            self.current_marker.type = db.getMarkerType(name=marker_type_class0)
            self.current_marker.save()
            self.displayNext()

        if event.key() == QtCore.Qt.Key_Right:
            # @key Right: set category 1
            print(self.current_image.id, self.current_marker.id, 1)
            self.current_marker.type = db.getMarkerType(name=marker_type_class1)
            self.current_marker.save()
            self.displayNext()


# create qt application
app = QtWidgets.QApplication(sys.argv)

# start window
window = ClassifierWindow()
window.show()
app.exec_()
