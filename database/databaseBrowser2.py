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
    #power2 = int(np.log10(value * 10) // 3)
    #if power2 > power:
    #    value /= 10 ** (power2 * 3)
    #    return ("%.1f" % value + postfix[power2])[1:]
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
        QMessageBox.question(None, 'Warning', 'Your selection doesn\'t contain any images.', QMessageBox.Ok)
        return
    print("Selected %d images." % counter)
    if platform.system() == 'Windows':
        subprocess.Popen(r"python.exe ..\ClickPoints.py -srcpath=files.txt")
    elif platform.system() == 'Linux':
        subprocess.Popen(['clickpoints', 'files.txt'], shell=False)


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
        self.setMinimumWidth(900)
        self.setMinimumHeight(500)
        self.setGeometry(100, 100, 500, 600)
        self.setWindowTitle("Database Browser")
        self.setWindowIcon(QIcon(QIcon(os.path.join(icon_path, "DatabaseViewer.ico"))))
        self.global_layout = QHBoxLayout(self)
        self.layout = QVBoxLayout()
        self.global_layout.addLayout(self.layout)
        self.layout2 = QVBoxLayout()
        self.global_layout.addLayout(self.layout2)

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
        layout = QHBoxLayout()
        self.layout.addLayout(layout)
        self.date_start = QtGui.QLineEdit()
        layout.addWidget(self.date_start)
        self.date_end = QtGui.QLineEdit()
        layout.addWidget(self.date_end)

        layout = QHBoxLayout()
        self.layout.addLayout(layout)
        self.button_open = QtGui.QPushButton("Open")
        self.button_open.clicked.connect(self.Open)
        layout.addWidget(self.button_open)

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
        #tree.clicked.connect(self.TreeSelected)
        tree.selectionModel().selectionChanged.connect(lambda x, y: self.TreeSelected(x))
        self.tree = tree
        #self.tree.setMaximumWidth(200)

        self.time_label = QtGui.QLabel()
        font = QtGui.QFont()
        font.setPointSize(16)
        self.time_label.setFont(font)
        self.layout2.addWidget(self.time_label)

        self.view = QExtendedGraphicsView()
        self.view.setMinimumWidth(600)
        self.layout2.addWidget(self.view)
        self.pixmap = QtGui.QGraphicsPixmapItem(QtGui.QPixmap(1, 1), self.view.origin)
        self.thread_display = None
        self.update_image.connect(self.UpdateImage)

        self.slider = QtGui.QSlider(QtCore.Qt.Horizontal)
        self.layout2.addWidget(self.slider)
        self.slider.sliderReleased.connect(self.SliderChanged)

        #QtCore.QTimer.singleShot(1, self.connectDB)

    def Open(self):
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
        if isinstance(index, QtGui.QItemSelection):
            index = index.indexes()[0]
        item = index.model().itemFromIndex(index)
        entry = item.entry
        self.selected_entry = entry
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
        index = self.slider.sliderPosition()
        if isinstance(self.selected_entry, Year):
            query = (self.database.SQL_Files.select()
                     .where(self.database.SQL_Files.system == self.selected_entry.device.system.id)
                     .where(self.database.SQL_Files.device == self.selected_entry.device.id)
                     .where(fn.year(self.database.SQL_Files.timestamp) == self.selected_entry.year)
                     .limit(1).offset(index)
                     )
            self.ImageDisplaySchedule(query)
        if isinstance(self.selected_entry, Month):
            query = (self.database.SQL_Files.select()
                     .where(self.database.SQL_Files.system == self.selected_entry.device.system.id)
                     .where(self.database.SQL_Files.device == self.selected_entry.device.id)
                     .where(fn.year(self.database.SQL_Files.timestamp) == self.selected_entry.year)
                     .where(fn.month(self.database.SQL_Files.timestamp) == self.selected_entry.month)
                     .limit(1).offset(index)
                     )
            self.ImageDisplaySchedule(query)
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
        if self.thread_display is not None:
            self.thread_display.stop()
        self.thread_display = StoppableThread()
        self.thread_display.start(self, entry)

    def UpdateImage(self):
        self.pixmap.setPixmap(QtGui.QPixmap(self.qimage))
        self.view.setExtend(self.im.shape[1], self.im.shape[0])
        self.time_label.setText(self.time_text)

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
            child.entry = Year(entry, row.year, row.timestamp, row.count)
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
            child.entry = Month(entry.device, entry.year, row.month, row.timestamp, row.count)
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
            child.entry = Day(entry.device, entry.year, entry.month, row.day, row.timestamp, row.count)
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
    app = QApplication(sys.argv)

    window = DatabaseBrowser()
    window.show()
    app.exec_()
