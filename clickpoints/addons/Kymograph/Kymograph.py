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


class Addon(clickpoints.Addon):
    signal_update_plot = QtCore.Signal()
    signal_plot_finished = QtCore.Signal()
    image_plot = None
    last_update = 0
    exporting = False
    exporting_index = 0

    def __init__(self, *args, **kwargs):
        clickpoints.Addon.__init__(self, *args, **kwargs)
        # set the title and layout
        self.setWindowTitle("Kymograph - ClickPoints")
        self.layout = QtWidgets.QVBoxLayout(self)

        # add a mode selector, which formatting should be used for the output
        self.addOption(key="frames", display_name="Frames", default=50, value_type="int",
                       tooltip="How many images to use for the kymograph.")
        self.input_count = AddQSpinBox(self.layout, "Frames:", value=self.getOption("frames"), float=False)
        self.linkOption("frames", self.input_count)

        self.addOption(key="scaleLength", display_name="Scale Length", default=1, value_type="float",
                       tooltip="What is distance a pixel represents.")
        self.input_scale1 = AddQSpinBox(self.layout, "Scale Length:", value=self.getOption("scaleLength"), float=True)
        self.linkOption("scaleLength", self.input_scale1)

        self.addOption(key="scaleTime", display_name="Scale Time", default=1, value_type="float",
                       tooltip="What is the time difference between two images.")
        self.input_scale2 = AddQSpinBox(self.layout, "Scale Time:", value=self.getOption("scaleTime"), float=True)
        self.linkOption("scaleTime", self.input_scale2)

        self.addOption(key="colormap", display_name="Colormap", default="None", value_type="string",
                       tooltip="The colormap to use for the kymograph.")
        maps = ["None"]
        maps.extend(plt.colormaps())
        self.input_colormap = AddQComboBox(self.layout, "Colormap:", selectedValue=self.getOption("colormap"), values=maps)
        self.input_colormap.setEditable(True)
        self.linkOption("colormap", self.input_colormap)

        self.tableWidget = QtWidgets.QTableWidget(0, 1, self)
        self.layout.addWidget(self.tableWidget)
        self.row_headers = ["Line Length"]
        self.tableWidget.setHorizontalHeaderLabels(self.row_headers)
        self.tableWidget.setMinimumHeight(180)
        self.setMinimumWidth(500)
        self.tableWidget.setCurrentCell(0, 0)

        self.my_type = self.db.setMarkerType("kymograph", "#ef7fff", self.db.TYPE_Line)
        self.my_type2 = self.db.setMarkerType("kymograph_end", "#df00ff", self.db.TYPE_Normal)
        self.cp.reloadTypes()

        self.plot = MatplotlibWidget(self)
        self.layout.addWidget(self.plot)
        self.layout.addWidget(NavigationToolbar(self.plot, self))

        self.tableWidget.cellClicked.connect(self.cellSelected)

        layout = QtWidgets.QHBoxLayout()
        self.button_export = QtWidgets.QPushButton("Export")
        self.button_export.clicked.connect(self.export)
        layout.addWidget(self.button_export)
        self.button_export2 = QtWidgets.QPushButton("Export All")
        self.button_export2.clicked.connect(self.export2)
        layout.addWidget(self.button_export2)
        self.layout.addLayout(layout)

        self.progressbar = QtWidgets.QProgressBar()
        self.layout.addWidget(self.progressbar)

        self.updateTable()
        self.selected = None

        self.signal_update_plot.connect(self.updatePlotImage)
        self.signal_plot_finished.connect(self.plotFinishedEvent)

    def cellSelected(self, row, column):
        self.selected = row
        self.updatePlot()

    def setTableText(self, row, column, text):
        if column == -1:
            item = self.tableWidget.verticalHeaderItem(row)
            if item is None:
                item = QtWidgets.QTableWidgetItem("")
                self.tableWidget.setVerticalHeaderItem(row, item)
        else:
            item = self.tableWidget.item(row, column)
            if item is None:
                item = QtWidgets.QTableWidgetItem("")
                self.tableWidget.setItem(row, column, item)
                if column == 2:
                    item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(str(text))

    def updateTable(self):
        self.updateing = True
        bars = self.db.getLines(type=self.my_type)
        self.bars = [bar for bar in bars]
        self.bar_dict = {}
        self.tableWidget.setRowCount(bars.count())
        self.last_image_id = None
        for idx, bar in enumerate(bars):
            self.updateRow(idx)
            self.bar_dict[bar.id] = idx
        self.updateing = False

    def updateRow(self, idx):
        bar = self.bars[idx]
        self.setTableText(idx, -1, "#%d" % bar.id)
        self.setTableText(idx, 0, bar.length())

    def getLine(self, image, line, height):
        x1 = np.min([line.x1, line.x2])
        x2 = np.max([line.x1, line.x2])
        y1 = np.min([line.y1, line.y2])
        y2 = np.max([line.y1, line.y2])
        w = x2 - x1
        h = y2 - y1
        length = np.sqrt(w ** 2 + h ** 2)
        data = []

        for i in np.linspace(0, 1, np.ceil(length)):
            x = x1 + w * i
            y = y1 + h * i
            xp = x - np.floor(x)
            yp = y - np.floor(y)
            v = np.dot(np.array([[1 - yp, yp]]).T, np.array([[1 - xp, xp]]))
            if len(image.shape) == 3:
                data.append(np.sum(image[int(y):int(y) + 2, int(x):int(x) + 2, :] * v[:, :, None], axis=(0, 1), dtype=image.dtype))
            else:
                data.append(np.sum(image[int(y):int(y) + 2, int(x):int(x) + 2] * v, dtype=image.dtype))

        return np.array(data)

    def updatePlot(self):
        if self.selected is None:
            return
        self.n = -1
        self.terminate()

        self.bar = self.bars[self.selected]
        self.plot.axes.clear()
        image_start = self.bar.image
        self.h = 1
        if int(self.input_count.value()) == 0:
            print("here")
            image = self.bar.image.sort_index
            end_marker = self.db.table_marker.select().where(self.db.table_marker.type==self.my_type2).join(self.db.table_image).where(self.db.table_image.sort_index > image).limit(1)
            self.n = end_marker[0].image.sort_index - image
        else:
            print(int(self.input_count.value()), int(self.input_count.value()) == 0)
            self.n = int(self.input_count.value())
        self.progressbar.setRange(0, self.n-1)
        data = image_start.data
        line_cut = self.getLine(data, self.bar, self.h)
        self.w = line_cut.shape[0]

        if len(data.shape) == 3:
            self.current_data = np.zeros((self.h * self.n, self.w, data.shape[2]), dtype=line_cut.dtype)
        else:
            self.current_data = np.zeros((self.h * self.n, self.w), dtype=line_cut.dtype)
        self.current_data[0, :] = line_cut

        extent = (0, self.current_data.shape[1]*self.input_scale1.value(), 0, self.current_data.shape[0]*self.input_scale2.value())
        if self.input_colormap.currentText () != "None":
            if len(self.current_data.shape) == 3:
                data_gray = np.dot(self.current_data[..., :3], [0.299, 0.587, 0.114])
                self.image_plot = self.plot.axes.imshow(data_gray, cmap=self.input_colormap.currentText(),
                                                        extent=extent)
            else:
                self.image_plot = self.plot.axes.imshow(self.current_data, cmap=self.input_colormap.currentText (), extent=extent)
        else:
            self.image_plot = self.plot.axes.imshow(self.current_data, cmap="gray", extent=extent)
        self.plot.axes.set_xlabel(u"distance (µm)")
        self.plot.axes.set_ylabel("time (s)")
        self.plot.figure.tight_layout()
        self.plot.draw()

        self.last_update = time.time()

        self.run_threaded(image_start.sort_index+1)

    def updatePlotImage(self):
        t = time.time()
        if t-self.last_update < 0.1 and self.index < self.n-1:
            return
        self.last_update = t
        if self.image_plot:
            if len(self.current_data.shape) == 3 and self.input_colormap.currentText() != "None":
                data_gray = np.dot(self.current_data[..., :3], [0.299, 0.587, 0.114])
                self.image_plot.set_data(data_gray)
            else:
                self.image_plot.set_data(self.current_data)
        self.plot.draw()
        self.progressbar.setValue(self.index)

    def run(self, start_frame=0):
        for index, image in enumerate(self.db.getImageIterator(start_frame)):
            self.index = index
            line_cut = self.getLine(image.data, self.bar, self.h)
            self.current_data[index, :] = line_cut
            self.signal_update_plot.emit()
            if index >= self.n - 1 or self.cp.stop:
                self.signal_plot_finished.emit()
                break

    def plotFinishedEvent(self):
        if self.exporting:
            self.export()
            self.exporting_index += 1
            if self.exporting_index < len(self.bars):
                self.cellSelected(self.exporting_index, 0)
            else:
                self.exporting_index = 0
                self.exporting = False

    def calculateBar(self, data):
        if data.shape[0] == 0 or data.shape[1] == 0:
            return
        return np.sum(data)-np.min(data)

    def export(self):
        # convert to grayscale if it is a color image that should be saved with a colormap
        if len(self.current_data.shape) == 3 and self.input_colormap.currentText() != "None":
            data_gray = np.dot(self.current_data[..., :3], [0.299, 0.587, 0.114])
        # if not just keep it
        else:
            data_gray = self.current_data
        # save the data as a numpy file
        np.savez("kymopgraph%d.npz" % self.bar.id, data_gray)
        # get the colormap
        cmap = self.input_colormap.currentText()
        if cmap == "None":
            cmap = "gray"
        # save the kymograph as an image
        plt.imsave("kymopgraph%d.png" % self.bar.id, data_gray, cmap=cmap)
        # print a log in the console
        print("Exported", "kymopgraph%d.npz" % self.bar.id)

    def export2(self):
        self.exporting_index = 0
        self.exporting = True
        self.cellSelected(self.exporting_index, 0)

    def markerMoveEvent(self, marker):
        if marker.type == self.my_type:
            row = self.bar_dict[marker.id]
            self.bars[row] = marker
            self.tableWidget.selectRow(row)
            self.updateRow(row)
            self.selected = row
            self.updatePlot()

    def markerAddEvent(self, entry):
        self.updateTable()

    def markerRemoveEvent(self, entry):
        self.updateTable()

    def buttonPressedEvent(self):
        self.show()
