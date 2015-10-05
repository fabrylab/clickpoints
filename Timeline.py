from __future__ import division, print_function
import sys
import os
import glob

try:
    from PyQt5 import QtGui, QtCore
    from PyQt5.QtWidgets import QIcon, QGraphicsRectItem, QPen, QBrush, QColor, QLinearGradient, QGraphicsPathItem, QPainterPath, QGraphicsScene, QGraphicsView, QPalette, QCursor
    from PyQt5.QtCore import Qt, QPointF
except ImportError:
    from PyQt4 import QtGui, QtCore
    from PyQt4.QtGui import QIcon, QGraphicsRectItem, QPen, QBrush, QColor, QLinearGradient, QGraphicsPathItem, QPainterPath, QGraphicsScene, QGraphicsView, QPalette, QCursor
    from PyQt4.QtCore import Qt, QPointF

icon_path = os.path.join(os.path.dirname(__file__), ".", "icons")


class TimeLineGrabber(QGraphicsPathItem):
    def __init__(self, parent):
        QGraphicsPathItem.__init__(self, None, parent.scene)
        self.parent = parent
        self.range = [0,100]
        self.setCursor(QCursor(QtCore.Qt.OpenHandCursor))
        self.dragged = False

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
        self.slider_start = TimeLineGrabber(self)
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
        self.slider_end = TimeLineGrabber(self)
        self.slider_end.setPath(path)
        gradient = QLinearGradient(QPointF(0, -12), QPointF(0, -2.5))
        gradient.setColorAt(0, QColor(255,0,0))
        gradient.setColorAt(1, QColor(128,0,0))
        self.slider_end.setBrush(QBrush(gradient))
        self.slider_end.setZValue(10)
        self.slider_end.value = 100

        path = QPainterPath()
        path.addRect(-2, -7, 5, 14)
        self.slider_position = TimeLineGrabber(self)
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


