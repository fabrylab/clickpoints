from __future__ import division, print_function
import sys
import os
import glob
import time
import numpy as np
import thread

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

def Remap(value, minmax1, minmax2):
    length1 = minmax1[1]-minmax1[0]
    length2 = minmax2[1]-minmax2[0]
    if length1 == 0:
        return 0
    percentage = (value-minmax1[0])/length1
    value2 = percentage*length2 + minmax2[0]
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


class PreciseTimer(QObject):
    timeout = pyqtSignal()

    def __init__(self, ):
        QObject.__init__(self)
        self.thread = None
        self.delta = 1
        self.timer_start = time.time()
        self.count = 1
        self.run = False

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

    def thread_timer(self):
        while self.run:
            if (time.time()-self.timer_start)*1e3 > self.delta*self.count:
                self.count += 1
                self.timeout.emit()

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
        self.layoutCtrl = QtGui.QHBoxLayout()
        layout.addLayout(self.layoutCtrl)
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
            digits = "%d" % np.ceil(np.log10(self.media_handler.get_frame_count()))
            format_string = ('%0'+digits+'d/%d  %.1ffps')
            fps = self.current_fps if self.current_fps is not None else 0
            self.label_frame.setText(format_string % (self.media_handler.get_index(), self.media_handler.get_frame_count() - 1, fps))

    def FrameChangeEvent(self):
        dt = time.time()-self.last_time
        self.last_time = time.time()
        if self.current_fps is None:
            self.current_fps = 1/dt
        else:
            a = np.exp(-dt)
            self.current_fps = a*self.current_fps + (1-a) * 1/dt

        self.updateLabel()

    def MaskAdded(self):
        self.frameSlider.addTickMarker(self.media_handler.get_index(), type=1)

    def MarkerPointsAdded(self):
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
