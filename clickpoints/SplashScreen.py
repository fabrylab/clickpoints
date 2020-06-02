#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SplashScreen.py

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

from qtpy import QtWidgets, QtGui, QtCore
import os
import sys

def StartSplashScreen():
    global app, splash
    try:
        return app, splash
    except NameError:
        pass
    try:
        app
    except NameError:
        app = QtWidgets.QApplication(sys.argv)

    # Create and display the splash screen
    splash_pix = QtGui.QPixmap(os.path.join(os.path.dirname(__file__), 'icons', 'Splash.png'))
    splash = QtWidgets.QSplashScreen(splash_pix, QtCore.Qt.WindowStaysOnTopHint)
    splash.setMask(splash_pix.mask())
    splash.show()
    app.processEvents()
    return app, splash

def StopSplashScreen(window):
    global splash
    try:
        splash.finish(window)
    except NameError:
        pass

if __name__ == "__main__":
    import time
    StartSplashScreen()
    time.sleep(10)
