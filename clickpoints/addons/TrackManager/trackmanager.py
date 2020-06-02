#!/usr/bin/env python
# -*- coding: utf-8 -*-
# trackmanager.py

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
from clickpoints.includes.QtShortCuts import AddQSpinBox
from qtpy import QtCore, QtGui, QtWidgets

class Addon(clickpoints.Addon):

    def __init__(self, *args, **kwargs):
        clickpoints.Addon.__init__(self, *args, **kwargs)
        # set the title and layout
        self.setWindowTitle("TrackManager - ClickPoints")
        self.layout = QtWidgets.QVBoxLayout(self)

        # add some options
        # the minimum track length
        self.addOption(key="minLength", display_name="Min Track Length", default=-1, value_type="int",
                       tooltip="How many points a track has to have to be displayed.", min=-1)
        self.spinBox_minLength = AddQSpinBox(self.layout, "Min Track Length:", value=self.getOption("minLength"), float=False)
        self.linkOption("minLength", self.spinBox_minLength)
        # the maximum track length
        self.addOption(key="maxLength", display_name="Max Track Length", default=-1, value_type="int",
                       tooltip="How many points a track has to have to be displayed.", min=-1)
        self.spinBox_maxLength = AddQSpinBox(self.layout, "Max Track Length:", value=self.getOption("maxLength"),
                                             float=False)
        self.linkOption("maxLength", self.spinBox_maxLength)
        # the minimum track displacement
        self.addOption(key="minDisplacement", display_name="Min Track Displacement", default=-1, value_type="float",
                       tooltip="How much displacement a track has to have to be displayed.", min=-1)
        self.spinBox_minDisplacement = AddQSpinBox(self.layout, "Min Track Displacement:", value=self.getOption("minDisplacement"),
                                             float=True)
        self.linkOption("minDisplacement", self.spinBox_minDisplacement)
        # the maximum track displacement
        self.addOption(key="maxDisplacement", display_name="Max Track Displacement", default=-1, value_type="float",
                       tooltip="How much displacement a track has to have to be displayed.", min=-1)
        self.spinBox_maxDisplacement = AddQSpinBox(self.layout, "Max Track Displacement:",
                                                   value=self.getOption("maxDisplacement"),
                                                   float=True)
        self.linkOption("maxDisplacement", self.spinBox_maxDisplacement)

        # add export buttons
        self.button_update = QtWidgets.QPushButton("Update")
        self.button_update.clicked.connect(self.update)
        self.layout.addWidget(self.button_update)

    def buttonPressedEvent(self):
        self.show()

    def update(self):
        # empty lists
        query_filters = []
        query_parameters = []
        # add filter for min count
        minCount = self.spinBox_minLength.value()
        if minCount > 0:
            query_filters.append("count(marker.track_id) > ?")
            query_parameters.append(minCount)
        # add filter for max count
        maxCount = self.spinBox_maxLength.value()
        if maxCount > -1:
            query_filters.append("count(marker.track_id) < ?")
            query_parameters.append(maxCount)
        # add filter for min displacement
        minDisplacement = self.spinBox_minDisplacement.value()
        if minDisplacement > 0:
            query_filters.append("((min(marker.x)-max(marker.x))*(min(marker.x)-max(marker.x)))+((min(marker.y)-max(marker.y))*(min(marker.y)-max(marker.y))) > ?")
            query_parameters.append(minDisplacement**2)
        # add filter for max displacement
        maxDisplacement = self.spinBox_maxDisplacement.value()
        if maxDisplacement > -1:
            query_filters.append(
                "((min(marker.x)-max(marker.x))*(min(marker.x)-max(marker.x)))+((min(marker.y)-max(marker.y))*(min(marker.y)-max(marker.y))) < ?")
            query_parameters.append(maxDisplacement ** 2)

        # apply filters
        if len(query_filters) > 0:
            self.db.db.execute_sql("UPDATE track SET hidden = (SELECT 1-("+" AND ".join(query_filters)+") FROM marker WHERE track.id = marker.track_id GROUP BY track_id)", query_parameters)
        # or show all if no filters are active
        else:
            self.db.db.execute_sql("UPDATE track SET hidden = 0")

        # reload the tracks
        self.cp.reloadTracks()

