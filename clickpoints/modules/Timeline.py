#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Timeline.py

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

import asyncio
import datetime
import os
import re
import time
from datetime import timedelta
from typing import Optional, Set, Union, Any

import numpy as np
import qtawesome as qta
from numpy import float64, int32, ndarray
from qtpy import QtGui, QtCore, QtWidgets
from quamash import QEventLoop

from clickpoints.includes.Database import DataFileExtended
from clickpoints.includes.QtShortCuts import AddQSpinBox
from clickpoints.includes.Tools import MySpinBox, HiddeableLayout


def timedelta_mul(self: timedelta, other: float) -> timedelta:
    if isinstance(other, (int, float)):
        return datetime.timedelta(seconds=self.total_seconds() * other)
    else:
        return NotImplemented


def timedelta_div(self: timedelta, other: int) -> timedelta:
    if isinstance(other, (int, float)):
        return datetime.timedelta(seconds=self.total_seconds() / other)
    else:
        return NotImplemented


def BoundBy(value: Any, min: Any, max: Any) -> Any:
    if value is None:
        return min
    if value < min:
        return min
    if value > max:
        return max
    return value


def roundTime(dt: Optional[datetime.datetime] = None, roundTo: float = 60) -> datetime:
    """Round a datetime object to any time laps in seconds
    dt : datetime.datetime object, default now.
    roundTo : Closest number of seconds to round to, default 1 minute.
    Author: Thierry Husson 2012 - Use it as you want but don't blame me.
    """
    if dt == None: dt = datetime.datetime.now()
    seconds = (dt - dt.min).seconds
    # // is a floor division, not a comment on following line:
    rounding = (seconds + roundTo / 2) // roundTo * roundTo
    return dt + datetime.timedelta(0, rounding - seconds, -dt.microsecond)


