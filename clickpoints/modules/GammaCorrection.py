#!/usr/bin/env python
# -*- coding: utf-8 -*-
# GammaCorrection.py

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

import os

from qtpy import QtGui, QtCore, QtWidgets
from qtpy.QtCore import Qt
import qtawesome as qta

from includes.Tools import MySlider, BoxGrabber, TextButton

class GammaCorrection(QtWidgets.QGraphicsRectItem):
    data_file = None
    config = None
    schedule_update = False

    initialized = False

    def __init__(self, parent_hud, image_display, window):
        QtWidgets.QGraphicsRectItem.__init__(self, parent_hud)
        self.window = window

        self.image = image_display
        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))

        self.setScale(self.window.scale_factor)

        self.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 128)))
        self.setPos(-140*self.window.scale_factor, (-140-20)*self.window.scale_factor)
        self.setZValue(19)

        self.hist = QtWidgets.QGraphicsPathItem(self)
        self.hist.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 0)))
        self.hist.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255, 128)))
        self.hist.setPos(0, 110)

        self.conv = QtWidgets.QGraphicsPathItem(self)
        self.conv.setPen(QtGui.QPen(QtGui.QColor(255, 0, 0, 128), 2))
        self.conv.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 0)))
        self.conv.setPos(0, 110)

        self.sliders = {}

        self.button_brightness = QtWidgets.QPushButton()
        self.button_brightness.setCheckable(True)
        self.button_brightness.setIcon(qta.icon("fa.adjust"))
        self.button_brightness.setToolTip("display brightness/gamma adjust")
        self.button_brightness.clicked.connect(self.ToggleInterfaceEvent)
        self.window.layoutButtons.addWidget(self.button_brightness)

        self.hidden = False
        self.ToggleInterfaceEvent(hidden=True)

        self.current_layer = 0

    def initSliders(self):
        functions = [self.updateGamma, self.updateBrightnes, self.updateContrast]
        self.max_value = self.image.image_pixMapItem.max_value
        min_max = [[0, 2], [0, self.max_value], [0, self.max_value]]
        start = [1, self.max_value, 0]
        formats = [" %.2f", "    %3d", "    %3d"]
        for i, name in enumerate(["Gamma", "Max", "Min"]):
            slider = MySlider(self, name, start_value=start[i], max_value=min_max[i][1], min_value=min_max[i][0],
                              font=self.window.mono_font, scale=self.window.scale_factor)
            slider.format = formats[i]
            slider.setPos(5, 40 + i * 30)
            slider.setValue(start[i])
            slider.valueChanged = functions[i]
            self.sliders.update({name: slider})

        self.button_update = TextButton(self, 50, "update", font=self.window.mono_font, scale=self.window.scale_factor)
        self.button_update.setPos(3, 40 + 3 * 30 - 20)
        self.button_update.clicked.connect(self.updateROI)
        self.button_reset = TextButton(self, 50, "reset", font=self.window.mono_font, scale=self.window.scale_factor)
        self.button_reset.setPos(56, 40 + 3 * 30 - 20)
        self.button_reset.clicked.connect(self.reset)

        self.setRect(QtCore.QRectF(0, 0, 110, 110 + 18))
        BoxGrabber(self)
        self.dragged = False

        self.ToggleInterfaceEvent(hidden=True)

    def closeDataFile(self):
        self.data_file = None
        self.config = None

    def updateDataFile(self, data_file, new_database):
        self.data_file = data_file
        self.config = data_file.getOptionAccess()

        # if new_database:
        #     values = self.config.contrast[self.current_layer]
        #     for i, name in enumerate(self.sliders):
        #         self.sliders[name].setValue(values[i])
        #     self.image.Change(gamma=values[0])
        #     self.image.Change(max_brightness=values[1])
        #     self.image.Change(min_brightness=values[2])

        self.ToggleInterfaceEvent(hidden=self.config.contrast_interface_hidden)
        # if self.config.contrast_gamma != 1 or self.config.contrast_max != 255 or self.config.contrast_min != 0:
        #     self.schedule_update = True
        if self.current_layer in self.config.contrast:
            if self.config.contrast[self.current_layer][0] != 1. or self.config.contrast[self.current_layer][1] != 255 or \
                        self.config.contrast[self.current_layer][2] != 0:
                self.schedule_update = True

    def updateHist(self, hist):
        if hist is None:
            return
        histpath = QtGui.QPainterPath()
        w = 100. / self.max_value
        h = 98./max(hist[0])
        for i, v in enumerate(hist[0]):
            histpath.addRect(i * w + 5, 0, w, -v * h)
        self.hist.setPath(histpath)

    def updateConv(self):
        if self.image.conversion is None:
            return
        convpath = QtGui.QPainterPath()
        w = 100. / len(self.image.conversion)
        h = 98./255
        for i, v in enumerate(self.image.conversion):
            convpath.lineTo(float(i) * w + 5, -float(v) * h)
        self.conv.setPath(convpath)

    def updateGamma(self, value):
        QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
        update_hist = self.image.preview_slice is None
        self.image.Change(gamma=value)
        self.updateConv()
        if update_hist:
            self.updateHist(self.image.hist)
        if self.config:
            # self.config.contrast_gamma = value
            contrast_old = dict(self.config.contrast)
            if self.current_layer in contrast_old:
                old_value = contrast_old[self.current_layer]
                old_value[0] = value
                contrast_old.update({self.current_layer: old_value})
                self.config.contrast = contrast_old
            else:
                contrast_old.update({self.current_layer: [value, self.max_value, 0]})
                self.config.contrast = contrast_old
        QtWidgets.QApplication.restoreOverrideCursor()

    def updateBrightnes(self, value):
        QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
        update_hist = self.image.preview_slice is None
        self.image.Change(max_brightness=value)
        self.updateConv()
        if update_hist:
            self.updateHist(self.image.hist)
        if self.config:
            # self.config.contrast_max = value
            contrast_old = dict(self.config.contrast)
            if self.current_layer in contrast_old:
                old_value = contrast_old[self.current_layer]
                old_value[1] = value
                contrast_old.update({self.current_layer: old_value})
                self.config.contrast = contrast_old
            else:
                contrast_old.update({self.current_layer: [1.0, value, 0]})
                self.config.contrast = contrast_old
        QtWidgets.QApplication.restoreOverrideCursor()

    def updateContrast(self, value):
        QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
        update_hist = self.image.preview_slice is None
        self.image.Change(min_brightness=value)
        self.updateConv()
        if update_hist:
            self.updateHist(self.image.hist)
        if self.config:
            # self.config.contrast_min = value
            contrast_old = dict(self.config.contrast)
            if self.current_layer in contrast_old:
                old_value = contrast_old[self.current_layer]
                old_value[2] = value
                contrast_old.update({self.current_layer: old_value})
                self.config.contrast = contrast_old
            else:
                contrast_old.update({self.current_layer: [1.0, self.max_value, value]})
                self.config.contrast = contrast_old

        QtWidgets.QApplication.restoreOverrideCursor()

    def setActiveLayer(self, new_index):
        QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
        update_hist = self.image.preview_slice is None
        if new_index in self.config.contrast:
            values = self.config.contrast[new_index]
            for i, name in enumerate(self.sliders):
                self.sliders[name].setValue(values[i])
            self.image.Change(min_brightness=values[2], max_brightness=values[1], gamma=values[0])
            self.updateConv()
            if update_hist:
                self.updateHist(self.image.hist)
        else:
            if len(self.config.contrast.keys()) == 0:
                values = [1, self.image.image_pixMapItem.max_value, 0]
            else:
                values = self.config.contrast[list(self.config.contrast.keys())[0]]
            for i, name in enumerate(self.sliders):
                self.sliders[name].setValue(values[i])
            self.image.Change(min_brightness=values[2], max_brightness=values[1], gamma=values[0])
            self.updateConv()
            if update_hist:
                self.updateHist(self.image.hist)
        QtWidgets.QApplication.restoreOverrideCursor()

    def imageLoadedEvent(self, filename="", frame_number=0):
        if not self.initialized:
            self.initialized = True
            self.initSliders()
        if self.image.preview_rect is not None:
            self.updateHist(self.image.hist)
        if self.schedule_update:
            values = self.config.contrast[self.current_layer]
            for i, name in enumerate(self.sliders):
                self.sliders[name].setValue(values[i])
            # self.sliders["Gamma"].setValue(self.config.contrast_gamma)
            # self.sliders["Max"].setValue(self.config.contrast_max)
            # self.sliders["Min"].setValue(self.config.contrast_min)
            self.schedule_update = False

    def mousePressEvent(self, event):
        if event.button() == 2:
            self.reset()
        pass

    def reset(self):
        for slider in self.sliders.values():
            slider.reset()
        self.image.ResetPreview()
        self.hist.setPath(QtGui.QPainterPath())
        self.conv.setPath(QtGui.QPainterPath())

    def updateROI(self):
        #QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
        #self.image.PreviewRect()
        self.image.Change()
        self.updateHist(self.image.hist)
        QtWidgets.QApplication.restoreOverrideCursor()

    def keyPressEvent(self, event):

        # @key ---- Gamma/Brightness Adjustment ---
        if event.key() == Qt.Key_G:
            # @key G: update rect
            self.updateROI()

    def ToggleInterfaceEvent(self, event=None, hidden=None):
        if hidden is None:
            self.hidden = not self.hidden
        else:
            self.hidden = hidden
        if self.config is not None:
            self.config.contrast_interface_hidden = self.hidden
        self.setVisible(not self.hidden)
        self.button_brightness.setChecked(not self.hidden)

    def LayerChangedEvent(self, layer):
        self.current_layer = layer
        self.setActiveLayer(layer)


    @staticmethod
    def file():
        return __file__
