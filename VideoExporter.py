from __future__ import division, print_function
import os

try:
    from PyQt5 import QtCore
except ImportError:
    from PyQt4 import QtCore, QtGui
    from PyQt4.QtGui import QWidget

from scipy.misc import imsave
try:
    import cv2
    cv2_loaded = True
    try:
        from cv2.cv import CV_CAP_PROP_POS_FRAMES as CAP_PROP_POS_FRAMES
        from cv2.cv import CV_CAP_PROP_FRAME_COUNT as CAP_PROP_FRAME_COUNT
        from cv2.cv import CV_CAP_PROP_FRAME_WIDTH as CAP_PROP_FRAME_WIDTH
        from cv2.cv import CV_CAP_PROP_FRAME_HEIGHT as CAP_PROP_FRAME_HEIGHT
        from cv2.cv import CV_CAP_PROP_FPS as CAP_PROP_FPS

        from cv2.cv import CV_FOURCC as VideoWriter_fourcc
        from cv2.cv import CV_RGB2BGR as COLOR_RGB2BGR
    except ImportError:
        from cv2 import CAP_PROP_POS_FRAMES as CAP_PROP_POS_FRAMES
        from cv2 import CAP_PROP_FRAME_COUNT as CAP_PROP_FRAME_COUNT
        from cv2 import CAP_PROP_FRAME_WIDTH as CAP_PROP_FRAME_WIDTH
        from cv2 import CAP_PROP_FRAME_HEIGHT as CAP_PROP_FRAME_HEIGHT
        from cv2 import CAP_PROP_FPS as CAP_PROP_FPS

        from cv2 import VideoWriter_fourcc
        from cv2 import COLOR_RGB2BGR as COLOR_RGB2BGR
except ImportError:
    cv2_loaded = False
try:
    import imageio
    imageio_loaded = True
except ImportError:
    imageio_loaded = False

import numpy as np
import re

