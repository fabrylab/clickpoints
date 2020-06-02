#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Dronpa.py

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

from __future__ import print_function, division
import clickpoints
from .GetIntensities import getIntensities
from .FitDiffusionConstants import fitDiffusionConstants, GetModel
from matplotlib import pyplot as plt
from qtpy import QtCore, QtGui, QtWidgets
import numpy as np
from scipy.optimize import minimize
from clickpoints.includes.matplotlibwidget import MatplotlibWidget, NavigationToolbar
from clickpoints.includes.QtShortCuts import AddQComboBox, AddQSaveFileChoose, AddQSpinBox, AddQLineEdit

class AddHLine(QtWidgets.QFrame):
    def __init__(self):
        QtWidgets.QFrame.__init__(self)
        self.setFrameShape(QtWidgets.QFrame.HLine)
        self.setFrameShadow(QtWidgets.QFrame.Sunken)

class Addon(clickpoints.Addon):

    def __init__(self, *args, **kwargs):
        clickpoints.Addon.__init__(self, *args, **kwargs)

        # set the title and layout
        self.setWindowTitle("Fluorescence Diffusion - ClickPoints")
        self.layout = QtWidgets.QVBoxLayout(self)

        self.addOption(key="delta_t", display_name="Delta t", default=2, value_type="float")
        self.addOption(key="color_channel", display_name="Color Channel", default=1, value_type="int")
        self.addOption(key="output_folder", display_name="Output Folder", default="output", value_type="string")

        # create a line type "connect"
        if not self.db.getMarkerType("connect"):
            self.db.setMarkerType("connect", [0, 255, 255], self.db.TYPE_Line)
            self.cp.reloadTypes()

        self.layout_intensity = QtWidgets.QHBoxLayout()
        self.layout.addLayout(self.layout_intensity)

        self.layout_intensity1 = QtWidgets.QVBoxLayout()
        self.layout_intensity.addLayout(self.layout_intensity1)

        self.input_delta_t = AddQSpinBox(self.layout_intensity1, "Delta T:", value=self.getOption("delta_t"), float=True)
        self.input_delta_t.setSuffix(" s")
        self.linkOption("delta_t", self.input_delta_t)

        self.input_color = AddQSpinBox(self.layout_intensity1, "Color Channel:", value=self.getOption("color_channel"), float=False)
        self.linkOption("color_channel", self.input_color)

        self.button_update = QtWidgets.QPushButton("Calculate Intensities")
        self.layout_intensity1.addWidget(self.button_update)
        self.button_update.clicked.connect(self.updateIntensities)

        # the table listing the line objects
        self.tableWidget = QtWidgets.QTableWidget(0, 1, self)
        self.layout_intensity1.addWidget(self.tableWidget)

        self.layout_intensity_plot = QtWidgets.QVBoxLayout()
        self.layout_intensity.addLayout(self.layout_intensity_plot)
        self.plot_intensity = MatplotlibWidget(self)
        self.layout_intensity_plot.addWidget(self.plot_intensity)
        self.layout_intensity_plot.addWidget(NavigationToolbar(self.plot_intensity, self))


        self.layout.addWidget(AddHLine())

        self.layout_diffusion = QtWidgets.QHBoxLayout()
        self.layout.addLayout(self.layout_diffusion)

        self.layout_diffusion1 = QtWidgets.QVBoxLayout()
        self.layout_diffusion.addLayout(self.layout_diffusion1)

        self.button_calculate = QtWidgets.QPushButton("Calculate Diffusion")
        self.layout_diffusion1.addWidget(self.button_calculate)
        self.button_calculate.clicked.connect(self.calculateDiffusion)

        # the table listing the line objects
        self.tableWidget2 = QtWidgets.QTableWidget(0, 1, self)
        self.layout_diffusion1.addWidget(self.tableWidget2)

        self.layout_diffusion_plot = QtWidgets.QVBoxLayout()
        self.layout_diffusion.addLayout(self.layout_diffusion_plot)
        self.plot_diffusion = MatplotlibWidget(self)
        self.layout_diffusion_plot.addWidget(self.plot_diffusion)
        self.layout_diffusion_plot.addWidget(NavigationToolbar(self.plot_diffusion, self))

        # add a progress bar
        self.progressbar = QtWidgets.QProgressBar()
        self.layout.addWidget(self.progressbar)

        self.diffusionConstants = []

    def calculateIntensities(self):
        self.cp.save()
        self.times = []
        # get times
        for t, im in enumerate(self.db.getImages()):
            self.times.append(t * self.input_delta_t.value())
        # iterate over cells
        self.cell_intensities = []
        self.cell_names = []
        self.cell_colors = []
        self.cell_indices = []
        self.cell_areas = []
        for m, cell in enumerate(self.db.getMaskTypes()):
            self.cell_names.append(cell.name)
            self.cell_colors.append(cell.color)
            self.cell_indices.append(cell.index)
            inte_list = []
            size = 0
            for t, im in enumerate(self.db.getImages()):
                mask = (im.mask.data == cell.index)
                if not np.any(mask):
                    break
                im1 = im.data
                if len(im1.shape) == 3:
                    if im1.shape[2] == 1:
                        im1 = im1[:, :, 0]
                    else:
                        im1 = im1[:, :, self.input_color.value()]
                inte_list.append(np.mean(im1[mask]))
                if t == 0:
                    size = np.sum(mask)
            self.cell_intensities.append(inte_list)
            self.cell_areas.append(size)

        self.link_pairs = []
        for connection in self.db.getLines(type="connect"):
            pair1 = connection.image.mask.data[int(connection.y1), int(connection.x1)]
            pair2 = connection.image.mask.data[int(connection.y2), int(connection.x2)]
            try:
                pair1 = self.cell_indices.index(pair1)
                pair2 = self.cell_indices.index(pair2)
            except ValueError:
                print("Invalid connection!")
                continue
            if pair1 < pair2:
                pair = (pair1, pair2)
            else:
                pair = (pair2, pair1)
            if pair not in self.link_pairs:
                self.link_pairs.append(pair)
            print(self.link_pairs)
        if len(self.diffusionConstants) != len(self.link_pairs):
            self.diffusionConstants = np.zeros(len(self.link_pairs))

    def setTableText(self, tableWidget, row, column, text):
        if column == -1:
            item = tableWidget.verticalHeaderItem(row)
            if item is None:
                item = QtWidgets.QTableWidgetItem("")
                tableWidget.setVerticalHeaderItem(row, item)
        elif row == -1:
            item = tableWidget.horizontalHeaderItem(column)
            if item is None:
                item = QtWidgets.QTableWidgetItem("")
                tableWidget.setHorizontalHeaderItem(column, item)
        else:
            item = tableWidget.item(row, column)
            if item is None:
                item = QtWidgets.QTableWidgetItem("")
                tableWidget.setItem(row, column, item)
                if column == 2:
                    item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(str(text))

    def updateTable(self):
        self.tableWidget.setRowCount(len(self.cell_names))
        self.tableWidget.setColumnCount(len(self.times))
        for index, time in enumerate(self.times):
            self.setTableText(self.tableWidget, -1, index, "%s s" % str(time))
        for index, cell in enumerate(self.cell_names):
            self.setTableText(self.tableWidget, index, -1, cell)
            for index2, intensity in enumerate(self.cell_intensities[index]):
                self.setTableText(self.tableWidget, index, index2, "%.2f" % intensity)
        self.tableWidget.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)

        self.tableWidget2.setRowCount(len(self.link_pairs))
        print(self.tableWidget2.rowCount(), len(self.link_pairs))
        self.tableWidget2.setColumnCount(1)
        self.setTableText(self.tableWidget2, -1, 0, "Diffusion")
        for index, pair in enumerate(self.link_pairs):
            self.setTableText(self.tableWidget2, index, -1, "%s - %s" % (self.cell_names[pair[0]], self.cell_names[pair[1]]))
            self.setTableText(self.tableWidget2, index, 0, self.diffusionConstants[index])

    def updateIntensityPlot(self):
        ax = self.plot_intensity.figure.axes[0]
        ax.clear()
        plots = []
        for index, cell in enumerate(self.cell_names):
            p, = ax.plot(self.times, self.cell_intensities[index], "-", color=self.cell_colors[index])
            plots.append(p)
        ax.set_xlabel("time (s)")
        ax.set_ylabel("mean intensity")
        ax.legend(plots, self.cell_names)
        self.plot_intensity.figure.tight_layout()
        self.plot_intensity.figure.canvas.draw()

    def updateIntensities(self):
        self.calculateIntensities()
        self.updateTable()
        self.updateIntensityPlot()

    def calculateDiffusion(self):
        self.calculateIntensities()
        self.run_threaded()

    def updateDiffusionPlot(self):
        I = np.array(self.Model(self.diffusionConstants))
        ax = self.plot_diffusion.figure.axes[0]
        ax.clear()
        plots = []
        for index, cell in enumerate(self.cell_names):
            p, = ax.plot(self.times, self.cell_intensities[index], "o", color=self.cell_colors[index])
            p, = ax.plot(self.times, I[:, index]/self.cell_areas[index], "-", color=self.cell_colors[index])
            plots.append(p)
        ax.set_xlabel("time (s)")
        ax.set_ylabel("mean intensity")
        ax.legend(plots, self.cell_names)
        self.plot_diffusion.figure.tight_layout()
        self.plot_diffusion.figure.canvas.draw()

    def run(self, start_frame=0):
        self.progressbar.setRange(0, 0)
        self.cp.window.app.processEvents()
        print("---- Building Model ----")
        self.ModelCost, self.Model = GetModel(self.times, np.array(self.cell_intensities).T * np.array(self.cell_areas),
                                              self.link_pairs, len(self.cell_names), self.cell_areas)

        # random starting values
        p = np.random.rand(len(self.link_pairs) + 1) * 5 + 20
        # find best diffusion constants
        print("---- Minimize Model ----")
        res = minimize(self.ModelCost, p, method='L-BFGS-B', jac=True, options={'disp': True, 'maxiter': int(1e5)},
                       bounds=((0, None),) * len(p))
        self.diffusionConstants = res['x']

        print("---- Plot Model ----")
        self.updateTable()
        self.updateDiffusionPlot()
        self.progressbar.setRange(0, 100)

    def buttonPressedEvent(self):
        self.updateIntensities()
        self.show()
