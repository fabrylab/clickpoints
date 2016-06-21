from __future__ import division, print_function
import sys
import os
import glob
import time
import numpy as np
import datetime
from threading import Thread

from qtpy import QtGui, QtCore, QtWidgets
from qtpy.QtCore import Qt
import qtawesome as qta

icon_path = os.path.join(os.path.dirname(__file__), "..", "icons")

def timedelta_mul(self, other):
    if isinstance(other, (int, float)):
        return datetime.timedelta(seconds=self.total_seconds()*other)
    else:
        return NotImplemented

def timedelta_div(self, other):
    if isinstance(other, (int, float)):
        return datetime.timedelta(seconds=self.total_seconds()/other)
    else:
        return NotImplemented

def BoundBy(value, min, max):
    if value is None:
        return min
    if value < min:
        return min
    if value > max:
        return max
    return value

def roundTime(dt=None, roundTo=60):
    """Round a datetime object to any time laps in seconds
    dt : datetime.datetime object, default now.
    roundTo : Closest number of seconds to round to, default 1 minute.
    Author: Thierry Husson 2012 - Use it as you want but don't blame me.
    """
    if dt == None : dt = datetime.datetime.now()
    seconds = (dt - dt.min).seconds
    # // is a floor division, not a comment on following line:
    rounding = (seconds+roundTo/2) // roundTo * roundTo
    return dt + datetime.timedelta(0,rounding-seconds,-dt.microsecond)

