__author__ = 'fox'
import get_update as gu
import sys
import os
import datetime

try:
    from PyQt5 import QtGui, QtCore, QObject
    from PyQt5.QtWidgets import QWidget, QApplication, QCursor, QFileDialog, QCursor, QIcon, QMessageBox
    from PyQt5.QtCore import Qt, QThread, QObject
    from PyQt4.QtCore import pyqtSignal
except ImportError:
    from PyQt4 import QtGui, QtCore
    from PyQt4.QtGui import QWidget, QApplication, QCursor, QFileDialog, QCursor, QIcon, QMessageBox
    from PyQt4.QtCore import Qt, QThread, QObject
    from PyQt4.QtCore import pyqtSignal

logfile="lastnotified.log"
timeformat='%Y%m%d-%H%M%S'

class lastNotifiedLogger:
    def __init__(self,file):
        self.file=file
        self.tl=None
        self.dt=None

        if os.path.exists(file):
            print('read lnl log')
            self.f=open(file,'r')
            self.line=self.f.readline()
            self.f.close()
            self.dt=datetime.datetime.strptime(self.line.strip(),timeformat)
            print(self.dt)
        else:
            print('write lnl log')
            self.f=open(file,'w')
            self.dt=datetime.datetime.now()
            self.f.write(datetime.datetime.now().strftime(timeformat))
            self.f.close()
            print(self.dt)

    def timeElapsed(self):
        self.tl= datetime.datetime.now()-self.dt
        print(self.tl)

    def excedTimeElpased(self,hours):
        self.timeElapsed()
        if self.tl > datetime.timedelta(hours=hours):
            return True
        else:
            return False

    def clear(self):
        print('clear lnl log')
        os.remove(self.file)
        self.dt=None
        self.tl=None

    def update(self):
        print('update lnl log')
        self.f=open(self.file,'w')
        self.dt=datetime.datetime.now()
        self.f.write(datetime.datetime.now().strftime(timeformat))
        self.f.close()
        print(self.dt)


if __name__ == "__main__":

    print("Init lastNotifiedLogger class")
    lnl = lastNotifiedLogger(logfile)
    print("calc time elapesd:")
    lnl.timeElapsed()
    print("calc if more than 24h have passed")
    lnl.excedTimeElpased(24)
