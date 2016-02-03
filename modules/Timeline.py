from __future__ import division, print_function
import sys
import os
import glob
import time
import numpy as np
import datetime
try:
    import thread  # python 2
except ImportError:
    import _thread as thread  # python 3

try:
    from PyQt5 import QtGui, QtCore
    from PyQt5.QtWidgets import QIcon, QGraphicsRectItem, QPen, QBrush, QColor, QLinearGradient, QGraphicsPathItem, QPainterPath, QGraphicsScene, QGraphicsView, QPalette, QCursor
    from PyQt5.QtCore import Qt, QPointF, QObject
    from PyQt5.QtCore import pyqtSignal
except ImportError:
    from PyQt4 import QtGui, QtCore
    from PyQt4.QtGui import QIcon, QGraphicsRectItem, QPen, QBrush, QColor, QLinearGradient, QGraphicsPathItem, QPainterPath, QGraphicsScene, QGraphicsView, QPalette, QCursor
    from PyQt4.QtCore import Qt, QPointF, QObject
    from PyQt4.QtCore import pyqtSignal

icon_path = os.path.join(os.path.dirname(__file__), "..", "icons")

def BoundBy(value, min, max):
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

class TimeLineGrabberSignal(QObject):
    sliderPressed = pyqtSignal()
    sliderMoved = pyqtSignal()
    sliderReleased = pyqtSignal()

class TimeLineGrabber(QGraphicsPathItem):
    def __init__(self, parent, value, path, gradient):
        QGraphicsPathItem.__init__(self, None, parent.scene)
        self.parent = parent
        self.pixel_range = [0, 100]
        self.value_range = [0, 100]
        self.setCursor(QCursor(QtCore.Qt.OpenHandCursor))
        self.dragged = False

        self.setPath(path)
        self.setBrush(QBrush(gradient))
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

    def setValue(self, value):
        self.value = value
        self.updatePos()

class TimeLineSlider(QGraphicsView):
    def __init__(self, max_value=100, min_value=0):
        QGraphicsView.__init__(self)

        self.setMaximumHeight(30)
        #self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.scene.setBackgroundBrush(self.palette().color(QPalette.Background))
        self.setStyleSheet("border: 0px")

        self.max_value = max_value
        self.min_value = min_value

        self.slider_line = QGraphicsRectItem(None, self.scene)
        self.slider_line.setPen(QPen(QColor("black")))
        self.slider_line.setPos(0, -2.5)
        gradient = QLinearGradient(QPointF(0, 0), QPointF(0, 5))
        gradient.setColorAt(0, QColor("black"))
        gradient.setColorAt(1, QColor(128, 128, 128))
        self.slider_line.setBrush(QBrush(gradient))
        self.slider_line.mousePressEvent = self.SliderBarMousePressEvent

        self.slider_line_active = QGraphicsRectItem(None, self.scene)
        self.slider_line_active.setPen(QPen(QColor("black")))
        self.slider_line_active.setPos(0, -2.5)
        gradient = QLinearGradient(QPointF(0, 0), QPointF(0, 5))
        gradient.setColorAt(0, QColor(128, 128, 128))
        gradient.setColorAt(1, QColor(200, 200, 200))
        self.slider_line_active.setBrush(QBrush(gradient))

        path = QPainterPath()
        path.moveTo(-4, +12)
        path.lineTo( 0,  +2.5)
        path.lineTo(+4, +12)
        path.lineTo(-4, +12)
        gradient = QLinearGradient(QPointF(0, 12), QPointF(0, 2.5))
        gradient.setColorAt(0, QColor(255, 0, 0))
        gradient.setColorAt(1, QColor(128, 0, 0))
        self.slider_start = TimeLineGrabber(self, 0, path, gradient)
        self.slider_start.signal.sliderMoved.connect(self.slider_start_changed)

        path = QPainterPath()
        path.moveTo(-4, -12)
        path.lineTo( 0,  -2.5)
        path.lineTo(+4, -12)
        path.lineTo(-4, -12)
        gradient = QLinearGradient(QPointF(0, -12), QPointF(0, -2.5))
        gradient.setColorAt(0, QColor(255, 0, 0))
        gradient.setColorAt(1, QColor(128, 0, 0))
        self.slider_end = TimeLineGrabber(self, 100, path, gradient)
        self.slider_end.signal.sliderMoved.connect(self.slider_end_changed)

        path = QPainterPath()
        path.addRect(-2, -7, 5, 14)
        gradient = QLinearGradient(QPointF(0, -7), QPointF(0, 14))
        gradient.setColorAt(0, QColor(255, 0, 0))
        gradient.setColorAt(1, QColor(128, 0, 0))
        self.slider_position = TimeLineGrabber(self, 0, path, gradient)

        self.length = 1

        self.tick_marker = {}

    def SliderBarMousePressEvent(self, event):
        self.setValue(self.PixelToValue(self.slider_line.mapToScene(event.pos()).x()))
        self.slider_position.signal.sliderReleased.emit()

    def addTickMarker(self, pos, type=0, color=QColor("red"), height=12):
        if type == 1:
            color = QColor("green")
            height = 8
        if pos in self.tick_marker and type in self.tick_marker[pos]:
            tick_marker = self.tick_marker[pos][type]
        else:
            width = self.ValueToPixel(1)
            if pos == self.max_value:
                width = 2
            tick_marker = QGraphicsRectItem(0.0, -3.5, width, -height, None, self.scene)
        tick_marker.setPen(QPen(color))
        tick_marker.setBrush(QBrush(color))
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
            my_range = range(pos+1,self.max_value,+1)
        else:
            my_range = range(pos-1,self.min_value,-1)
        search_marked = True
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

