from __future__ import division

try:
    from PyQt5 import QtGui, QtCore
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except ImportError:
    from PyQt4 import QtGui, QtCore
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

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
    def __init__(self, parent=None, name="", start_value=None, max_value=100, min_value=0):
        QGraphicsView.__init__(self)

        self.setMaximumHeight(20)

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.scene.setBackgroundBrush(QColor(240, 240, 240))
        self.setStyleSheet("border: 0px")

        self.max_value = max_value
        self.min_value = min_value

        self.slider_line = QGraphicsLineItem(None, self.scene)
        self.slider_line.setPen(QPen(QColor("black")))

        path = QPainterPath()
        path.addEllipse(-5, -5, 10, 10)
        self.slideMarker = MyMultiSliderGrabber(self)
        self.slideMarker.setPath(path)
        self.slideMarker.setBrush(QBrush(QColor(255, 0, 0, 255)))

        path = QPainterPath()
        path.moveTo(-5, -10)
        path.lineTo(0, 0)
        path.lineTo(+5, -10)
        path.lineTo(-5, -10)
        self.slideMarker2 = MyMultiSliderGrabber(self)
        self.slideMarker2.setPath(path)
        self.slideMarker2.setBrush(QBrush(QColor(255, 0, 0, 255)))

        path = QPainterPath()
        path.moveTo(-5, -10)
        path.lineTo(0, 0)
        path.lineTo(+5, -10)
        path.lineTo(-5, -10)
        self.slideMarker3 = MyMultiSliderGrabber(self)
        self.slideMarker3.setPath(path)
        self.slideMarker3.setBrush(QBrush(QColor(255, 0, 0, 255)))

        self.length = 0
        self.slider_value = 0

        self.tick_marker = []

    def addTickMarker(self, pos):
        tick_marker = QGraphicsLineItem(0, 0, 0, -10, None, self.scene)
        tick_marker.setPen(QPen(QColor("red")))
        tick_marker.value = pos
        tick_marker.setPos(self.ValueToPixel(pos), 0)
        self.tick_marker.append(tick_marker)

    def resizeEvent(self, event):
        self.length = self.size().width()-20
        self.slider_line.setLine(0, 0, self.length, 0)
        self.slideMarker3.setRange(0, self.length)
        self.slideMarker2.setRange(0, self.length)
        self.slideMarker.setRange(0, self.length)
        self.ensureVisible(self.slider_line)
        for tick in self.tick_marker:
            tick.setPos(self.ValueToPixel(tick.value), 0)

    def setMinimum(self, value):
        self.min_value = value

    def setMaximum(self, value):
        self.max_value = value

    def setValue(self, value):
        self.slider_value = value
        self.slideMarker.setPos(self.ValueToPixel(self.slider_value), 0)

    def PixelToValue(self, pixel):
        return int(pixel/self.length*(self.max_value-self.min_value)+self.min_value)

    def ValueToPixel(self, value):
        return (value-self.min_value)/(self.max_value-self.min_value)*self.length

    def markerPosChanged(self, x, marker):
        if marker == self.slideMarker:
            self.slider_value = self.PixelToValue(x)
            self.sliderMoved()

    def value(self):
        return self.slider_value

    @staticmethod
    def sliderPressed():
        pass

    @staticmethod
    def sliderMoved():
        pass

    @staticmethod
    def sliderReleased():
        pass
        """
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
        self.slideMarker = MyMultiSliderGrabber(self)
        self.slideMarker.setPath(path)
        self.slideMarker.setBrush(QBrush(QColor(255, 0, 0, 255)))

        self.setRect(QRectF(-5, -5, 110, 10))
        self.dragged = False

        self.value = (self.maxValue + self.minValue) * 0.5
        if start_value != None:
            self.value = start_value
        self.start_value = self.value
        #self.setValue(self.value)
        """
    """
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
    """
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