class VideoExporterDialog(QWidget):
    def __init__(self, parent, window, media_handler, config, modules):
        QWidget.__init__(self)
        # default settings and parameters
        self.window = window
        self.media_handler = media_handler
        self.config = config
        self.modules = modules

        # widget layout and elements
        self.setMinimumWidth(700)
        self.setMinimumHeight(300)
        self.setWindowTitle('Video Export')
        self.layout = QtGui.QVBoxLayout(self)
        self.parent = parent

        Hlayout = QtGui.QHBoxLayout(self)
        self.cbType = QtGui.QComboBox(self)
        self.cbType.insertItem(0, "Video")
        self.cbType.insertItem(1, "Images")
        self.cbType.insertItem(2, "Gif")
        Hlayout.addWidget(self.cbType)
        self.layout.addLayout(Hlayout)

        self.StackedWidget = QtGui.QStackedWidget(self)
        self.layout.addWidget(self.StackedWidget)

        self.cbType.currentIndexChanged.connect(self.StackedWidget.setCurrentIndex)

        """ Video """
        videoWidget = QtGui.QGroupBox("Video Settings")
        self.StackedWidget.addWidget(videoWidget)
        Vlayout = QtGui.QVBoxLayout(videoWidget)
        Hlayout = QtGui.QHBoxLayout()
        Vlayout.addLayout(Hlayout)
        Hlayout.addWidget(QtGui.QLabel('Filename:'))
        self.leAName = QtGui.QLineEdit(os.path.join(self.config.outputpath, "export.avi"), self)
        self.leAName.setEnabled(False)
        Hlayout.addWidget(self.leAName)
        button = QtGui.QPushButton("Choose File")
        button.pressed.connect(self.OpenDialog)
        Hlayout.addWidget(button)

        Hlayout = QtGui.QHBoxLayout()
        Vlayout.addLayout(Hlayout)
        Hlayout.addWidget(QtGui.QLabel('Codec (fourcc code):'))
        self.leCodec = QtGui.QLineEdit("XVID", self)
        self.leCodec.setMaxLength(4)
        Hlayout.addWidget(self.leCodec)
        Vlayout.addStretch()

        """ Image """
        imageWidget = QtGui.QGroupBox("Image Settings")
        self.StackedWidget.addWidget(imageWidget)
        Vlayout = QtGui.QVBoxLayout(imageWidget)
        Hlayout = QtGui.QHBoxLayout()
        Vlayout.addLayout(Hlayout)
        Hlayout.addWidget(QtGui.QLabel('Filename:'))
        self.leANameI = QtGui.QLineEdit(os.path.join(self.config.outputpath, "images%d.jpg"), self)
        self.leANameI.setEnabled(False)
        Hlayout.addWidget(self.leANameI)
        button = QtGui.QPushButton("Choose File")
        button.pressed.connect(self.OpenDialog2)
        Hlayout.addWidget(button)
        Vlayout.addWidget(QtGui.QLabel('Image names have to contain %d as a placeholder for the image number.'))
        Vlayout.addStretch()

        """ Gif """
        gifWidget = QtGui.QGroupBox("Animated Gif Settings")
        self.StackedWidget.addWidget(gifWidget)
        Vlayout = QtGui.QVBoxLayout(gifWidget)
        Hlayout = QtGui.QHBoxLayout()
        Vlayout.addLayout(Hlayout)
        Hlayout.addWidget(QtGui.QLabel('Filename:'))
        self.leANameG = QtGui.QLineEdit(os.path.join(self.config.outputpath, "export.gif"), self)
        self.leANameG.setEnabled(False)
        Hlayout.addWidget(self.leANameG)
        button = QtGui.QPushButton("Choose File")
        button.pressed.connect(self.OpenDialog3)
        Hlayout.addWidget(button)
        Vlayout.addStretch()

        Hlayout = QtGui.QHBoxLayout(self)
        self.progressbar = QtGui.QProgressBar()
        Hlayout.addWidget(self.progressbar)
        button = QtGui.QPushButton("Start")
        button.pressed.connect(self.SaveImage)
        Hlayout.addWidget(button)
        self.layout.addLayout(Hlayout)

    def ComboBoxChanged(self, index):
        if index == 0:
            for layout in self.video_layouts:
                layout.setHidden(False)
            for layout in self.images_layouts:
                layout.setHidden(True)
        if index == 1:
            for layout in self.video_layouts:
                layout.setHidden(True)
            for layout in self.images_layouts:
                layout.setHidden(False)

    def OpenDialog(self):
        srcpath = str(QtGui.QFileDialog.getSaveFileName(None, "Choose Video", os.getcwd(), "Videos (*.avi)"))
        self.leAName.setText(srcpath)

    def OpenDialog2(self):
        srcpath = str(QtGui.QFileDialog.getSaveFileName(None, "Choose Image", os.getcwd(), "Images (*.jpg *.png *.tif)"))
        srcpath = re.sub(r"\d+", "%d", srcpath, count=1)
        self.leANameI.setText(srcpath)

    def OpenDialog3(self):
        srcpath = str(QtGui.QFileDialog.getSaveFileName(None, "Choose Gif", os.getcwd(), "Animated Gifs (*.gif)"))
        self.leANameG.setText(srcpath)

    def SaveImage(self):
        timeline = self.window.GetModule("Timeline")
        marker_handler = self.window.GetModule("MarkerHandler")
        start = timeline.frameSlider.startValue()
        end = timeline.frameSlider.endValue()
        writer = None
        if self.cbType.currentIndex() == 0:
            path = str(self.leAName.text())
            writer_params = dict(format="avi", mode="I", fps=timeline.fps)
        elif self.cbType.currentIndex() == 1:
            path = str(self.leANameI.text())
        elif self.cbType.currentIndex() == 2:
            path = str(self.leANameG.text())
            writer_params = dict(format="gif", mode="I", fps=timeline.fps)
        self.progressbar.setMinimum(start)
        self.progressbar.setMaximum(end)
        for frame in range(start, end+1):
            self.progressbar.setValue(frame)
            self.window.JumpToFrame(frame)
            self.preview_rect = self.window.view.GetExtend(True)
            self.image = self.window.ImageDisplay.image
            start_x, start_y, end_x, end_y = self.preview_rect
            if start_x < 0: start_x = 0
            if start_y < 0: start_y = 0
            if end_x > self.image.shape[1]: end_x = self.image.shape[1]
            if end_y > self.image.shape[0]: end_y = self.image.shape[0]
            if end_x < start_x: end_x = start_x+1
            if end_y < start_y: end_y = start_y+1
            if end_x > start_x + self.config.max_image_size: end_x = start_x + self.config.max_image_size
            if end_y > start_y + self.config.max_image_size: end_y = start_y + self.config.max_image_size
            if (end_y-start_y) % 2 != 0: end_y -= 1
            if (end_x-start_x) % 2 != 0: end_x -= 1
            self.preview_slice = self.image[start_y:end_y, start_x:end_x, :]

            if self.preview_slice.shape[2] == 1:
                self.preview_slice = np.dstack((self.preview_slice,self.preview_slice,self.preview_slice))
            #if marker_handler:
            #    print("MarkerHandler")
            #    marker_handler.drawToImage(self.image, start_x, start_y)
            if self.cbType.currentIndex() == 0:
                if writer == None:
                    writer = imageio.get_writer(path, **writer_params)
                writer.append_data(self.preview_slice)
                """
                if writer == None:
                    fourcc = VideoWriter_fourcc(*str(self.leCodec.text()))
                    writer = cv2.VideoWriter(path, fourcc, timeline.fps, (self.preview_slice.shape[1], self.preview_slice.shape[0]))
                writer.write(cv2.cvtColor(self.preview_slice, COLOR_RGB2BGR))
                """
            elif self.cbType.currentIndex() == 1:
                imsave(path % (frame-start), self.preview_slice)
            elif self.cbType.currentIndex() == 0 or self.cbType.currentIndex() == 2:
                if writer == None:
                    writer = imageio.get_writer(path, **writer_params)
                writer.append_data(self.preview_slice)
        if self.cbType.currentIndex() == 2 or self.cbType.currentIndex() == 0:
            writer.close()
        #if self.cbType.currentIndex() == 0:
        #    writer.release()

class VideoExporter:
    def __init__(self, window, media_handler, modules, config=None):
        # default settings and parameters
        self.window = window
        self.media_handler = media_handler
        self.config = config
        self.modules = modules
        self.ExporterWindow = None

    def keyPressEvent(self, event):

        # @key Z: Export Video
        if event.key() == QtCore.Qt.Key_Z:
            self.ExporterWindow = VideoExporterDialog(self, self.window, self.media_handler, self.config, self.modules)
            self.ExporterWindow.show()

    def closeEvent(self, event):
        if self.ExporterWindow:
            self.ExporterWindow.close()

    @staticmethod
    def file():
        return __file__
