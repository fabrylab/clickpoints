#!/usr/bin/env python
# -*- coding: utf-8 -*-
# GrabPlotData.py

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
import os, sys
import clickpoints
from qtpy import QtCore, QtGui, QtWidgets


def Remap(value, minmax1, minmax2):
    """ Map from range minmax1 to range minmax2 """
    length1 = minmax1[1]-minmax1[0]
    length2 = minmax2[1]-minmax2[0]
    if length1 == 0:
        return 0
    percentage = (value-minmax1[0])/length1
    return percentage*length2 + minmax2[0]


class QRangeInput(QtWidgets.QWidget):
    valueChanged = QtCore.Signal(float, float)
    no_signal = False

    def __init__(self, layout, name, range):
        QtWidgets.QWidget.__init__(self)
        self.layout = QtWidgets.QHBoxLayout(self)

        self.label = QtWidgets.QLabel(name)
        self.layout.addWidget(self.label)

        self.input1 = QtWidgets.QDoubleSpinBox()
        self.input1.setValue(range[0])
        self.input1.valueChanged.connect(self.valueChangedEvent)
        self.input1.setRange(-999999, 999999)
        self.layout.addWidget(self.input1)

        self.input2 = QtWidgets.QDoubleSpinBox()
        self.input2.setValue(range[1])
        self.input2.valueChanged.connect(self.valueChangedEvent)
        self.input2.setRange(-999999, 999999)
        self.layout.addWidget(self.input2)

        if layout is not None:
            layout.addWidget(self)

    def valueChangedEvent(self):
        if self.no_signal is False:
            self.valueChanged.emit(*self.range())

    def range(self):
        return (self.input1.value(), self.input2.value())

    def setRange(self, lower, upper):
        self.no_signal = True
        self.input1.setValue(lower)
        self.input2.setValue(upper)
        self.no_signal = False


class Addon(clickpoints.Addon):
    def __init__(self, *args, **kwargs):
        clickpoints.Addon.__init__(self, *args, **kwargs)

        # Check if the marker types are present
        reload_types = False
        if not self.db.getMarkerType("x_axis"):
            self.db.setMarkerType("x_axis", [0, 200, 0], self.db.TYPE_Line)
            reload_types = True
        if not self.db.getMarkerType("y_axis"):
            self.db.setMarkerType("y_axis", [200, 200, 0], self.db.TYPE_Line)
            reload_types = True
        if not self.db.getMarkerType("data"):
            self.db.setMarkerType("data", [200, 0, 0], self.db.TYPE_Normal)
            reload_types = True
        if reload_types:
            self.cp.reloadTypes()

        # set the title and layout
        self.setWindowTitle("Grab Plot Data - ClickPoints")
        self.layout = QtWidgets.QVBoxLayout(self)

        self.inputx = QRangeInput(self.layout, "x range", (0, 1))
        self.inputx.valueChanged.connect(self.updateMarkers)
        self.inputy = QRangeInput(self.layout, "y range", (0, 1))
        self.inputy.valueChanged.connect(self.updateMarkers)

        self.overlays = {}

        self.image = QtWidgets.QGraphicsPixmapItem(self.cp.window.view.origin)
        self.image.setZValue(5)

        self.button_run = QtWidgets.QPushButton("Export")
        self.button_run.clicked.connect(self.run)
        self.layout.addWidget(self.button_run)

    def updateMarker(self, marker):
        if marker.type.name != "x_axis" and marker.type.name != "y_axis":
            return
        if marker.id not in self.overlays:
            overlay = QtWidgets.QGraphicsPixmapItem(self.image)
            overlay.text = []
            overlay.text_parents = []
            overlay.setZValue(10)
            for i in range(2):
                text_parent = QtWidgets.QGraphicsPixmapItem(overlay)
                text = QtWidgets.QGraphicsSimpleTextItem(text_parent)
                text_parent.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations)
                text.setZValue(10)
                overlay.text.append(text)
                overlay.text_parents.append(text_parent)
                text.setBrush(QtGui.QBrush(QtGui.QColor(255, 0, 0, 255)))
            self.overlays[marker.id] = overlay
        else:
            overlay = self.overlays[marker.id]
        index = marker.type.name.startswith("y")

        if index == 0:
            values = self.inputx.range()
        else:
            values = self.inputy.range()

        positions = [(marker.x1, marker.y1), (marker.x2, marker.y2)]
        for i in range(2):
            overlay.text[i].setText(str(values[i]))
            rect = overlay.text[0].sceneBoundingRect()
            if index == 1:
                overlay.text_parents[i].setPos(positions[i][0], positions[i][1])
                overlay.text[i].setPos(- rect.width() - 5, - rect.height() / 2)
            else:
                overlay.text_parents[i].setPos(positions[i][0], positions[i][1])
                overlay.text[i].setPos(- rect.width()/2, 5)

    def updateMarkers(self):
        for id in self.overlays:
            entry = self.db.getLine(id=id)
            if entry is not None:
                self.updateMarker(entry)

    def deleteOverlay(self, marker):
        if marker.type.name != "x_axis" and marker.type.name != "y_axis":
            return
        if marker.id in self.overlays:
            overlay = self.overlays[marker.id]
            overlay.scene().removeItem(overlay)
            del self.overlays[marker.id]

    def markerMoveEvent(self, marker):
        self.updateMarker(marker)

    def markerAddEvent(self, entry):
        self.updateMarker(entry)

    def markerRemoveEvent(self, entry):
        self.deleteOverlay(entry)

    def delete(self):
        ids = [id for id in self.overlays.keys()]
        for id in ids:
            overlay = self.overlays[id]
            overlay.scene().removeItem(overlay)
            del self.overlays[id]
        self.image.scene.removeItem(self.image)

    def run(self, start_frame=0):
        # get the current image
        image = self.db.getImage(self.cp.getCurrentFrame())

        # try to load axis
        x_axis = self.db.getLines(image=image, type="x_axis")
        y_axis = self.db.getLines(image=image, type="y_axis")
        if len(x_axis) != 1 or len(y_axis) != 1:
            print("ERROR: Please mark exactly one line with type 'x_axis' and exactly one with 'y_axis'.\nFound %d x_axis and %d y_axis" % (len(x_axis), len(y_axis)))
            sys.exit(-1)
        x_axis = x_axis[0]
        y_axis = y_axis[0]

        # create remap functions for x and y axis
        remap_x = lambda x: Remap(x, [x_axis.x1, x_axis.x2], self.inputx.range())
        remap_y = lambda y: Remap(y, [y_axis.y1, y_axis.y2], self.inputy.range())

        # get all markers
        markers = self.db.getMarkers(image=image, type="data")
        # compose the output filename
        filename = os.path.splitext(image.filename)[0]+".txt"
        # iterate over all data markers
        with open(filename, "w") as fp:
            for data in markers:
                print(remap_x(data.x), remap_y(data.y))
                fp.write("%f %f\n" % (remap_x(data.x), remap_y(data.y)))
        # print success
        print("%d datepoints written to file \"%s\"" % (markers.count(), filename))

    def buttonPressedEvent(self):
        self.show()
