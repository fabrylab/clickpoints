#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Tools.py

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

import os
import sys
from typing import Any, List, Union, Optional

import numpy as np
import qtawesome as qta
from qtpy import QtGui, QtCore, QtWidgets


def array2qimage(a: np.ndarray) -> QtGui.QImage:
    # get the dimensions and color channels
    h, w, c = a.shape
    # get the number of bytes per line
    bytesPerLine = a.nbytes // h
    if not all(np.diff(a.strides) > 0):
        a = a.data.tobytes()
    else:
        a = a.data
    # a grayscale image
    if c == 1:
        return QtGui.QImage(a, w, h, bytesPerLine, QtGui.QImage.Format_Grayscale8)
    # a RGB image
    if c == 3:
        return QtGui.QImage(a, w, h, bytesPerLine, QtGui.QImage.Format_RGB888)
    # a RGBa image
    if c == 4:
        return QtGui.QImage(a, w, h, bytesPerLine, QtGui.QImage.Format_RGBA8888)


def disk(radius: int) -> np.ndarray:
    disk_array = np.zeros((radius * 2 + 1, radius * 2 + 1))
    for x in range(radius * 2 + 1):
        for y in range(radius * 2 + 1):
            if np.sqrt((radius - x) ** 2 + (radius - y) ** 2) < radius:
                disk_array[y, x] = True
    return disk_array


def PosToArray(pos: QtCore.QPoint) -> np.ndarray:
    return np.array([pos.x(), pos.y()])


def rotate_list(l: list, n: list) -> list:
    return l[n:] + l[:n]


broadcast_modules = []


def SetBroadCastModules(modules: List[Any]) -> None:
    global broadcast_modules
    broadcast_modules = modules


def BroadCastEvent(modules: List[Any], function: str, *args, **kwargs) -> None:
    global broadcast_modules
    for module in modules:
        if function in dir(module):
            getattr(module, function)(*args, **kwargs)
    args = list(args)
    args.insert(0, function)
    for module in modules:
        if "receiveBroadCastEvent" in dir(module):
            getattr(module, "receiveBroadCastEvent")(*args, **kwargs)


def BroadCastEvent2(function: str, *args, **kwargs) -> None:
    global broadcast_modules
    for module in broadcast_modules:
        if function in dir(module):
            getattr(module, function)(*args, **kwargs)
    args = list(args)
    args.insert(0, function)
    for module in broadcast_modules:
        if "receiveBroadCastEvent" in dir(module):
            getattr(module, "receiveBroadCastEvent")(*args, **kwargs)


