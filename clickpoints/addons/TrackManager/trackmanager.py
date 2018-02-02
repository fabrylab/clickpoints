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
from clickpoints.includes.QtShortCuts import AddQSpinBox
from qtpy import QtCore, QtGui, QtWidgets

class Addon(clickpoints.Addon):

    def __init__(self, *args, **kwargs):
        clickpoints.Addon.__init__(self, *args, **kwargs)
        # set the title and layout
        self.setWindowTitle("TrackManager - ClickPoints")
        self.layout = QtWidgets.QVBoxLayout(self)

        # add some options
        # the frame number for the kymograph
        self.addOption(key="minLength", display_name="Min Track Length", default=-1, value_type="int",
                       tooltip="How many points a track has to have to be displayed", min=-1)
        self.spinBox_minLength = AddQSpinBox(self.layout, "Min Track Length:", value=self.getOption("minLength"), float=False)
        self.linkOption("minLength", self.spinBox_minLength)

        # add export buttons
        self.button_update = QtWidgets.QPushButton("Update")
        self.button_update.clicked.connect(self.update)
        self.layout.addWidget(self.button_update)

    def buttonPressedEvent(self):
        self.show()

    def update(self):
        minCount = self.spinBox_minLength.value()
        self.db.db.execute_sql("UPDATE track SET hidden = (SELECT count(marker.track_id) < ? FROM marker WHERE track.id = marker.track_id GROUP BY track_id)", (minCount,))
        # get the marker handler
        marker_handler = self.cp.window.GetModule("MarkerHandler")
        # get all track types
        track_types = self.db.getMarkerTypes(mode=self.db.TYPE_Track)
        # and reload them
        for type in track_types:
            marker_handler.ReloadTrackType(type)

