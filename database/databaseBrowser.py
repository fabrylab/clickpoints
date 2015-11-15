from __future__ import division, print_function
import os, sys, ctypes
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt4 import NavigationToolbar2QT as NavigationToolbar
from matplotlibwidget import MatplotlibWidget
import seaborn as sns
import time
from matplotlib.colors import LinearSegmentedColormap

try:
    from PyQt5 import QtGui, QtCore
    from PyQt5.QtWidgets import QWidget, QApplication, QCursor, QFileDialog, QCursor, QIcon, QMessageBox
    from PyQt5.QtCore import Qt
except ImportError:
    from PyQt4 import QtGui, QtCore
    from PyQt4.QtGui import QWidget, QApplication, QCursor, QFileDialog, QCursor, QIcon, QMessageBox
    from PyQt4.QtCore import Qt
try:
    from PyQt5 import QtGui, QtCore
    from PyQt5.QtWidgets import QWidget, QTextStream, QGridLayout
    from PyQt5.QtCore import Qt
except ImportError:
    from PyQt4 import QtGui, QtCore
    from PyQt4.QtGui import QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QPlainTextEdit, QTableWidget, QHeaderView, QTableWidgetItem, QSpinBox, QTabWidget, QSpacerItem
    from PyQt4.QtCore import Qt, QTextStream, QFile, QStringList, QObject, SIGNAL

from peewee import fn

from datetime import datetime, timedelta
import calendar
from database import Database

icon_path = os.path.join(os.path.dirname(__file__), "..", "icons")

def add_months(sourcedate,months):
     month = sourcedate.month - 1 + months
     year = int(sourcedate.year + month / 12 )
     month = month % 12 + 1
     day = min(sourcedate.day,calendar.monthrange(year,month)[1])
     return datetime(year,month,day)

