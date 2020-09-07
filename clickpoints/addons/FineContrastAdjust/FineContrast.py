#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kymograph.py

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
from clickpoints.includes.QtShortCuts import AddQComboBox, AddQSaveFileChoose, AddQSpinBox, AddQLineEdit
from qtpy import QtCore, QtGui, QtWidgets
import numpy as np
from clickpoints.includes.matplotlibwidget import MatplotlibWidget, NavigationToolbar


class Addon(clickpoints.Addon):

    def __init__(self, *args, **kwargs):
        clickpoints.Addon.__init__(self, *args, **kwargs)
        # set the title and layout
        self.setWindowTitle("Fine Contrast Adjust - ClickPoints")
        self.layout = QtWidgets.QVBoxLayout(self)

        # add a plot widget
        self.plot = MatplotlibWidget(self)
        self.layout.addWidget(self.plot)
        self.layout.addWidget(NavigationToolbar(self.plot, self))

        self.hist_plot, = self.plot.axes.plot([], [])
        self.vline1, = self.plot.axes.plot([], [], color="r")
        self.vline2, = self.plot.axes.plot([], [], color="m")

        self.slider = QtWidgets.QSlider()
        self.slider.setOrientation(QtCore.Qt.Horizontal)
        self.layout.addWidget(self.slider)
        self.slider.valueChanged.connect(self.setValue)

        self.slider2 = QtWidgets.QSlider()
        self.slider2.setOrientation(QtCore.Qt.Horizontal)
        self.layout.addWidget(self.slider2)
        self.slider2.valueChanged.connect(self.setValue2)

    def setValue(self, value):
        self.cp.window.GetModule("GammaCorrection").updateBrightnes(value)
        self.vline1.set_data([value, value], [0, 1])
        self.plot.draw()

    def setValue2(self, value):
        self.cp.window.GetModule("GammaCorrection").updateContrast(value)
        self.vline2.set_data([value, value], [0, 1])
        self.plot.draw()

    def frameChangedEvent(self):
        self.slider.setRange(0, self.cp.window.GetModule("GammaCorrection").max_value)
        im = self.cp.getImage().data
        hist, bins = np.histogram(im[::4, ::4].ravel(), bins=np.linspace(0, self.cp.window.GetModule("GammaCorrection").max_value+1, 256), density=True)
        self.hist_plot.set_data(bins[:-1], hist)
        self.plot.axes.set_ylim(0, np.max(hist)*1.2)
        self.plot.axes.set_xlim(0, self.cp.window.GetModule("GammaCorrection").max_value)
        self.plot.draw()


    def buttonPressedEvent(self):
        self.slider.setRange(0, self.cp.window.GetModule("GammaCorrection").max_value)
        self.slider2.setRange(0, self.cp.window.GetModule("GammaCorrection").max_value)
        self.frameChangedEvent()
        self.show()
