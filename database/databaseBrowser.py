from __future__ import division, print_function
import os, sys
import re
import glob
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt4 import NavigationToolbar2QT as NavigationToolbar
from matplotlibwidget import MatplotlibWidget
import seaborn as sns
import time
from matplotlib.colors import LinearSegmentedColormap
cmap = LinearSegmentedColormap("TransBlue", {'blue':((0, 0, 0),(1,176/255,176/255)),'red':((0,0,0),(1,76/255,76/255)),'green': ((0,0,0),(1,114/255,114/255)),'alpha':((0,0,0),(1,1,1))})

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
    from PyQt4.QtGui import QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QPlainTextEdit, QTableWidget, QHeaderView, QTableWidgetItem, QSpinBox
    from PyQt4.QtCore import Qt, QTextStream, QFile, QStringList, QObject, SIGNAL

from peewee import fn

from datetime import datetime, timedelta
import calendar
from database import Database

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

class DatabaseBrowser(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        # widget layout and elements
        self.setMinimumWidth(650)
        self.setMinimumHeight(400)
        self.setWindowTitle("Database Browser")
        self.layout = QGridLayout(self)
        self.layout.setColumnStretch(4, 0)
        self.layout.setColumnStretch(0, 1)
        self.layout.setColumnStretch(1, 1)
        self.layout.setColumnStretch(2, 1)
        self.layout.setColumnStretch(3, 1)

        self.layout.addWidget(QLabel('System:', self), 0, 0)
        self.ComboBoxSystem = QComboBox(self)
        self.systems = database.SQL_Systems.select()
        for item in self.systems:
            self.ComboBoxSystem.insertItem(1, item.name)
        self.ComboBoxSystem.currentIndexChanged.connect(self.ComboBoxSystemsChanged)
        self.ComboBoxSystem.setInsertPolicy(QComboBox.NoInsert)
        self.layout.addWidget(self.ComboBoxSystem, 0, 1)

        self.layout.addWidget(QLabel('Device:', self), 0, 2)
        self.ComboBoxDevice = QComboBox(self)
        self.devices = self.systems[0].devices()
        for item in self.devices:
            self.ComboBoxDevice.insertItem(item.id, item.name)
        self.ComboBoxDevice.currentIndexChanged.connect(self.counts)
        self.ComboBoxDevice.setInsertPolicy(QComboBox.NoInsert)
        self.layout.addWidget(self.ComboBoxDevice, 0, 3)

        layout_vert = QHBoxLayout()
        self.layout.addLayout(layout_vert, 1, 0, 1, 4)
        layout_vert.addWidget(QLabel('Year:', self))
        self.SpinBoxYear = QSpinBox(self)
        self.SpinBoxYear.setMaximum(2050)
        self.SpinBoxYear.setMinimum(2014)
        self.SpinBoxYear.valueChanged.connect(self.counts)
        layout_vert.addWidget(self.SpinBoxYear)

        layout_vert.addWidget(QLabel('Month:', self))
        self.SpinBoxMonth = QSpinBox(self)
        self.SpinBoxMonth.setMaximum(12)
        self.SpinBoxMonth.setMinimum(0)
        self.SpinBoxMonth.valueChanged.connect(self.counts)
        layout_vert.addWidget(self.SpinBoxMonth)

        layout_vert.addWidget(QLabel('Day:', self))
        self.SpinBoxDay = QSpinBox(self)
        self.SpinBoxDay.setMaximum(31)
        self.SpinBoxDay.setMinimum(0)
        self.SpinBoxDay.valueChanged.connect(self.counts)
        layout_vert.addWidget(self.SpinBoxDay)

        self.pbConfirm = QPushButton('C&onfirm', self)
        self.pbConfirm.pressed.connect(self.confirm)
        self.layout.addWidget(self.pbConfirm, 0, 4)

        self.pbDiscard = QPushButton('&Show', self)
        self.pbDiscard.pressed.connect(self.showData)
        self.layout.addWidget(self.pbDiscard, 1, 4)

        layout_vert = QVBoxLayout()
        self.layout.addLayout(layout_vert, 2, 4, 3, 1)
        layout_vert.addWidget(QLabel('Start:', self))
        self.EditStart = QLineEdit('20140101-000000', self)
        layout_vert.addWidget(self.EditStart)
        layout_vert.addWidget(QLabel('End:', self))
        self.EditEnd = QLineEdit('20140101-000000', self)
        layout_vert.addWidget(self.EditEnd)
        layout_vert.addStretch()

        self.plot = MatplotlibWidget(self)
        self.plot.figure.patch.set_facecolor([0,1,0,0])
        self.layout.addWidget(self.plot, 3, 0, 1, 4)
        self.plot.figure.clear()
        #self.navi_toolbar = NavigationToolbar(self.plot, self)
        #self.layout.addWidget(self.navi_toolbar, 4, 0, 1, 4)

        # Create Axes object
        self.axes1 = self.plot.figure.add_axes([0.1,0.1,0.8,0.8])

        """
        self.table = QTableWidget(0, 4, self)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setHorizontalHeaderLabels(QStringList(['Date', 'System', 'Device', 'Path']))
        self.table.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setResizeMode(3, QHeaderView.Stretch)
        self.layout.addWidget(self.table, 5, 0, 5, 4)
        """

        self.last_path_id = 0
        self.last_path = ""
        self.last_system_id = 0
        self.last_system_name = ""
        self.last_device_id = 0
        self.last_device_name = ""

    def showData(self):
        system_id = self.systems[self.ComboBoxSystem.currentIndex()].id
        device_id = self.devices[self.ComboBoxDevice.currentIndex()].id
        start_time = datetime.strptime(str(self.EditStart.text()), '%Y-%m-%d %H:%M:%S')
        end_time   = datetime.strptime(str(self.EditEnd.text()), '%Y-%m-%d %H:%M:%S')
        query = (database.SQL_Files.select()
                 .where(database.SQL_Files.system == system_id, database.SQL_Files.device == device_id, database.SQL_Files.timestamp > start_time, database.SQL_Files.timestamp < end_time)
                 .order_by(database.SQL_Files.timestamp)
                 )
        with open("config_tmp.txt","w") as fp:
            with open("config.txt","r") as fp2:
                for line in fp2.readlines():
                    fp.write(line)
            fp.write("\n\nsrcpath = [")
            for item in query:
                fp.write("r\"\\\\%s\",\n\t\t\t" % os.path.join(self.getPath(item.path), item.basename+item.extension))
            fp.write("]\n")
        os.system(r"E:\WinPython-64bit-2.7.10.1\python-2.7.10.amd64\python.exe ..\ClickPointsQT.py config_tmp.txt")
        pass

    def counts(self):
        import time
        system_id = self.systems[self.ComboBoxSystem.currentIndex()].id
        if self.ComboBoxDevice.currentIndex() == -1:
            return
        device_id = self.devices[self.ComboBoxDevice.currentIndex()].id
        self.axes1.cla()
        year = self.SpinBoxYear.value()
        month = self.SpinBoxMonth.value()
        if month:
            daycount = calendar.monthrange(year,month)[1]
            day = self.SpinBoxDay.value()
            if day > daycount:
                day = daycount
                self.SpinBoxDay.setValue(day)
        if month == 0:
            start = datetime(year, 1, 1)
            end = datetime(year+1, 1, 1)
            self.EditStart.setText(str(start))
            self.EditEnd.setText(str(end))
            count = np.zeros(12)
            t = time.time()
            query = (database.SQL_Devices
                 .select(database.SQL_Devices, fn.Count(database.SQL_Files.id).alias('count'), fn.month(database.SQL_Files.timestamp).alias('month')).where(database.SQL_Devices.id == device_id)
                 .join(database.SQL_Files).where( fn.year(database.SQL_Files.timestamp) == year)
                 .group_by(fn.month(database.SQL_Files.timestamp)))
            query.execute()
            print("Query Time:",time.time()-t)
            for item in query:
                count[item.month-1] = item.count
            self.axes1.bar(np.arange(0.1,12), count)
            self.axes1.set_xticks(np.arange(0.5,12))
            self.axes1.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
            self.axes1.set_xlim(0,12)
            cur_ylim = self.axes1.get_ylim(); self.axes1.set_ylim([0, cur_ylim[1]])
            self.axes1.set_title("%d" % year)
            self.plot.draw()
        elif day == 0:
            start = datetime(year, month, 1)
            end = add_months(start, 1)
            self.EditStart.setText(str(start))
            self.EditEnd.setText(str(end))
            count = np.zeros(daycount)
            query = (database.SQL_Devices
                 .select(database.SQL_Devices, fn.Count(database.SQL_Files.id).alias('count'), fn.day(database.SQL_Files.timestamp).alias('day')).where(database.SQL_Devices.id == device_id)
                 .join(database.SQL_Files).where( fn.year(database.SQL_Files.timestamp) == year, fn.month(database.SQL_Files.timestamp) == month)
                 .group_by(fn.day(database.SQL_Files.timestamp)))
            for item in query:
                count[item.day-1] = item.count
            self.axes1.cla()
            self.axes1.bar(np.arange(0.6,daycount), count)
            self.axes1.set_xlim(0.5,daycount+0.5)
            self.axes1.set_title("%s %d" % (["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][month-1],year))
            cur_ylim = self.axes1.get_ylim(); self.axes1.set_ylim([0, cur_ylim[1]])
            self.plot.draw()
        else:
            start = datetime(year, month, day)
            end = start + timedelta(days=1)
            self.EditStart.setText(str(start))
            self.EditEnd.setText(str(end))
            count = np.zeros(24)
            query = (database.SQL_Devices
                 .select(database.SQL_Devices, fn.Count(database.SQL_Files.id).alias('count'), fn.hour(database.SQL_Files.timestamp).alias('hour')).where(database.SQL_Devices.id == device_id)
                 .join(database.SQL_Files).where( fn.year(database.SQL_Files.timestamp) == year, fn.month(database.SQL_Files.timestamp) == month, fn.day(database.SQL_Files.timestamp) == day)
                 .group_by(fn.hour(database.SQL_Files.timestamp)))
            for item in query:
                count[item.hour-1] = item.count
            self.axes1.cla()
            self.axes1.bar(np.arange(0.6,24), count)
            self.axes1.set_xlim(0.5,24.5)
            self.axes1.set_title("%d. %s %d" % (day, ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][month-1],year))
            cur_ylim = self.axes1.get_ylim(); self.axes1.set_ylim([0, cur_ylim[1]])
            self.plot.draw()
            return

    def counts(self):
        system_id = self.systems[self.ComboBoxSystem.currentIndex()].id
        if self.ComboBoxDevice.currentIndex() == -1:
            return
        device_id = self.devices[self.ComboBoxDevice.currentIndex()].id
        self.axes1.cla()
        year = self.SpinBoxYear.value()
        month = self.SpinBoxMonth.value()
        if month:
            daycount = calendar.monthrange(year,month)[1]
            day = self.SpinBoxDay.value()
            if day > daycount:
                day = daycount
                self.SpinBoxDay.setValue(day)
        if month == 0:
            start = datetime(year, 1, 1)
            end = datetime(year+1, 1, 1)
            self.EditStart.setText(str(start))
            self.EditEnd.setText(str(end))
            count = np.zeros((12, 31))
            t = time.time()
            query = (database.SQL_Files
                     .select(fn.count(database.SQL_Files.id).alias('count'),
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
            self.axes1.scatter(x, y, c=count.T.flatten(), cmap=cmap, lw=0)
            for month in range(12):
                self.axes1.text(month+1, 32, ShortenNumber(np.sum(count[month,:])), ha="center")
            self.axes1.set_xticks(np.arange(1,13))
            self.axes1.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
            self.axes1.set_xlim(0.5,12.5)
            self.axes1.set_ylim(0.5,33.5)
            self.axes1.set_yticks([1,5,10,15,20,25,31])
        elif day == 0:
            start = datetime(year, month, 1)
            end = add_months(start, 1)
            self.EditStart.setText(str(start))
            self.EditEnd.setText(str(end))
            count = np.zeros((31,24))
            t = time.time()
            query = (database.SQL_Files
                     .select(fn.count(database.SQL_Files.id).alias('count'),
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
            self.axes1.scatter(x, y, c=count.T.flatten(), cmap=cmap, lw=0)
            for day in range(31):
                self.axes1.text(day+1, 27, ShortenNumber(np.sum(count[day,:])), ha="center", va="top", rotation=90)
            self.axes1.set_xlim(0.5, daycount+0.5)
            self.axes1.set_title("%s %d" % (["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][month-1],year))
        else:
            start = datetime(year, month, day)
            end = start + timedelta(days=1)
            self.EditStart.setText(str(start))
            self.EditEnd.setText(str(end))
            count = np.zeros(24)
            t = time.time()
            query = (database.SQL_Files
                     .select(fn.Count(database.SQL_Files.id).alias('count'),
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
            self.axes1.bar(np.arange(0.6,24), count)
            self.axes1.set_xlim(0.5,24.5)
            self.axes1.set_title("%d. %s %d" % (day, ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][month-1],year))
        cur_ylim = self.axes1.get_ylim(); self.axes1.set_ylim([0, cur_ylim[1]])
        self.plot.draw()

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

    def confirm(self):
        system_id = self.systems[self.ComboBoxSystem.currentIndex()].id
        device_id = self.devices[self.ComboBoxDevice.currentIndex()].id
        print("confirm", system_id, device_id)
        res = database.SQL_Files.select().where(database.SQL_Files.system == system_id, database.SQL_Files.device == device_id).order_by(database.SQL_Files.timestamp)
        text = ""

        for index, item in enumerate(res.naive().iterator()):
            if index >= self.table.rowCount():
                self.table.insertRow(self.table.rowCount())
                for j in range(7):
                    self.table.setItem(index, j, QTableWidgetItem())
            print(index)
            self.table.item(index, 0).setText(item.timestamp.strftime('%Y%m%d-%H%M%S'))
            self.table.item(index, 1).setText(self.getSystem(item.system_id))
            self.table.item(index, 2).setText(self.getDevice(item.device_id))
            self.table.item(index, 3).setText(self.getPath(item.path))
        for i in range(index+1, self.table.rowCount()):
            self.table.removeRow(i)
            #text += item.timestamp.strftime('%Y%m%d-%H%M%S')+"\n"#print("Path", item.path)
        #self.pteAnnotation.setPlainText(text)

    def ComboBoxSystemsChanged(self, value):
        print("changed")
        self.ComboBoxDevice.clear()
        self.devices = self.systems[value].devices()
        for item in self.devices:
            self.ComboBoxDevice.insertItem(item.id, item.name)

database = Database()

if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = DatabaseBrowser()
    window.show()
    app.exec_()

#database.SQL_Files.timestamp > datetime(2015,9,11,23,10,55) &
#res = database.SQL_Files.select(database.SQL_Files.path).where( (database.SQL_Files.timestamp > datetime(2014,3,01,23,10,55)) & (database.SQL_Files.timestamp < datetime(2014,6,11,23,20,55)) )
#for item in res:
#    print("Path", item.path)
