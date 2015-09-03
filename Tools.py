from __future__ import division

try:
    from PyQt5 import QtGui, QtCore
    from PyQt5.QtWidgets import QGraphicsRectItem, QGraphicsPathItem, QGraphicsView, QColor, QGraphicsItem, QCursor, QBrush, QPen, QGraphicsSimpleTextItem, QFont, QPainterPath, QGraphicsScene, QPalette, QLinearGradient
    from PyQt5.QtCore import QRectF, QPointF
except ImportError:
    from PyQt4 import QtGui, QtCore
    from PyQt4.QtGui import QGraphicsRectItem, QGraphicsPathItem, QGraphicsView, QColor, QGraphicsItem, QCursor, QBrush, QPen, QGraphicsSimpleTextItem, QFont, QPainterPath, QGraphicsScene, QPalette, QLinearGradient
    from PyQt4.QtCore import QRectF, QPointF

import numpy as np


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

def BroadCastEvent(modules, function, *args, **kwargs):
    for module in modules:
         if function in dir(module):
                eval("module."+function+"(*args, **kwargs)")

class HelpText(QGraphicsRectItem):
    def __init__(self, window, file, modules=[]):
        QGraphicsRectItem.__init__(self, window.view.hud)

        self.setCursor(QCursor(QtCore.Qt.ArrowCursor))

        self.help_text = QGraphicsSimpleTextItem(self)
        self.help_text.setFont(QFont("", 11))
        self.help_text.setPos(0, 10)
        self.help_text.setBrush(QBrush(QColor(255, 255, 255)))

        self.setBrush(QBrush(QColor(0, 0, 0, 128)))
        self.setPos(100, 100)
        self.setZValue(19)

        self.text = ""
        self.UpdateText(file)
        for mod in modules:
            self.UpdateText(mod.file())
        self.DisplayText()
        BoxGrabber(self)
        self.setVisible(False)

    def ShowHelpText(self):
        if self.isVisible():
            self.setVisible(False)
        else:
            self.setVisible(True)

    def UpdateText(self, file):
        import re
        if file[-4:] == ".pyc":
            file = file[:-4]+".py"
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


class MySlider(QGraphicsRectItem):
    def __init__(self, parent, name="", start_value=None, max_value=100, min_value=0):
        QGraphicsRectItem.__init__(self, parent)

        self.parent = parent
        self.name = name
        self.maxValue = max_value
        self.minValue = min_value
        self.format = "%.2f"

        self.setCursor(QCursor(QtCore.Qt.OpenHandCursor))
        self.setPen(QPen(QColor(255, 255, 255, 0)))

        self.text = QGraphicsSimpleTextItem(self)
        self.text.setFont(QFont("", 11))
        self.text.setPos(0, -23)
        self.text.setBrush(QBrush(QColor("white")))

        self.sliderMiddel = QGraphicsRectItem(self)
        self.sliderMiddel.setRect(QRectF(0, 0, 100, 1))
        self.sliderMiddel.setPen(QPen(QColor("white")))

        path = QPainterPath()
        path.addEllipse(-5, -5, 10, 10)
        self.slideMarker = QGraphicsPathItem(path, self)
        self.slideMarker.setBrush(QBrush(QColor(255, 0, 0, 255)))

        self.setRect(QRectF(-5, -5, 110, 10))
        self.dragged = False

        self.value = (self.maxValue + self.minValue) * 0.5
        if start_value != None:
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

class MyMultiSliderGrabber(QGraphicsPathItem):
    def __init__(self, parent):
        QGraphicsPathItem.__init__(self, None, parent.scene)
        self.parent = parent
        self.range = [0,100]
        self.setCursor(QCursor(QtCore.Qt.OpenHandCursor))

    def setRange(self, min, max):
        self.range = [min, max]

    def mousePressEvent(self, event):
        if event.button() == 1:
            self.dragged = True
            self.parent.sliderPressed()

    def mouseMoveEvent(self, event):
        if self.dragged:
            x = self.mapToParent(event.pos()).x()
            if x < self.range[0]: x = self.range[0]
            if x > self.range[1]: x = self.range[1]
            self.setPos(x, 0)
            self.parent.markerPosChanged(x, self)

    def mouseReleaseEvent(self, event):
        self.dragged = False
        self.parent.sliderReleased()


