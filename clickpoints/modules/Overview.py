#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Overview.py

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

from __future__ import division, print_function

from qtpy import QtCore, QtGui, QtWidgets

from qimage2ndarray import array2qimage, rgb_view
from clickpoints.includes.Tools import BoxGrabber

from clickpoints.includes.Tools import GraphicsItemEventFilter, disk, PosToArray, BroadCastEvent

try:
    import thread  # python 3
except ImportError:
    import _thread  # python 3

from PIL import Image
from PIL.ExifTags import TAGS
import time
import os
import numpy as np

def get_exif(fn):
    ret = {}
    i = Image.open(fn)
    info = i._getexif()
    for tag, value in info.items():
        decoded = TAGS.get(tag, tag)
        ret[decoded] = value
    return ret

class loaderSignals(QtCore.QObject):
    sig = QtCore.Signal(int)

class checkUpdateThread(QtCore.QThread):
    def __init__(self, parent):
        super(QtCore.QThread, self).__init__()
        self.exiting = False
        self.signal = loaderSignals()
        self.parent = parent

    def run(self):
        time.sleep(0.5)
        for i in xrange(len(self.parent.qimages)):
            print("Threading", i)

            thumb = self.parent.window.media_handler.GetThumbnails(i)
            self.parent.shapes[i] = thumb.shape
            self.parent.qimages[i] = array2qimage(thumb)
            self.signal.sig.emit(i)
            time.sleep(0.06)

class Overview(QtWidgets.QGraphicsRectItem):
    def __init__(self, parent_hud, window, image_display, config):
        QtGui.QGraphicsRectItem.__init__(self, parent_hud)
        self.config = config

        self.window = window
        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))

        self.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 250)))
        self.setZValue(30)

        self.setRect(QtGui.QRectF(0, 0, 110, 110))
        BoxGrabber(self)
        self.dragged = False

        self.hidden = False
        if self.config.hide_interfaces:
            self.setVisible(False)
            self.hidden = True

        self.qimages = []
        self.pixmaps = []
        self.shapes = []
        for i in xrange(600):
            self.pixmaps.append(QtGui.QGraphicsPixmapItem(self))
            self.qimages.append(QtGui.QImage())
            self.shapes.append((0, 0))

        self.offset = [0,0]

        self.t=checkUpdateThread(self)
        self.t.signal.sig.connect(self.updatePixmap)
        self.started = False

    def updatePixmap(self, index):
        self.pixmaps[index].setPixmap(QtGui.QPixmap(self.qimages[index]))
        self.pixmaps[index].mousePressEvent = lambda event, index=index: (self.ToggleOverviewInterfaceEvent(), self.window.JumpToFrame(index))
        self.resizeEvent(())

    def resizeEvent(self, event=None):
        self.setRect(QtGui.QRectF(0, 0, self.window.view.size().width(), self.window.view.size().height()))
        x = 0
        y = 0
        for i in xrange(len(self.pixmaps)):
            if x+self.shapes[i][1] > self.window.view.size().width():
                x = 0
                y += self.shapes[i][0]+10
            self.pixmaps[i].setOffset(x+self.offset[0]*0, y+self.offset[1])
            x += self.shapes[i][1]+10

    def mousePressEvent(self, event):
        self.last_pos = np.array([event.pos().x(),event.pos().y()])

    def mouseMoveEvent(self, event):
        self.offset -= self.last_pos-np.array([event.pos().x(),event.pos().y()])
        self.last_pos = np.array([event.pos().x(),event.pos().y()])
        self.resizeEvent("")

    def mouseReleaseEvent(self, event):
        pass

    def wheelEvent(self, event):
        if 0:#qt_version == '5':
            angle = event.angleDelta().y()
        else:
            angle = event.delta()
        if angle > 0:
            self.offset[1] += 50
            self.resizeEvent("")
        else:
            self.offset[1] -= 50
            self.resizeEvent("")
        event.setAccepted(True)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_F3:
            # @key F3: toggle Overview
            if self.started == False:
                self.t.start()
                self.started = True
            self.ToggleOverviewInterfaceEvent()

    def ToggleOverviewInterfaceEvent(self):
        self.setVisible(self.hidden)
        self.hidden = not self.hidden

    @staticmethod
    def file():
        return __file__
