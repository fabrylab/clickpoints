#!/usr/bin/env python
# -*- coding: utf-8 -*-
# persistent.py

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
import clickpoints
from clickpoints.modules.MarkerHandler import MyNonGrabberItem
from qtpy import QtCore, QtGui, QtWidgets


class Addon(clickpoints.Addon):
    initialized = False

    def __init__(self, *args, **kwargs):
        clickpoints.Addon.__init__(self, *args, **kwargs)

        self.points = {}

        if not self.db.getMarkerType("persistent"):
            self.db.setMarkerType("persistent", [0, 255, 255], self.db.TYPE_Normal)
            self.cp.reloadTypes()

        self.cp.window.view.origin.is_new = False

        self.my_type = self.db.getMarkerType(name="persistent")

        # load the current frame


    def imageLoadedEvent(self, filename, framenumber):
        if not self.initialized:
            self.initialize()

    def initialize(self):
        # clear the points from the last frame
        self.clearPoints()

        markers = self.db.getMarkers(type="persistent")

        for marker in markers:
            self.addPoint(marker)

        self.initialized = True

    def addPoint(self, marker):
        point = MyNonGrabberItem(self.cp.window.view.origin, QtGui.QColor(self.my_type.color), marker.x, marker.y)
        point.setZValue(1000)
        self.points[marker.id] = point

    def markerMoveEvent(self, entry):
        if entry.type == self.my_type:
            self.points[entry.id].setPos(entry.x, entry.y)

    def markerAddEvent(self, marker):
        if marker.type == self.my_type:
            self.addPoint(marker)

    def markerRemoveEvent(self, marker):
        if marker.type == self.my_type:
            self.points[marker.id].delete()
            del self.points[marker.id]

    def clearPoints(self):
        # delete all the points
        for id in self.points:
            self.points[id].delete()
        # and create a new empty array
        self.points = {}

    def delete(self):
        # when the add-on is removed delete all points
        self.clearPoints()

    def buttonPressedEvent(self):
        # do nothing when the button is pressed
        pass
