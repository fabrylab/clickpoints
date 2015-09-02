import sys
import os
import glob

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "mediahandler"))
try:
    from PyQt4 import QtOpenGL
    from OpenGL import GL
    gotopengl=True
except:
    pass

from PyQt4 import QtGui, QtCore
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from qimage2ndarray import array2qimage, rgb_view

import mediahandler as mh

from Tools import MyMultiSlider

class Viewer():
    def __init__(self, window, parent=None, MediaHandler=None, layout=None, outputpath=None, config=None, modules=[]):
        self.window = window
        if MediaHandler is None:
            self.m = mh.MediaHandler(path,rettype='qpixmap')
        else:
            self.m = MediaHandler
        if self.m.dtype == 'video':
            self.fps = self.m.fps
            self.skip = 0
            self.lastskip=0
        else:
            self.fps = 1
            self.skip = 0
            self.lastskip=0

        self.outputpath=outputpath
        self.config = config

        self.layout = layout
        self.modules = modules

        ## control elemnts
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
        self.lbCFrame.setText('%d' % self.m.currentPos)
        self.lbCFrame.setMinimumWidth(40)
        self.lbCFrame.setAlignment(Qt.AlignVCenter)
        self.layoutCtrl.addWidget(self.lbCFrame, 0, 1)

        self.frameSlider = MyMultiSlider()
        self.frameSlider.sliderReleased = self.hfReleaseSlider
        self.frameSlider.setMinimum(0)
        self.frameSlider.setMaximum(self.m.totalNr - 1)
        self.frameSlider.setValue(self.m.currentPos)
        if self.config.play_start != None:
            # if >1 its a frame nr if < 1 its a fraction
            if self.config.play_start >= 1:
                self.frameSlider.setStartValue(self.config.play_start)
                print self.config.play_start
            else:
                self.frameSlider.setStartValue(int(self.m.totalNr*self.config.play_start))
                print int(self.m.totalNr*self.config.play_start)
        if self.config.play_end != None:
            if self.config.play_end > 1:
                self.frameSlider.setEndValue(self.config.play_end)
                print self.config.play_end
            else:
                self.frameSlider.setEndValue(int(self.m.totalNr*self.config.play_end))
                print int(self.m.totalNr*self.config.play_end)
        self.fsl_update = True
        self.layoutCtrl.addWidget(self.frameSlider, 0, 2)

        self.lbTFrame = QtGui.QLabel()
        self.lbTFrame.setText("%d" % (self.m.totalNr - 1))
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
        self.ctrlwidgets = [self.pbPlay,
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

        # init with first frame
        if self.m.rettype=='img':
            self.frame = self.m.getImgNr(self.m.currentPos)
            self.qframe = array2qimage(self.frame)
            self.frameshape = self.frame.shape
            self.qframeView = rgb_view(self.qframe)
            self.inpixmap = QtGui.QPixmap.fromImage(self.qframe)
            self.pixitem = QtGui.QGraphicsPixmapItem(self.inpixmap)
        elif self.m.rettype == 'qpixmap':
            self.pixitem = QtGui.QGraphicsPixmapItem(self.m.getImgNr(self.m.currentPos))

        self.hide = True

        self.realFPStime = QtCore.QTime()
        self.realFPStime.start()
        self.nextframedone = False

        self.frame_list = [os.path.split(file)[1][:-4] for file in self.m.filelist]

        # add marker in timeline for marker and masks
        marker_filelist = glob.glob(os.path.join(self.outputpath, '*' + config.logname_tag))
        marker_filelist.extend(glob.glob(os.path.join(self.outputpath, '*' + config.maskname_tag)))
        for file in marker_filelist:
            filename = os.path.split(file)[1]
            basename = filename[:-len(config.logname_tag)]
            try:
                index = self.frame_list.index(basename)
            except ValueError:
                pass
            else:
                self.frameSlider.addTickMarker(index, type=1)

        marker_filelist = glob.glob(os.path.join(self.outputpath, '*' + config.annotation_tag))
        for file in marker_filelist:
            filename = os.path.split(file)[1]
            basename = filename[:-len(config.annotation_tag)]
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
            self.pbPlay.setIcon(QIcon("./icons/media-playback-pause.png"))
        else:
            self.tUpdate.stop()
            self.pbPlay.setIcon(QIcon("./icons/media-playback-start.png"))

    def updateFrame(self, nr=-1):
        if nr != -1:
            self.window.JumpToFrame(nr)
        else:
            if self.m.currentPos < self.frameSlider.startValue() or self.m.currentPos >= self.frameSlider.endValue():
                self.window.JumpToFrame(self.frameSlider.startValue())
            else:
                self.window.JumpFrames(1+self.skip)

    def FrameChangeEvent(self):
        if self.m.valid:
            if self.fsl_update:
                self.frameSlider.setValue(self.m.currentPos)
                self.lbCFrame.setText('%d' % self.m.currentPos)

            delta_t =  self.realFPStime.elapsed() - 1000/self.fps
            print "%d ms, jitter %d" % (self.realFPStime.elapsed(),delta_t)
            self.realFPStime.restart()
        else:
            # stop timer
            self.pbPlay.setChecked(False)

    def MarkerPointsAdded(self):
        self.frameSlider.addTickMarker(self.m.currentPos, type=1)

    def MarkerPointsRemoved(self):
        self.frameSlider.removeTickMarker(self.m.currentPos, type=1)

    def AnnotationAdded(self):
        self.frameSlider.addTickMarker(self.m.currentPos, type=0)

    def AnnotationRemoved(self):
        self.frameSlider.removeTickMarker(self.m.currentPos, type=0)

    def keyPressEvent(self, event):
        # @key H: hide control elements
        if event.key() == QtCore.Qt.Key_H:
            if self.hide:
                for widget in self.ctrlwidgets:
                    widget.setHidden(True)
                self.layoutCtrl.setContentsMargins(0, 0, 0, 0)
            else:
                for widget in self.ctrlwidgets:
                    widget.setHidden(False)
                self.layoutCtrl.setContentsMargins(5, 5, 5, 5)
            self.hide = not self.hide
        # @key Space: run/pause
        if event.key() == QtCore.Qt.Key_Space:
            self.pbPlay.toggle()
        """
        # @key A: add/edit annotation
        if event.key() == QtCore.Qt.Key_A:
            self.w = ah.AnnotationEditor(self.m.getCurrentFilename(nr=self.m.currentPos),outputpath=self.outputpath, modules=self.modules, config=self.config)
            self.w.show()
        # @key Y: show annotation overview
        if event.key() == QtCore.Qt.Key_Y:
            self.y = ao.AnnotationOverview(self.window,self.m,outputpath=self.outputpath,frameSlider=self.frameSlider, config=self.config)
            self.y.show()
        """
    @staticmethod
    def file():
        return __file__