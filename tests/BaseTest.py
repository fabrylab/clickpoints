#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BaseTest.py

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

import os
import shutil
import sys

import qtawesome as qta
import ClickPoints
from qtpy.QtTest import QTest
from qtpy.QtCore import Qt
from qtpy import QtGui
from qtpy import QtCore
from qtpy.QtWidgets import QApplication

app = QApplication(sys.argv)

class BaseTest():
    test_path = None

    def createInstance(self, path):
        global __path__
        """ Create the GUI """
        if "__path__" in globals():
            self.test_path = os.path.abspath(os.path.normpath(os.path.join(__path__, "..", "..", path)))
        else:
            __path__ = os.path.dirname(__file__)
            self.test_path = os.path.abspath(os.path.normpath(os.path.join(__path__, "..", "..", path)))

        print("Test Path", self.test_path)
        sys.argv = [__file__, r"-srcpath="+self.test_path]
        print(sys.argv)
        config = ClickPoints.LoadConfig()
        for addon in config.addons:
            with open(addon + ".py") as f:
                code = compile(f.read(), addon + ".py", 'exec')
                exec(code)

        self.window = ClickPoints.ClickPointsWindow(config)
        #self.window.show()

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

    def wait_for_image_load(self):
        # wait for image to be loaded
        while self.window.loading_image:
            QTest.qWait(1)

    def tearDown(self):
        # close window
        QTest.qWait(100)
        if "window" in dir(self):
            self.window.data_file.exists = True  # to prevent the "do you want to save" window
            self.window.close()
            QTest.qWait(100)
            self.window.data_file.db.close()
