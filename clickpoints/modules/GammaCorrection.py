#!/usr/bin/env python
# -*- coding: utf-8 -*-
# GammaCorrection.py

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

from typing import Optional, Tuple, Union

import qtawesome as qta
from numpy import ndarray
from qtpy import QtGui, QtCore, QtWidgets

from clickpoints.includes.BigImageDisplay import BigImageDisplay
from clickpoints.includes.Database import DataFileExtended
from clickpoints.includes.Tools import MySlider, BoxGrabber, TextButton


class GammaCorrection(QtWidgets.QGraphicsRectItem):
    data_file = None
    config = None
    schedule_update = False

    initialized = False

    auto_contrast = False

    max_value = None

    def __init__(self, parent_hud: QtWidgets.QGraphicsPathItem, image_display: BigImageDisplay,
                 window: "ClickPointsWindow") -> None:
        QtWidgets.QGraphicsRectItem.__init__(self, parent_hud)
        self.window = window

        self.image = image_display
        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))

        self.setScale(self.window.scale_factor)

        self.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 128)))
        self.setPos(-140 * self.window.scale_factor, (-140 - 20) * self.window.scale_factor)
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

    def initSliders(self) -> None:
        y_off = 15
        self.button_autocontrast = TextButton(self, 100, "auto (off)", font=self.window.mono_font,
                                              scale=self.window.scale_factor)
        self.button_autocontrast.setPos(3, 10)
        self.button_autocontrast.clicked.connect(self.toogleAutocontrast)

        functions = [self.updateGamma, self.updateBrightnes, self.updateContrast]
        self.max_value = self.image.image_pixMapItem.max_value
        min_max = [[0, 2], [0, 100], [0, 100]]
        start = [1, 99, 1]
        formats = [" %.2f", "%3d%%", "%3d%%"]
        names = ["Gamma", "Max P.", "Min P."]

        for i, name in enumerate(names):
            slider = MySlider(self, name, start_value=start[i], max_value=min_max[i][1], min_value=min_max[i][0],
                              font=self.window.mono_font, scale=self.window.scale_factor)
            slider.format = formats[i]
            slider.setPos(5, y_off + 40 + i * 30)
            slider.setValue(start[i])
            slider.valueChanged = functions[i]
            self.sliders.update({name: slider})

        self.button_update = TextButton(self, 50, "update", font=self.window.mono_font, scale=self.window.scale_factor)
        self.button_update.setPos(3, y_off + 40 + 3 * 30 - 20)
        self.button_update.clicked.connect(self.updateROI)
        self.button_reset = TextButton(self, 50, "reset", font=self.window.mono_font, scale=self.window.scale_factor)
        self.button_reset.setPos(56, y_off + 40 + 3 * 30 - 20)
        self.button_reset.clicked.connect(self.reset)

        self.setRect(QtCore.QRectF(0, 0, 110, y_off + 110 + 18))
        BoxGrabber(self)
        self.dragged = False

        self.ToggleInterfaceEvent(hidden=True)

        self.updateButtons()

    def toogleAutocontrast(self):
        self.config.auto_contrast = not self.config.auto_contrast
        self.updateButtons()

    def updateButtons(self) -> None:
        if self.max_value is None:
            return

        def getGamma():
            value = self.getConfigValue(0, 1)
            if value > 1:
                return 1 / value - 2.00001
            return value

        if self.config.auto_contrast is True:
            self.button_autocontrast.setText("auto (on)")
            min_max = [[0, 2], [0, 100], [0, 100]]
            start = [getGamma(), self.getConfigValue(3, 99), self.getConfigValue(4, 1)]
            formats = [" %.2f", "%3d%%", "%3d%%"]
            names = ["Gamma", "Max P.", "Min P."]
        else:
            max_value = self.max_value
            self.button_autocontrast.setText("auto (off)")
            min_max = [[0, 2], [0, max_value], [0, max_value]]
            start = [getGamma(), self.getConfigValue(1, max_value), self.getConfigValue(2, 0)]
            formats = [" %.2f", "    %3d", "    %3d"]
            names = ["Gamma", "Max", "Min"]

        for i, slider in enumerate(self.sliders.values()):
            slider.format = formats[i]
            slider.setText(names[i])
            slider.minValue = min_max[i][0]
            slider.maxValue = min_max[i][1]
            slider.setValue(start[i])

    def closeDataFile(self) -> None:
        self.data_file = None
        self.config = None

    def updateDataFile(self, data_file: DataFileExtended, new_database: bool) -> None:
        self.data_file = data_file
        self.config = data_file.getOptionAccess()

        self.ToggleInterfaceEvent(hidden=self.config.contrast_interface_hidden)
        self.schedule_update = True

    def updateHist(self, hist: Optional[Tuple[ndarray, ndarray]]) -> None:
        if hist is None:
            return
        histpath = QtGui.QPainterPath()
        w = 100. / len(hist[0])
        h = 98. / max(hist[0])
        for i, v in enumerate(hist[0]):
            histpath.addRect(i * w + 5, 0, w, -v * h)
        self.hist.setPath(histpath)

    def updateConv(self) -> None:
        if self.image.image_pixMapItem.conversion is None:
            return
        convpath = QtGui.QPainterPath()
        w = 100. / len(self.image.image_pixMapItem.conversion)
        h = 98. / 255
        for i, v in enumerate(self.image.image_pixMapItem.conversion):
            convpath.lineTo(float(i) * w + 5, -float(v) * h)
        self.conv.setPath(convpath)

    def setConfigValue(self, index: int, value: Union[float, int]) -> None:
        if self.config.contrast is None:
            self.config.contrast = {}
        if self.current_layer not in self.config.contrast:
            self.config.contrast[self.current_layer] = [None] * 5
        if len(self.config.contrast[self.current_layer]) < 5:
            self.config.contrast[self.current_layer] = [None] * 5
        self.config.contrast[self.current_layer][index] = value
        # to trigger the saving of the option
        self.config.contrast = self.config.contrast

    def getConfigValue(self, index: int, default: int) -> Union[float, int]:
        if self.config.contrast is None:
            return default
        if self.current_layer in self.config.contrast:
            try:
                value = self.config.contrast[self.current_layer][index]
            except IndexError:
                value = None
            if value is None:
                return default
            return value
        return default

    def updateGamma(self, value: float) -> None:
        # x * (1 - (value - 1) + 0.00001) = 1.
        # (1 - (value - 1) + 0.00001) = 1./x
        # value = 1/x - 2.00001
        if value > 1:
            self.setConfigValue(0, 1. / (1 - (value - 1) + 0.00001))
        else:
            self.setConfigValue(0, value)

        self.image.Change()

        self.updateConv()
        self.updateHist(self.image.hist)

    def updateBrightnes(self, value: int) -> None:
        if self.config.auto_contrast is True:
            self.setConfigValue(3, int(value))
        else:
            self.setConfigValue(1, int(value))

        self.image.Change()

        self.updateConv()
        self.updateHist(self.image.hist)

    def updateContrast(self, value: int) -> None:
        if self.config.auto_contrast is True:
            self.setConfigValue(4, int(value))
        else:
            self.setConfigValue(2, int(value))

        self.image.Change()

        self.updateConv()
        self.updateHist(self.image.hist)

    def setActiveLayer(self, new_index: int) -> None:
        update_hist = self.image.preview_slice is None
        self.updateButtons()
        self.image.Change()
        self.updateConv()
        if update_hist:
            self.updateHist(self.image.hist)

    def imageLoadedEvent(self, filename: str = "", frame_number: int = 0) -> None:
        if not self.initialized:
            self.initialized = True
            self.initSliders()
        if self.image.preview_rect is not None:
            self.updateHist(self.image.hist)
        if self.schedule_update:
            self.updateButtons()
            if 0:
                values = self.config.contrast[self.current_layer]
                for i, name in enumerate(self.sliders):
                    self.sliders[name].setValue(values[i])
                # self.sliders["Gamma"].setValue(self.config.contrast_gamma)
                # self.sliders["Max"].setValue(self.config.contrast_max)
                # self.sliders["Min"].setValue(self.config.contrast_min)
            self.schedule_update = False

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == 2:
            self.reset()
        pass

    def reset(self):
        self.config.contrast[self.current_layer] = [None] * 5
        self.updateButtons()
        self.image.ResetPreview()
        self.hist.setPath(QtGui.QPainterPath())
        self.conv.setPath(QtGui.QPainterPath())

    def updateROI(self):
        # QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
        # self.image.PreviewRect()
        self.image.Change()
        self.updateHist(self.image.hist)
        QtWidgets.QApplication.restoreOverrideCursor()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:

        # @key ---- Gamma/Brightness Adjustment ---
        if event.key() == QtCore.Qt.Key_G:
            # @key G: update rect
            self.updateROI()

    def ToggleInterfaceEvent(self, event: Optional[bool] = None, hidden: Optional[bool] = None) -> None:
        if hidden is None:
            self.hidden = not self.hidden
        else:
            self.hidden = hidden
        if self.config is not None:
            self.config.contrast_interface_hidden = self.hidden
        self.setVisible(not self.hidden)
        self.button_brightness.setChecked(not self.hidden)

    def LayerChangedEvent(self, layer: int) -> None:
        self.current_layer = layer
        self.setActiveLayer(layer)

    @staticmethod
    def file() -> str:
        return __file__
