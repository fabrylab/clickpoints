#!/usr/bin/env python
# -*- coding: utf-8 -*-
# databaseBrowser2.py

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
import os, sys, ctypes, platform
import subprocess
import numpy as np
import sip

import qtawesome as qta

import time
from threading import Thread
import threading
from qimage2ndarray import array2qimage
import imageio

from qtpy import QtGui, QtCore, QtWidgets

from peewee import fn, SQL
import re

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar

from databaseFiles import DatabaseFiles

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from includes import QExtendedGraphicsView

# from databaseAnnotation import DatabaseAnnotation, config
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "modules"))
from AnnotationHandler import pyQtTagSelector

icon_path = os.path.join(os.path.dirname(__file__), "..", "icons")

from Config import Config

config = Config('sql.cfg').sql


def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = int(sourcedate.year + month / 12)
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime(year, month, day)


def ShortenNumber(value):
    if value == 0 or np.isnan(value):
        return ""
    if value < 1:
        return "%d" % value
    postfix = ["", "k", "M", "G", "T", "P", "E", "Z", "Y"]
    power = int(np.log10(value) // 3)
    #power2 = int(np.log10(value * 10) // 3)
    #if power2 > power:
    #    value /= 10 ** (power2 * 3)
    #    return ("%.1f" % value + postfix[power2])[1:]
    value /= 10 ** (power * 3)
    return "%d" % value + postfix[power]

def GetMonthName(month):
    return ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][month]


class queryThread(QtCore.QThread):
    sig = QtCore.Signal(QtCore.QThread)

    def __init__(self, parent, query):
        super(QtCore.QThread, self).__init__()
        self.parent = parent
        self.query = query

    def run(self):
        self.query.execute()
        self.sig.emit(self)


class Year:
    def __init__(self, device, year, timestamp=None, count=1):
        self.device = device
        self.year = year
        self.expanded = False
        self.timestamp = timestamp
        self.count = count

class Month:
    def __init__(self, device, year, month, timestamp=None, count=1):
        self.device = device
        self.year = year
        self.month = month
        self.expanded = False
        self.timestamp = timestamp
        self.count = count

class Day:
    def __init__(self, device, year, month, day, timestamp=None, count=1):
        self.device = device
        self.year = year
        self.month = month
        self.day = day
        self.expanded = False
        self.timestamp = timestamp
        self.count = count

class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self):
        super(StoppableThread, self).__init__()
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

    def start(self, window, entry):
        self.window = window
        self.entry = entry
        super(StoppableThread, self).start()

    def run(self):
        try:
            self.entry = self.entry[0]
        except TypeError:
            pass
        filename = os.path.join(window.database.getPath(self.entry.path), self.entry.basename + self.entry.extension)
        if self.stopped():
            return
        im = imageio.get_reader("\\\\" + filename).get_data(0)
        if self.stopped():
            return
        window.im = im
        window.qimage = array2qimage(im)
        window.time_text = str(self.entry.timestamp)
        window.update_image.emit()

def OpenClickPoints(query, database):
    counter = 0
    with open("files.txt", "w") as fp:
        print("Wrinting the file")
        for item in query:
            print(counter, item)
            # get timestamp
            timest = item.timestamp
            # get path
            file_path = "\\\\" + os.path.join(database.getPath(item.path), item.basename + item.extension)
            # check for OS, if linux replace smb_ip_paths with local mount_path
            """
            if platform.system() == 'Linux':
                for id, smb_target in enumerate(self.parent.smb_targets):
                    if file_path.startswith(smb_target):
                        file_path = file_path.replace(smb_target, self.parent.smb_mounts[id])
                        break
                else:
                    print("No smb path translation found for", file_path)
                    pass
            """

            fp.write(file_path + " " +
                     timest.strftime('%Y%m%d-%H%M%S') + " " + str(item.id) + " " + str(item.annotation_id) + "\n")
            counter += 1

    if counter is None:
        return
    if counter == 0:
        QtWidgets.QMessageBox.question(None, 'Warning', 'Your selection doesn\'t contain any images.', QMessageBox.Ok)
        return
    print("Selected %d images." % counter)
    if platform.system() == 'Windows':
        subprocess.Popen(r"python.exe ..\ClickPoints.py -srcpath=files.txt")
    elif platform.system() == 'Linux':
        subprocess.Popen(['clickpoints', 'files.txt'], shell=False)