class Timeline:
    def __init__(self, window, media_handler, layout, outputpath, config, modules):
        self.window = window
        self.media_handler = media_handler
        self.config = config

        self.layout = layout
        self.modules = modules

        self.fps = self.media_handler.fps
        if self.fps == 0:
            self.fps = 25
        if self.config.fps != 0:
            self.fps = self.config.fps
        self.skip = 0

        # control elements
        self.layoutCtrl = QtGui.QHBoxLayout()
        self.layout.addLayout(self.layoutCtrl)
        # frame control
        self.pbPlay = QtGui.QPushButton()
        self.pbPlay.setCheckable(True)
        self.pbPlay.toggled.connect(self.hpbPlay)
        sys.path.append(os.path.join(os.path.dirname(__file__), ".", "icons"))
        self.layoutCtrl.addWidget(self.pbPlay)

        self.lbCFrame = QtGui.QLabel()
        self.lbCFrame.setText('%d' % self.media_handler.currentPos)
        self.lbCFrame.setMinimumWidth(40)
        self.lbCFrame.setAlignment(Qt.AlignVCenter)
        self.layoutCtrl.addWidget(self.lbCFrame)

        self.frameSlider = TimeLineSlider()
        self.frameSlider.sliderReleased = self.hfReleaseSlider
        self.frameSlider.setMinimum(0)
        self.frameSlider.setMaximum(self.media_handler.totalNr - 1)
        self.frameSlider.setValue(self.media_handler.currentPos)
        if self.config.play_start is not None:
            # if >1 its a frame nr if < 1 its a fraction
            if self.config.play_start >= 1:
                self.frameSlider.setStartValue(self.config.play_start)
                print(self.config.play_start)
            else:
                self.frameSlider.setStartValue(int(self.media_handler.totalNr*self.config.play_start))
                print(int(self.media_handler.totalNr*self.config.play_start))
        if self.config.play_end is not None:
            if self.config.play_end > 1:
                self.frameSlider.setEndValue(self.config.play_end)
                print(self.config.play_end)
            else:
                self.frameSlider.setEndValue(int(self.media_handler.totalNr*self.config.play_end))
                print(int(self.media_handler.totalNr*self.config.play_end))
        self.fsl_update = True
        self.layoutCtrl.addWidget(self.frameSlider)

        self.lbTFrame = QtGui.QLabel()
        self.lbTFrame.setText("%d" % (self.media_handler.totalNr - 1))
        self.lbTFrame.setMinimumWidth(40)
        self.lbTFrame.setAlignment(Qt.AlignVCenter)
        self.layoutCtrl.addWidget(self.lbTFrame)

        self.sbFPS = QtGui.QSpinBox()
        self.sbFPS.setMinimum(1)
        self.sbFPS.setMaximum(1000)
        self.sbFPS.setValue(self.fps)
        self.sbFPS.valueChanged.connect(self.hsbFPS)
        self.layoutCtrl.addWidget(self.sbFPS)

        self.sbSkip = QtGui.QSpinBox()
        self.sbSkip.setMinimum(0)
        self.sbSkip.setMaximum(1000)
        self.sbSkip.setValue(self.skip)
        self.sbSkip.valueChanged.connect(self.hsbSkip)
        self.layoutCtrl.addWidget(self.sbSkip)

        # widget list for control
        self.control_widgets = [self.pbPlay,
                                self.frameSlider,
                                self.lbCFrame,
                                self.lbTFrame,
                                self.sbFPS,
                                self.sbSkip
                                ]

        # video replay
        self.tUpdate = QtCore.QTimer()
        self.tUpdate.timeout.connect(self.htUpdate)

        self.hpbPlay(self.config.playing)

        self.hidden = True

        self.real_fps_time = QtCore.QTime()
        self.real_fps_time.start()

        self.HideInterface(self.config.timeline_hide)

        self.FolderChangeEvent()

    def FolderChangeEvent(self):
        self.frameSlider.setMaximum(self.media_handler.totalNr - 1)
        self.lbTFrame.setText("%d" % (self.media_handler.totalNr - 1))

        self.frameSlider.clearTickMarker()

        self.frame_list = self.media_handler.getImgList(extension=False, path=False)

        # add marker in time line for marker and masks
        marker_file_list = glob.glob(os.path.join(self.config.outputpath, '*' + self.config.logname_tag))
        for file in marker_file_list:
            filename = os.path.split(file)[1]
            basename = filename[:-len(self.config.logname_tag)]
            try:
                index = self.frame_list.index(basename)
            except ValueError:
                pass
            else:
                self.frameSlider.addTickMarker(index, type=1)

        marker_file_list = glob.glob(os.path.join(self.config.outputpath, '*' + self.config.maskname_tag))
        for file in marker_file_list:
            filename = os.path.split(file)[1]
            basename = filename[:-len(self.config.maskname_tag)]
            try:
                index = self.frame_list.index(basename)
            except ValueError:
                pass
            else:
                self.frameSlider.addTickMarker(index, type=1)

        marker_file_list = glob.glob(os.path.join(self.config.outputpath, '*' + self.config.annotation_tag))
        for file in marker_file_list:
            filename = os.path.split(file)[1]
            basename = filename[:-len(self.config.annotation_tag)]
            try:
                index = self.frame_list.index(basename)
            except ValueError:
                pass
            else:
                self.frameSlider.addTickMarker(index, type=0)

    def hsbSkip(self):
        self.skip = self.sbSkip.value()

    def hsbFPS(self):
        self.fps = self.sbFPS.value()
        self.tUpdate.stop()
        self.tUpdate.start(1000 / self.fps)

    def hfReleaseSlider(self):
        n = self.frameSlider.value()
        self.fsl_update = True
        self.lbCFrame.setText("%d" % n)
        self.updateFrame(nr=n)

    def hfPressSlider(self):
        self.fsl_update = False

    def htUpdate(self):
        self.updateFrame()

    def hpbPlay(self, state):
        if state:
            self.tUpdate.start(1000 / self.fps)
            self.pbPlay.setIcon(QIcon(os.path.join(icon_path, "media-playback-pause.png")))
        else:
            self.tUpdate.stop()
            self.pbPlay.setIcon(QIcon(os.path.join(icon_path, "media-playback-start.png")))

    def updateFrame(self, nr=-1):
        if nr != -1:
            self.window.JumpToFrame(nr)
        else:
            if self.media_handler.currentPos < self.frameSlider.startValue() or self.media_handler.currentPos >= self.frameSlider.endValue():
                self.window.JumpToFrame(self.frameSlider.startValue())
            else:
                self.window.JumpFrames(1+self.skip)

    def FrameChangeEvent(self):
        if self.media_handler.valid:
            if self.fsl_update:
                self.frameSlider.setValue(self.media_handler.currentPos)
                self.lbCFrame.setText('%d' % self.media_handler.currentPos)

            delta_t = self.real_fps_time.elapsed() - 1000/self.fps
            print("%d ms, jitter %d" % (self.real_fps_time.elapsed(), delta_t))
            self.real_fps_time.restart()
        else:
            # stop timer
            self.pbPlay.setChecked(False)

    def MaskAdded(self):
        self.frameSlider.addTickMarker(self.media_handler.currentPos, type=1)

    def MarkerPointsAdded(self):
        self.frameSlider.addTickMarker(self.media_handler.currentPos, type=1)

    def MarkerPointsRemoved(self):
        self.frameSlider.removeTickMarker(self.media_handler.currentPos, type=1)

    def AnnotationAdded(self, *args):
        self.frameSlider.addTickMarker(self.media_handler.currentPos, type=0)

    def AnnotationRemoved(self, *args):
        self.frameSlider.removeTickMarker(self.media_handler.currentPos, type=0)

    def HideInterface(self, hide):
        self.hidden = hide
        if hide:
            for widget in self.control_widgets:
                widget.setHidden(True)
            self.layoutCtrl.setContentsMargins(0, 0, 0, 0)
        else:
            for widget in self.control_widgets:
                widget.setHidden(False)
            self.layoutCtrl.setContentsMargins(5, 5, 5, 5)

    def keyPressEvent(self, event):
        # @key H: hide control elements
        if event.key() == QtCore.Qt.Key_H:
            self.HideInterface(self.hidden == False)
        # @key Space: run/pause
        if event.key() == QtCore.Qt.Key_Space:
            self.pbPlay.toggle()

        # @key ---- Frame jumps ----
        if event.key() == QtCore.Qt.Key_Left and event.modifiers() & Qt.ControlModifier:
            # @key Left: previous image
            tick = self.frameSlider.getNextTick(self.media_handler.currentPos, back=True)
            self.window.JumpToFrame(tick)
        if event.key() == QtCore.Qt.Key_Right and event.modifiers() & Qt.ControlModifier:
            # @key Right: next image
            tick = self.frameSlider.getNextTick(self.media_handler.currentPos)
            self.window.JumpToFrame(tick)

    @staticmethod
    def file():
        return __file__
