#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Export.py

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
from clickpoints.includes.QtShortCuts import AddQComboBox, AddQSaveFileChoose, AddQSpinBox, AddQLineEdit, AddQOpenFileChoose, QInputBool, QInputNumber
from qtpy import QtCore, QtGui, QtWidgets
import numpy as np
from clickpoints.includes.matplotlibwidget import MatplotlibWidget, NavigationToolbar
from matplotlib import pyplot as plt
import time
import imageio
import re
import os
import matplotlib as mpl
from qimage2ndarray import array2qimage

#region utility functions
def readFlow(name):
    """
    Read *.flow output file containing a numpy array with 2 channels for x and y displacement
    :param name: filename including path
    :return: numpy array
    """

    f = open(name, 'rb')

    header = f.read(4)
    if header.decode("utf-8") != 'PIEH':
        raise Exception('Flow file header does not contain PIEH')

    width = np.fromfile(f, np.int32, 1).squeeze()
    height = np.fromfile(f, np.int32, 1).squeeze()

    flow = np.fromfile(f, np.float32, width * height * 2).reshape((height, width, 2))

    return flow.astype(np.float32)


class AddHLine(QtWidgets.QFrame):
    def __init__(self):
        QtWidgets.QFrame.__init__(self)
        self.setFrameShape(QtWidgets.QFrame.HLine)
        self.setFrameShadow(QtWidgets.QFrame.Sunken)


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

        group = QtWidgets.QGroupBox("Export Images")
        self.layout.addWidget(group)
        layout = QtWidgets.QVBoxLayout(group)

        # Check if the marker type is present
        self.my_type = self.db.setMarkerType("export_rect", [0, 255, 255], self.db.TYPE_Rect)
        self.my_track = self.db.setMarkerType("flow_track", [255, 255, 0], self.db.TYPE_Track)
        self.cp.reloadTypes()

        self.addOption(key="output_filename", display_name="Export Filename", default="export/flow%04d.jpg", value_type="string",
                       tooltip="Where to save the exported images.")
        self.input_filename = AddQSaveFileChoose(layout, 'Export Filename:', self.getOption("output_filename"),
                                           "Choose Image - ClickPoints", "Images (*.jpg *.png *.tif, *.svg)",
                                           lambda filename: self.CheckImageFilename(filename, ".jpg"))
        self.linkOption("output_filename", self.input_filename)

        # add export button
        self.button_export = QtWidgets.QPushButton("Export")
        self.button_export.clicked.connect(self.exportButton)
        layout.addWidget(self.button_export)


        ## FLOW DISPLAY
        group = QtWidgets.QGroupBox("Flow Display")
        self.layout.addWidget(group)
        layout = QtWidgets.QVBoxLayout(group)

        # input for the flow field
        self.addOption(key="flow_filename", display_name="Flow Files", default="flow/flow%04d.flo", value_type="string",
                       tooltip="The path to the flow files which are used to display.")
        self.input_filename_flow = AddQOpenFileChoose(layout, 'Flow Files:', self.getOption("flow_filename"),
                                                 "Choose Flow Files - ClickPoints", "Images (*.flo)",
                                                 lambda filename: self.CheckImageFilename(filename, ".flo"))
        self.linkOption("flow_filename", self.input_filename_flow)

        self.opacity_slider = QtWidgets.QSlider()
        layout.addWidget(self.opacity_slider)
        self.opacity_slider.setRange(0, 255)
        self.opacity_slider.setValue(255)
        self.opacity_slider.setOrientation(QtCore.Qt.Horizontal)
        self.opacity_slider.valueChanged.connect(lambda value: self.imageLoadedEvent("", self.cp.getCurrentFrame()))

        # use mask
        self.mask = None
        self.mask_checkbox = QInputBool(layout=layout, name='Use Mask',value=False)
        self.mask_checkbox.checkbox.stateChanged.connect(lambda value: self.imageLoadedEvent("", self.cp.getCurrentFrame()))

        # use display slider
        self.displacement_checkbox = QInputBool(layout=layout, name='Use displacement',value=False)
        self.displacement_checkbox.checkbox.stateChanged.connect(lambda value: self.imageLoadedEvent("", self.cp.getCurrentFrame()))

        # min displacement slider
        self.minDisplacement_slider = QInputNumber(layout, 'min Disp', 0, 0, 100, True, True, 2)
        self.minDisplacement_slider.slider.setOrientation(QtCore.Qt.Horizontal)
        self.minDisplacement_slider.valueChanged.connect(
            lambda value: self.imageLoadedEvent("", self.cp.getCurrentFrame()))

        # max displacement slider
        self.maxDisplacement_slider = QInputNumber(layout, 'max Disp', 100, 0, 100, True, True, 2)
        self.maxDisplacement_slider.slider.setOrientation(QtCore.Qt.Horizontal)
        self.maxDisplacement_slider.valueChanged.connect(
            lambda value: self.imageLoadedEvent("", self.cp.getCurrentFrame()))

        ## FLOW TRACKING
        group = QtWidgets.QGroupBox("Flow Tracking")
        self.layout.addWidget(group)
        layout = QtWidgets.QVBoxLayout(group)

        # add track button
        self.button_track = QtWidgets.QPushButton("Track")
        self.button_track.clicked.connect(self.trackButton)
        layout.addWidget(self.button_track)

        self.button_track_once = QtWidgets.QPushButton("Track One Frame")
        self.button_track_once.clicked.connect(self.trackOnceButton)
        layout.addWidget(self.button_track_once)

        # add a progress bar
        self.progressbar = QtWidgets.QProgressBar()
        self.layout.addWidget(self.progressbar)

        # the flow overlay over the image
        self.image = QtWidgets.QGraphicsPixmapItem(self.cp.window.view.origin)

        # display the current flow image
        self.imageLoadedEvent("", self.cp.getCurrentFrame())

    def delete(self):
        self.image.scene().removeItem(self.image)

    def imageLoadedEvent(self, filename, framenumber):
        # only proceed if the frame is valid
        if framenumber is None:
            return

        try:
            flow = readFlow(self.input_filename_flow.text() % framenumber)
        except (TypeError, FileNotFoundError):
            self.image.setPixmap(QtGui.QPixmap())
            return
        dx = flow[:, :, 0]
        dy = flow[:, :, 1]

        if self.mask_checkbox.value():
            print("mask used")
            try:
                self.mask = self.db.getMasks()[0].data
                print(self.mask.shape)

                # set masked values to zero
                dx[self.mask>0]=0
                dy[self.mask>0]=0

            except:
                print('No mask available')
        else:
            self.mask = None


        from scipy.ndimage.filters import gaussian_filter

        #ox = gaussian_filter(dx, sigma=5)
        #oy = gaussian_filter(dy, sigma=5)
        ox = np.mean(dx[-100:, :100])
        oy = np.mean(dy[-100:, :100])

        #dx = dx-ox
        #dy = dy-oy

        a = np.arctan2(dx, dy)
        flow_dir = (np.arctan2(dx, dy)/np.pi + 1)/2
        flow_mag = np.sqrt((dx ** 2 + dy ** 2))

        cmap = mpl.cm.get_cmap('hsv')
        flow_mapped = cmap(flow_dir)

        if self.displacement_checkbox.value():
            flow_mag = (flow_mag - self.minDisplacement_slider.value()) / (self.maxDisplacement_slider.value() - self.minDisplacement_slider.value() )
        else:
            flow_mag -= 0.5
            flow_mag[flow_mag<0] = 0
            flow_mag /= 5
            flow_mag[flow_mag>1] = 1

        flow_mapped[:, :, 3] = flow_mag*self.opacity_slider.value()/255.

        self.image.setPixmap(QtGui.QPixmap(array2qimage(flow_mapped*255)))
        self.image.setZValue(10)

    def CheckImageFilename(self, srcpath, extension):
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
        return self.checkExtension(srcpath, extension)

    def checkExtension(self, name, ext):
        # in some versions the Qt file dialog doesn't automatically add an extension
        name = os.path.normpath(name)
        basename, current_extension = os.path.splitext(name)
        if current_extension == "":
            return name+ext
        return name

    def trackButton(self):
        # get the frame range
        self.start, self.end, self.skip = self.cp.getFrameRange()
        # ensure that the range is divisable by skip
        self.end -= (self.end - self.start) % self.skip
        # init the progessbar
        self.progressbar.setRange(0, self.end - self.start)
        self.cp.save()
        # run the tracking
        self.run_threaded(function=self.track)

    def trackOnceButton(self):
        # get the frame range
        self.start, self.end, self.skip = self.cp.getCurrentFrame(), self.cp.getCurrentFrame()+2, 1
        # init the progessbar
        self.progressbar.setRange(0, self.end - self.start)
        self.cp.save()
        # run the tracking
        self.run_threaded(function=self.track)

    def track(self, _):
        print("Trackking from ", self.start, self.end, self.skip)
        images = self.db.getImageIterator(self.start, self.end, skip=self.skip)

        # retrieve first image
        image_last = next(images)

        # get points and corresponding tracks
        points = self.db.getMarkers(image=image_last, processed=0, type=self.my_track)
        p0 = np.array([[point.x, point.y] for point in points]).astype(np.float32)
        tracks = [point.track for point in points]
        if len(p0) == 0:
            print("Nothing to track")
            return
        print("init", p0.shape, image_last.sort_index, image_last.id, image_last)

        # start iterating over all images
        for index, image in enumerate(images):
            self.progressbar.setValue(index)
            print("Tracking frame number %d, %d tracks" % (image.sort_index, len(tracks)), image.id, image_last.id)

            flow = readFlow("flow/flow%04d.flo" % image_last.sort_index)

            dx = flow[:, :, 0]
            dy = flow[:, :, 1]
            flow_mag = np.sqrt((dx ** 2 + dy ** 2))

            for i in range(p0.shape[0]):
                print(i)
                x, y = p0[i, :].astype("int")
                u = np.unravel_index(np.argmax(flow_mag[y-3:y+4, x-3:x+4]), flow_mag[y-3:y+4, x-3:x+4].shape)
                print("u", u)
                iy, ix = np.array(u)-3
                p0[i, 0] += dx[y+iy, x+ix] + ix
                p0[i, 1] += dy[y+iy, x+ix] + iy
            print("save", p0.shape)
            # set the new positions
            self.db.setMarkers(image=image, x=p0[:, 0], y=p0[:, 1], processed=0, track=tracks, type=self.my_track)

            # mark the marker in the last frame as processed
            self.db.setMarkers(image=image_last, x=p0[:, 0], y=p0[:, 1], processed=1, track=tracks, type=self.my_track)

            # update ClickPoints
            self.cp.reloadMarker(image.sort_index)
            self.cp.jumpToFrameWait(image.sort_index)

            # store positions and image
            image_last = image

            # check if we should terminate
            if self.cp.hasTerminateSignal():
                print("Cancelled Tracking")
                return
        # set the progessbar to 100%
        self.progressbar.setValue(self.end - self.start)

    def exportButton(self):
        # get the frame range
        self.start, self.end, self.skip = self.cp.getFrameRange()
        # ensure that the range is divisable by skip
        self.end -= (self.end - self.start) % self.skip
        # init the progessbar
        self.progressbar.setRange(0, self.end-self.start)
        # and start the export
        self.run_threaded(function=self.export)

    def export(self, start_frame=0):
        # get the rectangle
        rectangle = self.db.getRectangles(frame=self.cp.getCurrentFrame(), type=self.my_type)[0]
        # iterate over images
        for index, image in enumerate(self.db.getImageIterator(self.start, self.end, skip=self.skip)):
            # update the progressbar
            self.progressbar.setValue(index*self.skip)
            # slice the image
            image_sliced = rectangle.cropImage(image)
            # write the image
            filename = self.input_filename.text() % index
            print(filename)
            if not os.path.exists(os.path.dirname(filename)):
                os.mkdir(os.path.dirname(filename))
            imageio.imwrite(filename, image_sliced)

            # check if we should terminate
            if self.cp.hasTerminateSignal():
                print("Cancelled Export")
                return
        # set the progessbar to 100%
        self.progressbar.setValue(self.end-self.start)

    def ensureMarkerBlockSize(self, marker):
        # round start position
        marker.x = round(marker.x)
        marker.y = round(marker.y)
        # make width and height divisible by 64
        marker.width = round(marker.width / 64) * 64
        marker.height = round(marker.height / 64) * 64
        # count blocks
        marker.text = "%d blocks" % (marker.width / 64 * marker.height / 64)
        # save the marker
        marker.save()

    def markerMoveFinishedEvent(self, marker):
        # if the marker is of the current type
        if marker.type == self.my_type:
            # ensure its divisible by 64
            self.ensureMarkerBlockSize(marker)
            # repaint the markers
            self.cp.reloadMarker()

    def markerAddEvent(self, marker):
        pass

    def markerRemoveEvent(self, entry):
        pass

    def buttonPressedEvent(self):
        self.show()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_0:
            self.trackOnceButton()