class RealTimeSlider(QGraphicsView):
    def __init__(self, max_value=100, min_value=0):
        QGraphicsView.__init__(self)

        self.setMaximumHeight(30)
        #self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.scene.setBackgroundBrush(self.palette().color(QPalette.Background))
        self.setStyleSheet("border: 0px")


        self.slider_line = QGraphicsRectItem(None, self.scene)
        self.slider_line.setPen(QPen(QColor("black")))
        self.slider_line.setPos(0, -2.5)
        gradient = QLinearGradient(QPointF(0, 0), QPointF(0, 5))
        gradient.setColorAt(0, QColor("black"))
        gradient.setColorAt(1, QColor(128, 128, 128))
        self.slider_line.setBrush(QBrush(gradient))
        #self.slider_line.mousePressEvent = self.SliderBarMousePressEvent

        self.markerParent = QGraphicsPathItem(None, self.scene)
        self.markerGroupParents = []
        for i in range(20):
            self.markerGroupParents.append(QGraphicsPathItem(self.markerParent))
        #self.markerGroupParents[0].setVisible(False)



        path = QPainterPath()
        path.addRect(-2, -7, 5, 14)
        gradient = QLinearGradient(QPointF(0, -7), QPointF(0, 14))
        gradient.setColorAt(0, QColor(255, 0, 0))
        gradient.setColorAt(1, QColor(128, 0, 0))
        self.slider_position = TimeLineGrabberTime(self, 0, path, gradient)

        self.length = 1

        self.scene_panning = False

        self.tick_marker = {}

        self.scale = 1
        self.pan = 0

    def SliderBarMousePressEvent(self, event):
        self.setValue(self.PixelToValue(self.slider_line.mapToScene(event.pos()).x()))
        self.slider_position.signal.sliderReleased.emit()

    def tick_time(self, tick_marker):
        tick_marker.setAlpha(0.5)
        tick_marker.timer.stop()
        print("tick_time")

    def addTickMarker(self, pos, type=-1, type_name="", color=QColor("red"), height=12, text=""):
        if pos in self.tick_marker and type in self.tick_marker[pos]:
            tick_marker = self.tick_marker[pos][type]
        else:
            if type == -1:
                tick_marker = QtGui.QGraphicsLineItem(0, -5, 0, -height, self.markerParent)
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
                tick_marker = QtGui.QGraphicsLineItem(0, -0.5, 0, -height, self.markerGroupParents[type])#self.scene)
                tick_marker.setZValue(1)#+type)
        tick_marker.setPen(QPen(color))
        if type == -1:
            tick_marker.setPen(QPen(color, 3))
        #tick_marker.setBrush(QBrush(color))
        tick_marker.value = pos
        tick_marker.type = type
        tick_marker.height = height

        #tick_marker.timer = QtCore.QTimer(self)
        #tick_marker.timer.timeout.connect(lambda p=tick_marker: self.tick_time(p))
        #tick_marker.timer.startTimer(10)

        tick_marker.setPos(self.ValueToPixel(pos), 0)
        if text != "":
            self.font_parent = QtGui.QGraphicsPathItem(tick_marker)

            self.font = QtGui.QFont()
            self.font.setPointSize(8)
            self.text = QtGui.QGraphicsSimpleTextItem(self.font_parent)
            self.text.setFont(self.font)
            self.text.setText(text)
            offsetX = self.text.boundingRect().width()
            offsetY = self.text.boundingRect().height()
            self.text.setPos(-offsetX*0.5+1, 0)#+height*0.5+offsetY)
            self.font_parent.setFlag(QtGui.QGraphicsItem.ItemIgnoresTransformations)
            tick_marker.text = self.text
        else:
            tick_marker.text = None
        if pos not in self.tick_marker:
            self.tick_marker[pos] = {}
        self.tick_marker[pos][type] = tick_marker
        #self.repaint()

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
            my_range = range(pos+1,self.max_value,+1)
        else:
            my_range = range(pos-1,self.min_value,-1)
        search_marked = True
        if pos in self.tick_marker and my_range[0] in self.tick_marker:
            search_marked = False
        for i in my_range:
            if (i in self.tick_marker) == search_marked:
                return i
        return my_range[-1]

    def resizeEvent(self, event):
        self.length = self.size().width()#-20
        self.slider_line.setRect(0, -0.5, self.length, 1)
        self.setSceneRect(0, -10, self.size().width(), 20)
        self.ensureVisible(self.slider_line)
        for pos, ticks in self.tick_marker.items():
            for type, tick in ticks.items():
                tick.setPos(self.ValueToPixel(pos), 0)
                #width = 2#self.ValueToPixel(1)
                #if pos == self.max_value:
                #    width = 2
                #tick.setRect(0.0, -3.5, width, -tick.height)
        for marker in [self.slider_position]:
            marker.setPixelRange(0, self.length)
        self.repaint()

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

    def setTimes(self, media_handler):
        import time as timing
        print("Start Timeline")
        t = timing.time()
        self.media_handler = media_handler
        self.min_value = np.min(self.media_handler.timestamps)
        self.max_value = np.max(self.media_handler.timestamps)
        #delta = np.min(np.diff(self.media_handler.timestamps))
        self.slider_position.setValueRange(self.min_value, self.max_value)
        for time in self.media_handler.timestamps:
            self.addTickMarker(time, color=QColor(128, 128, 128))
        start = self.media_handler.timestamps[0]
        tick_types = [["second", 5, 0],
                      ["second", 10, 0],
                      ["second", 0, 0],
                      ["minute", 5, 0],
                      ["minute", 10, 0],
                      ["minute", 0, 0],
                      ["hour", 3, 0],
                      ["hour", 6, 0],
                      ["hour", 12, 0],
                      ["hour", 0, 0],
                      ["day", 0, 1],
                      ["month", 0, 1],
                      ["year", 0, 1]]
        tick_time = datetime.datetime(year=start.year, month=start.month, day=start.day, hour=start.hour, minute=start.minute)#datetime.datetime.combine(self.media_handler.timestamps[0].date(), datetime.time())+datetime.timedelta(days=1)
        '''
        while tick_time < self.max_value:
            type = 0
            while 1:
                tick_type = tick_types[type]
                #print(tick_type, tick_type[1])
                value = getattr(tick_time, tick_type[0])
                #if tick_type[0] == "minute":
                #    print(tick_type[0], value, tick_type[1], tick_type[2])
                if tick_type[1]:
                    value %= tick_type[1]
                    #if tick_type[0] == "minute":
                    #    print("Modul", value, tick_type[1], tick_type[0], getattr(tick_time, tick_type[0]))
                if value != tick_type[2]:
                    break
                type += 1
            #if type >= 2:
            #    print(type)
            self.addTickMarker(tick_time, color=QColor(0, 128, 255), height=15, type=type, type_name=tick_types[type][0])
            """
            if tick_time.minute == 0 and tick_time.day == 1 and tick_time.hour == 0:
                self.addTickMarker(tick_time, color=QColor(0, 128, 255), text="%02d.%02d" % (tick_time.day, tick_time.month), height=15, type=12)
            elif tick_time.minute == 0 and tick_time.hour == 0:
                self.addTickMarker(tick_time, color=QColor(0, 0, 255), text="%02d" % tick_time.day, type=11)
            elif tick_time.minute == 0:
                self.addTickMarker(tick_time, color=QColor(50, 0, 128), text="%02dh" % tick_time.hour, height=8, type=10)
            else:
                self.addTickMarker(tick_time, color=QColor(50, 0, 128), text="%02d'" % tick_time.minute, height=8, type=10)
            """
            tick_time = tick_time+datetime.timedelta(**{tick_types[0][0]+"s":1})
        '''
        print("End Timeline", timing.time()-t)

    def updateTicks(self):

        for pos, ticks in self.tick_marker.items():
            for type, tick in ticks.items():
                if type == -1:
                    continue
                if tick.scene():
                    tick.scene().removeItem(tick)
                del self.tick_marker[pos][type]
                #del tick
            if self.tick_marker[pos] == {}:
                del self.tick_marker[pos]

        # determine the smallest possible ticks
        delta_min = self.PixelToValue(60)-self.min_value
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
                       ]
        type_delta = type_deltas[0]
        type_delta_minor = type_deltas[0]
        for type_delta_test in type_deltas:
            type_delta = type_delta_test
            if type_delta_test > delta_min:
                break
            type_delta_minor = type_delta_test
        #print(self.ValueToPixel(type_delta+self.min_value), self.ValueToPixel(delta_min+self.min_value))

        tick_types = [["second", 0, 0],
                      ["minute", 0, 0],
                      ["hour", 0, 0],
                      ["day", 0, 1],
                      ["month", 0, 1],
                      ["year", 0, 1]]
        # round to the nearest tick
        years = 0
        months = 0
        if type_delta >= datetime.timedelta(days=356):
            # round to years
            years = int(type_delta.days/356)
            tick_time = datetime.datetime(roundValue(self.min_value.year, years), 1, 1)
        elif type_delta >= datetime.timedelta(days=30):
            # round to months
            months = int(type_delta.days/30)
            print("############# rounding to months", roundValue(self.min_value.month, months, 1), months)
            tick_time = datetime.datetime(self.min_value.year, roundValue(self.min_value.month, months, 1), 1)
        else:
            tick_time = roundTime(self.min_value, type_delta.total_seconds())

        type_delta_major = type_delta
        type_delta = type_delta_minor
        print("Major Minor", type_delta_major, type_delta_minor)

        count = 0
        self.tick_start = tick_time
        while tick_time < self.max_value:
            type = 0
            while 1:
                tick_type = tick_types[type]
                #print(tick_type, tick_type[1])
                value = getattr(tick_time, tick_type[0])
                #if tick_type[0] == "minute":
                #    print(tick_type[0], value, tick_type[1], tick_type[2])
                if tick_type[1]:
                    value %= tick_type[1]
                    #if tick_type[0] == "minute":
                    #    print("Modul", value, tick_type[1], tick_type[0], getattr(tick_time, tick_type[0]))
                if value != tick_type[2]:
                    break
                type += 1
            #if type >= 2:
            #    print(type)
            #print("Major?", (tick_time-self.tick_start).total_seconds() % type_delta_major.total_seconds(), type_delta_major.total_seconds())
            if (tick_time-self.tick_start).total_seconds() % type_delta_major.total_seconds() == 0:
                self.addTickMarker(tick_time, color=QColor(0, 0, 0), height=15, type=type, type_name=tick_types[type][0])
            else:
                self.addTickMarker(tick_time, color=QColor(0, 0, 0), height=10, type=type, type_name="")
            if years:
                tick_time = datetime.datetime(tick_time.year+years, tick_time.month, 1)
            elif months:
                if tick_time.month+months > 12:
                    tick_time = datetime.datetime(tick_time.year+1, 1, 1)
                else:
                    tick_time = datetime.datetime(tick_time.year, tick_time.month+months, 1)
            else:
                tick_time = tick_time+type_delta
            count += 1
        print(type_delta, count)
        self.repaint()
        #type_jumps = [{"seconds": 1}, {"seconds": 5}, {"seconds": 10}, {"minutes": 1}, {"minutes": 5}, {"minutes": 10}, {"hours": 1}, {"hours": 3}, {"hours": 6}, {"hours": 12}, {"days": 1}, {"days": 30}, {"days": 356}]


    def mousePressEvent(self, event):
        if event.button() == 2:
            self.last_pos = PosToArray(self.mapToScene(event.pos()))
            self.scene_panning = True
        super(RealTimeSlider, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.scene_panning:
            new_pos = PosToArray(self.mapToScene(event.pos()))
            delta = (new_pos-self.last_pos)[0]
            self.last_pos = new_pos
            print(delta)
            delta = self.PixelToValue(delta)-self.min_value
            print(delta)
            #self.markerParent.translate(delta/self.scale, 0)
            self.min_value -= delta
            self.max_value -= delta
            #self.translater.setTransform(QtGui.QTransform(1, 0, 0, 1, *delta/self.scaler.transform().m11()), combine=True)
            self.last_pos = new_pos
            self.fitted = 0
            self.slider_position.setValueRange(self.min_value, self.max_value)
            self.updateTicks()
            self.resizeEvent(None)
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
        if angle > 0:
            self.scale *= 1.1
            self.markerParent.scale(1.1, 1)
            #self.scaleOrigin(1.1, event.pos())
        else:
            self.scale *= 0.9
            self.markerParent.scale(0.9, 1)
            #self.scaleOrigin(0.9, event.pos())
        event.accept()

        self.updateTicks()
        """
        tick_types = ["second", "5 seconds", "10 seconds", "minute", "5 minutes", "10 minutes", "hour", "day", "month", "year"]
        type_jumps = [{"seconds": 1}, {"seconds": 5}, {"seconds": 10}, {"minutes": 1}, {"minutes": 5}, {"minutes": 10}, {"hours": 1}, {"hours": 3}, {"hours": 6}, {"hours": 12}, {"days": 1}, {"days": 30}, {"days": 356}]
        tick_type_defaults = [0, 0, 1, 1, 1]
        for index, type_jump in enumerate(type_jumps):
            type_pixel = self.ValueToPixel(datetime.timedelta(**type_jump)+self.min_value)*self.scale
            self.markerGroupParents[index].setVisible(type_pixel > 40)
            #print(tick_types[index], type_pixel)
        """

    def wheelEvent(self, event):
        event.ignore()
        super(RealTimeSlider, self).wheelEvent(event)
        if event.isAccepted():
            return

        if 0:#qt_version == '5':
            angle = event.angleDelta().y()
        else:
            angle = event.delta()
        pos = self.PixelToValue(event.pos().x())
        percent = Remap(pos, [self.min_value, self.max_value], [0, 1])
        if angle > 0:
            zoom_percent = +0.1#1.1
        else:
            zoom_percent = -0.1#0.9

        try:
            zoom_delta = (self.max_value-self.min_value)*zoom_percent

            self.min_value += zoom_delta*percent
            self.max_value += zoom_delta*(1-percent)
        except TypeError:  # for python 2
            zoom_delta = datetime.timedelta(seconds=zoom_percent*(self.max_value-self.min_value).total_seconds())

            self.min_value += datetime.timedelta(seconds=zoom_delta.total_seconds()*percent)
            self.max_value -= datetime.timedelta(seconds=zoom_delta.total_seconds()*(1-percent))
        self.slider_position.setValueRange(self.min_value, self.max_value)

        self.updateTicks()
        """
        hour_pixel = self.ValueToPixel(datetime.timedelta(hours=1)+self.min_value)
        day_pixel = self.ValueToPixel(datetime.timedelta(days=1)+self.min_value)
#        if hour_pixel < 15:
        for pos, ticks in self.tick_marker.items():
            for type, tick in ticks.items():
                if type == 10:
                    tick.setVisible(hour_pixel > 15)
                    tick.text.setVisible(hour_pixel > 20)
                if type == 11:
                    tick.setPen(QPen(tick.pen().color(), 1+(hour_pixel > 15)*1))
                    f = tick.text.font()
                    f.setWeight(50+13*(hour_pixel > 20))
                    tick.text.setFont(f)
                    tick.pen().setWidth(50)#+(hour_pixel > 15)*5)
                    tick.setVisible(day_pixel > 15)
                    tick.text.setVisible(day_pixel > 20)
        self.resizeEvent(None)
        """
        self.resizeEvent(None)
        event.accept()


def PosToArray(pos):
    return np.array([pos.x(), pos.y()])

class PreciseTimer(QObject):
    timeout = pyqtSignal()

    def __init__(self, ):
        QObject.__init__(self)
        self.thread = None
        self.delta = 1
        self.timer_start = time.time()
        self.count = 1
        self.run = False
        self.active = 1

    def start(self, delta=None):
        if delta is not None:
            self.delta = delta
        self.timer_start = time.time()
        self.count = 1
        if not self.run:
            self.run = True
            thread.start_new_thread(self.thread_timer, tuple())

    def stop(self):
        self.run = False

    def allow_next(self):
        self.active = 1

    def thread_timer(self):
        while self.run:
            if (time.time()-self.timer_start)*1e3 > self.delta*self.count and self.active:
                self.count += 1
                self.timeout.emit()
                self.active = 0
            time.sleep(0.01)

class Timeline:
    def __init__(self, window, media_handler, layout, outputpath, config, modules):
        self.window = window
        self.media_handler = media_handler
        self.config = config
        self.modules = modules

        self.fps = 0#self.media_handler.fps
        if self.fps == 0:
            self.fps = 25
        if self.config.fps != 0:
            self.fps = self.config.fps
        self.skip = 0

        # control elements
        self.layoutCtrlParent = QtGui.QVBoxLayout()
        layout.addLayout(self.layoutCtrlParent)
        self.layoutCtrl = QtGui.QHBoxLayout()
        self.layoutCtrlParent.addLayout(self.layoutCtrl)
        self.layoutCtrl2 = QtGui.QHBoxLayout()
        self.layoutCtrlParent.addLayout(self.layoutCtrl2)

        # second
        self.timeSlider = RealTimeSlider()
        self.timeSlider.setTimes(self.media_handler)
        self.layoutCtrl2.addWidget(self.timeSlider)

        self.timeSlider.slider_position.signal.sliderPressed.connect(self.PressedSlider)
        self.timeSlider.slider_position.signal.sliderReleased.connect(self.ReleasedSlider2)

        # frame control
        self.button_play = QtGui.QPushButton()
        self.button_play.setCheckable(True)
        self.button_play.toggled.connect(self.Play)
        self.layoutCtrl.addWidget(self.button_play)

        self.label_frame = QtGui.QLabel("")
        self.label_frame.setMinimumWidth(40)
        self.label_frame.setAlignment(Qt.AlignVCenter)
        self.layoutCtrl.addWidget(self.label_frame)

        self.frameSlider = TimeLineSlider()
        self.frameSlider.slider_position.signal.sliderPressed.connect(self.PressedSlider)
        self.frameSlider.slider_position.signal.sliderReleased.connect(self.ReleasedSlider)
        self.frameSlider.setRange(0, self.media_handler.get_frame_count() - 1)
        self.frameSlider.setValue(self.media_handler.get_index())
        if self.config.play_start is not None:
            # if >1 its a frame nr if < 1 its a fraction
            if self.config.play_start >= 1:
                self.frameSlider.setStartValue(self.config.play_start)
            else:
                self.frameSlider.setStartValue(int(self.media_handler.get_frame_count()*self.config.play_start))
        if self.config.play_end is not None:
            if self.config.play_end > 1:
                self.frameSlider.setEndValue(self.config.play_end)
            else:
                self.frameSlider.setEndValue(int(self.media_handler.get_frame_count()*self.config.play_end))
        self.slider_update = True
        self.layoutCtrl.addWidget(self.frameSlider)

        self.spinBox_FPS = QtGui.QSpinBox()
        self.spinBox_FPS.setMinimum(1)
        self.spinBox_FPS.setMaximum(1000)
        self.spinBox_FPS.setValue(self.fps)
        self.spinBox_FPS.valueChanged.connect(self.ChangedFPS)
        self.layoutCtrl.addWidget(self.spinBox_FPS)

        self.spinBox_Skip = QtGui.QSpinBox()
        self.spinBox_Skip.setMinimum(0)
        self.spinBox_Skip.setMaximum(1000)
        self.spinBox_Skip.setValue(self.skip)
        self.spinBox_Skip.valueChanged.connect(self.ChangedSkip)
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

    def FolderChangeEvent(self):
        self.media_handler = self.window.media_handler
        if self.config.play_end is not None:
            if self.config.play_end > 1:
                self.frameSlider.setEndValue(self.config.play_end)
            else:
                self.frameSlider.setEndValue(int(self.media_handler.get_frame_count()*self.config.play_end))
        else:
            self.frameSlider.setMaximum(self.media_handler.get_frame_count() - 1)
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
        self.updateLabel()
        self.updateFrame(nr=n)

    def ReleasedSlider2(self):
        timestamp = self.timeSlider.value()
        n = self.media_handler.get_frame_number_by_timestamp(timestamp)
        self.slider_update = True
        self.updateLabel()
        self.updateFrame(nr=n)

    def PressedSlider(self):
        self.slider_update = False

    def Play(self, state):
        if state:
            self.timer.start(1000 / self.fps)
            self.button_play.setIcon(QIcon(os.path.join(icon_path, "media-playback-pause.png")))
            self.playing = True
        else:
            self.timer.stop()
            self.button_play.setIcon(QIcon(os.path.join(icon_path, "media-playback-start.png")))
            self.playing = False

    def updateFrame(self, nr=-1):
        if nr != -1:
            self.window.JumpToFrame(nr)
        else:
            if self.media_handler.get_index() < self.frameSlider.startValue() or self.media_handler.get_index()+1+self.skip > self.frameSlider.endValue():
                self.window.JumpToFrame(self.frameSlider.startValue(), self.frameSlider.startValue()+1+self.skip)
            else:
                self.window.JumpFrames(1+self.skip, 1+self.skip)

    def updateLabel(self):
        if self.slider_update:
            self.frameSlider.setValue(self.media_handler.get_index())
            self.timeSlider.setValue(self.media_handler.get_timestamp())
            digits = "%d" % np.ceil(np.log10(self.media_handler.get_frame_count()))
            format_string = ('%0'+digits+'d/%d  %.1ffps')
            fps = self.current_fps if self.current_fps is not None else 0
            label_string = format_string % (self.media_handler.get_index(), self.media_handler.get_frame_count() - 1, fps)
            self.label_frame.setText(label_string + "\n" + str(self.window.data_file.timestamp))

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
        self.frameSlider.addTickMarker(self.media_handler.get_index(), type=1)

    def MarkerPointsAdded(self, frame=None):
        if frame:
            self.frameSlider.addTickMarker(frame, type=1)
        else:
            self.frameSlider.addTickMarker(self.media_handler.get_index(), type=1)

    def MarkerPointsRemoved(self):
        self.frameSlider.removeTickMarker(self.media_handler.get_index(), type=1)

    def AnnotationAdded(self, *args):
        self.frameSlider.addTickMarker(self.media_handler.get_index(), type=0)

    def AnnotationRemoved(self, *args):
        self.frameSlider.removeTickMarker(self.media_handler.get_index(), type=0)

    def AnnotationMarkerAdd(self, position, *args):
        self.frameSlider.addTickMarker(position, type=0)

    def HideInterface(self, hide):
        self.hidden = hide
        control_widgets = (self.layoutCtrl.itemAt(i).widget() for i in range(self.layoutCtrl.count()))
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
            self.frameSlider.setStartValue(self.media_handler.get_index())
        # @key N: move start marker here
        if event.key() == QtCore.Qt.Key_N:
            self.frameSlider.setEndValue(self.media_handler.get_index())

        # @key ---- Frame jumps ----
        if event.key() == QtCore.Qt.Key_Left and event.modifiers() & Qt.ControlModifier:
            # @key Ctrl+Left: previous annotated image
            tick = self.frameSlider.getNextTick(self.media_handler.get_index(), back=True)
            self.window.JumpToFrame(tick)
        if event.key() == QtCore.Qt.Key_Right and event.modifiers() & Qt.ControlModifier:
            # @key Ctrl+Right: next annotated image
            tick = self.frameSlider.getNextTick(self.media_handler.get_index())
            self.window.JumpToFrame(tick)

    @staticmethod
    def file():
        return __file__
