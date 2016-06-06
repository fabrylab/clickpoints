from __future__ import division, print_function
import os, sys, ctypes, platform
import subprocess
import numpy as np
import sip

import qtawesome as qta

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt4 import NavigationToolbar2QT as NavigationToolbar
from matplotlibwidget import MatplotlibWidget
import seaborn as sns
import time
from matplotlib.colors import LinearSegmentedColormap
from threading import Thread
import threading
from qimage2ndarray import array2qimage
import imageio

try:
    from PyQt5 import QtGui, QtCore
    from PyQt5.QtWidgets import QWidget, QTextStream, QGridLayout, QProgressBar
    from PyQt5.QtCore import Qt
except ImportError:
    from PyQt4 import QtGui, QtCore
    from PyQt4.QtGui import QWidget, QApplication, QCursor, QFileDialog, QIcon, QMessageBox, QSizePolicy, QGridLayout, \
        QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QPlainTextEdit, QTableWidget, QHeaderView, \
        QTableWidgetItem, QSpinBox, QTabWidget, QSpacerItem, QProgressBar
    from PyQt4.QtCore import Qt, QTextStream, QFile, QObject, SIGNAL

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
    power2 = int(np.log10(value * 10) // 3)
    if power2 > power:
        value /= 10 ** (power2 * 3)
        return ("%.1f" % value + postfix[power2])[1:]
    value /= 10 ** (power * 3)
    return "%d" % value + postfix[power]

def GetMonthName(month):
    return ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][month]


class queryThread(QtCore.QThread):
    sig = QtCore.pyqtSignal(QtCore.QThread)

    def __init__(self, parent, query):
        super(QtCore.QThread, self).__init__()
        self.parent = parent
        self.query = query

    def run(self):
        self.query.execute()
        self.sig.emit(self)


class Year:
    def __init__(self, device, year, timestamp=None):
        self.device = device
        self.year = year
        self.expanded = False
        self.timestamp = timestamp

class Month:
    def __init__(self, device, year, month, timestamp=None):
        self.device = device
        self.year = year
        self.month = month
        self.expanded = False
        self.timestamp = timestamp

class Day:
    def __init__(self, device, year, month, day, timestamp=None):
        self.device = device
        self.year = year
        self.month = month
        self.day = day
        self.expanded = False
        self.timestamp = timestamp