def ShortenNumber(value):
    if value == 0:
        return ""
    if value < 1:
        return "%d" % value
    postfix = ["", "k", "M", "G", "T", "P", "E", "Z", "Y"]
    power = int(np.log10(value)//3)
    power2 = int(np.log10(value*10)//3)
    if power2 > power:
        value /= 10**(power2*3)
        return ("%.1f" % value+postfix[power2])[1:]
    value /= 10**(power*3)
    return "%d" % value+postfix[power]

class DatabaseByFiles(QWidget):
    def __init__(self,parent):
        QWidget.__init__(self)
        self.parent = parent

        # main layout splits top bottom (control / display)
        self.layout = QVBoxLayout(self)

        # top split in left right segment
        # self.layout_top = QHBoxLayout()
        # self.layout.addLayout(self.layout_top)

        # vertical split on left and right side
        # self.layout_top_v_left = QVBoxLayout()
        # self.layout_top_v_left.setContentsMargins(0,0,20,0)
        # self.layout_top_v_right = QVBoxLayout()
        # self.layout_top_v_right.setContentsMargins(0,0,20,0)
        # self.layout_top.addLayout(self.layout_top_v_left)
        # self.layout_top.addLayout(self.layout_top_v_right)
        self.layout_top = QGridLayout()
        self.layout_top.setContentsMargins(20,10,0,0)
        self.layout.addLayout(self.layout_top)


        # non persistant hbox for label + combo box
        # System
        layout_hor = QHBoxLayout()
        self.layout_top.addLayout(layout_hor,0,0)
        layout_hor.addWidget(QLabel('System:', self))

        self.ComboBoxSystem = QComboBox(self)
        self.systems = database.SQL_Systems.select()
        for index, item in enumerate(self.systems):
            self.ComboBoxSystem.insertItem(index, item.name)
        self.ComboBoxSystem.currentIndexChanged.connect(self.ComboBoxSystemsChanged)
        self.ComboBoxSystem.setInsertPolicy(QComboBox.NoInsert)
        layout_hor.addWidget(self.ComboBoxSystem)
        layout_hor.addSpacing(30)

        # Device
        layout_hor = QHBoxLayout()
        layout_hor.setSpacing(1)
        self.layout_top.addLayout(layout_hor,1,0)
        layout_hor.addWidget(QLabel('Device:', self))
        self.ComboBoxDevice = QComboBox(self)
        self.devices = self.systems[0].devices()
        self.ComboBoxDevice.insertItem(0, "All")
        for index, item in enumerate(self.devices):
            self.ComboBoxDevice.insertItem(index+1, item.name)
        #self.ComboBoxDevice.currentIndexChanged.connect(self.counts)
        self.ComboBoxDevice.setInsertPolicy(QComboBox.NoInsert)
        layout_hor.addWidget(self.ComboBoxDevice)
        layout_hor.addSpacing(30)

        #self.layout_top_v_left.addSpacing(30)

        # Year
        layout_hor = QHBoxLayout()
        self.layout_top.addLayout(layout_hor,0,1)
        layout_hor.addWidget(QLabel('Year:', self))
        self.SpinBoxYearStart = QSpinBox(self)
        self.SpinBoxYearStart.setMaximum(2050)
        self.SpinBoxYearStart.setMinimum(0)
        self.SpinBoxYearStart.setValue(2014)
        self.SpinBoxYearStart.valueChanged.connect(self.update_timerange)
        layout_hor.addWidget(self.SpinBoxYearStart)
        self.SpinBoxYearEnd = QSpinBox(self)
        self.SpinBoxYearEnd.setMaximum(2050)
        self.SpinBoxYearEnd.setMinimum(0)
        self.SpinBoxYearEnd.setValue(0)
        self.SpinBoxYearEnd.valueChanged.connect(self.update_timerange)
        layout_hor.addWidget(self.SpinBoxYearEnd)
        button = QPushButton('R', self)
        button.setMaximumWidth(20)
        button.pressed.connect(self.reset_year)
        layout_hor.addWidget(button)
        # Month
        layout_hor = QHBoxLayout()
        self.layout_top.addLayout(layout_hor,1,1)
        layout_hor.addWidget(QLabel('Month:', self))
        self.SpinBoxMonthStart = QSpinBox(self)
        self.SpinBoxMonthStart.setMaximum(13)
        self.SpinBoxMonthStart.setMinimum(0)
        self.SpinBoxMonthStart.valueChanged.connect(self.update_timerange)
        layout_hor.addWidget(self.SpinBoxMonthStart)
        self.SpinBoxMonthEnd = QSpinBox(self)
        self.SpinBoxMonthEnd.setMaximum(13)
        self.SpinBoxMonthEnd.setMinimum(0)
        self.SpinBoxMonthEnd.valueChanged.connect(self.update_timerange)
        layout_hor.addWidget(self.SpinBoxMonthEnd)
        button = QPushButton('R', self)
        button.setMaximumWidth(20)
        button.pressed.connect(self.reset_month)
        layout_hor.addWidget(button)
        # Day
        layout_hor = QHBoxLayout()
        self.layout_top.addLayout(layout_hor,2,1)
        layout_hor.addWidget(QLabel('Day:', self))
        self.SpinBoxDayStart = QSpinBox(self)
        self.SpinBoxDayStart.setMaximum(32)
        self.SpinBoxDayStart.setMinimum(0)
        self.SpinBoxDayStart.valueChanged.connect(self.update_timerange)
        layout_hor.addWidget(self.SpinBoxDayStart)
        self.SpinBoxDayEnd = QSpinBox(self)
        self.SpinBoxDayEnd.setMaximum(32)
        self.SpinBoxDayEnd.setMinimum(0)
        self.SpinBoxDayEnd.valueChanged.connect(self.update_timerange)
        layout_hor.addWidget(self.SpinBoxDayEnd)
        button = QPushButton('R', self)
        button.setMaximumWidth(20)
        button.pressed.connect(self.reset_day)
        layout_hor.addWidget(button)

        self.listSpinBoxStart = [self.SpinBoxYearStart,self.SpinBoxMonthStart,self.SpinBoxDayStart]



        # PLOT
        self.layout.addSpacing(50)
        self.layout.setStretch(1,1)

        self.plot = MatplotlibWidget(self)
        self.plot.figure.patch.set_facecolor([0,1,0,0])
        self.layout.addWidget(self.plot)
        self.plot.figure.clear()

        self.plot2 = MatplotlibWidget(self, width=1)
        self.plot2.figure.patch.set_facecolor([0,1,0,0])

        self.plot2.figure.clear()
        #self.navi_toolbar = NavigationToolbar(self.plot, self)
        #self.layout.addWidget(self.navi_toolbar, 4, 0, 1, 4)
        self.toggle_widgets=[self.plot2]

        # Create Axes object
        self.axes1 = self.plot.figure.add_axes([0.1,0.15,0.86,0.8])
        self.axes2 = self.plot2.figure.add_axes([0, 0, 1, 1], axisbg='none')
        self.axes2.grid()

        self.last_path_id = 0
        self.last_path = ""
        self.last_system_id = 0
        self.last_system_name = ""
        self.last_device_id = 0
        self.last_device_name = ""

        self.CreateColorMaps()

    def post_init(self):
        self.parent.layout_vert.addWidget(self.plot2)
        self.updateSpinBoxState()

    def hideWidgets(self,flag):
        [w.setHidden(flag) for w in self.toggle_widgets]

    def CreateColorMaps(self):
        cmap_b = LinearSegmentedColormap("TransBlue", {'blue':((0, 0, 0),(1,176/255,176/255)),'red':((0,0,0),(1,76/255,76/255)),'green': ((0,0,0),(1,114/255,114/255)),'alpha':((0,0,0),(1,1,1))})
        cmap_r = LinearSegmentedColormap("TransBlue", {'blue':((0, 0, 0),(1,104/255,104/255)),'red':((0,0,0),(1,85/255,85/255)),'green': ((0,0,0),(1,168/255,168/255)),'alpha':((0,0,0),(1,1,1))})
        cmap_g = LinearSegmentedColormap("TransBlue", {'blue':((0, 0, 0),(1,82/255,82/255)),'red':((0,0,0),(1,196/255,196/255)),'green': ((0,0,0),(1,78/255,78/255)),'alpha':((0,0,0),(1,1,1))})
        cmap_r2 = LinearSegmentedColormap("TransBlue", {'blue':((0, 0, 0),(1,178/255,178/255)),'red':((0,0,0),(1,129/255,129/255)),'green': ((0,0,0),(1,114/255,114/255)),'alpha':((0,0,0),(1,1,1))})
        cmap_g2 = LinearSegmentedColormap("TransBlue", {'blue':((0, 0, 0),(1,116/255,116/255)),'red':((0,0,0),(1,204/255,204/255)),'green': ((0,0,0),(1,185/255,185/255)),'alpha':((0,0,0),(1,1,1))})
        cmap_b2 = LinearSegmentedColormap("TransBlue", {'blue':((0, 0, 0),(1,100/255,100/255)),'red':((0,0,0),(1,205/255,205/255)),'green': ((0,0,0),(1,181/255,181/255)),'alpha':((0,0,0),(1,1,1))})
        self.cmaps = [cmap_b, cmap_r, cmap_g, cmap_r2, cmap_g2, cmap_b2]

    def reset_year(self):
        self.SpinBoxYearEnd.setValue(0)
        self.SpinBoxYearStart.setValue(0)


    def reset_month(self):
        self.SpinBoxMonthEnd.setValue(0)
        self.SpinBoxMonthStart.setValue(0)

    def reset_day(self):
        self.SpinBoxDayEnd.setValue(0)
        self.SpinBoxDayStart.setValue(0)

    def counts(self):
        system_id = self.systems[self.ComboBoxSystem.currentIndex()].id
        if self.ComboBoxDevice.currentIndex() == -1:
            return
        self.axes1.cla()
        self.plot_list = []
        self.plot_list_names = []
        if self.ComboBoxDevice.currentIndex() != 0:
            device_id = self.devices[self.ComboBoxDevice.currentIndex()-1].id
            device_name = self.devices[self.ComboBoxDevice.currentIndex()-1].name
            self.DrawData(device_id)
            self.axes2.legend(self.plot_list, [device_name], loc="lower left", bbox_to_anchor=(-0.1, 0))
            self.plot2.draw()
        else:
            for index, device in enumerate(self.devices):
                self.plot_list_names.append(device.name)
                self.DrawData(device.id, offset=index/(self.devices.count()+1), color=index, max_count=(self.devices.count()+1))
                self.plot.draw()
                self.axes2.legend(self.plot_list, self.plot_list_names, loc="lower left", scatterpoints=1, bbox_to_anchor=(-0.1, 0))
                print(self.plot_list, self.plot_list_names)
                self.plot2.draw()
        cur_ylim = self.axes1.get_ylim(); self.axes1.set_ylim([0, cur_ylim[1]])
        self.plot.draw()

    def showData(self):
        if self.ComboBoxDevice.currentIndex() == 0:
            QMessageBox.question(None, 'Warning', 'You have to select a single device to display images.', QMessageBox.Ok)
            return
        count = self.SaveFileList()
        if count == 0:
            QMessageBox.question(None, 'Warning', 'Your selection doesn\'t contain any images.', QMessageBox.Ok)
            return
        print("Selected %d images." % count)
        os.system(r"python.exe ..\ClickPointsQT.py ConfigClickPoints.txt -srcpath=files.txt")

    def DrawData(self, device_id, offset=0, color=0, max_count=1):
        cmap = self.cmaps[color % len(self.cmaps)]
        year = self.SpinBoxYearStart.value()
        month = self.SpinBoxMonthStart.value()
        if month:
            daycount = calendar.monthrange(year,month)[1]
            day = self.SpinBoxDayStart.value()
            if day > daycount:
                day = daycount
                self.SpinBoxDayStart.setValue(day)
        else:
            day = 0
        if year == 0:
            t = time.time()
            query = (database.SQL_Files
                     .select((fn.count(database.SQL_Files.id)*database.SQL_Files.frames).alias('count'),
                             fn.year(database.SQL_Files.timestamp).alias('year'),
                             fn.month(database.SQL_Files.timestamp).alias('month'))
                     .where(database.SQL_Files.device == device_id)
                     .group_by(fn.year(database.SQL_Files.timestamp)*13+fn.month(database.SQL_Files.timestamp)))
            query.execute()
            print("Query Time:", time.time()-t)
            years = np.unique([item.year for item in query])
            year_count = max(years)-min(years)+1
            print("years", years, year_count)
            count = np.zeros((year_count, 12))
            for item in query:
                count[item.year-min(years), item.month-1] = item.count
            x, y = np.meshgrid(np.arange(0, year_count), np.arange(1, 13))
            self.axes1.scatter(x+offset, y, c=count.T.flatten(), cmap=cmap, lw=0)
            p = self.axes1.scatter([-2,-2], [0,0], c=[1,0], cmap=cmap, lw=0)
            self.plot_list.append(p)
            for year in range(year_count):
                self.axes1.text(year+offset, 12.2, ShortenNumber(np.sum(count[year,:])), ha="center")
            self.axes1.set_xlim(-0.5,year_count-0.5+(1 if max_count > 2 else 0))
            self.axes1.set_ylim(0.5,12.5)
            self.axes1.set_xticks(np.arange(0,year_count))
            self.axes1.set_xticklabels(np.arange(0,year_count)+min(years))
            self.axes1.set_yticks(np.arange(1,13))
            self.axes1.set_yticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
            #self.axes1.set_yticks([1,5,10,15,20,25,31])
            self.axes1.set_title("All data")
            self.axes1.set_xlabel("year")
            self.axes1.set_ylabel("month")
        elif month == 0:
            count = np.zeros((12, 31))
            t = time.time()
            query = (database.SQL_Files
                     .select((fn.count(database.SQL_Files.id)*database.SQL_Files.frames).alias('count'),
                             fn.day(database.SQL_Files.timestamp).alias('day'),
                             fn.month(database.SQL_Files.timestamp).alias('month'))
                     .where(database.SQL_Files.device == device_id,
                            fn.year(database.SQL_Files.timestamp) == year)
                     .group_by(fn.dayofyear(database.SQL_Files.timestamp)))
            query.execute()
            print("Query Time:", time.time()-t)
            for item in query:
                count[item.month-1, item.day-1] = item.count
            x, y = np.meshgrid(np.arange(1, 13), np.arange(1, 32))
            self.axes1.scatter(x+offset, y, c=count.T.flatten(), cmap=cmap, lw=0)
            p = self.axes1.scatter([0,0], [0,0], c=[1,0], cmap=cmap, lw=0)
            self.plot_list.append(p)
            for month in range(12):
                self.axes1.text(month+1, 32, ShortenNumber(np.sum(count[month,:])), ha="center")
            self.axes1.set_xticks(np.arange(1,13))
            self.axes1.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
            self.axes1.set_xlim(0.5,12.5)
            self.axes1.set_ylim(0.5,33.5)
            self.axes1.set_yticks([1,5,10,15,20,25,31])
            self.axes1.set_title("%d" % (year))
            self.axes1.set_xlabel("month")
            self.axes1.set_ylabel("day")
        elif day == 0:
            count = np.zeros((31,24))
            t = time.time()
            query = (database.SQL_Files
                     .select((fn.count(database.SQL_Files.id)*database.SQL_Files.frames).alias('count'),
                             fn.day(database.SQL_Files.timestamp).alias('day'),
                             fn.hour(database.SQL_Files.timestamp).alias('hour'))
                     .where(database.SQL_Files.device == device_id,
                            fn.year(database.SQL_Files.timestamp) == year,
                            fn.month(database.SQL_Files.timestamp) == month)
                     .group_by(fn.dayofyear(database.SQL_Files.timestamp) * 24 + fn.hour(database.SQL_Files.timestamp)))
            query.execute()
            print("Query Time:", time.time()-t)
            for item in query:
                count[item.day-1,item.hour-1] = item.count
            x, y = np.meshgrid(np.arange(1,32),np.arange(1,25))
            self.axes1.scatter(x+offset, y, c=count.T.flatten(), cmap=cmap, lw=0)
            p = self.axes1.scatter([0,0], [0,0], c=[1,0], cmap=cmap, lw=0)
            self.plot_list.append(p)
            for day in range(31):
                self.axes1.text(day+1, 27, ShortenNumber(np.sum(count[day,:])), ha="center", va="top", rotation=90)
            self.axes1.set_xlim(0.5, daycount+0.5)
            self.axes1.set_title("%s %d" % (["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][month-1],year))
            self.axes1.set_xlabel("day")
            self.axes1.set_ylabel("hour")
        else:
            count = np.zeros(24)
            t = time.time()
            query = (database.SQL_Files
                     .select((fn.count(database.SQL_Files.id)*database.SQL_Files.frames).alias('count'),
                             fn.hour(database.SQL_Files.timestamp).alias('hour'))
                     .where(database.SQL_Files.device == device_id,
                            fn.year(database.SQL_Files.timestamp) == year,
                            fn.month(database.SQL_Files.timestamp) == month,
                            fn.day(database.SQL_Files.timestamp) == day)
                     .group_by(fn.hour(database.SQL_Files.timestamp)))
            query.execute()
            print("Query Time:", time.time()-t)
            for item in query:
                count[item.hour-1] = item.count
            p = self.axes1.bar(np.arange(0.6,24)+offset, count, width=1/max_count, color=cmap(255))
            self.plot_list.append(p)
            self.axes1.set_xlim(0.5,24.5)
            self.axes1.set_title("%d. %s %d" % (day, ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][month-1],year))
            self.axes1.set_xlabel("hour")
            self.axes1.set_ylabel("count")

    def getPath(self, path_index):
        if path_index != self.last_path_id:
            self.last_path = database.getPath(path_index)
            self.last_path_id = path_index
        return self.last_path

    def getSystem(self, system_index):
        if system_index != self.last_system_id:
            self.last_system_id = system_index
            for sys in self.systems:
                if sys.id == self.last_system_id:
                    self.last_system_name = sys.name
        return self.last_system_name

    def getDevice(self, device_index):
        if device_index != self.last_device_id:
            self.last_device_id = device_index
            for dev in self.devices:
                if dev.id == self.last_device_id:
                    self.last_device_name = dev.name
        return self.last_device_name

    def ComboBoxSystemsChanged(self, value):
        print("changed")
        self.ComboBoxDevice.clear()
        print(self.systems, value, self.systems[value].name)
        self.devices = self.systems[value].devices()
        self.ComboBoxDevice.insertItem(0, "All")
        for index, item in enumerate(self.devices):
            self.ComboBoxDevice.insertItem(index+1, item.name)


    def update_timerange(self):
        ### get shorter handels for values
        year = self.SpinBoxYearStart.value()
        month = self.SpinBoxMonthStart.value()

        year_end = self.SpinBoxYearEnd.value()
        month_end = self.SpinBoxMonthEnd.value()

        ### handle overruns
        # month overrun handling
        if month == 13:
            self.SpinBoxMonthStart.setValue(1)
            self.SpinBoxYearStart.setValue(year+1)
            return
        if month_end == 13:
            self.SpinBoxMonthEnd.setValue(1)
            self.SpinBoxYearEnd.setValue(year+1)
            return

        # day overrun handling
        if month:
            daycount = calendar.monthrange(year,month)[1]
            day = self.SpinBoxDayStart.value()
            if day > daycount:
                self.SpinBoxMonthStart.setValue(month+1)
                self.SpinBoxDayStart.setValue(1)
                return
            daycount = calendar.monthrange(year_end,month_end)[1]
            day_end = self.SpinBoxDayEnd.value()
            if day_end > daycount:
                self.SpinBoxMonthEnd.setValue(month_end+1)
                self.SpinBoxDayEnd.setValue(1)
                return

        ### set start stop text fields
        if year == 0:
            return

        if month == 0:
            # select full year if start==stop
            # otherwise select specified intervall
            if year == year_end:
                start = datetime(year, 1, 1)
                end = datetime(year_end+1, 1, 1)
            else:
                start = datetime(year, 1, 1)
                end = datetime(year_end, 1, 1)
            self.parent.EditStart.setText(str(start))
            self.parent.EditEnd.setText(str(end))

        elif day == 0:
            # select full month if start==stop
            # otherwise select specified intervall
            if month == month_end:
                start = datetime(year, month, 1)
                end = datetime(year_end, month+1, 1)
            else:
                start = datetime(year, month, 1)
                end = datetime(year_end, month_end, 1)
            self.parent.EditStart.setText(str(start))
            self.parent.EditEnd.setText(str(end))
        else:
            # select full day if start==stop
            # otherwise select specified intervall
            if day==day_end:
                start = datetime(year, month, day)
                end = datetime(year_end,month_end,day_end)+ timedelta(days=1)
            else:
                start = datetime(year, month, day)
                end = datetime(year_end, month_end, day_end)
            self.parent.EditStart.setText(str(start))
            self.parent.EditEnd.setText(str(end))

    def updateSpinBoxState(self):
        print("sender:",self.sender())
        # if start field is zero - deactivate stop field
        if self.SpinBoxYearStart.value()== 0:
            self.SpinBoxYearEnd.setValue(0);
            self.SpinBoxYearEnd.setEnabled(False);

            self.SpinBoxMonthStart.setValue(0);
            self.SpinBoxMonthStart.setEnabled(False);
        else:
            self.SpinBoxYearEnd.setEnabled(True);
            # prevent end < start
            if self.SpinBoxYearEnd.value() < self.SpinBoxYearStart.value():
                self.SpinBoxYearEnd.setValue(self.SpinBoxYearStart.value());
            self.SpinBoxMonthStart.setEnabled(True);
            
        if self.SpinBoxMonthStart.value()== 0:
            self.SpinBoxMonthEnd.setValue(0);
            self.SpinBoxMonthEnd.setEnabled(False);

            self.SpinBoxDayStart.setValue(0);
            self.SpinBoxDayStart.setEnabled(False);
        else:
            self.SpinBoxMonthEnd.setEnabled(True);
            if self.SpinBoxMonthEnd.value()==0:
                self.SpinBoxMonthEnd.setValue(self.SpinBoxMonthStart.value());
            # prevent end < start
            if self.SpinBoxMonthEnd.value() < self.SpinBoxMonthStart.value() \
                    and self.SpinBoxYearEnd.value()==self.SpinBoxYearStart.value():
                self.SpinBoxMonthEnd.setValue(self.SpinBoxMonthStart.value());
            self.SpinBoxDayStart.setEnabled(True);
            
        if self.SpinBoxDayStart.value()== 0:
            self.SpinBoxDayEnd.setValue(0);
            self.SpinBoxDayEnd.setEnabled(False);
        else:
            self.SpinBoxDayEnd.setEnabled(True);
            # prevent zero on go active
            if self.SpinBoxDayEnd.value()==0:
                self.SpinBoxDayEnd.setValue(self.SpinBoxDayStart.value());
            # prevent end < start
            if self.SpinBoxDayEnd.value() < self.SpinBoxDayStart.value() \
                and self.SpinBoxYearEnd.value() == self.SpinBoxYearStart.value()\
                and self.SpinBoxMonthEnd.value() == self.SpinBoxMonthStart.value():
                self.SpinBoxDayEnd.setValue(self.SpinBoxDayStart.value());


    def SaveFileList(self):
        if self.ComboBoxDevice.currentIndex() == 0:
            print("No Device selected")
            return 0
        system_id = self.systems[self.ComboBoxSystem.currentIndex()].id
        device_id = self.devices[self.ComboBoxDevice.currentIndex()-1].id
        print(system_id, device_id)
        start_time = datetime.strptime(str(self.parent.EditStart.text()), '%Y-%m-%d %H:%M:%S')
        end_time   = datetime.strptime(str(self.parent.EditEnd.text()), '%Y-%m-%d %H:%M:%S')
        query = (database.SQL_Files.select()
                 .where(database.SQL_Files.system == system_id, database.SQL_Files.device == device_id, database.SQL_Files.timestamp > start_time, database.SQL_Files.timestamp < end_time)
                 .order_by(database.SQL_Files.timestamp)
                 )
        counter = 0
        with open("files.txt","w") as fp:
            for item in query:
                fp.write("\\\\"+os.path.join(self.getPath(item.path), item.basename+item.extension)+" "+str(item.id)+" "+str(item.annotation_id) +"\n")
                counter += 1
        return counter

    def doSaveFilelist(self):
        if self.ComboBoxDevice.currentIndex() == 0:
            QMessageBox.question(None, 'Warning', 'You have to select a single device to write file list.', QMessageBox.Ok)
            return
        count = self.SaveFileList()
        QMessageBox.question(None, 'Saved', 'The file list fielist.txt has been saved with %d entries.' % count, QMessageBox.Ok)
        return

class DatabaseBrowser(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        # widget layout and elements
        self.setMinimumWidth(655)
        self.setMinimumHeight(500)
        self.setGeometry(100,100,500,600)
        self.setWindowTitle("Database Browser")
        self.setWindowIcon(QIcon(QIcon(os.path.join(icon_path, "DatabaseViewer.ico"))))
        self.layout = QGridLayout(self)
        self.layout.setColumnStretch(0, 1)
        self.layout.setColumnStretch(1, 1)
        self.layout.setColumnStretch(2, 0)
        self.layout_vert = QVBoxLayout()

        self.dbByFiles=DatabaseByFiles(self)
        self.dbByAnnotation=DatabaseByFiles(self)

        self.tabWidget=QTabWidget(self)
        self.tabWidget.addTab(self.dbByFiles,'by File')
        self.tabWidget.addTab(self.dbByAnnotation,'by Annotation')
        self.tab_dict={0:self.dbByFiles,
                       1:self.dbByAnnotation}
        self.fWidget=self.dbByFiles
        self.tabWidget.currentChanged.connect(self.setFocusTab)
        self.layout.addWidget(self.tabWidget,0,0,2,2)
        self.layout.addLayout(self.layout_vert, 0, 2, 2, 1)

        self.pbConfirm = QPushButton('C&onfirm', self)
        self.pbConfirm.pressed.connect(self.fWidget.counts)
        self.layout_vert.addWidget(self.pbConfirm)

        self.pbShow = QPushButton('&Show', self)
        self.pbShow.pressed.connect(self.fWidget.showData)
        self.layout_vert.addWidget(self.pbShow)

        self.pbFilelist = QPushButton('&Filelist', self)
        self.pbFilelist.pressed.connect(self.fWidget.doSaveFilelist)
        self.layout_vert.addWidget(self.pbFilelist)

        self.layout_vert.addWidget(QLabel('Start:', self))
        self.EditStart = QLineEdit('', self)
        self.layout_vert.addWidget(self.EditStart)
        self.layout_vert.addWidget(QLabel('End:', self))
        self.EditEnd = QLineEdit('', self)
        self.layout_vert.addWidget(self.EditEnd)
        self.layout_vert.addStretch()

        self.fWidget.update_timerange()

        for key,tabWidget in self.tab_dict.iteritems():
            tabWidget.post_init()

    def setFocusTab(self,n):
        print("changed to tab: ",n)
        print(self.tabWidget.tabText(n))
        print("set active to:", self.tab_dict[n])
        self.fWidget=self.tab_dict[n]

        # hife widgets of all other tabs
        [v.hideWidgets(True) for k,v in self.tab_dict.iteritems()]
        # show widgets of current acitve tab
        self.fWidget.hideWidgets(False)


database = Database()

if __name__ == '__main__':
    if sys.platform[:3] == 'win':
        myappid = 'fabrybiophysics.databasebrowser' # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    app = QApplication(sys.argv)

    window = DatabaseBrowser()
    window.show()
    app.exec_()