def HiddeableLayout(parent_layout: QtWidgets.QLayout, layout_class: QtWidgets.QLayout) -> QtWidgets.QLayout:
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
    def __init__(self, window: "ClickPointsWindow", file: str, modules: List[Any] = []) -> None:
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

    def ShowHelpText(self) -> None:
        if self.isVisible():
            self.setVisible(False)
        else:
            if self.text == "":
                self.LoadTexts()
                BoxGrabber(self)
            self.setVisible(True)

    def LoadTexts(self) -> None:
        for file_ in self.files:
            try:
                self.UpdateText(file_)
            except AttributeError:
                pass
        self.DisplayText()

    def UpdateText(self, file: str) -> None:
        import re
        if file[-4:] == ".pyc":
            file = file[:-4] + ".py"
        if os.path.exists(file):
            with open(file) as fp:
                for line in fp.readlines():
                    m = re.match(r'\w*# @key (.*)$', line.strip())
                    if m:
                        self.text += m.groups()[0].replace(":", ":\t", 1) + "\n"

    def DisplayText(self) -> None:
        self.help_text.setText(self.text[:-1])
        rect = self.help_text.boundingRect()
        rect.setX(-5)
        rect.setWidth(rect.width() + 5)
        rect.setHeight(rect.height() + 15)
        self.setRect(rect)

    def mousePressEvent(self, event) -> None:
        pass

    def mouseMoveEvent(self, event) -> None:
        pass

    def mouseReleaseEvent(self, event) -> None:
        pass

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
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
    def __init__(self, parent: QtWidgets.QWidget, name: str = "", start_value: Optional[int] = None, max_value: int = 100,
                 min_value: int = 0, font: Optional[QtGui.QFont] = None, scale: float = 1) -> None:
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
            font = QtGui.QFont("", 11 / scale)
        else:
            font.setPointSize(11 / scale)
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

    def mousePressEvent(self, event) -> None:
        if event.button() == 1:
            self.dragged = True

    def mouseMoveEvent(self, event) -> None:
        if self.dragged:
            pos = event.pos()
            x = pos.x()
            if x < 0: x = 0
            if x > 100: x = 100
            self.setValue(x / 100. * self.maxValue + self.minValue)

    def reset(self) -> None:
        self.setValue(self.start_value, True)

    def setValue(self, value: Union[float, int], noCall: bool = False) -> None:
        self.value = value
        self.text.setText(self.name + ": " + self.format % value)
        self.slideMarker.setPos((value - self.minValue) * 100 / self.maxValue, 0)
        if not noCall:
            self.valueChanged(value)

    def valueChanged(self, value: int) -> None:
        pass

    def mouseReleaseEvent(self, event) -> None:
        self.dragged = False

    def setText(self, text: str) -> None:
        self.name = text
        self.text.setText(self.name + ": " + self.format % self.value)


class BoxGrabber(QtWidgets.QGraphicsRectItem):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
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

    def mousePressEvent(self, event) -> None:
        if event.button() == 1:
            self.dragged = True
            self.drag_offset = self.parent.mapToParent(self.mapToParent(event.pos())) - self.parent.pos()

    def mouseMoveEvent(self, event) -> None:
        if self.dragged:
            pos = self.parent.mapToParent(self.mapToParent(event.pos())) - self.drag_offset
            self.parent.setPos(pos.x(), pos.y())

    def mouseReleaseEvent(self, event) -> None:
        self.dragged = False


class TextButtonSignals(QtCore.QObject):
    clicked = QtCore.Signal()


class TextButton(QtWidgets.QGraphicsRectItem):
    def __init__(self, parent: QtWidgets.QWidget, width: int, text: str = "", font: Optional[QtGui.QFont] = None,
                 scale: float = 1) -> None:
        QtWidgets.QGraphicsRectItem.__init__(self, parent)

        self.parent = parent
        self.setAcceptHoverEvents(True)
        # self.setCursor(QCursor(QtCore.Qt.OpenHandCursor))

        self.text = QtWidgets.QGraphicsSimpleTextItem(self)
        if font is None:
            font = QtGui.QFont("", 11 / scale)
        else:
            font.setPointSize(11 / scale)
        self.text.setFont(font)
        self.text.setText(text)
        self.text.setPos((width - self.text.boundingRect().width()) / 2 + 1, 0)
        self.text.setBrush(QtGui.QBrush(QtGui.QColor("white")))

        self.setRect(QtCore.QRectF(0, 0, width, self.text.boundingRect().height()))

        self.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 128)))
        self.signals = TextButtonSignals()
        self.clicked = self.signals.clicked

    def hoverEnterEvent(self, event) -> None:
        self.setBrush(QtGui.QBrush(QtGui.QColor(128, 128, 128, 128)))

    def hoverLeaveEvent(self, event) -> None:
        self.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 128)))

    def mousePressEvent(self, event) -> None:
        if event.button() == 1:
            self.clicked.emit()

    def mouseReleaseEvent(self, event) -> None:
        pass

    def setText(self, text: str) -> None:
        self.text.setText(text)


