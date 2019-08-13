#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BigImageDisplay.py

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
from qtpy import QtGui, QtCore, QtWidgets
import numpy as np
from clickpoints.includes.Tools import array2qimage


def BoundBy(value, min, max):
    # return value bound by min and max
    if value is None:
        return min
    if value < min:
        return min
    if value > max:
        return max
    return value


def generateLUT(min, max, gamma, bins):
    if min >= max:
        min = max-1
    if min < 0:
        min = 0
    if max >= bins:
        max = bins-1
    if max <= min:
        max = min+1
    dynamic_range = max - min
    conversion = np.arange(0, int(bins), dtype=np.uint8)
    conversion[:min] = 0
    conversion[min:max] = np.power(np.linspace(0, 1, dynamic_range, endpoint=False), gamma) * 255
    conversion[max:] = 255
    return conversion


class ImageDisplaySignal(QtCore.QObject):
    display = QtCore.Signal()


class MyQGraphicsPixmapItem(QtWidgets.QGraphicsPixmapItem):
    conversion = None
    max_value = 256

    def __init__(self, *args):
        super().__init__(*args)
        self.setImage = self.setImageFirstTime

    def setImage(self, image):
        pass

    def setImageFirstTime(self, image):
        # set image called for the first time, therefore, we set a conversion if none is set
        if image.dtype == np.uint16:
            if image.max() < 2**12:
                self.max_value = 2**12
            else:
                self.max_value = 2**16
            self.setConversion(generateLUT(0, self.max_value, 1, 2**16))
        else:
            self.setImage = self.setImageDirect
        self.setImage(image)

    def setImageDirect(self, image):
        self.setPixmap(QtGui.QPixmap(array2qimage(image.astype(np.uint8))))

    def setImageLUT(self, image):
        self.setPixmap(QtGui.QPixmap(array2qimage(self.conversion[image[:, :, :3]])))

    def setConversion(self, conversion):
        self.conversion = conversion
        if isinstance(conversion, np.ndarray):
            self.setImage = self.setImageLUT
        else:
            self.setImage = self.setImageDirect