class DatabaseBrowser(QWidget):
    update_image = QtCore.pyqtSignal()

    def __init__(self):
        QWidget.__init__(self)

        # read local mount lookup table
        if platform.system() == 'Linux':
            try:
                from linuxmountlookup import LinuxMountLookup
                self.smb_targets = [k for k, v in LinuxMountLookup.iteritems()]
                self.smb_mounts = [v for k, v in LinuxMountLookup.iteritems()]
            except:
                raise Exception(
                    "Warning - Linux systems require mounted smb shares - please add translation dictionary to linuxmountlookup.py")

        # widget layout and elements
        self.setMinimumWidth(655)
        self.setMinimumHeight(500)
        self.setGeometry(100, 100, 500, 600)
        self.setWindowTitle("Database Browser")
        self.setWindowIcon(QIcon(QIcon(os.path.join(icon_path, "DatabaseViewer.ico"))))
        self.layout = QVBoxLayout(self)

        # Progress bar
        self.progress_bar = QtGui.QProgressBar()
        self.layout.addWidget(self.progress_bar)

        # Information
        layout = QHBoxLayout()
        self.layout.addLayout(layout)
        self.system_name = QtGui.QLineEdit()
        self.system_name.setDisabled(True)
        layout.addWidget(self.system_name)
        self.device_name = QtGui.QLineEdit()
        self.device_name.setDisabled(True)
        layout.addWidget(self.device_name)
        self.date_start = QtGui.QLineEdit()
        layout.addWidget(self.date_start)
        self.date_end = QtGui.QLineEdit()
        layout.addWidget(self.date_end)

        tree = QtGui.QTreeView()
        self.layout.addWidget(tree)
        model = QtGui.QStandardItemModel(0, 0)

        self.database = DatabaseFiles(config)

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

        tree.setUniformRowHeights(True)
        tree.setHeaderHidden(True)
        tree.setAnimated(True)
        tree.setModel(model)
        tree.expanded.connect(self.TreeExpand)
        tree.clicked.connect(self.TreeSelected)
        self.tree = tree

        self.view = QExtendedGraphicsView()
        self.layout.addWidget(self.view)
        self.pixmap = QtGui.QGraphicsPixmapItem(QtGui.QPixmap(1, 1), self.view.origin)
        self.thread_display = None
        self.update_image.connect(self.UpdateImage)

        #QtCore.QTimer.singleShot(1, self.connectDB)

    def TreeSelected(self, index):
        item = index.model().itemFromIndex(index)
        entry = item.entry
        if isinstance(entry, self.database.SQL_Systems):
            self.system_name.setText(entry.name)
            self.device_name.setText("")
            self.date_start.setText("")
            self.date_end.setText("")
            entry = self.database.SQL_Files.get(system=entry.id)
            self.ImageDisplaySchedule(entry)

        if isinstance(entry, self.database.SQL_Devices):
            self.system_name.setText(entry.system.name)
            self.device_name.setText(entry.name)
            self.date_start.setText("")
            self.date_end.setText("")
            entry = self.database.SQL_Files.get(system=entry.system.id, device=entry.id)
            self.ImageDisplaySchedule(entry)

        if isinstance(entry, Year):
            self.system_name.setText(entry.device.system.name)
            self.device_name.setText(entry.device.name)
            self.date_start.setText("%04d0101" % entry.year)
            self.date_end.setText("%04d0101" % (entry.year+1))
            entry = self.database.SQL_Files.get(system=entry.device.system.id, device=entry.device.id, timestamp=entry.timestamp)
            self.ImageDisplaySchedule(entry)

        if isinstance(entry, Month):
            self.system_name.setText(entry.device.system.name)
            self.device_name.setText(entry.device.name)
            self.date_start.setText("%04d%02d01" % (entry.year, entry.month))
            if entry.month == 12:
                self.date_end.setText("%04d%02d01" % (entry.year + 1, 1))
            else:
                self.date_end.setText("%04d%02d01" % (entry.year, entry.month + 1))
            entry = self.database.SQL_Files.get(system=entry.device.system.id, device=entry.device.id,
                                                timestamp=entry.timestamp)
            self.ImageDisplaySchedule(entry)

        if isinstance(entry, Day):
            self.system_name.setText(entry.device.system.name)
            self.device_name.setText(entry.device.name)
            self.date_start.setText("%04d%02d%02d" % (entry.year, entry.month, entry.day))
            if entry.month == 12 and entry.day == 31:
                self.date_end.setText("%04d%02d%02d" % (entry.year+1, 1, 1))
            elif entry.day == calendar.monthrange(entry.year, entry.month)[1]:
                self.date_end.setText("%04d%02d%02d" % (entry.year, entry.month+1, 1))
            else:
                self.date_end.setText("%04d%02d%02d" % (entry.year, entry.month, entry.day+1))
            entry = self.database.SQL_Files.get(system=entry.device.system.id, device=entry.device.id,
                                                timestamp=entry.timestamp)
            self.ImageDisplaySchedule(entry)

    def ImageDisplaySchedule(self, entry):
        self.thread_display = Thread(target=self.ImageDisplay, args=(entry, ))
        self.thread_display.start()

    def ImageDisplay(self, entry):
        filename = os.path.join(self.database.getPath(entry.path), entry.basename + entry.extension)
        print(filename)
        im = imageio.get_reader("\\\\" + filename).get_data(0)
        self.im = im
        self.update_image.emit()
        print(entry.basename, entry.extension)

    def UpdateImage(self):
        self.pixmap.setPixmap(QtGui.QPixmap(array2qimage(self.im)))
        self.view.setExtend(self.im.shape[1], self.im.shape[0])


    def ExpandSystem(self, index, item, entry):
        item.setIcon(qta.icon('fa.hourglass-o'))
        item.removeRow(0)
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
        entry.expanded = True
        item.setIcon(qta.icon('fa.desktop'))

    def ExpandDevice(self, index, item, entry):
        item.setIcon(qta.icon('fa.hourglass-o'))
        item.removeRow(0)

        query = (self.database.SQL_Files
                 .select((fn.count(self.database.SQL_Files.id) * self.database.SQL_Files.frames).alias('count'),
                         fn.year(self.database.SQL_Files.timestamp).alias('year'), self.database.SQL_Files.timestamp)
                 .where(self.database.SQL_Files.device == entry.id)
                 .group_by(fn.year(self.database.SQL_Files.timestamp)))

        for row in query:
            child = QtGui.QStandardItem("%d (%s)" % (row.year, ShortenNumber(row.count)))
            child.setIcon(qta.icon("fa.calendar"))
            child.setEditable(False)
            child.entry = Year(entry, row.year, row.timestamp)
            item.appendRow(child)

            # add dummy child
            child2 = QtGui.QStandardItem("")
            child2.setEditable(False)
            child.appendRow(child2)
        entry.expanded = True
        item.setIcon(qta.icon('fa.camera'))

    def ExpandYear(self, index, item, entry):
        item.setIcon(qta.icon('fa.hourglass-o'))
        item.removeRow(0)

        query = (self.database.SQL_Files
                 .select((fn.count(self.database.SQL_Files.id) * self.database.SQL_Files.frames).alias('count'),
                         fn.month(self.database.SQL_Files.timestamp).alias('month'), self.database.SQL_Files.timestamp)
                 .where(self.database.SQL_Files.device == entry.device.id,
                        fn.year(self.database.SQL_Files.timestamp) == entry.year)
                 .group_by(fn.month(self.database.SQL_Files.timestamp)))

        for row in query:
            child = QtGui.QStandardItem("%s (%s)" % (GetMonthName(row.month), ShortenNumber(row.count)))
            child.setIcon(qta.icon("fa.calendar-o"))
            child.setEditable(False)
            child.entry = Month(entry.device, entry.year, row.month, row.timestamp)
            item.appendRow(child)

            # add dummy child
            child2 = QtGui.QStandardItem("")
            child2.setEditable(False)
            child.appendRow(child2)
        entry.expanded = True
        item.setIcon(qta.icon('fa.calendar'))

    def ExpandMonth(self, index, item, entry):
        item.setIcon(qta.icon('fa.hourglass-o'))
        item.removeRow(0)

        query = (self.database.SQL_Files
                 .select((fn.count(self.database.SQL_Files.id) * self.database.SQL_Files.frames).alias('count'),
                         fn.day(self.database.SQL_Files.timestamp).alias('day'), self.database.SQL_Files.timestamp)
                 .where(self.database.SQL_Files.device == entry.device.id,
                        fn.year(self.database.SQL_Files.timestamp) == entry.year,
                        fn.month(self.database.SQL_Files.timestamp) == entry.month)
                 .group_by(fn.dayofyear(self.database.SQL_Files.timestamp)))

        for row in query:
            child = QtGui.QStandardItem("%02d. (%s)" % (row.day, ShortenNumber(row.count)))
            child.setIcon(qta.icon("fa.bookmark-o"))
            child.setEditable(False)
            child.entry = Day(entry.device, entry.year, entry.month, row.day, row.timestamp)
            item.appendRow(child)

        entry.expanded = True
        item.setIcon(qta.icon('fa.calendar-o'))

    def TreeExpand(self, index):
        item = index.model().itemFromIndex(index)
        entry = item.entry
        # Expand system with devices
        if isinstance(entry, self.database.SQL_Systems) and entry.expanded is False:
            thread = Thread(target=self.ExpandSystem, args=(index, item, entry))
            thread.daemon = True
            thread.start()

        if isinstance(entry, self.database.SQL_Devices) and entry.expanded is False:
            thread = Thread(target=self.ExpandDevice, args=(index, item, entry))
            thread.daemon = True
            thread.start()

        if isinstance(entry, Year) and entry.expanded is False:
            thread = Thread(target=self.ExpandYear, args=(index, item, entry))
            thread.daemon = True
            thread.start()

        if isinstance(entry, Month) and entry.expanded is False:
            thread = Thread(target=self.ExpandMonth, args=(index, item, entry))
            thread.daemon = True
            thread.start()

    def connectDB(self):
        self.progress_bar.setRange(0, 0)
        print("connecting to database")
        self.database = DatabaseFiles(config)
        time.sleep(1)
        print("...connected")
        self.progress_bar.setRange(0, 100)

if __name__ == '__main__':
    if sys.platform[:3] == 'win':
        myappid = 'fabrybiophysics.databasebrowser'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    app = QApplication(sys.argv)

    window = DatabaseBrowser()
    window.show()
    app.exec_()
