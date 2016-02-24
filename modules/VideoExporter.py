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
from PIL import ImageDraw, Image, ImageFont

def HTMLColorToRGB(colorstring):
    """ convert #RRGGBB to an (R, G, B) tuple """
    colorstring = str(colorstring).strip()
    if colorstring[0] == '#': colorstring = colorstring[1:]
    if len(colorstring) != 6 and len(colorstring) != 8:
        raise (ValueError, "input #%s is not in #RRGGBB format" % colorstring)
    return [int(colorstring[i*2:i*2+2], 16) for i in range(int(len(colorstring)/2))]

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
        self.leAName = QtGui.QLineEdit(os.path.join(self.config.outputpath, "export/export.avi"), self)
        self.leAName.setEnabled(False)
        Hlayout.addWidget(self.leAName)
        button = QtGui.QPushButton("Choose File")
        button.pressed.connect(self.OpenDialog)
        Hlayout.addWidget(button)

        Hlayout = QtGui.QHBoxLayout()
        Vlayout.addLayout(Hlayout)
        Hlayout.addWidget(QtGui.QLabel('Codec:'))
        self.leCodec = QtGui.QLineEdit("libx264", self)
        Hlayout.addWidget(self.leCodec)

        Hlayout = QtGui.QHBoxLayout()
        Vlayout.addLayout(Hlayout)
        Hlayout.addWidget(QtGui.QLabel('Quality (0 lowest, 10 highest):'))
        self.sbQuality = QtGui.QSpinBox(self)
        self.sbQuality.setValue(5)
        self.sbQuality.setRange(0, 10)
        Hlayout.addWidget(self.sbQuality)
        Hlayout.addStretch()

        Vlayout.addStretch()

        """ Image """
        imageWidget = QtGui.QGroupBox("Image Settings")
        self.StackedWidget.addWidget(imageWidget)
        Vlayout = QtGui.QVBoxLayout(imageWidget)
        Hlayout = QtGui.QHBoxLayout()
        Vlayout.addLayout(Hlayout)
        Hlayout.addWidget(QtGui.QLabel('Filename:'))
        self.leANameI = QtGui.QLineEdit(os.path.join(self.config.outputpath, "export/images%d.jpg"), self)
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
        self.leANameG = QtGui.QLineEdit(os.path.join(self.config.outputpath, "export/export.gif"), self)
        self.leANameG.setEnabled(False)
        Hlayout.addWidget(self.leANameG)
        button = QtGui.QPushButton("Choose File")
        button.pressed.connect(self.OpenDialog3)
        Hlayout.addWidget(button)
        Vlayout.addStretch()

        """ Time """
        timeWidget = QtGui.QGroupBox("Time")
        self.layout.addWidget(timeWidget)
        Vlayout = QtGui.QVBoxLayout(timeWidget)

        Hlayout = QtGui.QHBoxLayout()
        Vlayout.addLayout(Hlayout)
        Hlayout.addWidget(QtGui.QLabel('Display time:'))
        self.cbTime = QtGui.QCheckBox(self)
        self.cbTime.setChecked(True)
        Hlayout.addWidget(self.cbTime)
        Hlayout.addStretch()

        Hlayout = QtGui.QHBoxLayout()
        Vlayout.addLayout(Hlayout)
        Hlayout.addWidget(QtGui.QLabel('Start from zero:'))
        self.cbTimeZero = QtGui.QCheckBox(self)
        self.cbTimeZero.setChecked(True)
        Hlayout.addWidget(self.cbTimeZero)
        Hlayout.addStretch()

        Hlayout = QtGui.QHBoxLayout()
        Vlayout.addLayout(Hlayout)
        Hlayout.addWidget(QtGui.QLabel('Font size:'))
        self.cbTimeFontSize = QtGui.QSpinBox(self)
        self.cbTimeFontSize.setValue(50)
        Hlayout.addWidget(self.cbTimeFontSize)
        Hlayout.addStretch()

        Hlayout = QtGui.QHBoxLayout()
        Vlayout.addLayout(Hlayout)
        Hlayout.addWidget(QtGui.QLabel('Color:'))
        self.cbTimeColor = QtGui.QLineEdit(self)
        self.cbTimeColor.setText("#FFFFFF")
        Hlayout.addWidget(self.cbTimeColor)
        Hlayout.addStretch()

        Vlayout.addStretch()

        """ Progress bar """

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
        match = re.match(r"%\s*\d*d", srcpath)
        if not match:
            path, name = os.path.split(srcpath)
            basename, ext = os.path.splitext(name)
            basename_new = re.sub(r"\d+", "%04d", basename, count=1)
            if basename_new == basename:
                basename_new = basename+"%04d"
            srcpath = os.path.join(path, basename_new+ext)
        self.leANameI.setText(srcpath)

    def OpenDialog3(self):
        srcpath = str(QtGui.QFileDialog.getSaveFileName(None, "Choose Gif", os.getcwd(), "Animated Gifs (*.gif)"))
        self.leANameG.setText(srcpath)

    def SaveImage(self):
        timeline = self.window.GetModule("Timeline")
        marker_handler = self.window.GetModule("MarkerHandler")
        start = timeline.frameSlider.startValue()
        end = timeline.frameSlider.endValue()
        skip = timeline.skip if timeline.skip >= 1 else 1
        writer = None
        if self.cbType.currentIndex() == 0:
            path = str(self.leAName.text())
            writer_params = dict(format="avi", mode="I", fps=timeline.fps, codec=str(self.leCodec.text()), quality=self.sbQuality.value())
        elif self.cbType.currentIndex() == 1:
            path = str(self.leANameI.text())
        elif self.cbType.currentIndex() == 2:
            path = str(self.leANameG.text())
            writer_params = dict(format="gif", mode="I", fps=timeline.fps)
        if not os.path.exists(os.path.dirname(path)):
            try:
                os.mkdir(os.path.dirname(path))
            except OSError:
                print("ERROR: can't create folder %s", os.path.dirname(path))
                return
        self.time_drawing = None
        if self.cbTime.isChecked():
            class TimeDrawing: pass
            self.time_drawing = TimeDrawing()
            self.time_drawing.font = ImageFont.truetype("tahoma.ttf", self.cbTimeFontSize.value())
            self.time_drawing.start = None
            self.time_drawing.x = 15
            self.time_drawing.y = 10
            self.time_drawing.color = tuple(HTMLColorToRGB(self.cbTimeColor.text()))
        self.progressbar.setMinimum(start)
        self.progressbar.setMaximum(end)
        for frame in range(start, end+1, skip):
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
                self.preview_slice = np.dstack((self.preview_slice, self.preview_slice, self.preview_slice))

            if self.window.ImageDisplay.conversion is not None:
                self.preview_slice = self.window.ImageDisplay.conversion[self.preview_slice.astype(np.uint8)[:, :, :3]].astype(np.uint8)
            pil_image = Image.fromarray(self.preview_slice)
            draw = ImageDraw.Draw(pil_image)
            if marker_handler:
                marker_handler.drawToImage(draw, start_x, start_y)
            if self.time_drawing is not None:
                time = self.window.media_handler.get_timestamp()
                if time is not None:
                    if frame == start and self.cbTimeZero.isChecked():
                        self.time_drawing.start = time
                    if self.time_drawing.start is not None:
                        text = str(time-self.time_drawing.start)
                    else:
                        text = time.strftime("%Y-%m-%d %H:%M:%S")
                    draw.text((self.time_drawing.x, self.time_drawing.y), text, self.time_drawing.color, font=self.time_drawing.font)
            if self.cbType.currentIndex() == 0:
                if writer == None:
                    writer = imageio.get_writer(path, **writer_params)
                writer.append_data(np.array(pil_image))
            elif self.cbType.currentIndex() == 1:
                pil_image.save(path % (frame-start))
            elif self.cbType.currentIndex() == 0 or self.cbType.currentIndex() == 2:
                if writer == None:
                    writer = imageio.get_writer(path, **writer_params)
                writer.append_data(np.array(pil_image))
        self.progressbar.setValue(end)
        if self.cbType.currentIndex() == 2 or self.cbType.currentIndex() == 0:
            writer.close()

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