class BigImageDisplay:
    data_file = None
    config = None
    thread = None

    def __init__(self, origin, window):
        self.origin = origin
        self.window = window

        self.image = None
        self.hist = None
        self.conversion = None

        self.background_rect = QtWidgets.QGraphicsRectItem(self.origin)
        self.background_rect.setRect(0, 0, 10, 10)
        self.background_rect.setZValue(15)

        self.image_pixMapItem = MyQGraphicsPixmapItem(self.origin)
        self.image_pixMapItem.setZValue(1)

        self.preview_pixMapItem = QtWidgets.QGraphicsPixmapItem(self.origin)
        self.preview_pixMapItem.setZValue(10)
        self.preview_slice = None
        self.preview_qimage = None
        self.preview_qimageView = None

        self.slice_zoom_pixmap = QtWidgets.QGraphicsPixmapItem(self.origin)
        self.slice_zoom_pixmap.setZValue(10)

        self.preview_rect = None

        self.gamma = 1
        self.min = 0
        self.max = None

        self.eventFilters = []

        self.last_offset = np.array([0, 0])
        self.new_offset = np.array([0, 0])

    def setCursor(self, cursor):
        self.image_pixMapItem.setCursor(cursor)

    def unsetCursor(self):
        self.image_pixMapItem.unsetCursor()

    def closeDataFile(self):
        if self.thread is not None:
            self.thread.join()
        self.data_file = None
        self.config = None

    def updateDataFile(self, data_file, new_database):
        self.data_file = data_file
        self.config = data_file.getOptionAccess()

    def AddEventFilter(self, event_filter):
        # add a new event filter to the pixmaps
        self.eventFilters.append(event_filter)
        #for pixmap in self.pixMapItems:
        #    pixmap.installSceneEventFilter(event_filter)
        self.background_rect.setAcceptHoverEvents(True)
        self.background_rect.installSceneEventFilter(event_filter)

    async def SetImage_async(self, image, offset):
        self.background_rect.setRect(0, 0, image.shape[1], image.shape[0])
        # if image doesn't have a dimension for color channels, add one
        if len(image.shape) == 2:
            image = image.reshape((image.shape[0], image.shape[1], 1))

        # store the image
        self.image = image

        if not isinstance(image, np.ndarray):
            image = self.image.read_region((0, 0), self.image.level_count - 1,
                                           self.image.level_dimensions[self.image.level_count - 1])
            image = np.asarray(image)
            self.image_pixMapItem.setImage(image)
            self.image_pixMapItem.setScale(self.image.level_downsamples[-1])
            self.slice_zoom_image = image
            self.updateSlideView()
        else:
            self.image_pixMapItem.setImage(image)
            self.image_pixMapItem.setScale(1)
            self.slice_zoom_pixmap.setVisible(False)

    def updateSlideView(self):
        if self.image is not None and not isinstance(self.image, np.ndarray):  # is slide
            preview_rect = np.array(self.window.view.GetExtend(True)).astype("int") + np.array([0, 0, 1, 1])
            for i in [0, 1]:
                if preview_rect[i] < 0:
                    preview_rect[i] = 0
                if preview_rect[i + 2] - preview_rect[i] > self.image.dimensions[i]:
                    preview_rect[i + 2] = self.image.dimensions[i] + preview_rect[i]

            level = self.image.get_best_level_for_downsample(1 / self.window.view.getOriginScale())
            self.last_level = level
            downsample = self.image.level_downsamples[level]

            dimensions_downsampled = (np.array(preview_rect[2:4]) - np.array(preview_rect[:2])) / downsample
            data = np.asarray(self.image.read_region(preview_rect[0:2], level, dimensions_downsampled.astype("int")))
            self.slice_zoom_image = data
            if self.conversion is not None:
                self.slice_zoom_image = self.conversion[self.slice_zoom_image[:, :, :3]]
            self.slice_zoom_pixmap.setPixmap(QtGui.QPixmap(array2qimage(self.slice_zoom_image)))
            self.slice_zoom_pixmap.setOffset(*(np.array(preview_rect[0:2]) / downsample))
            self.slice_zoom_pixmap.setScale(downsample)
            self.slice_zoom_pixmap.show()

    def GetImageRect(self, rect, use_max_image_size=False):
        if not isinstance(self.image, np.ndarray):
            return self.slice_zoom_image, 0, 0
        # extract start and end points from rect
        start_x, start_y, end_x, end_y = rect
        # constrain start points
        start_x = BoundBy(start_x, 0, self.image.shape[1])
        start_y = BoundBy(start_y, 0, self.image.shape[0])
        # constrain end points
        end_x = BoundBy(end_x, start_x+1, self.image.shape[1])
        end_y = BoundBy(end_y, start_y+1, self.image.shape[0])
        if use_max_image_size:
            end_x = BoundBy(end_x, start_x+1, start_x + self.config.max_image_size)
            end_y = BoundBy(end_y, start_y+1, start_y + self.config.max_image_size)
        # return image rect
        return self.image[int(start_y):int(end_y), int(start_x):int(end_x), :], int(start_x), int(start_y)

    def UpdatePreviewImage(self):
        # get the gamma correction rect minus the display offsets
        rect = self.preview_rect-np.hstack((self.last_offset, self.last_offset))
        # extract the image rect
        self.preview_slice, start_x, start_y = self.GetImageRect(rect, use_max_image_size=True)

        # calculate histogram over image patch
        #self.hist = np.histogram(self.preview_slice.flatten(), bins=np.linspace(0, 2**12, 255), density=True)

    def ResetPreview(self):
        self.min = 0
        self.max = self.image_pixMapItem.max_value
        self.gamma = 1
        self.Change()

    def Change(self, gamma=None, min_brightness=None, max_brightness=None):
        if self.hist is None and isinstance(self.image, np.ndarray):
            self.hist = np.histogram(self.image.flatten(), bins=np.linspace(0, self.image_pixMapItem.max_value, 256), density=True)
        # update gamma if set
        if gamma is not None:
            if gamma > 1:
                gamma = 1. / (1 - (gamma - 1) + 0.00001)
            self.gamma = gamma
        # update min brightness if set
        if min_brightness is not None:
            self.min = int(min_brightness)
        # update max brightness if set
        if max_brightness is not None:
            self.max = int(max_brightness)
        elif self.max is None:
            self.max = self.image_pixMapItem.max_value
        # ensure that min is smaller than max
        if self.min >= self.max:
            if self.max == 0:
                self.max = self.min + 1
            else:
                self.min = self.max-1

        # calculate conversion look up table
        self.conversion = generateLUT(self.min, self.max, self.gamma, self.image_pixMapItem.max_value)

        if not isinstance(self.image, np.ndarray):  # is slide
            self.updateSlideView()
            return
        # apply changes
        self.image_pixMapItem.setConversion(self.conversion)
        self.image_pixMapItem.setImage(self.image)
