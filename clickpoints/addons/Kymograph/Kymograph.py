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
from matplotlib import pyplot as plt
import time


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
        self.setWindowTitle("Kymograph - ClickPoints")
        self.layout = QtWidgets.QVBoxLayout(self)

        # add some options
        # the frame number for the kymograph
        self.addOption(key="frames", display_name="Frames", default=50, value_type="int",
                       tooltip="How many images to use for the kymograph.")
        self.input_count = AddQSpinBox(self.layout, "Frames:", value=self.getOption("frames"), float=False)
        self.linkOption("frames", self.input_count)

        # the with in pixel of each line
        self.addOption(key="width", display_name="Width", default=1, value_type="int",
                       tooltip="The width of the slice to cut from the image.")
        self.input_width = AddQSpinBox(self.layout, "Width:", value=self.getOption("width"), float=False)
        self.linkOption("width", self.input_width)

        # the length scaling
        self.addOption(key="scaleLength", display_name="Scale Length", default=1, value_type="float",
                       tooltip="What is distance a pixel represents.")
        self.input_scale1 = AddQSpinBox(self.layout, "Scale Length:", value=self.getOption("scaleLength"), float=True)
        self.linkOption("scaleLength", self.input_scale1)

        # the time scaling
        self.addOption(key="scaleTime", display_name="Scale Time", default=1, value_type="float",
                       tooltip="What is the time difference between two images.")
        self.input_scale2 = AddQSpinBox(self.layout, "Scale Time:", value=self.getOption("scaleTime"), float=True)
        self.linkOption("scaleTime", self.input_scale2)

        # the colormap
        self.addOption(key="colormap", display_name="Colormap", default="None", value_type="string",
                       tooltip="The colormap to use for the kymograph.")
        maps = ["None"]
        maps.extend(plt.colormaps())
        self.input_colormap = AddQComboBox(self.layout, "Colormap:", selectedValue=self.getOption("colormap"), values=maps)
        self.input_colormap.setEditable(True)
        self.linkOption("colormap", self.input_colormap)

        # the table listing the line objects
        self.tableWidget = QtWidgets.QTableWidget(0, 1, self)
        self.layout.addWidget(self.tableWidget)
        self.row_headers = ["Line Length"]
        self.tableWidget.setHorizontalHeaderLabels(self.row_headers)
        self.tableWidget.setMinimumHeight(180)
        self.setMinimumWidth(500)
        self.tableWidget.setCurrentCell(0, 0)
        self.tableWidget.cellClicked.connect(self.cellSelected)

        # add kymograph types
        self.my_type = self.db.setMarkerType("kymograph", "#ef7fff", self.db.TYPE_Line, text="#$marker_id")
        self.my_type2 = self.db.setMarkerType("kymograph_end", "#df00ff", self.db.TYPE_Normal)
        self.cp.reloadTypes()

        # add a plot widget
        self.plot = MatplotlibWidget(self)
        self.layout.addWidget(self.plot)
        self.layout.addWidget(NavigationToolbar(self.plot, self))
        self.plot.figure.canvas.mpl_connect('button_press_event', self.button_press_callback)

        # add export buttons
        layout = QtWidgets.QHBoxLayout()
        self.button_export = QtWidgets.QPushButton("Export")
        self.button_export.clicked.connect(self.export)
        layout.addWidget(self.button_export)
        self.button_export2 = QtWidgets.QPushButton("Export All")
        self.button_export2.clicked.connect(self.export2)
        layout.addWidget(self.button_export2)
        self.layout.addLayout(layout)

        # add a progress bar
        self.progressbar = QtWidgets.QProgressBar()
        self.layout.addWidget(self.progressbar)

        # connect slots
        self.signal_update_plot.connect(self.updatePlotImageEvent)
        self.signal_plot_finished.connect(self.plotFinishedEvent)

        # initialize the table
        self.updateTable()
        self.selected = None

    def button_press_callback(self, event):
        # only drag with left mouse button
        if event.button != 1:
            return
        # if the user doesn't have clicked on an axis do nothing
        if event.inaxes is None:
            return
        # get the pixel of the kymograph
        x, y = event.xdata/self.input_scale1.value(), event.ydata/self.h/self.input_scale2.value()
        # jump to the frame in time
        self.cp.jumpToFrame(self.bar.image.sort_index+int(y))
        # and to the xy position
        self.cp.centerOn(*self.getLinePoint(self.bar, x))

    def cellSelected(self, row, column):
        # store the row
        self.selected = row
        # and update the plot
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
        self.updating = True
        bars = self.db.getLines(type=self.my_type)
        self.bars = [bar for bar in bars]
        self.bar_dict = {}
        self.tableWidget.setRowCount(bars.count())
        self.last_image_id = None
        for idx, bar in enumerate(bars):
            self.updateRow(idx)
            self.bar_dict[bar.id] = idx
        self.updating = False

    def updateRow(self, idx):
        bar = self.bars[idx]
        self.setTableText(idx, -1, "#%d" % bar.id)
        self.setTableText(idx, 0, bar.length())

    def getLinePoint(self, line, percentage):
        x1 = line.x1
        x2 = line.x2
        y1 = line.y1
        y2 = line.y2
        if self.mirror:
            y1, y2 = y2, y1
        w = x2 - x1
        h = y2 - y1
        length = np.sqrt(w ** 2 + h ** 2)
        if self.mirror:
            percentage = length - percentage
        return x1 + w * percentage/length, y1 + h * percentage/length

    def getLine(self, image, line, height, image_entry=None):
        x1 = line.x1
        x2 = line.x2
        y1 = line.y1
        y2 = line.y2
        if self.mirror:
            y1, y2 = y2, y1
        w = x2 - x1
        h = y2 - y1
        length = np.sqrt(w ** 2 + h ** 2)
        w2 = h/length
        h2 = -w/length

        if image_entry and image_entry.offset:
            offx, offy = image_entry.offset.x, image_entry.offset.y
        else:
            offx, offy = 0, 0
        x1 -= offx - self.start_offx
        y1 -= offy - self.start_offy

        datas = []
        for j in np.arange(0, self.h)-self.h/2.+0.5:
            data = []
            for i in np.linspace(0, 1, np.ceil(length)):
                x = x1 + w * i + w2 * j
                y = y1 + h * i + h2 * j
                xp = x - np.floor(x)
                yp = y - np.floor(y)
                v = np.dot(np.array([[1 - yp, yp]]).T, np.array([[1 - xp, xp]]))
                if len(image.shape) == 3:
                    data.append(np.sum(image[int(y):int(y) + 2, int(x):int(x) + 2, :] * v[:, :, None], axis=(0, 1), dtype=image.dtype))
                else:
                    data.append(np.sum(image[int(y):int(y) + 2, int(x):int(x) + 2] * v, dtype=image.dtype))
            datas.append(data)

        if self.mirror:
            return np.array(datas)[:, ::-1]
        return np.array(datas)[::-1, :]

    def updatePlot(self):
        if self.selected is None:
            return
        self.n = -1
        self.terminate()
        self.mirror = False
        if self.db.getOption("rotation") == 180:
            self.mirror = True

        self.bar = self.bars[self.selected]
        self.plot.axes.clear()
        image_start = self.bar.image
        if image_start.offset:
            self.start_offx, self.start_offy = image_start.offset.x, image_start.offset.y
        else:
            self.start_offx, self.start_offy = 0, 0
        self.h = self.input_width.value()
        if int(self.input_count.value()) == 0:
            image = self.bar.image.sort_index
            end_marker = self.db.table_marker.select().where(self.db.table_marker.type==self.my_type2).join(self.db.table_image).where(self.db.table_image.sort_index > image).limit(1)
            self.n = end_marker[0].image.sort_index - image
        else:
            self.n = int(self.input_count.value())
        self.progressbar.setRange(0, self.n-1)
        data = image_start.data
        line_cut = self.getLine(data, self.bar, self.h, image_start)
        self.w = line_cut.shape[1]

        if len(data.shape) == 3:
            self.current_data = np.zeros((self.h * self.n, self.w, data.shape[2]), dtype=line_cut.dtype)
        else:
            self.current_data = np.zeros((self.h * self.n, self.w), dtype=line_cut.dtype)
        self.current_data[0:self.h, :] = line_cut

        extent = (0, self.current_data.shape[1]*self.input_scale1.value(), self.current_data.shape[0]*self.input_scale2.value(), 0)
        if self.input_colormap.currentText() != "None":
            if len(self.current_data.shape) == 3:
                data_gray = np.dot(self.current_data[..., :3], [0.299, 0.587, 0.114])
                self.image_plot = self.plot.axes.imshow(data_gray, cmap=self.input_colormap.currentText(), extent=extent)
            else:
                self.image_plot = self.plot.axes.imshow(self.current_data, cmap=self.input_colormap.currentText(), extent=extent)
        else:
            self.image_plot = self.plot.axes.imshow(self.current_data, cmap="gray", extent=extent)
        self.plot.axes.set_xlabel(u"distance (µm)")
        self.plot.axes.set_ylabel("time (s)")
        self.plot.figure.tight_layout()
        self.plot.draw()

        self.last_update = time.time()

        self.run_threaded(image_start.sort_index+1, self.run)

    def updatePlotImageEvent(self):
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
            index += 1
            self.index = index
            line_cut = self.getLine(image.data, self.bar, self.h, image)
            self.current_data[index*self.h:(index+1)*self.h, :] = line_cut
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

    def export(self):
        filename = "kymograph%d.%s"
        # convert to grayscale if it is a color image that should be saved with a colormap
        if len(self.current_data.shape) == 3 and self.input_colormap.currentText() != "None":
            data_gray = np.dot(self.current_data[..., :3], [0.299, 0.587, 0.114])
        # if not just keep it
        else:
            data_gray = self.current_data
        # save the data as a numpy file
        np.savez(filename % (self.bar.id, "npz"), data_gray)
        # get the colormap
        cmap = self.input_colormap.currentText()
        if cmap == "None":
            cmap = "gray"
        # save the kymograph as an image
        plt.imsave(filename % (self.bar.id, "png"), data_gray, cmap=cmap)
        # print a log in the console
        print("Exported", filename % (self.bar.id, "npz"))

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
