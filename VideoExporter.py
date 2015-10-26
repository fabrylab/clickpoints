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
import numpy as np

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

        """ Video """
        self.video_layouts = []
        Hlayout = QtGui.QHBoxLayout(self)
        Hlayout.addWidget(QtGui.QLabel('Filename:'))
        self.leAName = QtGui.QLineEdit(os.path.join(self.config.outputpath, "export.avi"), self)
        self.leAName.setEnabled(False)
        Hlayout.addWidget(self.leAName)
        button = QtGui.QPushButton("Choose File")
        button.pressed.connect(self.OpenDialog)
        Hlayout.addWidget(button)
        self.layout.addLayout(Hlayout)
        self.video_layouts.append(Hlayout)

        Hlayout = QtGui.QHBoxLayout(self)
        Hlayout.addWidget(QtGui.QLabel('Codec (fourcc code):'))
        self.leCodec = QtGui.QLineEdit("XVID", self)
        self.leCodec.setMaxLength(4)
        Hlayout.addWidget(self.leCodec)
        self.layout.addLayout(Hlayout)
        self.video_layouts.append(Hlayout)

        """ Image """
        self.images_layouts = []
        Hlayout = QtGui.QHBoxLayout(self)
        Hlayout.addWidget(QtGui.QLabel('Filename:'))
        self.leAName = QtGui.QLineEdit(os.path.join(self.config.outputpath, "images%d.avi"), self)
        self.leAName.setEnabled(False)
        Hlayout.addWidget(self.leAName)
        button = QtGui.QPushButton("Choose File")
        button.pressed.connect(self.OpenDialog)
        Hlayout.addWidget(button)
        self.layout.addLayout(Hlayout)
        self.images_layouts.append(Hlayout)

        #Hlayout = QtGui.QHBoxLayout(self)
        #Hlayout.addWidget(QtGui.QLabel('Codec (fourcc code):'))
        #self.leCodec = QtGui.QLineEdit("XVID", self)
        #self.leCodec.setMaxLength(4)
        #Hlayout.addWidget(self.leCodec)
        #self.layout.addLayout(Hlayout)
        #self.images_layouts.append(Hlayout)


        Hlayout = QtGui.QHBoxLayout(self)
        self.progressbar = QtGui.QProgressBar()
        Hlayout.addWidget(self.progressbar)
        button = QtGui.QPushButton("Start")
        button.pressed.connect(self.SaveImage)
        Hlayout.addWidget(button)
        self.layout.addLayout(Hlayout)

    def OpenDialog(self):
        srcpath = str(QtGui.QFileDialog.getSaveFileName(None, "Choose Image", os.getcwd(), "Videos (*.avi)"))
        self.leAName.setText(srcpath)

    def SaveImage(self):
        timeline = self.window.GetModule("Timeline")
        marker_handler = self.window.GetModule("MarkerHandler")
        start = timeline.frameSlider.startValue()
        end = timeline.frameSlider.endValue()
        video_writer = None
        path = str(self.leAName.text())
        use_video = True
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
            self.preview_slice = self.image[start_y:end_y, start_x:end_x, :]

            if self.preview_slice.shape[2] == 1:
                self.preview_slice = np.dstack((self.preview_slice,self.preview_slice,self.preview_slice))
            if marker_handler:
                print("MarkerHandler")
                marker_handler.drawToImage(self.image, start_x, start_y)
            if use_video:
                if video_writer == None:
                    fourcc = VideoWriter_fourcc(*str(self.leCodec.text()))
                    video_writer = cv2.VideoWriter(path, fourcc, timeline.fps, (self.preview_slice.shape[1], self.preview_slice.shape[0]))
                video_writer.write(cv2.cvtColor(self.preview_slice, COLOR_RGB2BGR))
            else:
                imsave(path % (frame-start), self.preview_slice)
        video_writer.release()

class VideoExporter:
    def __init__(self, window, media_handler, modules, config=None):
        # default settings and parameters
        self.window = window
        self.media_handler = media_handler
        self.config = config
        self.modules = modules

    def keyPressEvent(self, event):

        # @key Z: Export Video
        if event.key() == QtCore.Qt.Key_Z:
            self.ExporterWindow = VideoExporterDialog(self, self.window, self.media_handler, self.config, self.modules)
            self.ExporterWindow.show()
            #self.SaveImage()

    @staticmethod
    def file():
        return __file__