def roundValue(value, modulo, offset=0):
    return int((value-offset) // modulo) * modulo + offset

def DateDivision(x, y):
    return x.total_seconds()/y.total_seconds()

def Remap(value, minmax1, minmax2):
    length1 = minmax1[1]-minmax1[0]
    length2 = minmax2[1]-minmax2[0]
    if length1 == 0:
        return 0
    try:
        percentage = (value-minmax1[0])/length1
    except TypeError:
        percentage = DateDivision((value-minmax1[0]), length1)
    try:
        value2 = percentage*length2 + minmax2[0]
    except TypeError:
        value2 = datetime.timedelta(seconds=percentage*length2.total_seconds()) + minmax2[0]
    return value2

class TimeLineGrabberSignal(QtCore.QObject):
    sliderPressed = QtCore.pyqtSignal()
    sliderMoved = QtCore.pyqtSignal()
    sliderReleased = QtCore.pyqtSignal()

class TimeLineGrabber(QtWidgets.QGraphicsPathItem):
    def __init__(self, parent, value, path, gradient, parent_item=None):
        if parent_item is None:
            QtWidgets.QGraphicsPathItem.__init__(self, None, parent.scene)
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

    def setPixelRange(self, min, max):
        self.pixel_range = [min, max]
        self.updatePos()

    def setValueRange(self, min, max):
        self.value_range = [min, max]

    def setValue(self, value):
        self.value = int(round(value))
        self.updatePos()

    def updatePos(self):
        self.setPos(self.value_to_pixel(self.value), 0)

    def mousePressEvent(self, event):
        if event.button() == 1:
            self.dragged = True
            self.signal.sliderPressed.emit()

    def mouseMoveEvent(self, event):
        if self.dragged:
            x = BoundBy(self.mapToParent(event.pos()).x(), self.pixel_range[0], self.pixel_range[1])
            self.setValue(self.pixel_to_value(x))
            self.signal.sliderMoved.emit()

    def mouseReleaseEvent(self, event):
        self.dragged = False
        self.signal.sliderReleased.emit()

    def pixel_to_value(self, pixel):
        return Remap(pixel, self.pixel_range, self.value_range)

    def value_to_pixel(self, value):
        return Remap(value, self.value_range, self.pixel_range)

class TimeLineGrabberTime(TimeLineGrabber):
    #def __init__(self, *args):
    #    QGraphicsPathItem.__init__(self, None, parent.scene)

    def mouseMoveEvent(self, event):
        if self.dragged:
            x = self.pos().x()+event.pos().x()/self.parent.scale/self.parent.slider_line.transform().m11()
            self.setValue(self.pixel_to_value(x))

    def setValue(self, value):
        self.value = value
        self.updatePos()

class TimeLineSlider(QtWidgets.QGraphicsView):
    def __init__(self, max_value=100, min_value=0):
        QtWidgets.QGraphicsView.__init__(self)

        self.setMaximumHeight(30)
        #self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.scene = QtWidgets.QGraphicsScene(self)
        self.setScene(self.scene)
        self.scene.setBackgroundBrush(self.palette().color(QtGui.QPalette.Background))
        self.setStyleSheet("border: 0px")

        self.max_value = max_value
        self.min_value = min_value

        self.slider_line = QtWidgets.QGraphicsRectItem(None, self.scene)
        self.slider_line.setPen(QtGui.QPen(QtGui.QColor("black")))
        self.slider_line.setPos(0, -2.5)
        gradient = QtGui.QLinearGradient(QtCore.QPointF(0, 0), QtCore.QPointF(0, 5))
        gradient.setColorAt(0, QtGui.QColor("black"))
        gradient.setColorAt(1, QtGui.QColor(128, 128, 128))
        self.slider_line.setBrush(QtGui.QBrush(gradient))
        self.slider_line.mousePressEvent = self.SliderBarMousePressEvent

        self.slider_line_active = QtWidgets.QGraphicsRectItem(None, self.scene)
        self.slider_line_active.setPen(QtGui.QPen(QtGui.QColor("black")))
        self.slider_line_active.setPos(0, -2.5)
        gradient = QtGui.QLinearGradient(QtCore.QPointF(0, 0), QtCore.QPointF(0, 5))
        gradient.setColorAt(0, QtGui.QColor(128, 128, 128))
        gradient.setColorAt(1, QtGui.QColor(200, 200, 200))
        self.slider_line_active.setBrush(QtGui.QBrush(gradient))

        path = QtGui.QPainterPath()
        path.moveTo(-4, +12)
        path.lineTo( 0,  +2.5)
        path.lineTo(+4, +12)
        path.lineTo(-4, +12)
        gradient = QtGui.QLinearGradient(QtCore.QPointF(0, 12), QtCore.QPointF(0, 2.5))
        gradient.setColorAt(0, QtGui.QColor(255, 0, 0))
        gradient.setColorAt(1, QtGui.QColor(128, 0, 0))
        self.slider_start = TimeLineGrabber(self, 0, path, gradient)
        self.slider_start.signal.sliderMoved.connect(self.slider_start_changed)

        path = QtGui.QPainterPath()
        path.moveTo(-4, -12)
        path.lineTo( 0,  -2.5)
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

    def SliderBarMousePressEvent(self, event):
        self.setValue(self.PixelToValue(self.slider_line.mapToScene(event.pos()).x()))
        self.slider_position.signal.sliderReleased.emit()

    def addTickMarker(self, pos, type=0, color=QtGui.QColor("red"), height=12):
        if type == 1:
            color = QtGui.QColor("green")
            height = 8
        if pos in self.tick_marker and type in self.tick_marker[pos]:
            tick_marker = self.tick_marker[pos][type]
        else:
            width = self.ValueToPixel(1)
            if pos == self.max_value:
                width = 2
            tick_marker = QtWidgets.QGraphicsRectItem(0.0, -3.5, width, -height, None, self.scene)
        tick_marker.setPen(QtGui.QPen(color))
        tick_marker.setBrush(QtGui.QBrush(color))
        tick_marker.value = pos
        tick_marker.type = type
        tick_marker.height = height
        tick_marker.setZValue(1+type)
        tick_marker.setPos(self.ValueToPixel(pos), 0)
        if pos not in self.tick_marker:
            self.tick_marker[pos] = {}
        self.tick_marker[pos][type] = tick_marker
        self.repaint()

    def removeTickMarker(self, pos, type=0):
        if pos in self.tick_marker and type in self.tick_marker[pos]:
            tick_marker = self.tick_marker[pos][type]
            self.scene.removeItem(tick_marker)
            del self.tick_marker[pos][type]
            if self.tick_marker[pos] == {}:
                del self.tick_marker[pos]
            self.repaint()

    def clearTickMarker(self):
        for pos, ticks in self.tick_marker.items():
            for type, tick in ticks.items():
                self.scene.removeItem(tick)
        self.tick_marker = {}
        self.repaint()

    def getNextTick(self, pos, back=False):
        if back is False:
            my_range = range(pos+1, self.max_value, +1)
        else:
            my_range = range(pos-1, self.min_value, -1)
        search_marked = True
        for i in my_range:
            if (i in self.tick_marker) == search_marked:
                return i
        if len(my_range) == 0:
            if back is False:
                return pos+1
            return pos-1
        return my_range[-1]

    def getNextTickChange(self, pos, back=False):
        if back is False:
            my_range = range(pos+1, self.max_value, +1)
        else:
            my_range = range(pos-1, self.min_value, -1)
        search_marked = True
        if len(my_range) == 0:
            if back is False:
                return pos+1
            return pos-1
        if pos in self.tick_marker and my_range[0] in self.tick_marker:
            search_marked = False
        for i in my_range:
            if (i in self.tick_marker) == search_marked:
                return i
        return my_range[-1]

    def resizeEvent(self, event):
        self.length = self.size().width()-20
        self.slider_line.setRect(0, 0, self.length, 5)
        self.slider_line_active.setRect(self.ValueToPixel(self.slider_start.value), 0, self.ValueToPixel(self.slider_end.value)-self.ValueToPixel(self.slider_start.value), 5)
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

    def setRange(self, min_value, max_value):
        self.min_value = min_value
        self.max_value = max_value
        for marker in [self.slider_position, self.slider_start, self.slider_end]:
            marker.setValueRange(self.min_value, self.max_value)

    def setValue(self, value):
        self.slider_position.setValue(BoundBy(value, self.min_value, self.max_value))

    def setStartValue(self, value):
        self.slider_start.setValue(BoundBy(value, self.min_value, self.max_value))
        self.updatePlayRange()

    def setEndValue(self, value):
        self.slider_end.setValue(BoundBy(value, self.min_value, self.max_value))
        self.updatePlayRange()

    def PixelToValue(self, pixel):
        return Remap(pixel, [0, self.length], [self.min_value, self.max_value])

    def ValueToPixel(self, value):
        return Remap(value, [self.min_value, self.max_value], [0, self.length])

    def slider_start_changed(self):
        if self.slider_start.value > self.slider_end.value:
            self.slider_end.setValue(self.slider_start.value)
        self.updatePlayRange()

    def slider_end_changed(self):
        if self.slider_start.value > self.slider_end.value:
            self.slider_start.setValue(self.slider_end.value)
        self.updatePlayRange()

    def updatePlayRange(self):
        self.slider_line_active.setRect(self.ValueToPixel(self.slider_start.value), 0, self.ValueToPixel(self.slider_end.value)-self.ValueToPixel(self.slider_start.value), 5)

    def value(self):
        return self.slider_position.value

    def startValue(self):
        return self.slider_start.value

    def endValue(self):
        return self.slider_end.value

    def keyPressEvent(self, event):
        event.setAccepted(False)
        return

class RealTimeSlider(QtWidgets.QGraphicsView):
    def __init__(self):
        QtWidgets.QGraphicsView.__init__(self)

        self.setMaximumHeight(30)
        #self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.scene = QtWidgets.QGraphicsScene(self)
        self.setScene(self.scene)
        self.scene.setBackgroundBrush(self.palette().color(QtGui.QPalette.Background))
        self.setStyleSheet("border: 0px")

        self.slider_line = QtWidgets.QGraphicsRectItem(None, self.scene)
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

    def resizeEvent(self, event):
        self.length = self.size().width()
        self.slider_line.setRect(0, -0.5, self.pixel_len, 1)
        self.slider_line.resetTransform()
        self.slider_line.scale(self.length/self.pixel_len, 1)
        self.setSceneRect(0, -10, self.size().width(), 20)
        self.repaint()

    def SliderBarMousePressEvent(self, event):
        self.setValue(self.PixelToValue(self.slider_line.mapToScene(event.pos()).x()))
        self.slider_position.signal.sliderReleased.emit()

    def addTickBlock(self, pos1, pos2):
        color = QtGui.QColor(128, 128, 128)
        height = 10

        x1 = Remap(pos1, [self.min_value, self.max_value], [0, self.pixel_len])
        x2 = Remap(pos2, [self.min_value, self.max_value], [0, self.pixel_len])

        tick_block = QtWidgets.QGraphicsRectItem(0, -2, x2-x1, -height, self.markerGroupParents[0])
        tick_block.setPos(x1, 0)

        tick_block.setBrush(QtGui.QBrush(color))
        tick_block.setPen(QtGui.QPen(color))
        tick_block.setZValue(-10)

        self.tick_blocks.append(tick_block)

    def addTickMarker(self, pos, type=-1, type_name="", color=QtGui.QColor("red"), height=12, text=""):
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
            self.text.setPos(-offsetX*0.5+1, 2)
            self.font_parent.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations)
            tick_marker.text = self.text
        else:
            tick_marker.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations)
            tick_marker.text = None
        self.tick_marker.append(tick_marker)

    def setRange(self, min_value, max_value):
        self.min_value = min_value
        self.max_value = max_value
        for marker in [self.slider_position]:
            marker.setValueRange(self.min_value, self.max_value)

    def setValue(self, value):
        self.slider_position.setValue(BoundBy(value, self.min_value, self.max_value))

    def PixelToValue(self, pixel):
        return Remap(pixel, [0, self.length], [self.min_value, self.max_value])

    def ValueToPixel(self, value):
        return Remap(value, [self.min_value, self.max_value], [0, self.length])

    def value(self):
        return self.slider_position.value

    def keyPressEvent(self, event):
        event.setAccepted(False)
        return

    def setTimes(self, data_file):
        # remove old time ticks
        for tick in self.tick_blocks:
            if tick.scene():
                tick.scene().removeItem(tick)
        self.tick_blocks = []

        # get timestamps
        self.data_file = data_file
        timestamps = [t.timestamp for t in self.data_file.table_images.select(self.data_file.table_images.timestamp) if t.timestamp]

        # handle empty timeline
        if len(timestamps) == 0:
            self.min_value = datetime.datetime.today()
            self.max_value = datetime.datetime.today()+datetime.timedelta(hours=1)
            self.slider_position.setValueRange(self.min_value, self.max_value)
            return
        # get min/max values
        self.min_value = np.amin(timestamps)
        self.max_value = np.amax(timestamps)
        if self.max_value == self.min_value:
            self.max_value = self.min_value+datetime.timedelta(hours=1)
        range = self.max_value-self.min_value

        # add some border
        self.min_value -= timedelta_mul(range, 0.01)
        self.max_value += timedelta_mul(range, 0.01)

        # apply ranges
        self.slider_position.setValueRange(self.min_value, self.max_value)

        # add tick blocks
        last_time = None
        last_delta = None
        start_time = None
        for time in timestamps:
            if last_time is None:
                start_time = time
                last_time = time
                continue
            if last_delta is None:
                last_delta = time-last_time
                last_time = time
                continue
            if time-last_time > last_delta*2:
                self.addTickBlock(start_time, last_time)
                start_time = time
            last_time = time
        self.addTickBlock(start_time, last_time)

        # update display
        self.updateTicks()
        self.repaint()

    def updateTicks(self):
        span = self.max_value-self.min_value
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
        delta_min = timedelta_mul(right_end-left_end, 60/self.pixel_len)#self.PixelToValue(60)-left_end
        type_deltas = [datetime.timedelta(seconds=1),
                       #datetime.timedelta(seconds=2),
                       datetime.timedelta(seconds=5),
                       datetime.timedelta(seconds=10),
                       #datetime.timedelta(seconds=15),
                       datetime.timedelta(seconds=30),
                       datetime.timedelta(minutes=1),
                       #datetime.timedelta(minutes=2),
                       datetime.timedelta(minutes=5),
                       datetime.timedelta(minutes=10),
                       #datetime.timedelta(minutes=15),
                       datetime.timedelta(minutes=30),
                       datetime.timedelta(hours=1),
                       #datetime.timedelta(hours=2),
                       datetime.timedelta(hours=3),
                       datetime.timedelta(hours=6),
                       datetime.timedelta(hours=12),
                       datetime.timedelta(days=1),
                       #datetime.timedelta(days=2),
                       #datetime.timedelta(days=5),
                       #datetime.timedelta(days=10),
                       #datetime.timedelta(days=15),
                       datetime.timedelta(days=30),
                       #datetime.timedelta(days=30*2),
                       datetime.timedelta(days=30*3),
                       datetime.timedelta(days=30*6),
                       datetime.timedelta(days=356),
                       datetime.timedelta(days=356*5),
                       datetime.timedelta(days=356*10),
                       datetime.timedelta(days=356*50),
                       datetime.timedelta(days=356*100),
                       datetime.timedelta(days=356*200),
                       datetime.timedelta(days=356*500),
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
                years = int(type_delta_minor.days/356)
            else:
                months = int(type_delta_minor.days/30)
            years_major = int(type_delta_major.days/356)
            tick_time = datetime.datetime(BoundBy(roundValue(left_end.year, max(years, 1)), datetime.MINYEAR, datetime.MAXYEAR), 1, 1)
        elif type_delta_major >= datetime.timedelta(days=30):
            # round to months
            if type_delta_minor >= datetime.timedelta(days=30):
                months = int(type_delta_minor.days/30)
            months_major = int(type_delta_major.days/30)
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
                if tick_time.day == 1 and tick_time.month == 1 and tick_time.year == roundValue(tick_time.year, years_major):
                    is_major_tick = True
            elif months_major:
                if tick_time.day == 1 and tick_time.month == roundValue(tick_time.month, months_major, 1):
                    is_major_tick = True
            elif days_major:
                if tick_time.day == roundValue(tick_time.day, days_major, 1):
                    is_major_tick = True
            elif (tick_time-self.tick_start).total_seconds() % type_delta_major.total_seconds() == 0:
                is_major_tick = True

            # place the tick
            if is_major_tick:
                self.addTickMarker(tick_time, color=QtGui.QColor(0, 0, 0), height=15, type=type, type_name=tick_types[type][0])
            else:
                self.addTickMarker(tick_time, color=QtGui.QColor(0, 0, 0), height=10, type=type, type_name="")

            # apply the delta
            if years:
                try:
                    tick_time = datetime.datetime(tick_time.year+years, tick_time.month, 1)
                except ValueError:
                    break
            elif months:
                if tick_time.month+months > 12:
                    tick_time = datetime.datetime(tick_time.year+1, 1, 1)
                else:
                    tick_time = datetime.datetime(tick_time.year, tick_time.month+months, 1)
            elif days:
                try:
                    tick_time = datetime.datetime(tick_time.year, tick_time.month, tick_time.day+days)
                except ValueError:
                    try:
                        tick_time = datetime.datetime(tick_time.year, tick_time.month+1, 1)
                    except ValueError:
                        tick_time = datetime.datetime(tick_time.year+1, 1, 1)
            else:
                tick_time = tick_time+type_delta_minor
            count += 1
        self.repaint()

    def mousePressEvent(self, event):
        if event.button() == 2:
            self.last_pos = PosToArray(self.slider_line.mapFromScene(self.mapToScene(event.pos())))#PosToArray(self.mapToScene(event.pos()))
            self.scene_panning = True
        super(RealTimeSlider, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.scene_panning:
            new_pos = PosToArray(self.slider_line.mapFromScene(self.mapToScene(event.pos())))
            delta = (new_pos-self.last_pos)[0]
            self.last_pos = new_pos
            self.pan += delta
            self.markerParent.setPos(self.pan, 0)
            self.updateTicks()
            self.repaint()
        super(RealTimeSlider, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == 2:
            self.scene_panning = False
        super(RealTimeSlider, self).mouseReleaseEvent(event)

    def wheelEvent(self, event):
        event.ignore()
        super(RealTimeSlider, self).wheelEvent(event)
        if event.isAccepted():
            return

        if 0:#qt_version == '5':
            angle = event.angleDelta().y()
        else:
            angle = event.delta()
        old_scale = self.scale
        if angle > 0:
            self.scale *= 1.1
            self.markerParent.scale(1.1, 1)
        else:
            self.scale *= 0.9
            self.markerParent.scale(0.9, 1)
        new_pos = PosToArray(self.slider_line.mapFromScene(self.mapToScene(event.pos())))
        x = new_pos[0]
        self.pan = x - self.scale/old_scale*(x-self.pan)
        self.markerParent.setPos(self.pan, 0)
        event.accept()

        self.updateTicks()


def PosToArray(pos):
    return np.array([pos.x(), pos.y()])

class PreciseTimer(QtCore.QObject):
    timeout = QtCore.pyqtSignal()
    thread = None
    timer_start = None
    delta = 1
    count = 1
    run = False
    active = 1

    def __init__(self, ):
        QtCore.QObject.__init__(self)
        self.timer_start = time.time()

    def start(self, delta=None):
        if delta is not None:
            self.delta = delta
        self.timer_start = time.time()
        self.count = 1
        if not self.run:
            self.run = True
            if self.thread is not None:
                self.thread.join()
            self.thread = Thread(target=self.thread_timer, args=tuple())
            self.thread.start()

    def stop(self):
        self.run = False
        if self.thread is not None:
            self.thread.join()

    def allow_next(self):
        self.active = 1

    def thread_timer(self):
        while self.run:
            if (time.time()-self.timer_start)*1e3 > self.delta*self.count and self.active:
                self.count = int((time.time()-self.timer_start)*1e3//self.delta)+1
                self.timeout.emit()
                self.active = 0
            time.sleep(0.01)

class Timeline(QtCore.QObject):
    images_added_signal = QtCore.pyqtSignal()

    def __init__(self, window, data_file, layout, outputpath, config, modules):
        QtCore.QObject.__init__(self)

        self.window = window
        self.data_file = data_file
        self.config = config
        self.modules = modules

        self.fps = 0
        if self.fps == 0:
            self.fps = 25
        if self.config.fps != 0:
            self.fps = self.config.fps
        self.skip = 0

        self.images_added_signal.connect(self.ImagesAddedMain)

        self.button = QtWidgets.QPushButton()
        self.button.setCheckable(True)
        self.button.setIcon(qta.icon("fa.play"))
        self.button.setToolTip("display timeline")
        self.button.clicked.connect(lambda: self.HideInterface(self.hidden is False))
        self.window.layoutButtons.addWidget(self.button)

        # control elements
        self.layoutCtrlParent = QtWidgets.QVBoxLayout()
        layout.addLayout(self.layoutCtrlParent)
        self.layoutCtrl = QtWidgets.QHBoxLayout()
        self.layoutCtrlParent.addLayout(self.layoutCtrl)

        # second
        if self.config.datetimeline_show:
            self.layoutCtrl2 = QtWidgets.QHBoxLayout()
            self.layoutCtrlParent.addLayout(self.layoutCtrl2)

            self.timeSlider = RealTimeSlider()
            self.timeSlider.setTimes(self.data_file)
            self.layoutCtrl2.addWidget(self.timeSlider)

            self.timeSlider.slider_position.signal.sliderPressed.connect(self.PressedSlider)
            self.timeSlider.slider_position.signal.sliderReleased.connect(self.ReleasedSlider2)

            self.timeSlider.setToolTip("current time stamp")
        else:
            self.timeSlider = None

        # frame control
        self.button_play = QtWidgets.QPushButton()
        self.button_play.setCheckable(True)
        self.button_play.setToolTip("start/stop playback\n[space]")
        self.button_play.toggled.connect(self.Play)
        self.layoutCtrl.addWidget(self.button_play)

        self.label_frame = QtWidgets.QLabel("")
        self.label_frame.setMinimumWidth(40)
        self.label_frame.setAlignment(Qt.AlignVCenter)
        self.label_frame.setToolTip("current frame number, frame rate and timestamp")
        self.layoutCtrl.addWidget(self.label_frame)

        self.frameSlider = TimeLineSlider()
        self.frameSlider.slider_position.signal.sliderPressed.connect(self.PressedSlider)
        self.frameSlider.slider_position.signal.sliderReleased.connect(self.ReleasedSlider)
        self.frameSlider.setRange(0, self.get_frame_count() - 1)
        self.frameSlider.setToolTip("current frame, drag to change current frame\n[b], [n] to set start/end marker")
        self.frameSlider.setValue(self.get_frame_count())
        if self.config.play_start is not None:
            # if >1 its a frame nr if < 1 its a fraction
            if self.config.play_start >= 1:
                self.frameSlider.setStartValue(self.config.play_start)
            else:
                self.frameSlider.setStartValue(int(self.get_frame_count()*self.config.play_start))
        if self.config.play_end is not None:
            if self.config.play_end > 1:
                self.frameSlider.setEndValue(self.config.play_end)
            else:
                self.frameSlider.setEndValue(int(self.get_frame_count()*self.config.play_end))
        self.slider_update = True
        self.layoutCtrl.addWidget(self.frameSlider)

        self.spinBox_FPS = QtWidgets.QSpinBox()
        self.spinBox_FPS.setMinimum(1)
        self.spinBox_FPS.setMaximum(1000)
        self.spinBox_FPS.setValue(self.fps)
        self.spinBox_FPS.valueChanged.connect(self.ChangedFPS)
        self.spinBox_FPS.setToolTip("play frame rate")
        self.layoutCtrl.addWidget(self.spinBox_FPS)

        self.spinBox_Skip = QtWidgets.QSpinBox()
        self.spinBox_Skip.setMinimum(0)
        self.spinBox_Skip.setMaximum(1000)
        self.spinBox_Skip.setValue(self.skip)
        self.spinBox_Skip.valueChanged.connect(self.ChangedSkip)
        self.spinBox_Skip.setToolTip("how many frames to skip during playback after each frame")
        self.layoutCtrl.addWidget(self.spinBox_Skip)

        # video replay
        self.current_fps = 0
        self.last_time = time.time()
        self.timer = PreciseTimer()
        self.timer.timeout.connect(self.updateFrame)

        self.Play(self.config.playing)
        self.hidden = True
        self.HideInterface(self.config.timeline_hide)

        self.FolderChangeEvent()

    def get_current_frame(self):
        return self.data_file.get_current_image()

    def get_frame_count(self):
        return self.data_file.get_image_count()

    def ImagesAdded(self):
        self.images_added_signal.emit()

    def ImagesAddedMain(self):
        update_end = False
        if self.frameSlider.endValue() == self.frameSlider.max_value or self.frameSlider.max_value == -1:
            update_end = True
        self.frameSlider.setRange(0, self.get_frame_count() - 1)
        if update_end:
            self.frameSlider.setEndValue(self.get_frame_count() - 1)
        self.updateLabel()

    def FolderChangeEvent(self):
        self.data_file = self.window.data_file
        if self.config.play_end is not None:
            if self.config.play_end > 1:
                self.frameSlider.setEndValue(self.config.play_end)
            else:
                self.frameSlider.setEndValue(int(self.get_frame_count()*self.config.play_end))
        else:
            self.frameSlider.setMaximum(self.get_frame_count() - 1)
        self.updateLabel()

        self.frameSlider.clearTickMarker()

    def ChangedSkip(self):
        self.skip = self.spinBox_Skip.value()

    def ChangedFPS(self):
        self.fps = self.spinBox_FPS.value()
        if self.playing:
            self.timer.start(1000 / self.fps)

    def ReleasedSlider(self):
        n = self.frameSlider.value()
        self.slider_update = True
        self.updateFrame(nr=n)

    def ReleasedSlider2(self):
        timestamp = self.timeSlider.value()
        n = self.data_file.table_images.select(self.data_file.table_images.sort_index).where(self.data_file.table_images.timestamp > timestamp).limit(1)
        if n.count() == 0:
            return
        n = n[0].sort_index
        self.slider_update = True
        self.updateFrame(nr=n)

    def PressedSlider(self):
        self.slider_update = False

    def Play(self, state):
        if state:
            self.timer.start(1000 / self.fps)
            self.button_play.setIcon(QtGui.QIcon(os.path.join(icon_path, "media-playback-pause.png")))
            self.playing = True
        else:
            self.timer.stop()
            self.button_play.setIcon(QtGui.QIcon(os.path.join(icon_path, "media-playback-start.png")))
            self.playing = False

    def updateFrame(self, nr=-1):
        if nr != -1:
            self.window.JumpToFrame(nr)
        else:
            if self.get_current_frame() < self.frameSlider.startValue() or self.get_current_frame()+1+self.skip > self.frameSlider.endValue():
                self.window.JumpToFrame(self.frameSlider.startValue())
            else:
                self.window.JumpFrames(1+self.skip)

    def updateLabel(self):
        if self.slider_update or 1:
            self.frameSlider.setValue(self.get_current_frame())

            if self.timeSlider and self.data_file.image and self.data_file.image.timestamp:
                self.timeSlider.setValue(self.data_file.image.timestamp)
            if self.get_current_frame() is not None:
                format_string = "{:%d,}" % np.ceil(np.log10(self.get_frame_count()))
                format_string = (format_string+'/'+format_string+"  {:.1f}fps")
                fps = self.current_fps if self.current_fps is not None else 0
                label_string = format_string.format(self.get_current_frame(), self.get_frame_count() - 1, fps)
            else:
                label_string = ""
            if self.data_file.image:
                label_string += "\n" + str(self.data_file.image.timestamp)
            self.label_frame.setText(label_string)

    def FrameChangeEvent(self):
        dt = time.time()-self.last_time
        self.last_time = time.time()
        if self.current_fps is None:
            self.current_fps = 1/dt
        else:
            a = np.exp(-dt)
            self.current_fps = a*self.current_fps + (1-a) * 1/dt

        self.updateLabel()
        self.timer.allow_next()

    def MaskAdded(self):
        self.frameSlider.addTickMarker(self.get_current_frame(), type=1)

    def MarkerPointsAdded(self, frame=None):
        if frame is not None:
            self.frameSlider.addTickMarker(frame, type=1)
        else:
            self.frameSlider.addTickMarker(self.get_current_frame(), type=1)

    def MarkerPointsRemoved(self):
        self.frameSlider.removeTickMarker(self.get_current_frame(), type=1)

    def AnnotationAdded(self, *args):
        self.frameSlider.addTickMarker(self.get_current_frame(), type=0)

    def AnnotationRemoved(self, *args):
        self.frameSlider.removeTickMarker(self.get_current_frame(), type=0)

    def AnnotationMarkerAdd(self, position, *args):
        self.frameSlider.addTickMarker(position, type=0)

    def HideInterface(self, hide):
        self.hidden = hide
        control_widgets = [self.layoutCtrl.itemAt(i).widget() for i in range(self.layoutCtrl.count())]
        if self.timeSlider is not None:
            control_widgets.extend(self.layoutCtrl2.itemAt(i).widget() for i in range(self.layoutCtrl2.count()))
        if hide:
            for widget in control_widgets:
                widget.setHidden(True)
            self.layoutCtrl.setContentsMargins(0, 0, 0, 0)
        else:
            for widget in control_widgets:
                widget.setHidden(False)
            self.layoutCtrl.setContentsMargins(5, 5, 5, 5)

    def keyPressEvent(self, event):
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
        if event.key() == QtCore.Qt.Key_Left and event.modifiers() & Qt.ControlModifier:
            # @key Ctrl+Left: previous annotated image
            tick = self.frameSlider.getNextTick(self.get_current_frame(), back=True)
            self.window.JumpToFrame(tick)
        if event.key() == QtCore.Qt.Key_Right and event.modifiers() & Qt.ControlModifier:
            # @key Ctrl+Right: next annotated image
            tick = self.frameSlider.getNextTick(self.get_current_frame())
            self.window.JumpToFrame(tick)

        if event.key() == QtCore.Qt.Key_Left and event.modifiers() & Qt.AltModifier:
            # @key Alt+Left: previous annotation block
            tick = self.frameSlider.getNextTickChange(self.get_current_frame(), back=True)
            self.window.JumpToFrame(tick)
        if event.key() == QtCore.Qt.Key_Right and event.modifiers() & Qt.AltModifier:
            # @key Alt+Right: next annotation block
            tick = self.frameSlider.getNextTickChange(self.get_current_frame())
            self.window.JumpToFrame(tick)

    def closeEvent(self, event):
        self.Play(False)

    @staticmethod
    def file():
        return __file__