class MyMultiSlider(QGraphicsView):
    def __init__(self, max_value=100, min_value=0):
        QGraphicsView.__init__(self)

        self.setMaximumHeight(30)
        #self.setRenderHint(QtGui.QPainter.Antialiasing)

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.scene.setBackgroundBrush(self.palette().color(QPalette.Background))
        self.setStyleSheet("border: 0px")

        self.max_value = max_value
        self.min_value = min_value

        self.slider_line = QGraphicsRectItem(None, self.scene)
        self.slider_line.setPen(QPen(QColor("black")))
        self.slider_line.setPos(0,-2.5)
        gradient = QLinearGradient(QPointF(0, 0), QPointF(0, 5))
        gradient.setColorAt(0, QColor("black"))
        gradient.setColorAt(1, QColor(128,128,128))
        self.slider_line.setBrush(QBrush(gradient))
        self.slider_line.mousePressEvent = self.SliderBarMousePressEvent

        self.slider_line_active = QGraphicsRectItem(None, self.scene)
        self.slider_line_active.setPen(QPen(QColor("black")))
        self.slider_line_active.setPos(0,-2.5)
        gradient = QLinearGradient(QPointF(0, 0), QPointF(0, 5))
        gradient.setColorAt(0, QColor(128,128,128))
        gradient.setColorAt(1, QColor(200,200,200))
        self.slider_line_active.setBrush(QBrush(gradient))

        path = QPainterPath()
        path.moveTo(-4, +12)
        path.lineTo( 0,  +2.5)
        path.lineTo(+4, +12)
        path.lineTo(-4, +12)
        self.slider_start = MyMultiSliderGrabber(self)
        self.slider_start.setPath(path)
        gradient = QLinearGradient(QPointF(0, 12), QPointF(0, 2.5))
        gradient.setColorAt(0, QColor(255,0,0))
        gradient.setColorAt(1, QColor(128,0,0))
        self.slider_start.setBrush(QBrush(gradient))
        self.slider_start.setZValue(10)
        self.slider_start.value = 0

        path = QPainterPath()
        path.moveTo(-4,-12)
        path.lineTo( 0, -2.5)
        path.lineTo(+4,-12)
        path.lineTo(-4,-12)
        self.slider_end = MyMultiSliderGrabber(self)
        self.slider_end.setPath(path)
        gradient = QLinearGradient(QPointF(0, -12), QPointF(0, -2.5))
        gradient.setColorAt(0, QColor(255,0,0))
        gradient.setColorAt(1, QColor(128,0,0))
        self.slider_end.setBrush(QBrush(gradient))
        self.slider_end.setZValue(10)
        self.slider_end.value = 100

        path = QPainterPath()
        path.addRect(-2, -7, 5, 14)
        self.slider_position = MyMultiSliderGrabber(self)
        self.slider_position.setPath(path)
        gradient = QLinearGradient(QPointF(0, -7), QPointF(0, 14))
        gradient.setColorAt(0, QColor(255,0,0))
        gradient.setColorAt(1, QColor(128,0,0))
        self.slider_position.setBrush(QBrush(gradient))
        self.slider_position.setZValue(10)
        self.slider_position.value = 0

        self.length = 1

        self.tick_marker = {}

    def SliderBarMousePressEvent(self, event):
        self.setValue(self.PixelToValue(self.slider_line.mapToScene(event.pos()).x()))
        self.sliderReleased()

    def addTickMarker(self, pos, type=0, color=QColor("red"), height=12):
        if type == 1:
            color = QColor("green")
            height = 8
        if pos in self.tick_marker and type in self.tick_marker[pos]:
            tick_marker = self.tick_marker[pos][type]
        else:
            tick_marker = QGraphicsRectItem(0.0, -3.5, self.ValueToPixel(1), -height, None, self.scene)
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
                tick.setRect(0.0, -3.5, self.ValueToPixel(1), -tick.height)
        for marker in [self.slider_position, self.slider_start, self.slider_end]:
            marker.setPos(self.ValueToPixel(marker.value), 0)
            marker.setRange(0, self.length)
        self.repaint()

    def setMinimum(self, value):
        self.min_value = value

    def setMaximum(self, value):
        self.max_value = value
        self.slider_end.value = value

    def setValue(self, value):
        if value < self.min_value:
            value = self.min_value
        if value >= self.max_value:
            value = self.max_value
        self.slider_position.value = value
        self.slider_position.setPos(self.ValueToPixel(self.slider_position.value), 0)

    def setStartValue(self, value):
        if value < self.min_value:
            value = self.min_value
        if value >= self.max_value:
            value = self.max_value
        self.slider_start.value = value
        self.slider_start.setPos(self.ValueToPixel(self.slider_start.value), 0)

    def setEndValue(self, value):
        if value < 0:
            value = self.max_value-value
        if value < self.min_value:
            value = self.min_value
        if value >= self.max_value:
            value = self.max_value
        self.slider_end.value = value
        self.slider_end.setPos(self.ValueToPixel(self.slider_end.value), 0)

    def PixelToValue(self, pixel):
        return int(pixel/self.length*(self.max_value-self.min_value)+self.min_value)

    def ValueToPixel(self, value):
        return (value-self.min_value)/(self.max_value-self.min_value)*self.length

    def markerPosChanged(self, x, marker):
        if marker == self.slider_position:
            self.slider_position.value = self.PixelToValue(x)
            self.sliderMoved()
        if marker == self.slider_start:
            self.slider_start.value = self.PixelToValue(x)
            if self.slider_start.value > self.slider_end.value:
                self.slider_end.value = self.slider_start.value
                self.slider_end.setPos(self.ValueToPixel(self.slider_end.value), 0)
            self.slider_line_active.setRect(self.ValueToPixel(self.slider_start.value), 0, self.ValueToPixel(self.slider_end.value)-self.ValueToPixel(self.slider_start.value), 5)
        if marker == self.slider_end:
            self.slider_end.value = self.PixelToValue(x)
            if self.slider_start.value > self.slider_end.value:
                self.slider_start.value = self.slider_end.value
                self.slider_start.setPos(self.ValueToPixel(self.slider_start.value), 0)
            self.slider_line_active.setRect(self.ValueToPixel(self.slider_start.value), 0, self.ValueToPixel(self.slider_end.value)-self.ValueToPixel(self.slider_start.value), 5)

    def value(self):
        return self.slider_position.value

    def startValue(self):
        return self.slider_start.value

    def endValue(self):
        return self.slider_end.value

    @staticmethod
    def sliderPressed():
        pass

    @staticmethod
    def sliderMoved():
        pass

    @staticmethod
    def sliderReleased():
        pass

    def keyPressEvent(self, event):
        event.setAccepted(False)
        return

class BoxGrabber(QGraphicsRectItem):
    def __init__(self, parent):
        QGraphicsRectItem.__init__(self, parent)

        self.parent = parent
        self.setCursor(QCursor(QtCore.Qt.OpenHandCursor))
        width = parent.rect().width()
        self.setRect(QRectF(0, 0, width, 10))
        self.setPos(parent.rect().x(), 0)

        self.setBrush(QBrush(QColor(0, 0, 0, 128)))

        path = QPainterPath()
        path.moveTo(5, 3)
        path.lineTo(width - 5, 3)
        path.moveTo(5, 6)
        path.lineTo(width - 5, 6)
        pathItem = QGraphicsPathItem(path, self)
        pathItem.setPen(QPen(QColor(255, 255, 255)))
        pathItem.setBrush(QBrush(QColor(255, 255, 255)))

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


class GraphicsItemEventFilter(QGraphicsItem):
    def __init__(self, parent, command_object):
        super(GraphicsItemEventFilter, self).__init__(parent)
        self.commandObject = command_object
        self.active = False

    def paint(self, *args):
        pass

    def boundingRect(self):
        return QRectF(0, 0, 0, 0)

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