class MyCommandButton(QtWidgets.QGraphicsRectItem):

    def __init__(self, parent, marker_handler, icon, pos, scale):
        QtWidgets.QGraphicsRectItem.__init__(self, parent)
        self.parent = parent
        self.marker_handler = marker_handler

        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))

        self.setAcceptHoverEvents(True)
        self.active = False

        self.setZValue(9)

        self.pixmap = QtWidgets.QGraphicsPixmapItem(self)
        self.pixmap.setPixmap(icon.pixmap(16 * scale))

        self.setRect(-5 * scale, -3 * scale, 26 * scale, 22 * scale)
        self.setPos(pos[0] * scale, pos[1] * scale)

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
            self.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255, 128 + 128 / 2)))

    def hoverLeaveEvent(self, event):
        if self.active is False:
            self.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255, 128)))

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked()

    def delete(self):
        # delete from scene
        self.scene().removeItem(self)


class MyToolGroup(QtWidgets.QGraphicsPathItem):
    buttons = None
    active_index = 0

    def __init__(self, parent, font, scale_factor, group_name):
        QtWidgets.QGraphicsPathItem.__init__(self, parent)
        self.font = font
        self.scale_factor = scale_factor
        self.buttons = []
        self.group_name = group_name

    def setTools(self, tools, parent_class):
        self.command_object = parent_class

        self.tools = tools

        self.tool_buttons = []
        for index, tool in enumerate(self.tools):
            if self.getAlign() == QtCore.Qt.AlignLeft:
                pos = (30 + (26 + 5) * index, 10)
            else:
                pos = (-30 - (26 + 5) * index, 10)
            button = MyCommandButton(self, self, tool.getIcon(), pos,
                                     scale=self.scale_factor)
            button.setToolTip(tool.getTooltip())
            button.clicked = lambda i=index: self.selectTool(i)
            self.tool_buttons.append(button)
            self.tools[index].button = button

        self.tool_index = -1
        self.tool_index_clicked = -1

    def getAlign(self):
        return QtCore.Qt.AlignLeft

    def selectTool(self, index, temporary=False):
        if self.tool_index == index:
            return

        if self.tool_index >= 0:
            self.tools[self.tool_index].setInactive()
        # set the tool
        self.tool_index = index
        # and if not temporary the "clicked" tool
        # (this is for temporary changing the tool with Ctrl or Alt)
        if not temporary:
            self.tool_index_clicked = index

        if self.tool_index >= 0:
            # and notify the other modules
            BroadCastEvent(self.command_object.modules, "eventToolSelected", self.group_name, self.tool_index)

            self.tools[self.tool_index].setActive()

        # set the cursor according to the tool
        self.tools[self.tool_index].setCursor()

    def eventToolSelected(self, module, tool):
        if module == self.group_name:
            return
        # if another module has selected a tool, we deselect our tool
        self.selectTool(-1)

    def setVisible(self, visible: bool):
        if visible is False:
            self.selectTool(-1)
        return QtWidgets.QGraphicsPathItem.setVisible(self, visible)


