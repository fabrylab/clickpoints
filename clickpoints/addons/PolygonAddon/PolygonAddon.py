#!/usr/bin/env python
# -*- coding: utf-8 -*-
# PolygonAddon.py

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
import numpy as np
import sys
import clickpoints
import os
import json
from qtpy import QtCore, QtGui, QtWidgets
from clickpoints.includes.QtShortCuts import AddQLineEdit, AddQComboBox, AddQCheckBox
import qtawesome as qta
import matplotlibwidget
from scipy.spatial import ConvexHull

# define default dicts, enables .access on dicts
class dotdict(dict):
    def __getattr__(self, attr):
        if attr.startswith('__'):
            raise AttributeError
        return self.get(attr, None)

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

# convert between focal length + sensor dimension & fov

def getNumber(input, format):
    try:
        return (format % input)
    except TypeError:
        return "None"

def getFloat(input):
    try:
        return float(input)
    except:
        return None

def getInteger(input):
    try:
        return int(input)
    except:
        return None


class Addon(clickpoints.Addon):

    initialized = False

    def __init__(self, *args, **kwargs):
        clickpoints.Addon.__init__(self, *args, **kwargs)

        # Check if the marker type is present
        if not self.db.getMarkerType("Polygon_1"):
            self.db.setMarkerType("Polygon_1", [0, 255, 255], self.db.TYPE_Normal)
            self.cp.reloadTypes()

        self.initialized = True
        self.lines = dotdict()




    # def run(self, start_frame=0):
    #     self.frame = self.cp.getCurrentFrame()
    #     print("processing frame nr %d" % self.frame)


    def updatePolygon(self,marker):
        self.cp.save()
        # print("Update Polygon")
        marker = self.db.getMarkers(type=marker.type, image=marker.image)
        # print("%d marker found" % marker.count())


        if not marker[0].type.name in self.lines.keys():
            self.lines[marker[0].type.name] = []

        ## draw element
        # cleanup current line
        try:
            _ = [line.scene().removeItem(line) for line in self.lines[marker[0].type.name]]
            self.lines[marker[0].type.name] = []
        except:
            pass

        # set pen
        pen = QtGui.QPen(QtGui.QColor(marker[0].type.color))
        pen.setWidth(2)
        pen.setCosmetic(True)

        # draw vertices
        for i in np.arange(0, marker.count() - 1):
            # add object
            line = QtWidgets.QGraphicsLineItem(
                QtCore.QLineF(QtCore.QPointF(*marker[i].pos()), QtCore.QPointF(*marker[i + 1].pos())))

            self.lines[marker[0].type.name].append(line)

        # draw closing vertices
        line = QtWidgets.QGraphicsLineItem(QtCore.QLineF(QtCore.QPointF(*marker[marker.count()-1].pos()), QtCore.QPointF(*marker[0].pos())))
        self.lines[marker[0].type.name].append(line)

        # set Pen, ZValue, and Display Parent
        _ = [line.setPen(pen) for line in self.lines[marker[0].type.name]]
        _ = [line.setZValue(100) for line in self.lines[marker[0].type.name]]
        _ = [line.setParentItem(self.cp.window.view.origin) for line in self.lines[marker[0].type.name]]


    def markerMoveEvent(self, marker):
        """
        On moving a marker - update the text information
        """
        if self.initialized:
            if marker.type.name.startswith('Polygon_'):
                self.updatePolygon(marker)

    def markerAddEvent(self, marker):
        """
        On adding a marker - calculate values
        """
        if self.initialized:
            if marker.type.name.startswith('Polygon_'):
               self.updatePolygon(marker)

    def markerRemoveEvent(self, marker):
        if self.initialized:
            if marker.type.name.startswith('Polygon_'):
               self.updatePolygon(marker)

    def frameChangedEvent(self):
        marker_types = self.db.getMarkerTypes()
        for m in marker_types:
            if m.name.startswith("Polygon_"):
                marker = self.db.getMarkers(type=m, frame=self.cp.getCurrentFrame())

                if marker.count() > 0:
                    # update display
                    self.updatePolygon(marker[0])
                else:
                    # cleanup display
                    try:
                        _ = [line.scene().removeItem(line) for line in self.lines[m.name]]
                        self.lines[m.name] = []
                    except:
                        pass

    def buttonPressedEvent(self):
        # show the addon window when the button in ClickPoints is pressed
        self.show()

        try:
            self.run()
        except:
            pass

    def delete(self):
        pass