class DatabaseBrowser(QtWidgets.QWidget):
    update_image = QtCore.Signal()

    def __init__(self):
        QtWidgets.QWidget.__init__(self)

        # read local mount lookup table
        if platform.system() == 'Linux':
            try:
                from linuxmountlookup import LinuxMountLookup
                self.smb_targets = [k for k, v in LinuxMountLookup.iteritems()]
                self.smb_mounts = [v for k, v in LinuxMountLookup.iteritems()]
            except:
                raise Exception(
                    "Warning - Linux systems require mounted smb shares - please add translation dictionary to linuxmountlookup.py")

        # open the database
        self.database = DatabaseFiles(config)

        # widget layout and elements
        self.setMinimumWidth(900)
        self.setMinimumHeight(500)
        self.setGeometry(100, 100, 500, 600)
        self.setWindowTitle("Database Browser")
        self.setWindowIcon(QtGui.QIcon(QtGui.QIcon(os.path.join(icon_path, "DatabaseViewer.ico"))))

        # The global layout has two parts
        self.global_layout = QtWidgets.QHBoxLayout(self)
        self.layout = QtWidgets.QVBoxLayout()  # the left part for the tree view
        self.global_layout.addLayout(self.layout)
        self.layout2 = QtWidgets.QVBoxLayout()  # and the right part for the image display
        self.global_layout.addLayout(self.layout2)

        # System, device, start and end display
        layout = QtWidgets.QHBoxLayout()
        self.layout.addLayout(layout)
        self.system_name = QtWidgets.QLineEdit()
        self.system_name.setDisabled(True)
        layout.addWidget(self.system_name)
        self.device_name = QtWidgets.QLineEdit()
        self.device_name.setDisabled(True)
        layout.addWidget(self.device_name)
        layout = QtWidgets.QHBoxLayout()
        self.layout.addLayout(layout)
        self.date_start = QtWidgets.QLineEdit()
        layout.addWidget(self.date_start)
        self.date_end = QtWidgets.QLineEdit()
        layout.addWidget(self.date_end)

        # Open button
        layout = QtWidgets.QHBoxLayout()
        self.layout.addLayout(layout)
        self.button_open = QtWidgets.QPushButton("Open")
        self.button_open.clicked.connect(self.Open)
        layout.addWidget(self.button_open)

        # the tree view
        tree = QtWidgets.QTreeView()
        self.layout.addWidget(tree)
        model = QtGui.QStandardItemModel(0, 0)

        # add the systems as children for the three
        self.systems = self.database.SQL_Systems.select()
        for row, system in enumerate(self.systems):
            item = QtGui.QStandardItem(system.name)
            item.setIcon(qta.icon("fa.desktop"))
            item.setEditable(False)
            item.entry = system
            system.expanded = False

            # add dummy child
            child = QtGui.QStandardItem()
            child.setEditable(False)
            item.appendRow(child)
            model.setItem(row, 0, item)

        # some settings for the tree
        tree.setUniformRowHeights(True)
        tree.setHeaderHidden(True)
        tree.setAnimated(True)
        tree.setModel(model)
        tree.expanded.connect(self.TreeExpand)
        tree.selectionModel().selectionChanged.connect(lambda x, y: self.TreeSelected(x))
        self.tree = tree

        # the image display part
        # has a label
        self.time_label = QtWidgets.QLabel()
        font = QtGui.QFont()
        font.setPointSize(16)
        self.time_label.setFont(font)
        self.layout2.addWidget(self.time_label)

        # a GraphicsView
        self.view = QExtendedGraphicsView()
        self.view.setMinimumWidth(600)
        self.layout2.addWidget(self.view)
        self.pixmap = QtWidgets.QGraphicsPixmapItem(QtGui.QPixmap(1, 1), self.view.origin)
        self.thread_display = None
        self.update_image.connect(self.UpdateImage)

        # and a slider
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.layout2.addWidget(self.slider)
        self.slider.sliderReleased.connect(self.SliderChanged)

    def Open(self):
        # open all files between start and end in ClickPoints
        start_time = datetime.strptime(str(self.date_start.text()), '%Y-%m-%d %H:%M:%S')
        end_time = datetime.strptime(str(self.date_end.text()), '%Y-%m-%d %H:%M:%S')
        query = (self.database.SQL_Files.select()
                 .where(self.database.SQL_Files.device == self.selected_entry.device.id)
                 .where(self.database.SQL_Files.timestamp >= start_time)
                 .where(self.database.SQL_Files.timestamp <= end_time)
                 .order_by(self.database.SQL_Files.timestamp)
                 )
        OpenClickPoints(query, self.database)

    def TreeSelected(self, index):
        # get the selected entry and store it
        print(type(index))
        if isinstance(index, QtCore.QItemSelection):
            index = index.indexes()[0]
        item = index.model().itemFromIndex(index)
        entry = item.entry
        self.selected_entry = entry

        # Display system, device, start and end data, as well as an image
        if isinstance(entry, self.database.SQL_Systems):
            self.system_name.setText(entry.name)
            self.device_name.setText("")
            self.date_start.setText("")
            self.date_end.setText("")
            entry = self.database.SQL_Files.get(system=entry.id)
            self.ImageDisplaySchedule(entry)
            self.slider.setRange(0, 0)
            self.slider.setDisabled(True)

        if isinstance(entry, self.database.SQL_Devices):
            self.system_name.setText(entry.system.name)
            self.device_name.setText(entry.name)
            self.date_start.setText("")
            self.date_end.setText("")
            entry = self.database.SQL_Files.get(system=entry.system.id, device=entry.id)
            self.ImageDisplaySchedule(entry)
            self.slider.setRange(0, 0)
            self.slider.setDisabled(True)

        if isinstance(entry, Year):
            self.system_name.setText(entry.device.system.name)
            self.device_name.setText(entry.device.name)
            self.date_start.setText("%04d-01-01 00:00:00" % entry.year)
            self.date_end.setText("%04d-01-01 00:00:00" % (entry.year+1))
            self.slider.setSliderPosition(0)
            self.slider.setRange(0, entry.count)
            self.slider.setDisabled(False)
            entry = self.database.SQL_Files.get(system=entry.device.system.id, device=entry.device.id, timestamp=entry.timestamp)
            self.ImageDisplaySchedule(entry)

        if isinstance(entry, Month):
            self.system_name.setText(entry.device.system.name)
            self.device_name.setText(entry.device.name)
            self.date_start.setText("%04d-%02d-01 00:00:00" % (entry.year, entry.month))
            if entry.month == 12:
                self.date_end.setText("%04d-%02d-01 00:00:00" % (entry.year + 1, 1))
            else:
                self.date_end.setText("%04d-%02d-01 00:00:00" % (entry.year, entry.month + 1))
            self.slider.setSliderPosition(0)
            self.slider.setRange(0, entry.count)
            self.slider.setDisabled(False)
            entry = self.database.SQL_Files.get(system=entry.device.system.id, device=entry.device.id,
                                                timestamp=entry.timestamp)
            self.ImageDisplaySchedule(entry)

        if isinstance(entry, Day):
            self.system_name.setText(entry.device.system.name)
            self.device_name.setText(entry.device.name)
            self.date_start.setText("%04d-%02d-%02d 00:00:00" % (entry.year, entry.month, entry.day))
            if entry.month == 12 and entry.day == 31:
                self.date_end.setText("%04d-%02d-%02d 00:00:00" % (entry.year+1, 1, 1))
            elif entry.day == calendar.monthrange(entry.year, entry.month)[1]:
                self.date_end.setText("%04d-%02d-%02d 00:00:00" % (entry.year, entry.month+1, 1))
            else:
                self.date_end.setText("%04d-%02d-%02d 00:00:00" % (entry.year, entry.month, entry.day+1))
            self.slider.setSliderPosition(0)
            self.slider.setRange(0, entry.count)
            self.slider.setDisabled(False)
            entry = self.database.SQL_Files.get(system=entry.device.system.id, device=entry.device.id,
                                                timestamp=entry.timestamp)
            self.ImageDisplaySchedule(entry)

    def SliderChanged(self):
        # Get the position on the slider the user has just dropped
        index = self.slider.sliderPosition()

        # Get one image from the year
        if isinstance(self.selected_entry, Year):
            query = (self.database.SQL_Files.select()
                     .where(self.database.SQL_Files.system == self.selected_entry.device.system.id)
                     .where(self.database.SQL_Files.device == self.selected_entry.device.id)
                     .where(fn.year(self.database.SQL_Files.timestamp) == self.selected_entry.year)
                     .limit(1).offset(index)
                     )
            self.ImageDisplaySchedule(query)

        # Get one image from the month
        if isinstance(self.selected_entry, Month):
            query = (self.database.SQL_Files.select()
                     .where(self.database.SQL_Files.system == self.selected_entry.device.system.id)
                     .where(self.database.SQL_Files.device == self.selected_entry.device.id)
                     .where(fn.year(self.database.SQL_Files.timestamp) == self.selected_entry.year)
                     .where(fn.month(self.database.SQL_Files.timestamp) == self.selected_entry.month)
                     .limit(1).offset(index)
                     )
            self.ImageDisplaySchedule(query)

        # Get one image from the day
        if isinstance(self.selected_entry, Day):
            query = (self.database.SQL_Files.select()
                     .where(self.database.SQL_Files.system == self.selected_entry.device.system.id)
                     .where(self.database.SQL_Files.device == self.selected_entry.device.id)
                     .where(fn.year(self.database.SQL_Files.timestamp) == self.selected_entry.year)
                     .where(fn.month(self.database.SQL_Files.timestamp) == self.selected_entry.month)
                     .where(fn.day(self.database.SQL_Files.timestamp) == self.selected_entry.day)
                     .limit(1).offset(index)
                     )
            self.ImageDisplaySchedule(query)

    def ImageDisplaySchedule(self, entry):
        # Stop a running thread which tries to display an image
        if self.thread_display is not None:
            self.thread_display.stop()
        # Load and read the image from a separate thread
        self.thread_display = StoppableThread()
        self.thread_display.start(self, entry)

    def UpdateImage(self):
        # Update pixmap, extend and text
        self.pixmap.setPixmap(QtGui.QPixmap(self.qimage))
        self.view.setExtend(self.im.shape[1], self.im.shape[0])
        self.time_label.setText(self.time_text)

    def ExpandSystem(self, index, item, entry):
        # change icon to hourglass during waiting
        item.setIcon(qta.icon('fa.hourglass-o'))
        # remove the dummy child
        item.removeRow(0)

        # add the devices as children (implies a query)
        for device in entry.devices():
            child = QtGui.QStandardItem(device.name)
            child.setIcon(qta.icon("fa.camera"))
            child.setEditable(False)
            child.entry = device
            device.expanded = False
            item.appendRow(child)

            # add dummy child
            child2 = QtGui.QStandardItem("")
            child2.setEditable(False)
            child.appendRow(child2)

        # mark the entry as expanded and rest the icon
        entry.expanded = True
        item.setIcon(qta.icon('fa.desktop'))

    def ExpandDevice(self, index, item, entry):
        # change icon to hourglass during waiting
        item.setIcon(qta.icon('fa.hourglass-o'))
        # remove the dummy child
        item.removeRow(0)

        # query for the years
        query = (self.database.SQL_Files
                 .select((fn.count(self.database.SQL_Files.id) * self.database.SQL_Files.frames).alias('count'),
                         fn.count(self.database.SQL_Files.id).alias('count1'),
                         fn.year(self.database.SQL_Files.timestamp).alias('year'), self.database.SQL_Files.timestamp)
                 .where(self.database.SQL_Files.device == entry.id)
                 .group_by(fn.year(self.database.SQL_Files.timestamp)))

        # add the years as children
        for row in query:
            child = QtGui.QStandardItem("%d (%s)" % (row.year, ShortenNumber(row.count)))
            child.setIcon(qta.icon("fa.calendar"))
            child.setEditable(False)
            child.entry = Year(entry, row.year, row.timestamp, row.count1)
            item.appendRow(child)

            # add dummy child
            child2 = QtGui.QStandardItem("")
            child2.setEditable(False)
            child.appendRow(child2)

        # mark the entry as expanded and rest the icon
        entry.expanded = True
        item.setIcon(qta.icon('fa.camera'))

    def ExpandYear(self, index, item, entry):
        # change icon to hourglass during waiting
        item.setIcon(qta.icon('fa.hourglass-o'))
        # remove the dummy child
        item.removeRow(0)

        # query for the months
        query = (self.database.SQL_Files
                 .select((fn.count(self.database.SQL_Files.id) * self.database.SQL_Files.frames).alias('count'),
                         fn.count(self.database.SQL_Files.id).alias('count1'),
                         fn.month(self.database.SQL_Files.timestamp).alias('month'), self.database.SQL_Files.timestamp)
                 .where(self.database.SQL_Files.device == entry.device.id,
                        fn.year(self.database.SQL_Files.timestamp) == entry.year)
                 .group_by(fn.month(self.database.SQL_Files.timestamp)))

        # add the months as children
        for row in query:
            child = QtGui.QStandardItem("%s (%s)" % (GetMonthName(row.month-1), ShortenNumber(row.count)))
            child.setIcon(qta.icon("fa.calendar-o"))
            child.setEditable(False)
            child.entry = Month(entry.device, entry.year, row.month, row.timestamp, row.count1)
            item.appendRow(child)

            # add dummy child
            child2 = QtGui.QStandardItem("")
            child2.setEditable(False)
            child.appendRow(child2)

        # mark the entry as expanded and rest the icon
        entry.expanded = True
        item.setIcon(qta.icon('fa.calendar'))

    def ExpandMonth(self, index, item, entry):
        # change icon to hourglass during waiting
        item.setIcon(qta.icon('fa.hourglass-o'))
        # remove the dummy child
        item.removeRow(0)

        # query for the days
        query = (self.database.SQL_Files
                 .select((fn.count(self.database.SQL_Files.id) * self.database.SQL_Files.frames).alias('count'),
                         fn.count(self.database.SQL_Files.id).alias('count1'),
                         fn.day(self.database.SQL_Files.timestamp).alias('day'), self.database.SQL_Files.timestamp)
                 .where(self.database.SQL_Files.device == entry.device.id,
                        fn.year(self.database.SQL_Files.timestamp) == entry.year,
                        fn.month(self.database.SQL_Files.timestamp) == entry.month)
                 .group_by(fn.dayofyear(self.database.SQL_Files.timestamp)))

        # add the days as children
        for row in query:
            child = QtGui.QStandardItem("%02d. (%s)" % (row.day, ShortenNumber(row.count)))
            child.setIcon(qta.icon("fa.bookmark-o"))
            child.setEditable(False)
            child.entry = Day(entry.device, entry.year, entry.month, row.day, row.timestamp, row.count1)
            item.appendRow(child)

        # mark the entry as expanded and rest the icon
        entry.expanded = True
        item.setIcon(qta.icon('fa.calendar-o'))

    def TreeExpand(self, index):
        # Get item and entry
        item = index.model().itemFromIndex(index)
        entry = item.entry
        thread = None

        # Expand system with devices
        if isinstance(entry, self.database.SQL_Systems) and entry.expanded is False:
            thread = Thread(target=self.ExpandSystem, args=(index, item, entry))

        # Expand device with years
        if isinstance(entry, self.database.SQL_Devices) and entry.expanded is False:
            thread = Thread(target=self.ExpandDevice, args=(index, item, entry))

        # Expand year with months
        if isinstance(entry, Year) and entry.expanded is False:
            thread = Thread(target=self.ExpandYear, args=(index, item, entry))

        # Expand month with days
        if isinstance(entry, Month) and entry.expanded is False:
            thread = Thread(target=self.ExpandMonth, args=(index, item, entry))

        # Start thread as daemonic
        if thread:
            thread.setDaemon(True)
            thread.start()

    def connectDB(self):
        self.progress_bar.setRange(0, 0)
        print("connecting to database")
        self.database = DatabaseFiles(config)
        time.sleep(1)
        print("...connected")
        self.progress_bar.setRange(0, 100)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_F:
            # @key F: fit image to view
            self.view.fitInView()

        # @key R: rotate the image
        if event.key() == QtCore.Qt.Key_R:
            self.view.rotate(90)

        if event.key() == QtCore.Qt.Key_Escape:
            # @key Escape: close window
            self.close()

if __name__ == '__main__':
    if sys.platform[:3] == 'win':
        myappid = 'fabrybiophysics.databasebrowser'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    app = QtWidgets.QApplication(sys.argv)

    window = DatabaseBrowser()
    window.show()
    app.exec_()
