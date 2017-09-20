#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Tools.py

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

from __future__ import division, print_function

import qtawesome as qta
from qtpy import QtGui, QtCore, QtWidgets

import numpy as np
import os
import sys


def disk(radius):
    disk_array = np.zeros((radius * 2 + 1, radius * 2 + 1))
    for x in range(radius * 2 + 1):
        for y in range(radius * 2 + 1):
            if np.sqrt((radius - x) ** 2 + (radius - y) ** 2) < radius:
                disk_array[y, x] = True
    return disk_array


def PosToArray(pos):
    return np.array([pos.x(), pos.y()])

def rotate_list(l,n):
    return l[n:] + l[:n]

broadcast_modules = []
def SetBroadCastModules(modules):
    global broadcast_modules
    broadcast_modules = modules

def BroadCastEvent(modules, function, *args, **kwargs):
    global broadcast_modules
    for module in modules:
        if function in dir(module):
            eval("module."+function+"(*args, **kwargs)")
    args = list(args)
    args.insert(0, function)
    for module in modules:
        if "receiveBroadCastEvent" in dir(module):
            eval("module.receiveBroadCastEvent(*args, **kwargs)")

def BroadCastEvent2(function, *args, **kwargs):
    global broadcast_modules
    for module in broadcast_modules:
        if function in dir(module):
            eval("module."+function+"(*args, **kwargs)")
    args = list(args)
    args.insert(0, function)
    for module in broadcast_modules:
        if "receiveBroadCastEvent" in dir(module):
            eval("module.receiveBroadCastEvent(*args, **kwargs)")

def HiddeableLayout(parent_layout, layout_class):
    widget = QtWidgets.QWidget()
    parent_layout.addWidget(widget)
    new_layout = layout_class(widget)
    new_layout.widget = widget
    new_layout.setHidden = widget.setHidden
    new_layout.setVisible = widget.setVisible
    new_layout.isHidden = widget.isHidden
    new_layout.isVisible = widget.isVisible
    return new_layout

class HelpText(QtWidgets.QGraphicsRectItem):
    def __init__(self, window, file, modules=[]):
        QtWidgets.QGraphicsRectItem.__init__(self, window.view.hud)

        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))

        self.help_text = QtWidgets.QGraphicsSimpleTextItem(self)
        self.help_text.setFont(QtGui.QFont("", 11))
        self.help_text.setPos(0, 10)
        self.help_text.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255)))

        self.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 128)))
        self.setPos(100, 100)
        self.setZValue(19)

        self.button = QtWidgets.QPushButton()
        self.button.setCheckable(True)
        self.button.setIcon(qta.icon('fa.question'))
        self.button.setToolTip("display help")
        self.button.clicked.connect(self.ShowHelpText)
        window.layoutButtons.addWidget(self.button)

        self.files = [file]
        for mod in modules:
            try:
                self.files.append(mod.file())
            except AttributeError:
                pass
        self.text = ""
        self.setVisible(False)

    def ShowHelpText(self):
        if self.isVisible():
            self.setVisible(False)
        else:
            if self.text == "":
                self.LoadTexts()
                BoxGrabber(self)
            self.setVisible(True)

    def LoadTexts(self):
        for file_ in self.files:
            try:
                self.UpdateText(file_)
            except AttributeError:
                pass
        self.DisplayText()

    def UpdateText(self, file):
        import re
        if file[-4:] == ".pyc":
            file = file[:-4]+".py"
        if os.path.exists(file):
            with open(file) as fp:
                for line in fp.readlines():
                    m = re.match(r'\w*# @key (.*)$', line.strip())
                    if m:
                        self.text += m.groups()[0].replace(":", ":\t", 1) + "\n"

    def DisplayText(self):
        self.help_text.setText(self.text[:-1])
        rect = self.help_text.boundingRect()
        rect.setX(-5)
        rect.setWidth(rect.width() + 5)
        rect.setHeight(rect.height() + 15)
        self.setRect(rect)

    def mousePressEvent(self, event):
        pass

    def mouseMoveEvent(self, event):
        pass

    def mouseReleaseEvent(self, event):
        pass

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_F1:
            # @key F1: toggle help window
            self.ShowHelpText()


class MySpinBox(QtWidgets.QSpinBox):
    def keyPressEvent(self, *args, **kwargs):
        event = args[0]
        if event.key() == QtCore.Qt.Key_Return:
            res = QtWidgets.QSpinBox.keyPressEvent(self, *args, **kwargs)
            self.window().setFocus()
            return res
        return QtWidgets.QSpinBox.keyPressEvent(self, *args, **kwargs)


