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
from clickpoints.includes.QtShortCuts import AddQComboBox, AddQSaveFileChoose, AddQSpinBox, AddQLineEdit
from qtpy import QtCore, QtGui, QtWidgets
import numpy as np
from clickpoints.includes.matplotlibwidget import MatplotlibWidget, NavigationToolbar
from matplotlib import pyplot as plt
import time
import imageio
import re
import os

class Addon(clickpoints.Addon):
    signal_update_plot = QtCore.Signal()
    signal_plot_finished = QtCore.Signal()
    image_plot = None
    last_update = 0
    updating = False
    exporting = False
    exporting_index = 0

    def __init__(self, *args, **kwargs):
        clickpoints.Addon.__init__(self, *args, **kwargs)
        # set the title and layout
        self.setWindowTitle("Export For Flow - ClickPoints")
        self.layout = QtWidgets.QVBoxLayout(self)

        # Check if the marker type is present
        self.my_type = self.db.setMarkerType("export_rect", [0, 255, 255], self.db.TYPE_Rect)
        self.cp.reloadTypes()

        self.input_filename = AddQSaveFileChoose(self.layout, 'Filename:', "",
                                           "Choose Image - ClickPoints", "Images (*.jpg *.png *.tif, *.svg)",
                                           self.CheckImageFilename)

        # add export buttons
        self.button_export = QtWidgets.QPushButton("Export")
        self.button_export.clicked.connect(self.export)
        self.layout.addWidget(self.button_export)

        # add a progress bar
        self.progressbar = QtWidgets.QProgressBar()
        self.layout.addWidget(self.progressbar)

    def CheckImageFilename(self, srcpath):
        # ensure that image filenames contain %d placeholder for the number
        match = re.match(r"%\s*\d*d", srcpath)
        # if not add one, between filename and extension
        if not match:
            path, name = os.path.split(srcpath)
            basename, ext = os.path.splitext(name)
            basename_new = re.sub(r"\d+", "%04d", basename, count=1)
            if basename_new == basename:
                basename_new = basename+"%04d"
            srcpath = os.path.join(path, basename_new+ext)
        return self.checkExtension(srcpath, ".jpg")

    def checkExtension(self, name, ext):
        # in some versions the Qt file dialog doesn't automatically add an extension
        name = os.path.normpath(name)
        basename, current_extension = os.path.splitext(name)
        if current_extension == "":
            return name+ext
        return name

    def export(self):
        # get the frame range
        self.start, self.end, self.skip = self.cp.getFrameRange()
        # ensure that the range is divisable by skip
        self.end -= (self.end - self.start) % self.skip
        # init the progessbar
        self.progressbar.setRange(0, self.end-self.start)
        # and start the export
        self.run_threaded(0)

    def run(self, start_frame=0):
        # get the rectangle
        rectangle = self.db.getRectangles(frame=self.cp.getCurrentFrame(), type=self.my_type)[0]
        # iterate over images
        for index, image in enumerate(self.db.getImageIterator(self.start, self.end, skip=self.skip)):
            # update the progressbar
            self.progressbar.setValue(index*self.skip)
            # slice the image
            image_sliced = image.data[rectangle.slice_y(), rectangle.slice_x()]
            # write the image
            filename = self.input_filename.text() % index
            print(filename)
            imageio.imwrite(filename, image_sliced)
        # set the progessbar to 100%
        self.progressbar.setValue(self.end-self.start)

    def ensureMarkerBlockSize(self, marker):
        # round start position
        marker.x = round(marker.x)
        marker.y = round(marker.y)
        # make width and height divisable by 64
        marker.width = round(marker.width / 64) * 64
        marker.height = round(marker.height / 64) * 64
        # count blocks
        marker.text = "%d blocks" % (marker.width / 64 * marker.height / 64)
        # save the marker
        marker.save()

    def markerMoveFinishedEvent(self, marker):
        # if the marker is of the current type
        if marker.type == self.my_type:
            # ensure its divisable by 64
            self.ensureMarkerBlockSize(marker)
            # repaint the markers
            self.cp.reloadMarker()

    def markerAddEvent(self, marker):
        pass

    def markerRemoveEvent(self, entry):
        pass

    def buttonPressedEvent(self):
        self.show()
