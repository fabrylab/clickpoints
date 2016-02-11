import os
import shutil
import sys

import ClickPoints
from PyQt4.QtTest import QTest
from PyQt4.QtCore import Qt
from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtGui import QApplication

app = QApplication(sys.argv)

class BaseTest():
    def createInstance(self, path, database_file=None, mask_foldername=None):
        global __path__
        """ Create the GUI """
        if "__path__" in globals():
            self.test_path = os.path.abspath(os.path.normpath(os.path.join(__path__, "..", "..", "..", path)))
        else:
            __path__ = os.path.dirname(__file__)
            self.test_path = os.path.abspath(os.path.normpath(os.path.join(__path__, "..", "..", "..", path)))
        if database_file is None:
            database_file = self.id().replace(".", "_")+".db"
        if mask_foldername is None:
            mask_foldername = self.id().replace(".", "_")
        self.database_file = database_file
        self.mask_folder = mask_foldername

        self.database_path = os.path.join(self.test_path, database_file)
        self.mask_folder_path = os.path.join(self.test_path, mask_foldername)

        print("Test Path", self.test_path)
        sys.argv = [__file__, r"-srcpath="+self.test_path, r"-database_file="+self.database_file, r"-outputpath_mask="+mask_foldername]
        print(sys.argv)
        config = ClickPoints.LoadConfig()
        for addon in config.addons:
            with open(addon + ".py") as f:
                code = compile(f.read(), addon + ".py", 'exec')
                exec(code)

        self.database_already_existed = os.path.exists(self.database_path)
        self.maskfolder_already_existed = os.path.exists(self.mask_folder_path)

        self.window = ClickPoints.ClickPointsWindow(config)

    def mouseMove(self, x, y, delay=10, coordinates="origin"):
        v = self.window.view
        w = v.viewport()
        if coordinates == "origin":
            pos = self.window.view.mapFromOrigin(x, y)
        elif coordinates == "scene":
            pos = self.window.view.mapFromScene(x, y)
        event = QtGui.QMouseEvent(QtCore.QEvent.MouseMove, pos, w.mapToGlobal(pos), Qt.NoButton, Qt.NoButton, Qt.NoModifier)
        QApplication.postEvent(w, event)
        QTest.qWait(delay)

    def mouseDrag(self, x, y, x2, y2, button=None, delay=10, coordinates="origin"):
        if button is None:
            button = Qt.LeftButton
        v = self.window.view
        w = v.viewport()
        if coordinates == "origin":
            pos = self.window.view.mapFromOrigin(x, y)
            pos2 = self.window.view.mapFromOrigin(x2, y2)
        elif coordinates == "scene":
            pos = self.window.view.mapFromScene(x, y)
            pos2 = self.window.view.mapFromScene(x2, y2)
        event = QtGui.QMouseEvent(QtCore.QEvent.MouseMove, pos, w.mapToGlobal(pos), button, button, Qt.NoModifier)
        QApplication.postEvent(w, event)
        QTest.qWait(delay)
        event = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress, pos, w.mapToGlobal(pos), button, button, Qt.NoModifier)
        QApplication.postEvent(w, event)
        QTest.qWait(delay)
        event = QtGui.QMouseEvent(QtCore.QEvent.MouseMove, pos2, w.mapToGlobal(pos2), button, button, Qt.NoModifier)
        QApplication.postEvent(w, event)
        QTest.qWait(delay)
        event = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonRelease, pos2, w.mapToGlobal(pos2), button, button, Qt.NoModifier)
        QApplication.postEvent(w, event)
        QTest.qWait(delay)

    def mouseClick(self, x, y, button=None, modifier=None, delay=10, coordinates="origin"):
        if button is None:
            button = Qt.LeftButton
        if modifier is None:
            modifier = Qt.NoModifier
        if coordinates == "origin":
            pos = self.window.view.mapFromOrigin(x, y)
        elif coordinates == "scene":
            if x < 0:
                x = self.window.local_scene.width()+x
            pos = self.window.view.mapFromScene(x, y)
        QTest.mouseClick(self.window.view.viewport(), button, modifier, pos=pos, delay=delay)

    def keyPress(self, key, modifier=None, delay=10):
        if modifier is None:
            modifier = Qt.NoModifier
        QTest.keyPress(self.window, key, modifier, delay=delay)

    def wait(self, millies=100):
        QTest.qWait(millies)

    def tearDown(self):
        # close window
        QTest.qWait(100)
        if "window" in dir(self):
            self.window.close()
            QTest.qWait(100)
            self.window.data_file.db.close()

        # remove database
        if os.path.exists(self.database_path) and not self.database_already_existed:
            os.remove(self.database_path)
        if os.path.exists(self.mask_folder_path) and not self.maskfolder_already_existed:
            shutil.rmtree(self.mask_folder_path)
