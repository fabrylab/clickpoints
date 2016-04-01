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
from scipy.ndimage import shift

from QtShortCuts import AddQSaveFileChoose, AddQLineEdit, AddQSpinBox, AddQLabel, AddQCheckBox

def BoundBy(value, min, max):
    # return value bound by min and max
    if value is None:
        return min
    if value < min:
        return min
    if value > max:
        return max
    return value

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

        self.leAName = AddQSaveFileChoose(Vlayout, 'Filename:', os.path.join(self.config.outputpath, "export/export.avi"), "Choose Video", "Videos (*.avi)")
        self.leCodec = AddQLineEdit(Vlayout, "Codec:", "libx264", strech=True)
        self.sbQuality = AddQSpinBox(Vlayout, 'Quality (0 lowest, 10 highest):', 5, float=False, strech=True)
        self.sbQuality.setRange(0, 10)

        Vlayout.addStretch()

        """ Image """
        imageWidget = QtGui.QGroupBox("Image Settings")
        self.StackedWidget.addWidget(imageWidget)
        Vlayout = QtGui.QVBoxLayout(imageWidget)

        self.leANameI = AddQSaveFileChoose(Vlayout, 'Filename:', os.path.join(self.config.outputpath, "export/images%d.jpg"), "Choose Image", "Images (*.jpg *.png *.tif)", self.CheckImageFilename)
        AddQLabel(Vlayout, 'Image names have to contain %d as a placeholder for the image number.')

        Vlayout.addStretch()

        """ Gif """
        gifWidget = QtGui.QGroupBox("Animated Gif Settings")
        self.StackedWidget.addWidget(gifWidget)
        Vlayout = QtGui.QVBoxLayout(gifWidget)

        self.leANameG = AddQSaveFileChoose(Vlayout, 'Filename:', os.path.join(self.config.outputpath, "export/export.gif"), "Choose Gif", "Animated Gifs (*.gif)")

        Vlayout.addStretch()

        """ Time """
        timeWidget = QtGui.QGroupBox("Time")
        self.layout.addWidget(timeWidget)
        Vlayout = QtGui.QVBoxLayout(timeWidget)

        self.cbTime = AddQCheckBox(Vlayout, 'Display time:', True, strech=True)
        self.cbTimeZero = AddQCheckBox(Vlayout, 'Start from zero:', True, strech=True)
        self.cbTimeFontSize = AddQSpinBox(Vlayout, 'Font size:', 50, float=False, strech=True)
        self.cbTimeColor = AddQLineEdit(Vlayout, "Color:", "#FFFFFF", strech=True)

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

    def CheckImageFilename(self, srcpath):
        match = re.match(r"%\s*\d*d", srcpath)
        if not match:
            path, name = os.path.split(srcpath)
            basename, ext = os.path.splitext(name)
            basename_new = re.sub(r"\d+", "%04d", basename, count=1)
            if basename_new == basename:
                basename_new = basename+"%04d"
            srcpath = os.path.join(path, basename_new+ext)
        return srcpath

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

        # check if offsets for stabilisation are available in db
        offset_limits = self.window.data_file.get_offset_maxmin()
        if not any(v is None for v in offset_limits):
            offsets_available= True

        # determine export rect
        image = self.window.ImageDisplay.image
        offset = self.window.ImageDisplay.last_offset
        start_x, start_y, end_x, end_y = np.array(self.window.view.GetExtend(True)).astype("int") + np.hstack((offset, offset)).astype("int")
        # constrain start points
        start_x = BoundBy(start_x, 0, image.shape[1])
        start_y = BoundBy(start_y, 0, image.shape[0])
        # constrain end points
        end_x = BoundBy(end_x, start_x+1, image.shape[1])
        end_y = BoundBy(end_y, start_y+1, image.shape[0])
        if (end_y-start_y) % 2 != 0: end_y -= 1
        if (end_x-start_x) % 2 != 0: end_x -= 1
        self.preview_slice = np.zeros((end_y-start_y, end_x-start_x, 3), "uint8")

        # iterate over frames
        for frame in range(start, end+1, skip):
            self.progressbar.setValue(frame)
            self.window.JumpToFrame(frame, no_threaded_load=True)

            image = self.window.ImageDisplay.image
            offset = self.window.ImageDisplay.last_offset
            offset_int = offset.astype("int")
            offset_float = offset - offset_int

            start_x2 = start_x-offset_int[0]
            start_y2 = start_y-offset_int[1]
            end_x2 = end_x-offset_int[0]
            end_y2 = end_y-offset_int[1]
            start_x3 = BoundBy(start_x2, 0, image.shape[1])
            start_y3 = BoundBy(start_y2, 0, image.shape[0])
            end_x3 = BoundBy(end_x2, start_x3+1, image.shape[1])
            end_y3 = BoundBy(end_y2, start_y3+1, image.shape[0])

            # extract cropped image
            self.preview_slice[:] = 0
            print("x", start_x2, start_x3, end_x2, end_x3)
            print("y", start_y2, start_y3, end_y2, end_y3)
            self.preview_slice[start_y3-start_y2:self.preview_slice.shape[0]+(end_y3-end_y2), start_x3-start_x2:self.preview_slice.shape[1]+(end_x3-end_x2), :] = image[start_y3:end_y3, start_x3:end_x3, :]
            self.preview_slice = shift(self.preview_slice, -np.hstack((offset_float, 0)))

            # use min/max & gamma correction
            if self.window.ImageDisplay.conversion is not None:
                self.preview_slice = self.window.ImageDisplay.conversion[self.preview_slice.astype(np.uint8)[:, :, :3]].astype(np.uint8)

            pil_image = Image.fromarray(self.preview_slice)
            draw = ImageDraw.Draw(pil_image)
            if marker_handler:
                marker_handler.drawToImage(draw, start_x-offset[0], start_y-offset[1])
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