class MySlider(QtWidgets.QGraphicsRectItem):
    def __init__(self, parent, name="", start_value=None, max_value=100, min_value=0, font=None):
        QtWidgets.QGraphicsRectItem.__init__(self, parent)

        self.parent = parent
        self.name = name
        self.maxValue = max_value
        self.minValue = min_value
        self.format = "%.2f"

        self.setCursor(QtGui.QCursor(QtCore.Qt.OpenHandCursor))
        self.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 0)))

        self.text = QtWidgets.QGraphicsSimpleTextItem(self)
        if font is None:
            font = QtGui.QFont("", 11)
        else:
            font.setPointSize(11)
        self.text.setFont(font)
        self.text.setPos(0, -23)
        self.text.setBrush(QtGui.QBrush(QtGui.QColor("white")))

        self.sliderMiddel = QtWidgets.QGraphicsRectItem(self)
        self.sliderMiddel.setRect(QtCore.QRectF(0, 0, 100, 1))
        self.sliderMiddel.setPen(QtGui.QPen(QtGui.QColor("white")))

        path = QtGui.QPainterPath()
        path.addEllipse(-5, -5, 10, 10)
        self.slideMarker = QtWidgets.QGraphicsPathItem(path, self)
        self.slideMarker.setBrush(QtGui.QBrush(QtGui.QColor(255, 0, 0, 255)))

        self.setRect(QtCore.QRectF(-5, -5, 110, 10))
        self.dragged = False

        self.value = (self.maxValue + self.minValue) * 0.5
        if start_value is not None:
            self.value = start_value
        self.start_value = self.value
        self.setValue(self.value)

    def mousePressEvent(self, event):
        if event.button() == 1:
            self.dragged = True

    def mouseMoveEvent(self, event):
        if self.dragged:
            pos = event.pos()
            x = pos.x()
            if x < 0: x = 0
            if x > 100: x = 100
            self.setValue(x / 100. * self.maxValue + self.minValue)

    def reset(self):
        self.setValue(self.start_value, True)

    def setValue(self, value, noCall=False):
        self.value = value
        self.text.setText(self.name + ": " + self.format % value)
        self.slideMarker.setPos((value - self.minValue) * 100 / self.maxValue, 0)
        if not noCall:
            self.valueChanged(value)

    def valueChanged(self, value):
        pass

    def mouseReleaseEvent(self, event):
        self.dragged = False

class BoxGrabber(QtWidgets.QGraphicsRectItem):
    def __init__(self, parent):
        QtWidgets.QGraphicsRectItem.__init__(self, parent)

        self.parent = parent
        self.setCursor(QtGui.QCursor(QtCore.Qt.OpenHandCursor))
        width = parent.rect().width()
        self.setRect(QtCore.QRectF(0, 0, width, 10))
        self.setPos(parent.rect().x(), 0)

        self.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 128)))

        path = QtGui.QPainterPath()
        path.moveTo(5, 3)
        path.lineTo(width - 5, 3)
        path.moveTo(5, 6)
        path.lineTo(width - 5, 6)
        pathItem = QtWidgets.QGraphicsPathItem(path, self)
        pathItem.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255)))
        pathItem.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255)))

        self.dragged = False
        self.drag_offset = None

    def mousePressEvent(self, event):
        if event.button() == 1:
            self.dragged = True
            self.drag_offset = self.parent.mapToParent(self.mapToParent(event.pos())) - self.parent.pos()

    def mouseMoveEvent(self, event):
        if self.dragged:
            pos = self.parent.mapToParent(self.mapToParent(event.pos())) - self.drag_offset
            self.parent.setPos(pos.x(), pos.y())

    def mouseReleaseEvent(self, event):
        self.dragged = False


class TextButtonSignals(QtCore.QObject):
    clicked = QtCore.Signal()

class TextButton(QtWidgets.QGraphicsRectItem):
    def __init__(self, parent, width, text="", font=None):
        QtWidgets.QGraphicsRectItem.__init__(self, parent)

        self.parent = parent
        self.setAcceptHoverEvents(True)
        #self.setCursor(QCursor(QtCore.Qt.OpenHandCursor))

        self.text = QtWidgets.QGraphicsSimpleTextItem(self)
        if font is None:
            font = QtGui.QFont("", 11)
        else:
            font.setPointSize(11)
        self.text.setFont(font)
        self.text.setText(text)
        self.text.setPos((width-self.text.boundingRect().width())/2+1, 0)
        self.text.setBrush(QtGui.QBrush(QtGui.QColor("white")))

        self.setRect(QtCore.QRectF(0, 0, width, self.text.boundingRect().height()))

        self.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 128)))
        self.signals = TextButtonSignals()
        self.clicked = self.signals.clicked

    def hoverEnterEvent(self, event):
        self.setBrush(QtGui.QBrush(QtGui.QColor(128, 128, 128, 128)))

    def hoverLeaveEvent(self, event):
        self.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 128)))

    def mousePressEvent(self, event):
        if event.button() == 1:
            self.clicked.emit()

    def mouseReleaseEvent(self, event):
        pass