class MyTextButton(QtWidgets.QGraphicsRectItem):
    def __init__(self, parent, font, scale=1):
        QtWidgets.QGraphicsRectItem.__init__(self, parent)

        self.scale_factor = scale
        self.parent = parent

        # get hover events and set to inactive
        self.setAcceptHoverEvents(True)
        self.active = False

        # define the font
        self.font = font
        self.font.setPointSize(14)

        # initialize the tex
        self.text = QtWidgets.QGraphicsSimpleTextItem(self)
        self.text.setFont(self.font)
        self.text.setZValue(10)
        # self.updateText()

        # set the brush for the background color
        self.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 128)))
        self.setZValue(9)

    def setAlign(self, align):
        self.align = align

    def getText(self):
        return "text"

    def getColor(self):
        return QtGui.QColor("white")

    def updateText(self):
        # get text and color from type
        self.text.setText(self.getText())
        # apply color
        self.text.setBrush(QtGui.QBrush(self.getColor()))
        # update rect to fit text
        rect = self.text.boundingRect()
        rect.setX(-5 * self.scale_factor)
        rect.setWidth(rect.width() + 5 * self.scale_factor)
        self.setRect(rect)
        x, y = self.getPos()

        if self.getAlign() == "left":
            self.setPos(x, y)
        else:
            self.setPos(-rect.width() + x * self.scale_factor, y * self.scale_factor)

    def setText(self, text):
        # get text and color from type
        self.text.setText(text)
        # update rect to fit text
        rect = self.text.boundingRect()
        rect.setX(-5 * self.scale_factor)
        rect.setWidth(rect.width() + 5 * self.scale_factor)
        self.setRect(rect)

    def setColor(self, color):
        # apply color
        self.text.setBrush(QtGui.QBrush(color))

    def setPosition(self, x, y):
        if self.align == QtCore.Qt.AlignLeft:
            self.setPos(x * self.scale_factor, y * self.scale_factor)
        else:
            self.setPos(-self.rect().width() + x * self.scale_factor, y * self.scale_factor)

    def setToActiveColor(self):
        # change background color
        self.active = True
        self.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255, 128)))

    def setToInactiveColor(self):
        # change background color
        self.active = False
        self.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 128)))

    def hoverEnterEvent(self, event):
        # if not active highlight on mouse over
        if self.active is False:
            self.setBrush(QtGui.QBrush(QtGui.QColor(128, 128, 128, 128)))

    def hoverLeaveEvent(self, event):
        # ... or switch back to standard color
        if self.active is False:
            self.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 128)))

    def mousePressEvent(self, event):
        pass

    def delete(self):
        # delete from scene
        self.scene().removeItem(self)


class MyTextButtonGroup(QtWidgets.QGraphicsPathItem):
    buttons = None
    active_index = 0

    def __init__(self, parent, font, scale_factor):
        QtWidgets.QGraphicsPathItem.__init__(self, parent)
        self.font = font
        self.scale_factor = scale_factor
        self.buttons = []

    def getAlign(self):
        return QtCore.Qt.AlignLeft

    def setButtons(self, list_of_properties):
        # add buttons if we do not have enough
        for i in range(len(self.buttons), len(list_of_properties)):
            self.buttons.append(MyTextButton(self, self.font, self.scale_factor))

        # remove buttons if we do have too much
        for i in range(len(list_of_properties), len(self.buttons)):
            self.buttons[i].delete()
        self.buttons = self.buttons[:len(list_of_properties)]

        # set the properties of the buttons
        for index, (prop, button) in enumerate(zip(list_of_properties, self.buttons)):
            button.setAlign(self.getAlign())
            button.setText(prop["text"])
            button.setColor(QtGui.QColor(prop["color"]))
            if self.getAlign() == QtCore.Qt.AlignLeft:
                button.setPosition(5, (10 + 25 * index + 25))
            else:
                button.setPosition(- 5, (10 + 25 * index + 25))
            button.mousePressEvent = lambda event, index=index: self.buttonPressEvent(event, index)

    def buttonPressEvent(self, event, index):
        pass

    def setActive(self):
        # and the tool button to active
        self.buttons[self.active_index].setToActiveColor()

    def setInatice(self):
        # and the tool button to active
        for button in self.buttons:
            button.setToInactiveColor()

    def clear(self):
        # remove all counters
        if self.buttons is not None:
            for button in self.buttons:
                button.delete()
        self.buttons = []


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

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def HTMLColorToRGB(colorstring):
    """ convert #RRGGBB to an (R, G, B) tuple """
    colorstring = str(colorstring).strip()
    if colorstring[0] == '#': colorstring = colorstring[1:]
    if len(colorstring) != 6 and len(colorstring) != 8:
        raise ValueError("input #%s is not in #RRGGBB format" % colorstring)
    return [int(colorstring[i * 2:i * 2 + 2], 16) for i in range(int(len(colorstring) / 2))]


def IconFromFile(filename, color=None):
    pixmap = QtGui.QPixmap(os.path.join(os.environ["CLICKPOINTS_ICON"], filename))
    if color is None:
        color = QtGui.QColor(50, 50, 50)
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
