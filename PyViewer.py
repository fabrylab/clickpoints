from __future__ import division, print_function
import sys
import os
import glob

try:
    from PyQt5 import QtGui, QtCore
    from PyQt5.QtWidgets import QIcon
    from PyQt5.QtCore import Qt
except ImportError:
    from PyQt4 import QtGui, QtCore
    from PyQt4.QtGui import QIcon
    from PyQt4.QtCore import Qt

from Tools import MyMultiSlider

icon_path = os.path.join(os.path.dirname(__file__), ".", "icons")


class Viewer:
    def __init__(self, window, media_handler, layout, outputpath, config, modules):
        self.window = window
        self.media_handler = media_handler
        self.config = config

        self.layout = layout
        self.modules = modules

        if self.media_handler.dtype == 'video':
            self.fps = self.media_handler.fps
        else:
            self.fps = 1
        if self.config.fps != 0:
            self.fps = self.config.fps
        self.skip = 0

        # control elements
        self.layoutCtrl = QtGui.QGridLayout()
        self.layoutCtrl.setContentsMargins(5, 5, 5, 5)
        self.layout.addLayout(self.layoutCtrl)
        # frame control
        self.pbPlay = QtGui.QPushButton()
        self.pbPlay.setCheckable(True)
        self.pbPlay.toggled.connect(self.hpbPlay)
        sys.path.append(os.path.join(os.path.dirname(__file__), ".", "icons"))
        self.layoutCtrl.addWidget(self.pbPlay, 0, 0)

        self.lbCFrame = QtGui.QLabel()
        self.lbCFrame.setText('%d' % self.media_handler.currentPos)
        self.lbCFrame.setMinimumWidth(40)
        self.lbCFrame.setAlignment(Qt.AlignVCenter)
        self.layoutCtrl.addWidget(self.lbCFrame, 0, 1)

        self.frameSlider = MyMultiSlider()
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
        self.layoutCtrl.addWidget(self.frameSlider, 0, 2)

        self.lbTFrame = QtGui.QLabel()
        self.lbTFrame.setText("%d" % (self.media_handler.totalNr - 1))
        self.lbTFrame.setMinimumWidth(40)
        self.lbTFrame.setAlignment(Qt.AlignVCenter)
        self.layoutCtrl.addWidget(self.lbTFrame, 0, 4)

        self.sbFPS = QtGui.QSpinBox()
        self.sbFPS.setMinimum(1)
        self.sbFPS.setMaximum(1000)
        self.sbFPS.setValue(self.fps)
        self.sbFPS.valueChanged.connect(self.hsbFPS)
        self.layoutCtrl.addWidget(self.sbFPS, 1, 0)

        self.sbSkip = QtGui.QSpinBox()
        self.sbSkip.setMinimum(0)
        self.sbSkip.setMaximum(1000)
        self.sbSkip.setValue(self.skip)
        self.sbSkip.valueChanged.connect(self.hsbSkip)
        self.layoutCtrl.addWidget(self.sbSkip, 1, 1)

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
            if self.media_handler.currentPos < self.frameSlider.startValue() or self.media_handler.currentPos >= self.frameSlider.endValue()-1:
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