class MyCommandButton(QtWidgets.QGraphicsRectItem):

    def __init__(self, parent, marker_handler, icon, pos):
        QtWidgets.QGraphicsRectItem.__init__(self, parent)
        self.parent = parent
        self.marker_handler = marker_handler

        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))

        self.setAcceptHoverEvents(True)
        self.active = False

        self.setZValue(9)

        self.pixmap = QtWidgets.QGraphicsPixmapItem(self)
        self.pixmap.setPixmap(icon.pixmap(16))

        self.setRect(-5, -3, 26, 22)
        self.setPos(*pos)

        self.clicked = lambda: 0

        self.SetToInactiveColor()

    def SetToActiveColor(self):
        self.active = True
        self.setBrush(QtGui.QBrush(QtGui.QColor(204, 228, 247, 255)))
        self.setPen(QtGui.QPen(QtGui.QColor(0, 84, 153)))

    def SetToInactiveColor(self):
        self.active = False
        self.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255, 128)))
        self.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0)))

    def hoverEnterEvent(self, event):
        if self.active is False:
            self.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255, 128+128/2)))

    def hoverLeaveEvent(self, event):
        if self.active is False:
            self.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255, 128)))

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked()

    def delete(self):
        # delete from scene
        self.scene().removeItem(self)


class GraphicsItemEventFilter(QtWidgets.QGraphicsItem):
    def __init__(self, parent, command_object):
        super(GraphicsItemEventFilter, self).__init__(parent)
        self.commandObject = command_object
        self.active = False

    def paint(self, *args):
        pass

    def boundingRect(self):
        return QtCore.QRectF(0, 0, 0, 0)

    def sceneEventFilter(self, scene_object, event):
        if not self.active:
            return False
        return self.commandObject.sceneEventFilter(event)

# enables .access on dicts
class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    def __getattr__(self, attr):
        return self.get(attr)
    __setattr__= dict.__setitem__
    __delattr__= dict.__delitem__


def HTMLColorToRGB(colorstring):
    """ convert #RRGGBB to an (R, G, B) tuple """
    colorstring = str(colorstring).strip()
    if colorstring[0] == '#': colorstring = colorstring[1:]
    if len(colorstring) != 6 and len(colorstring) != 8:
        raise ValueError("input #%s is not in #RRGGBB format" % colorstring)
    return [int(colorstring[i*2:i*2+2], 16) for i in range(int(len(colorstring)/2))]


def IconFromFile(filename, color=None):
    pixmap = QtGui.QPixmap(os.path.join(os.environ["CLICKPOINTS_ICON"], filename))
    if color is not None:
        mask = pixmap.createMaskFromColor(QtGui.QColor('black'), QtCore.Qt.MaskOutColor)
        pixmap.fill((color))
        pixmap.setMask(mask)

    return QtGui.QIcon(pixmap)


def BoundBy(value, min, max):
    # return value bound by min and max
    if value is None:
        return min
    if value < min:
        return min
    if value > max:
        return max
    return value


class PrintHook:
    def __init__(self, out, storage_path, func, reset=False):
        self.func = func
        self.origOut = None

        if out:
            sys.stdout = self
            self.origOut = sys.__stdout__
        else:
            sys.stderr = self
            self.origOut = sys.__stderr__

        self.path = os.path.join(storage_path, "ClickPoints_%d.log" % os.getpid())
        if reset:
            with open(self.path, "w") as fp:
                fp.write("")

    def write(self, text):
        # write to stdout, file and call the function
        self.origOut.write(text)
        with open(self.path, "a") as fp:
            fp.write(text)
        if self.func:
            self.func(text)

    def __getattr__(self, name):
        # pass the rest to the original output
        return self.origOut.__getattr__(name)

global hook1, hook2
def StartHooks(reset=False):
    global hook1, hook2
    if sys.platform[:3] == 'win':
        storage_path = os.path.join(os.getenv('APPDATA'), "..", "Local", "Temp", "ClickPoints")
    else:
        storage_path = os.path.expanduser("~/.clickpoints/")
    hook1 = PrintHook(1, storage_path, None, reset)
    hook2 = PrintHook(0, storage_path, None, reset)

def GetHooks():
    global hook1, hook2
    return hook1, hook2
