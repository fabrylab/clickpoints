import get_update as gu
import sys
import os
import datetime
import subprocess

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

import lastNotifiedLogger as nl
logfile="lastnotified.log"
timeformat='%Y%m%d-%H%M%S'

class updaterSignals(QObject):
        sig = pyqtSignal()

class checkUpdateThread(QThread):
    def __init__(self):
        super(QThread, self).__init__()
        self.exiting = False
        self.signal = updaterSignals()

    def run(self):
        ret=gu.checkForUpdate()

        if ret:
            # check if we should notify the user
            print("verify user anoyance level...")
            lnl = nl.lastNotifiedLogger(logfile)

            if lnl.excedTimeElpased(24):
                print("update found - notify user")
                self.signal.sig.emit()
            else:
                print("to early notify later ...")

def showMessageBox(parent):
    """ notify user """
    print("start gui")
    reply = QMessageBox.question(None, 'Update available', 'Do you want to update ClickPoints now?', QMessageBox.Yes,
                             QMessageBox.No)
    if reply == QMessageBox.Yes:
        print('Preparing for update')
        # clear last notified logger
        lnl = nl.lastNotifiedLogger(logfile)
        lnl.clear()

        # fork update process
        subprocess.Popen([sys.executable,'get_update.py','prepare'])

        # close parent
        parent.close()
    else:
        # update last notified
        lnl = nl.lastNotifiedLogger(logfile)
        lnl.update()

class Updater(QWidget):
    def __init__(self,parent):
        QWidget.__init__(self)
        self.parent=parent

        self.t=checkUpdateThread()
        # otherwise we can't connect the function
        self.func=lambda : showMessageBox(self.parent)
        self.t.signal.sig.connect(self.func)
        self.t.start()

"""" TEST PART """
if __name__ == "__main__":

    class Window(QWidget):
        def __init__(self, parent = None):
            QWidget.__init__(self, parent)

            self.up=Updater(self)

    app = QApplication(sys.argv)
    window = Window()
    window.show()

    sys.exit(app.exec_())