def roundValue(value, modulo, offset=0):
    return int((value - offset) // modulo) * modulo + offset


def DateDivision(x, y):
    return x.total_seconds() / y.total_seconds()


def Remap(value: Any, minmax1: list, minmax2: list) -> Any:
    length1 = minmax1[1] - minmax1[0]
    length2 = minmax2[1] - minmax2[0]
    if length1 == 0:
        return 0
    try:
        percentage = (value - minmax1[0]) / length1
    except TypeError:
        percentage = DateDivision((value - minmax1[0]), length1)
    try:
        value2 = percentage * length2 + minmax2[0]
    except TypeError:
        value2 = datetime.timedelta(seconds=percentage * length2.total_seconds()) + minmax2[0]
    return value2


class SelectFrame(QtWidgets.QDialog):
    def __init__(self, frame, max_frame):
        QtWidgets.QDialog.__init__(self)

        # Widget
        self.setWindowTitle("Select Frame - ClickPoints")
        self.setWindowIcon(qta.icon("fa.play"))
        self.setModal(True)
        main_layout = QtWidgets.QVBoxLayout(self)
        self.spinBox = AddQSpinBox(main_layout, "Frame Number:", value=frame, float=False)
        self.spinBox.setRange(0, max_frame)
        # set LineEdit text to selected
        self.spinBox.findChild(QtWidgets.QLineEdit).selectAll()

        button2 = QtWidgets.QPushButton("Ok")
        button2.clicked.connect(lambda: self.done(self.spinBox.value() + 1))
        self.spinBox.managingLayout.addWidget(button2)


class TimeLineGrabberSignal(QtCore.QObject):
    sliderPressed = QtCore.Signal()
    sliderMoved = QtCore.Signal()
    sliderReleased = QtCore.Signal()


class TimeLineGrabber(QtWidgets.QGraphicsPathItem):
    def __init__(self, parent: Union["TimeLineSlider", "RealTimeSlider"], value: int, path: QtGui.QPainterPath,
                 gradient: QtGui.QLinearGradient, parent_item: Optional[QtWidgets.QGraphicsPathItem] = None) -> None:
        if parent_item is None:
            QtWidgets.QGraphicsPathItem.__init__(self, parent.parent)
        else:
            QtWidgets.QGraphicsPathItem.__init__(self, parent_item)
        self.parent = parent
        self.pixel_range = [0, 100]
        self.value_range = [0, 100]
        self.setCursor(QtGui.QCursor(QtCore.Qt.OpenHandCursor))
        self.dragged = False

        self.setPath(path)
        self.setBrush(QtGui.QBrush(gradient))
        self.setZValue(10)
        self.value = value

        self.signal = TimeLineGrabberSignal()

    def setPixelRange(self, min: float, max: float) -> None:
        self.pixel_range = [min, max]
        self.updatePos()

    def setValueRange(self, min: Any, max: Any) -> None:
        self.value_range = [min, max]

    def setValue(self, value: Any) -> None:
        self.value = int(round(value))
        self.updatePos()

    def updatePos(self) -> None:
        self.setPos(self.value_to_pixel(self.value), 0)

    def mousePressEvent(self, event: QtCore.QEvent) -> None:
        if event.button() == 1:
            self.dragged = True
            self.signal.sliderPressed.emit()

    def mouseMoveEvent(self, event: QtCore.QEvent) -> None:
        if self.dragged:
            x = BoundBy(self.mapToParent(event.pos()).x(), self.pixel_range[0], self.pixel_range[1])
            self.setValue(self.pixel_to_value(x))
            self.signal.sliderMoved.emit()

    def mouseReleaseEvent(self, event: QtCore.QEvent) -> None:
        self.dragged = False
        self.signal.sliderReleased.emit()

    def pixel_to_value(self, pixel: Any) -> Any:
        return Remap(pixel, self.pixel_range, self.value_range)

    def value_to_pixel(self, value: Any) -> Any:
        return Remap(value, self.value_range, self.pixel_range)


class TimeLineGrabberTime(TimeLineGrabber):
    # def __init__(self, *args):
    #    QGraphicsPathItem.__init__(self, None, parent.scene)

    def mouseMoveEvent(self, event: QtCore.QEvent) -> None:
        if self.dragged:
            x = self.pos().x() + event.pos().x() / self.parent.scale / self.parent.slider_line.transform().m11()
            self.setValue(self.pixel_to_value(x))

    def setValue(self, value: datetime) -> None:
        self.value = BoundBy(value, *self.value_range)
        self.updatePos()


class TimeLineSlider(QtWidgets.QGraphicsView):
    start_changed = QtCore.Signal(int)
    end_changed = QtCore.Signal(int)

    def __init__(self, max_value: int = 0, min_value: int = 0, scale: float = 1) -> None:
        QtWidgets.QGraphicsView.__init__(self)

        self.setMaximumHeight(30 * scale)
        if scale != 1:
            self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(self.sizePolicy().horizontalPolicy(), QtWidgets.QSizePolicy.Preferred)

        self.scene = QtWidgets.QGraphicsScene(self)
        self.setScene(self.scene)
        self.parent = QtWidgets.QGraphicsRectItem(None)
        self.parent.setScale(scale)
        self.scene.addItem(self.parent)
        self.scene.setBackgroundBrush(self.palette().color(QtGui.QPalette.Background))
        self.setStyleSheet("border: 0px")

        self.max_value = max_value
        self.min_value = min_value

        self.slider_line = QtWidgets.QGraphicsRectItem(self.parent)
        self.slider_line.setPen(QtGui.QPen(QtGui.QColor("black")))
        self.slider_line.setPos(0, -2.5)
        gradient = QtGui.QLinearGradient(QtCore.QPointF(0, 0), QtCore.QPointF(0, 5))
        gradient.setColorAt(0, QtGui.QColor("black"))
        gradient.setColorAt(1, QtGui.QColor(128, 128, 128))
        self.slider_line.setBrush(QtGui.QBrush(gradient))
        self.slider_line.mousePressEvent = self.SliderBarMousePressEvent

        self.slider_line_active = QtWidgets.QGraphicsRectItem(self.parent)
        self.slider_line_active.setPen(QtGui.QPen(QtGui.QColor("black")))
        self.slider_line_active.setPos(0, -2.5)
        gradient = QtGui.QLinearGradient(QtCore.QPointF(0, 0), QtCore.QPointF(0, 5))
        gradient.setColorAt(0, QtGui.QColor(128, 128, 128))
        gradient.setColorAt(1, QtGui.QColor(200, 200, 200))
        self.slider_line_active.setBrush(QtGui.QBrush(gradient))

        path = QtGui.QPainterPath()
        path.moveTo(-4, +12)
        path.lineTo(0, +2.5)
        path.lineTo(+4, +12)
        path.lineTo(-4, +12)
        gradient = QtGui.QLinearGradient(QtCore.QPointF(0, 12), QtCore.QPointF(0, 2.5))
        gradient.setColorAt(0, QtGui.QColor(255, 0, 0))
        gradient.setColorAt(1, QtGui.QColor(128, 0, 0))
        self.slider_start = TimeLineGrabber(self, 0, path, gradient)
        self.slider_start.signal.sliderMoved.connect(self.slider_start_changed)

        path = QtGui.QPainterPath()
        path.moveTo(-4, -12)
        path.lineTo(0, -2.5)
        path.lineTo(+4, -12)
        path.lineTo(-4, -12)
        gradient = QtGui.QLinearGradient(QtCore.QPointF(0, -12), QtCore.QPointF(0, -2.5))
        gradient.setColorAt(0, QtGui.QColor(255, 0, 0))
        gradient.setColorAt(1, QtGui.QColor(128, 0, 0))
        self.slider_end = TimeLineGrabber(self, 100, path, gradient)
        self.slider_end.signal.sliderMoved.connect(self.slider_end_changed)

        path = QtGui.QPainterPath()
        path.addRect(-2, -7, 5, 14)
        gradient = QtGui.QLinearGradient(QtCore.QPointF(0, -7), QtCore.QPointF(0, 14))
        gradient.setColorAt(0, QtGui.QColor(255, 0, 0))
        gradient.setColorAt(1, QtGui.QColor(128, 0, 0))
        self.slider_position = TimeLineGrabber(self, 0, path, gradient)

        self.length = 1

        self.tick_marker = {}

    def SliderBarMousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        self.setValue(self.PixelToValue(self.slider_line.mapToScene(event.pos()).x()))
        self.slider_position.signal.sliderReleased.emit()

    def addTickMarker(self, pos: int, type: int = 0, color: QtGui.QColor = QtGui.QColor("red"),
                      height: int = 12) -> None:
        if type == 1:
            color = QtGui.QColor("green")
            height = 8
        if pos in self.tick_marker and type in self.tick_marker[pos]:
            tick_marker = self.tick_marker[pos][type]
        else:
            width = self.ValueToPixel(1)
            if pos == self.max_value:
                width = 2
            tick_marker = QtWidgets.QGraphicsRectItem(0.0, -3.5, width, -height, self.parent)
        tick_marker.setPen(QtGui.QPen(color))
        tick_marker.setBrush(QtGui.QBrush(color))
        tick_marker.value = pos
        tick_marker.type = type
        tick_marker.height = height
        tick_marker.setZValue(1 + type)
        tick_marker.setPos(self.ValueToPixel(pos), 0)
        if pos not in self.tick_marker:
            self.tick_marker[pos] = {}
        self.tick_marker[pos][type] = tick_marker
        self.repaint()

    def removeTickMarker(self, pos: int, type: int = 0) -> None:
        if pos in self.tick_marker and type in self.tick_marker[pos]:
            tick_marker = self.tick_marker[pos][type]
            self.scene.removeItem(tick_marker)
            del self.tick_marker[pos][type]
            if self.tick_marker[pos] == {}:
                del self.tick_marker[pos]
            self.repaint()

    def clearTickMarker(self) -> None:
        for pos, ticks in self.tick_marker.items():
            for type, tick in ticks.items():
                self.scene.removeItem(tick)
        self.tick_marker = {}
        self.repaint()

    def getNextTick(self, pos: int, back: bool = False) -> int:
        if back is False:
            my_range = range(pos + 1, self.max_value + 1, +1)
        else:
            my_range = range(pos - 1, self.min_value - 1, -1)
        search_marked = True
        for i in my_range:
            if (i in self.tick_marker) == search_marked:
                return i
        if len(my_range) == 0:
            if back is False:
                return pos + 1
            return pos - 1
        return my_range[-1]

    def getNextTickChange(self, pos: int, back: bool = False) -> int:
        if back is False:
            my_range = range(pos + 1, self.max_value, +1)
        else:
            my_range = range(pos - 1, self.min_value, -1)
        search_marked = True
        if len(my_range) == 0:
            if back is False:
                return pos + 1
            return pos - 1
        if pos in self.tick_marker and my_range[0] in self.tick_marker:
            search_marked = False
        for i in my_range:
            if (i in self.tick_marker) == search_marked:
                return i
        return my_range[-1]

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        self.length = (self.size().width() - 20) / self.parent.scale()
        self.slider_line.setRect(0, 0, self.length, 5)
        self.slider_line_active.setRect(self.ValueToPixel(self.slider_start.value), 0,
                                        self.ValueToPixel(self.slider_end.value) - self.ValueToPixel(
                                            self.slider_start.value), 5)
        self.ensureVisible(self.slider_line)
        for pos, ticks in self.tick_marker.items():
            for type, tick in ticks.items():
                tick.setPos(self.ValueToPixel(pos), 0)
                width = self.ValueToPixel(1)
                if pos == self.max_value:
                    width = 2
                tick.setRect(0.0, -3.5, width, -tick.height)
        for marker in [self.slider_position, self.slider_start, self.slider_end]:
            marker.setPixelRange(0, self.length)
        self.repaint()

    def setRange(self, min_value: int, max_value: int) -> None:
        self.min_value = min_value
        self.max_value = max_value
        for marker in [self.slider_position, self.slider_start, self.slider_end]:
            marker.setValueRange(self.min_value, self.max_value)

    def setValue(self, value: float) -> None:
        self.slider_position.setValue(BoundBy(value, self.min_value, self.max_value))

    def setStartValue(self, value: int) -> None:
        self.slider_start.setValue(BoundBy(value, self.min_value, self.max_value))
        self.updatePlayRange()
        self.start_changed.emit(value)

    def setEndValue(self, value: float) -> None:
        self.slider_end.setValue(BoundBy(value, self.min_value, self.max_value))
        self.updatePlayRange()
        self.end_changed.emit(value)

    def PixelToValue(self, pixel: float) -> float:
        return Remap(pixel, [0, self.length], [self.min_value, self.max_value])

    def ValueToPixel(self, value: Union[int32, int]) -> Union[float, float64, int]:
        return Remap(value, [self.min_value, self.max_value], [0, self.length])

    def slider_start_changed(self) -> None:
        self.start_changed.emit(self.slider_start.value)
        if self.slider_start.value > self.slider_end.value:
            self.slider_end.setValue(self.slider_start.value)
            self.end_changed.emit(self.slider_end.value)
        self.updatePlayRange()

    def slider_end_changed(self) -> None:
        self.end_changed.emit(self.slider_end.value)
        if self.slider_start.value > self.slider_end.value:
            self.slider_start.setValue(self.slider_end.value)
            self.start_changed.emit(self.slider_start.value)
        self.updatePlayRange()

    def updatePlayRange(self) -> None:
        self.slider_line_active.setRect(self.ValueToPixel(self.slider_start.value), 0,
                                        self.ValueToPixel(self.slider_end.value) - self.ValueToPixel(
                                            self.slider_start.value), 5)

    def value(self) -> int:
        return self.slider_position.value

    def startValue(self) -> int:
        return self.slider_start.value

    def endValue(self) -> int:
        return self.slider_end.value

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        event.setAccepted(False)
        return


class RealTimeSlider(QtWidgets.QGraphicsView):
    is_hidden = True
    min_value = None
    max_value = None

    def __init__(self) -> None:
        QtWidgets.QGraphicsView.__init__(self)

        self.setMaximumHeight(30)
        # self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(self.sizePolicy().horizontalPolicy(), QtWidgets.QSizePolicy.Preferred)

        self.scene = QtWidgets.QGraphicsScene(self)
        self.setScene(self.scene)
        self.scene.setBackgroundBrush(self.palette().color(QtGui.QPalette.Background))
        self.setStyleSheet("border: 0px")

        self.slider_line = QtWidgets.QGraphicsRectItem(None)
        self.scene.addItem(self.slider_line)
        self.slider_line.setPen(QtGui.QPen(QtGui.QColor("black")))
        self.slider_line.setPos(0, 0)
        gradient = QtGui.QLinearGradient(QtCore.QPointF(0, 0), QtCore.QPointF(0, 5))
        gradient.setColorAt(0, QtGui.QColor("black"))
        gradient.setColorAt(1, QtGui.QColor(128, 128, 128))
        self.slider_line.setBrush(QtGui.QBrush(gradient))

        self.markerParent = QtWidgets.QGraphicsPathItem(self.slider_line)
        self.markerGroupParents = []
        for i in range(20):
            self.markerGroupParents.append(QtWidgets.QGraphicsPathItem(self.markerParent))

        path = QtGui.QPainterPath()
        path.addRect(-2, -7, 5, 14)
        gradient = QtGui.QLinearGradient(QtCore.QPointF(0, -7), QtCore.QPointF(0, 14))
        gradient.setColorAt(0, QtGui.QColor(255, 0, 0))
        gradient.setColorAt(1, QtGui.QColor(128, 0, 0))
        self.slider_position = TimeLineGrabberTime(self, 0, path, gradient, parent_item=self.markerGroupParents[-1])
        self.slider_position.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations)

        self.length = 1

        self.scene_panning = False

        self.tick_marker = []
        self.tick_blocks = []

        self.scale = 1
        self.pan = 0

        self.pixel_len = 1000
        self.slider_position.setPixelRange(0, self.pixel_len)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        self.length = self.size().width()
        self.slider_line.setRect(0, -0.5, self.pixel_len, 1)
        self.slider_line.resetTransform()
        self.slider_line.setTransform(QtGui.QTransform.fromScale(self.length / self.pixel_len, 1), True)
        self.setSceneRect(0, -10, self.size().width(), 20)
        self.repaint()

    def SliderBarMousePressEvent(self, event: QtCore.QEvent) -> None:
        self.setValue(self.PixelToValue(self.slider_line.mapToScene(event.pos()).x()))
        self.slider_position.signal.sliderReleased.emit()

    def addTickBlock(self, pos1: datetime, pos2: datetime) -> None:
        color = QtGui.QColor(128, 128, 128, 0)
        color2 = QtGui.QColor(128, 128, 128)
        height = 11

        x1 = Remap(pos1, [self.min_value, self.max_value], [0, self.pixel_len])
        x2 = Remap(pos2, [self.min_value, self.max_value], [0, self.pixel_len])

        tick_block = QtWidgets.QGraphicsRectItem(0, -1, x2 - x1, -height, self.markerGroupParents[0])
        tick_block.setPos(x1, 0)

        tick_block.setBrush(QtGui.QBrush(color2))
        tick_block.setPen(QtGui.QPen(color))
        tick_block.setZValue(-10)

        self.tick_blocks.append(tick_block)

    def addTickMarker(self, pos: datetime, type: int = -1, type_name: str = "",
                      color: QtGui.QColor = QtGui.QColor("red"), height: int = 12, text: str = "") -> None:
        if type == -1:
            tick_marker = QtGui.QGraphicsLineItem(0, -3, 0, -height, self.markerParent)
            tick_marker.setZValue(-10)
        else:
            if type_name == "second":
                text = "%02d:%02d:%02d" % (pos.hour, pos.minute, pos.second)
            elif type_name == "minute":
                text = "%02d:%02d" % (pos.hour, pos.minute)
            elif type_name == "hour":
                text = "%02d:%02d" % (pos.hour, pos.minute)
            elif type_name == "day":
                text = "%02d.%02d" % (pos.day, pos.month)
            elif type_name == "month":
                text = "%02d.%02d" % (pos.day, pos.month)
            elif type_name == "year":
                text = "%04d" % pos.year
            tick_marker = QtWidgets.QGraphicsLineItem(0, 3, 0, -height, self.markerGroupParents[type])
            tick_marker.setZValue(10)
        tick_marker.setPen(QtGui.QPen(color))
        if type == -1:
            tick_marker.setPen(QtGui.QPen(color, 3))
        tick_marker.value = pos
        tick_marker.type = type
        tick_marker.height = height

        tick_marker.setPos(Remap(pos, [self.min_value, self.max_value], [0, self.pixel_len]), 0)

        if text != "":
            self.font_parent = QtWidgets.QGraphicsPathItem(tick_marker)

            self.font = QtGui.QFont()
            self.font.setPointSize(8)
            self.text = QtWidgets.QGraphicsSimpleTextItem(self.font_parent)
            self.text.setFont(self.font)
            self.text.setText(text)
            offsetX = self.text.boundingRect().width()
            self.text.setPos(-offsetX * 0.5 + 1, 2)
            self.font_parent.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations)
            tick_marker.text = self.text
            tick_marker.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations)
        else:
            tick_marker.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations)
            tick_marker.text = None
        self.tick_marker.append(tick_marker)

    def setRange(self, min_value: Any, max_value: Any) -> None:
        self.min_value = min_value
        self.max_value = max_value
        for marker in [self.slider_position]:
            marker.setValueRange(self.min_value, self.max_value)

    def setValue(self, value: datetime) -> None:
        if self.min_value is not None and self.max_value is not None:
            self.slider_position.setValue(BoundBy(value, self.min_value, self.max_value))

    def PixelToValue(self, pixel: int) -> float:
        return Remap(pixel, [0, self.length], [self.min_value, self.max_value])

    def ValueToPixel(self, value: float) -> int:
        return Remap(value, [self.min_value, self.max_value], [0, self.length])

    def value(self) -> int:
        return self.slider_position.value

    def keyPressEvent(self, event: QtCore.QEvent) -> None:
        event.setAccepted(False)

    def setTimes(self, data_file: DataFileExtended) -> None:
        # remove old time ticks
        for tick in self.tick_blocks:
            if tick.scene():
                tick.scene().removeItem(tick)
        self.tick_blocks = []

        # get timestamps
        self.data_file = data_file
        timestamps = np.array(self.data_file.table_image.select(self.data_file.table_image.timestamp).where(
            self.data_file.table_image.timestamp != None).tuples().execute())

        # handle empty timeline
        if len(timestamps) == 0:
            self.min_value = datetime.datetime.today()
            self.max_value = datetime.datetime.today() + datetime.timedelta(hours=1)
            self.slider_position.setValueRange(self.min_value, self.max_value)
            self.is_hidden = True
            self.setHidden(True)
            return

        # remove obsolete dimension (Nx1 -> N)
        timestamps = timestamps[:, 0]

        self.is_hidden = False
        self.setHidden(False)

        # get min/max values
        self.min_value = np.amin(timestamps)
        self.max_value = np.amax(timestamps)
        if self.max_value == self.min_value:
            self.max_value = self.min_value + datetime.timedelta(hours=1)
        range = self.max_value - self.min_value

        # add some border
        self.min_value -= timedelta_mul(range, 0.01)
        self.max_value += timedelta_mul(range, 0.01)

        # apply ranges
        self.slider_position.setValueRange(self.min_value, self.max_value)

        # add tick blocks

        # calculate the time between frames
        deltas = timestamps[1:] - timestamps[:-1]

        # if we have only one image
        if len(deltas) == 0:
            return

        # find big gaps
        steps, = np.where(deltas > min(deltas) * 4)

        # start and end are the groups between these gaps
        starts = timestamps[np.concatenate(([0], steps + 1))]
        ends = timestamps[np.concatenate((steps, [len(timestamps) - 1]))]

        # add the groups to the timeline
        for start_time, end_time in zip(starts, ends):
            self.addTickBlock(start_time, end_time)

        # update display
        self.updateTicks()
        self.repaint()

    def updateTicks(self) -> None:
        span = self.max_value - self.min_value
        l = self.pixel_len
        time_per_pixel = timedelta_div(span, self.pixel_len)
        try:
            left_end = self.min_value + timedelta_mul(time_per_pixel, -self.pan / self.scale)
        except OverflowError:
            left_end = datetime.datetime(datetime.MINYEAR, 1, 1)
        try:
            right_end = self.min_value + timedelta_mul(time_per_pixel, (self.pixel_len - self.pan) / self.scale)
        except OverflowError:
            right_end = datetime.datetime(datetime.MAXYEAR, 1, 1)

        for tick in self.tick_marker:
            if tick.scene():
                tick.scene().removeItem(tick)
        self.tick_marker = []

        # determine the smallest possible ticks
        delta_min = timedelta_mul(right_end - left_end, 60 / self.pixel_len)  # self.PixelToValue(60)-left_end
        type_deltas = [datetime.timedelta(seconds=1),
                       # datetime.timedelta(seconds=2),
                       datetime.timedelta(seconds=5),
                       datetime.timedelta(seconds=10),
                       # datetime.timedelta(seconds=15),
                       datetime.timedelta(seconds=30),
                       datetime.timedelta(minutes=1),
                       # datetime.timedelta(minutes=2),
                       datetime.timedelta(minutes=5),
                       datetime.timedelta(minutes=10),
                       # datetime.timedelta(minutes=15),
                       datetime.timedelta(minutes=30),
                       datetime.timedelta(hours=1),
                       # datetime.timedelta(hours=2),
                       datetime.timedelta(hours=3),
                       datetime.timedelta(hours=6),
                       datetime.timedelta(hours=12),
                       datetime.timedelta(days=1),
                       # datetime.timedelta(days=2),
                       # datetime.timedelta(days=5),
                       # datetime.timedelta(days=10),
                       # datetime.timedelta(days=15),
                       datetime.timedelta(days=30),
                       # datetime.timedelta(days=30*2),
                       datetime.timedelta(days=30 * 3),
                       datetime.timedelta(days=30 * 6),
                       datetime.timedelta(days=356),
                       datetime.timedelta(days=356 * 5),
                       datetime.timedelta(days=356 * 10),
                       datetime.timedelta(days=356 * 50),
                       datetime.timedelta(days=356 * 100),
                       datetime.timedelta(days=356 * 200),
                       datetime.timedelta(days=356 * 500),
                       ]
        type_delta_major = type_deltas[0]
        type_delta_minor = type_deltas[0]
        for type_delta_test in type_deltas:
            type_delta_major = type_delta_test
            if type_delta_test > delta_min:
                break
            type_delta_minor = type_delta_test

        tick_types = [["second", 0, 0],
                      ["minute", 0, 0],
                      ["hour", 0, 0],
                      ["day", 0, 1],
                      ["month", 0, 1],
                      ["year", 0, 1]]
        # round to the nearest tick
        years = 0
        years_major = 0
        months = 0
        months_major = 0
        days = 0
        days_major = 0
        if type_delta_major >= datetime.timedelta(days=356):
            # round to years
            if type_delta_minor >= datetime.timedelta(days=356):
                years = int(type_delta_minor.days / 356)
            else:
                months = int(type_delta_minor.days / 30)
            years_major = int(type_delta_major.days / 356)
            tick_time = datetime.datetime(
                BoundBy(roundValue(left_end.year, max(years, 1)), datetime.MINYEAR, datetime.MAXYEAR), 1, 1)
        elif type_delta_major >= datetime.timedelta(days=30):
            # round to months
            if type_delta_minor >= datetime.timedelta(days=30):
                months = int(type_delta_minor.days / 30)
            months_major = int(type_delta_major.days / 30)
            tick_time = datetime.datetime(left_end.year, roundValue(left_end.month, max(months, 1), 1), 1)
        elif type_delta_minor >= datetime.timedelta(days=1):
            days = type_delta_minor.days
            days_major = type_delta_major.days
            tick_time = datetime.datetime(left_end.year, left_end.month, 1)
        else:
            tick_time = roundTime(left_end, type_delta_major.total_seconds())

        count = 0
        self.tick_start = tick_time
        while tick_time < right_end:
            for type in range(len(tick_types)):
                tick_type = tick_types[type]
                value = getattr(tick_time, tick_type[0])
                if tick_type[1]:
                    value %= tick_type[1]
                if value != tick_type[2]:
                    break
            # find out if this is a major tick or not
            is_major_tick = False
            if years_major:
                if tick_time.day == 1 and tick_time.month == 1 and tick_time.year == roundValue(tick_time.year,
                                                                                                years_major):
                    is_major_tick = True
            elif months_major:
                if tick_time.day == 1 and tick_time.month == roundValue(tick_time.month, months_major, 1):
                    is_major_tick = True
            elif days_major:
                if tick_time.day == roundValue(tick_time.day, days_major, 1):
                    is_major_tick = True
            elif (tick_time - self.tick_start).total_seconds() % type_delta_major.total_seconds() == 0:
                is_major_tick = True

            # place the tick
            if is_major_tick:
                self.addTickMarker(tick_time, color=QtGui.QColor(0, 0, 0), height=15, type=type,
                                   type_name=tick_types[type][0])
            else:
                self.addTickMarker(tick_time, color=QtGui.QColor(0, 0, 0), height=10, type=type, type_name="")

            # apply the delta
            if years:
                try:
                    tick_time = datetime.datetime(tick_time.year + years, tick_time.month, 1)
                except ValueError:
                    break
            elif months:
                if tick_time.month + months > 12:
                    tick_time = datetime.datetime(tick_time.year + 1, 1, 1)
                else:
                    tick_time = datetime.datetime(tick_time.year, tick_time.month + months, 1)
            elif days:
                try:
                    tick_time = datetime.datetime(tick_time.year, tick_time.month, tick_time.day + days)
                except ValueError:
                    try:
                        tick_time = datetime.datetime(tick_time.year, tick_time.month + 1, 1)
                    except ValueError:
                        tick_time = datetime.datetime(tick_time.year + 1, 1, 1)
            else:
                tick_time = tick_time + type_delta_minor
            count += 1
        self.repaint()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == 2:
            self.last_pos = PosToArray(
                self.slider_line.mapFromScene(self.mapToScene(event.pos())))  # PosToArray(self.mapToScene(event.pos()))
            self.scene_panning = True
        super(RealTimeSlider, self).mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self.scene_panning:
            new_pos = PosToArray(self.slider_line.mapFromScene(self.mapToScene(event.pos())))
            delta = (new_pos - self.last_pos)[0]
            self.last_pos = new_pos
            self.pan += delta
            self.markerParent.setPos(self.pan, 0)
            self.updateTicks()
            self.repaint()
        super(RealTimeSlider, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == 1:
            pos = (self.slider_line.mapFromScene(self.mapToScene(event.pos())) - self.markerParent.pos()) / self.scale
            pos = QtCore.QPointF(self.mapFromScene(self.slider_line.mapToScene(
                pos) * 1e6)) / 1e6  # Hack to prevent mapFromScene to discard float information
            self.setValue(self.PixelToValue(pos.x()))
            self.slider_position.signal.sliderReleased.emit()
        if event.button() == 2:
            self.scene_panning = False
        super(RealTimeSlider, self).mouseReleaseEvent(event)

    def wheelEvent(self, event: QtGui.QMouseEvent) -> None:
        event.ignore()
        super(RealTimeSlider, self).wheelEvent(event)
        if event.isAccepted():
            return

        try:  # PyQt 5
            angle = event.angleDelta().y()
        except AttributeError:  # PyQt 4
            angle = event.delta()
        old_scale = self.scale
        if angle > 0:
            self.scale *= 1.1
            self.markerParent.setTransform(QtGui.QTransform.fromScale(1.1, 1), True)
        else:
            self.scale *= 0.9
            self.markerParent.setTransform(QtGui.QTransform.fromScale(0.9, 1), True)
        new_pos = PosToArray(self.slider_line.mapFromScene(self.mapToScene(event.pos())))
        x = new_pos[0]
        self.pan = x - self.scale / old_scale * (x - self.pan)
        self.markerParent.setPos(self.pan, 0)
        event.accept()

        self.updateTicks()


def PosToArray(pos) -> np.ndarray:
    return np.array([pos.x(), pos.y()])


class Timeline(QtCore.QObject):
    images_added_signal = QtCore.Signal()
    data_file = None
    config = None
    _startframe = None
    _endframe = None

    fps = 25
    skip = 1  # where skip should be called step width i.e step=10 -> frame0 to frame10

    subsecond_decimals = 0

    def __init__(self, window: "ClickPointsWindow", layout: QtWidgets.QLayout,
                 modules: QtWidgets.QWidget) -> None:
        QtCore.QObject.__init__(self)

        self.window = window
        self.modules = modules

        self.images_added_signal.connect(self.ImagesAddedMain)

        self.button = QtWidgets.QPushButton()
        self.button.setCheckable(True)
        self.button.setIcon(qta.icon("fa.play"))
        self.button.setToolTip("display timeline")
        self.button.clicked.connect(lambda: self.HideInterface(self.hidden is False))
        self.button.setFocusPolicy(QtCore.Qt.NoFocus)
        self.window.layoutButtons.addWidget(self.button)

        # control elements
        self.layoutCtrlParent = HiddeableLayout(layout, QtWidgets.QVBoxLayout)
        self.layoutCtrlParent.setContentsMargins(0, 0, 0, 5)
        self.layoutCtrlParent.setSpacing(0)

        self.layoutCtrl = HiddeableLayout(self.layoutCtrlParent, QtWidgets.QHBoxLayout)
        self.layoutCtrl.setContentsMargins(5, 5, 5, 0)

        # second
        self.layoutCtrl2 = HiddeableLayout(self.layoutCtrlParent, QtWidgets.QHBoxLayout)
        self.layoutCtrl2.setContentsMargins(5, 0, 5, 0)
        self.timeSlider = RealTimeSlider()
        self.layoutCtrl2.addWidget(self.timeSlider)
        # self.timeSlider.setTimes(self.data_file)
        empty_space_keeper = QtWidgets.QLabel()
        empty_space_keeper.setMaximumHeight(0)
        empty_space_keeper.setMaximumWidth(0)
        self.layoutCtrl2.addWidget(empty_space_keeper)

        self.timeSlider.slider_position.signal.sliderPressed.connect(self.PressedSlider)
        self.timeSlider.slider_position.signal.sliderReleased.connect(self.ReleasedSlider2)

        self.timeSlider.setToolTip("current time stamp")

        self.layoutCtrl3 = HiddeableLayout(layout, QtWidgets.QHBoxLayout)
        self.layoutCtrl3.setContentsMargins(0, 0, 0, 0)
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.layoutCtrl3.setVisible(False)
        self.layoutCtrl3.addWidget(self.progress_bar)

        # frame control
        self.button_play = QtWidgets.QPushButton()
        self.button_play.setCheckable(True)
        self.button_play.setToolTip("start/stop playback\n[space]")
        self.button_play.toggled.connect(self.Play)
        self.layoutCtrl.addWidget(self.button_play)

        self.label_frame = QtWidgets.QLabel("")
        self.label_frame.setMinimumWidth(40)
        self.label_frame.setAlignment(QtCore.Qt.AlignVCenter)
        self.label_frame.setToolTip("current frame number, frame rate and timestamp")
        self.label_frame.mousePressEvent = self.labelClicked
        self.layoutCtrl.addWidget(self.label_frame)

        self.frameSlider = TimeLineSlider(scale=self.window.scale_factor)
        # if self.get_frame_count():
        #    self.frameSlider.setRange(0, self.get_frame_count() - 1)
        self.frameSlider.slider_position.signal.sliderPressed.connect(self.PressedSlider)
        self.frameSlider.slider_position.signal.sliderReleased.connect(self.ReleasedSlider)
        self.frameSlider.start_changed.connect(lambda value: self.data_file.setOption("play_start", value))
        self.frameSlider.end_changed.connect(lambda value: self.data_file.setOption("play_end", value))
        self.frameSlider.setToolTip("current frame, drag to change current frame\n[b], [n] to set start/end marker")
        # self.frameSlider.setValue(self.get_frame_count())
        self.slider_update = True
        self.layoutCtrl.addWidget(self.frameSlider)

        self.spinBox_FPS = MySpinBox()
        self.spinBox_FPS.setMinimum(1)
        self.spinBox_FPS.setMaximum(1000)
        self.spinBox_FPS.setValue(self.fps)
        self.spinBox_FPS.valueChanged.connect(self.ChangedFPS)
        self.spinBox_FPS.setToolTip("play frame rate")
        self.layoutCtrl.addWidget(self.spinBox_FPS)

        self.spinBox_Skip = MySpinBox()
        self.spinBox_Skip.setMinimum(1)
        self.spinBox_Skip.setMaximum(1000)
        self.spinBox_Skip.setValue(self.skip)
        self.spinBox_Skip.valueChanged.connect(self.ChangedSkip)
        self.spinBox_Skip.setToolTip("display every Nth frame")
        self.layoutCtrl.addWidget(self.spinBox_Skip)

        # video replay
        self.current_fps = 0
        self.last_time = time.time()
        # initialize the frame timer
        loop = self.window.app.loop
        asyncio.ensure_future(self.runTimer(loop), loop=loop)

        self.hidden = True

        self.closeDataFile()

    async def runTimer(self, loop: QEventLoop):

        t = time.time()
        target_fps = 25
        self.target_delta_t = 1 / target_fps
        last_overhead = 0
        mean_fps = target_fps
        averaging_decay = 0.9

        while True:
            if self.running:
                wait = loop.create_task(asyncio.sleep(max(self.target_delta_t - last_overhead, 0)))
                if self.data_file is None or self.get_current_frame() is None:
                    return
                if self.get_current_frame() < self.frameSlider.startValue() or self.get_current_frame() + self.skip > self.frameSlider.endValue():
                    await self.window.load_frame(self.frameSlider.startValue())
                else:
                    await self.window.load_frame(self.window.target_frame + self.skip)
                await wait

                # calculate the time slip
                delta_t = time.time() - t
                t = time.time()
                last_overhead += 0.1 * (delta_t - self.target_delta_t)

                mean_fps = averaging_decay * mean_fps + (1 - averaging_decay) * 1 / (delta_t + 1e-9)
            else:
                await asyncio.sleep(0.01)
                t = time.time()

    def closeDataFile(self) -> None:
        self.data_file = None
        self.config = None

        self.frameSlider.clearTickMarker()

        self.Play(False)

        self.HideInterface(True)

    # load Data File values
    def updateDataFile(self, data_file: DataFileExtended, new_database: bool) -> None:
        self.data_file = data_file
        self.config = data_file.getOptionAccess()

        self.fps = 0
        if self.fps == 0:
            self.fps = 25
        if self.config.fps != 0:
            self.fps = self.config.fps
        self.skip = self.config.skip

        self.spinBox_Skip.setValue(self.skip)

        # prepare timestamp output
        # detect %*f marker get number form 1 to 6 as *
        self.subsecond_decimals = 0
        regexp = re.compile('.*.%(\d)f.*')
        match = regexp.match(self.data_file.getOption("display_timeformat"))
        if match:
            self.subsecond_decimals = match.group(1)

        if self.data_file.getOption("play_start") is not None:
            self._startframe = self.data_file.getOption("play_start")
        if self.data_file.getOption("play_end") is not None:
            self._endframe = self.data_file.getOption("play_end")

        self.Play(self.data_file.getOption("playing"))
        self.hidden = True
        self.HideInterface(self.config.timeline_hide)

    def get_current_frame(self) -> Optional[int]:
        if self.data_file is None:
            return None
        return self.data_file.get_current_image()

    def get_frame_count(self) -> int:
        return self.data_file.get_image_count()

    def ImagesAdded(self) -> None:
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)
        self.layoutCtrl3.setVisible(True)
        self.images_added_signal.emit()

    def ImagesAddedMain(self) -> None:
        update_end = False
        if self.frameSlider.endValue() == self.frameSlider.max_value or self.frameSlider.endValue() == 0:
            update_end = True
        self.frameSlider.setRange(0, self.get_frame_count() - 1)
        if update_end:
            self.frameSlider.setEndValue(self.get_frame_count() - 1)
        self.updateLabel()

        # reset start and end marker (only if all images are loaded frames may be valid)
        if self._startframe is not None:
            # if >1 its a frame nr if < 1 its a fraction
            if self._startframe >= 1:
                self.frameSlider.setStartValue(self._startframe)
            else:
                self.frameSlider.setStartValue(int(self.get_frame_count() * self._startframe))
        if self._endframe is not None:
            if self._endframe > 1:
                self.frameSlider.setEndValue(self._endframe)
            else:
                self.frameSlider.setEndValue(int(self.get_frame_count() * self._endframe))

    def LoadingFinishedEvent(self) -> None:
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.layoutCtrl3.setHidden(True)
        if self.data_file.getOption("datetimeline_show"):
            self.timeSlider.setTimes(self.data_file)
            self.layoutCtrl2.setHidden(False)

    def ChangedSkip(self) -> None:
        self.skip = self.spinBox_Skip.value()
        self.data_file.setOption("skip", self.skip)

    def ChangedFPS(self) -> None:
        self.fps = self.spinBox_FPS.value()
        self.data_file.setOption("fps", self.fps)
        if self.playing:
            self.target_delta_t = 1 / self.fps
            self.running = True
            # self.timer.start(1000 / self.fps)

    def ReleasedSlider(self) -> None:
        n = self.frameSlider.value()
        self.slider_update = True
        self.updateFrame(nr=n)

    def ReleasedSlider2(self) -> None:
        timestamp = self.timeSlider.value()
        n = self.data_file.table_image.select(self.data_file.table_image.sort_index).where(
            self.data_file.table_image.timestamp > timestamp).limit(1)
        if n.count() == 0:
            return
        n = n[0].sort_index
        self.slider_update = True
        self.updateFrame(nr=n)

    def PressedSlider(self) -> None:
        self.slider_update = False

    def Play(self, state: bool) -> None:
        if state:
            self.target_delta_t = 1 / self.fps
            self.running = True
            # self.timer.start(1000 / self.fps)
            self.button_play.setIcon(QtGui.QIcon(os.path.join(os.environ["CLICKPOINTS_ICON"], "pause.ico")))
            self.playing = True
        else:
            self.running = False
            # self.timer.stop()
            self.button_play.setIcon(QtGui.QIcon(os.path.join(os.environ["CLICKPOINTS_ICON"], "play.ico")))
            self.playing = False

    def updateFrame(self, nr: int = -1) -> None:
        if self.data_file is None or self.get_current_frame() is None:
            return
        if nr != -1:
            self.window.JumpToFrame(nr)
        else:
            if self.get_current_frame() < self.frameSlider.startValue() or self.get_current_frame() + self.skip > self.frameSlider.endValue():
                self.window.JumpToFrame(self.frameSlider.startValue())
            else:
                self.window.JumpFrames(self.skip)

    def updateLabel(self) -> None:
        if self.slider_update or 1:
            self.frameSlider.setValue(self.get_current_frame())

            if self.timeSlider and self.data_file.image and self.data_file.image.timestamp:
                self.timeSlider.setValue(self.data_file.image.timestamp)
            if self.get_current_frame() is not None:
                if self.get_frame_count() == 0:
                    format_string = "{:1,}"
                else:
                    format_string = "{:%d,}" % np.ceil(np.log10(self.get_frame_count()))
                format_string = (format_string + '/' + format_string + "  {:.1f}fps")
                fps = self.current_fps if self.current_fps is not None else 0
                label_string = format_string.format(self.get_current_frame(), self.get_frame_count() - 1, fps)
            else:
                label_string = ""
            if self.data_file.image and self.data_file.image.timestamp:
                # if subsecond decimals are specified - adjust string accordingly
                if not self.subsecond_decimals == 0:
                    display_timeformat = self.data_file.getOption("display_timeformat").replace(
                        '%%%sf' % self.subsecond_decimals, ('%%0%sd' % self.subsecond_decimals) % (
                                self.data_file.image.timestamp.microsecond / 10 ** (
                                6 - int(self.subsecond_decimals))))
                label_string += "\n" + self.data_file.image.timestamp.strftime(display_timeformat)
            self.label_frame.setText(label_string)

    def labelClicked(self, event: QtCore.QEvent) -> None:
        self.select_frame_window = SelectFrame(self.get_current_frame(), self.get_frame_count())

        value = self.select_frame_window.exec_()
        if value > 0:
            self.window.JumpToFrame(value - 1)

    def frameChangedEvent(self) -> None:
        dt = max(time.time() - self.last_time, 1e-6)
        self.last_time = time.time()
        if self.current_fps is None or self.current_fps == 0:
            self.current_fps = 1 / dt
        else:
            a = np.exp(-dt)
            self.current_fps = a * self.current_fps + (1 - a) * 1 / dt

        self.updateLabel()
        # self.timer.allow_next() TODO

    def MaskAdded(self) -> None:
        self.frameSlider.addTickMarker(self.get_current_frame(), type=1)

    def MarkerPointsAdded(self, frame: None = None) -> None:
        if frame is not None:
            self.frameSlider.addTickMarker(frame, type=1)
        else:
            self.frameSlider.addTickMarker(self.get_current_frame(), type=1)

    def MarkerPointsAddedList(self, frames: Optional[Union[ndarray, Set[int32]]] = None) -> None:
        for frame in frames:
            if frame is not None:
                self.frameSlider.addTickMarker(frame, type=1)
            else:
                self.frameSlider.addTickMarker(self.get_current_frame(), type=1)

    def MarkerPointsRemoved(self) -> None:
        self.frameSlider.removeTickMarker(self.get_current_frame(), type=1)

    def AnnotationAdded(self, *args) -> None:
        self.frameSlider.addTickMarker(self.get_current_frame(), type=0)

    def AnnotationRemoved(self, *args):
        self.frameSlider.removeTickMarker(self.get_current_frame(), type=0)

    def AnnotationMarkerAdd(self, position: int, *args) -> None:
        self.frameSlider.addTickMarker(position, type=0)

    def HideInterface(self, hide: bool) -> None:
        self.hidden = hide
        if self.config:
            self.config.timeline_hide = self.hidden
        self.layoutCtrlParent.setHidden(hide)
        self.button.setChecked(not self.hidden)
        self.layoutCtrl2.setHidden(
            self.timeSlider.is_hidden | (self.data_file is None or not self.data_file.getOption("datetimeline_show")))

    def optionsChanged(self, key: None) -> None:
        self.HideInterface(self.hidden)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        # @key H: hide control elements
        if event.key() == QtCore.Qt.Key_H:
            self.HideInterface(self.hidden is False)
        # @key Space: run/pause
        if event.key() == QtCore.Qt.Key_Space:
            self.current_fps = None
            self.last_time = time.time()
            self.button_play.toggle()

        # @key B: move start marker here
        if event.key() == QtCore.Qt.Key_B:
            self.frameSlider.setStartValue(self.get_current_frame())
        # @key N: move start marker here
        if event.key() == QtCore.Qt.Key_N:
            self.frameSlider.setEndValue(self.get_current_frame())

        # @key ---- Frame jumps ----
        if event.key() == QtCore.Qt.Key_Left and event.modifiers() & QtCore.Qt.ControlModifier:
            # @key Ctrl+Left: previous annotated image
            tick = self.frameSlider.getNextTick(self.get_current_frame(), back=True)
            self.window.JumpToFrame(tick)
        if event.key() == QtCore.Qt.Key_Right and event.modifiers() & QtCore.Qt.ControlModifier:
            # @key Ctrl+Right: next annotated image
            tick = self.frameSlider.getNextTick(self.get_current_frame())
            self.window.JumpToFrame(tick)

        if event.key() == QtCore.Qt.Key_Left and event.modifiers() & QtCore.Qt.AltModifier:
            # @key Alt+Left: previous annotation block
            tick = self.frameSlider.getNextTickChange(self.get_current_frame(), back=True)
            self.window.JumpToFrame(tick)
        if event.key() == QtCore.Qt.Key_Right and event.modifiers() & QtCore.Qt.AltModifier:
            # @key Alt+Right: next annotation block
            tick = self.frameSlider.getNextTickChange(self.get_current_frame())
            self.window.JumpToFrame(tick)

        if event.key() == QtCore.Qt.Key_Home and event.modifiers() & QtCore.Qt.ControlModifier:
            # @key Ctrl+Home: jump to start marker
            self.window.JumpToFrame(self.frameSlider.startValue())
        if event.key() == QtCore.Qt.Key_End and event.modifiers() & QtCore.Qt.ControlModifier:
            # @key Ctrl+End: jump to end marker
            self.window.JumpToFrame(self.frameSlider.endValue())

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.Play(False)

    @staticmethod
    def file() -> str:
        return __file__
