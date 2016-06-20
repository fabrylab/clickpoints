from __future__ import division, print_function
import os

from qtpy import QtCore, QtGui, QtWidgets
import qtawesome as qta

import imageio
import numpy as np
import re
from PIL import ImageDraw, Image, ImageFont
from scipy.ndimage import shift

from Tools import HTMLColorToRGB, BoundBy
from QtShortCuts import AddQSaveFileChoose, AddQLineEdit, AddQSpinBox, AddQLabel, AddQCheckBox, AddQColorChoose


class VideoExporterDialog(QtGui.QWidget):
    def __init__(self, parent, window, data_file, config, modules):
        QtGui.QWidget.__init__(self)
        # default settings and parameters
        self.window = window
        self.data_file = data_file
        self.config = config
        self.modules = modules

        # widget layout and elements
        self.setMinimumWidth(700)
        self.setMinimumHeight(300)
        self.setWindowIcon(qta.icon('fa.film'))
        self.setWindowTitle('Video Export - ClickPoints')
        self.layout = QtGui.QVBoxLayout(self)
        self.parent = parent

        # add combo box to choose export mode
        Hlayout = QtGui.QHBoxLayout()
        self.cbType = QtGui.QComboBox(self)
        self.cbType.insertItem(0, "Video")
        self.cbType.insertItem(1, "Images")
        self.cbType.insertItem(2, "Gif")
        Hlayout.addWidget(self.cbType)
        self.layout.addLayout(Hlayout)

        # add stacked widget to store export mode parameter
        self.StackedWidget = QtGui.QStackedWidget(self)
        self.layout.addWidget(self.StackedWidget)

        self.cbType.currentIndexChanged.connect(self.StackedWidget.setCurrentIndex)

        """ Video """
        videoWidget = QtGui.QGroupBox("Video Settings")
        self.StackedWidget.addWidget(videoWidget)
        Vlayout = QtGui.QVBoxLayout(videoWidget)

        self.leAName = AddQSaveFileChoose(Vlayout, 'Filename:', os.path.join(os.getcwd(), "export/export.avi"), "Choose Video - ClickPoints", "Videos (*.avi)")
        self.leCodec = AddQLineEdit(Vlayout, "Codec:", "libx264", strech=True)
        self.sbQuality = AddQSpinBox(Vlayout, 'Quality (0 lowest, 10 highest):', 5, float=False, strech=True)
        self.sbQuality.setRange(0, 10)

        Vlayout.addStretch()

        """ Image """
        imageWidget = QtGui.QGroupBox("Image Settings")
        self.StackedWidget.addWidget(imageWidget)
        Vlayout = QtGui.QVBoxLayout(imageWidget)

        self.leANameI = AddQSaveFileChoose(Vlayout, 'Filename:', os.path.join(os.getcwd(), "export/images%d.jpg"), "Choose Image - ClickPoints", "Images (*.jpg *.png *.tif)", self.CheckImageFilename)
        AddQLabel(Vlayout, 'Image names have to contain %d as a placeholder for the image number.')

        Vlayout.addStretch()

        """ Gif """
        gifWidget = QtGui.QGroupBox("Animated Gif Settings")
        self.StackedWidget.addWidget(gifWidget)
        Vlayout = QtGui.QVBoxLayout(gifWidget)

        self.leANameG = AddQSaveFileChoose(Vlayout, 'Filename:', os.path.join(os.getcwd(), "export/export.gif"), "Choose Gif - ClickPoints", "Animated Gifs (*.gif)")

        Vlayout.addStretch()

        """ Time """
        timeWidget = QtGui.QGroupBox("Time")
        self.layout.addWidget(timeWidget)
        Vlayout = QtGui.QVBoxLayout(timeWidget)

        self.cbTime = AddQCheckBox(Vlayout, 'Display time:', True, strech=True)
        self.cbTimeZero = AddQCheckBox(Vlayout, 'Start from zero:', True, strech=True)
        self.cbTimeFontSize = AddQSpinBox(Vlayout, 'Font size:', 50, float=False, strech=True)
        self.cbTimeColor = AddQColorChoose(Vlayout, "Color:", "#FFFFFF", strech=True)

        self.cbMarkerScaleSize = AddQSpinBox(Vlayout, 'Marker scale:', 1.00, float=True, strech=True)

        Vlayout.addStretch()

        """ Progress bar """

        Hlayout = QtGui.QHBoxLayout()
        self.progressbar = QtGui.QProgressBar()
        Hlayout.addWidget(self.progressbar)
        self.button_start = QtGui.QPushButton("Start")
        self.button_start.pressed.connect(self.SaveImage)
        Hlayout.addWidget(self.button_start)
        self.button_stop = QtGui.QPushButton("Stop")
        self.button_stop.pressed.connect(self.StopSaving)
        self.button_stop.setHidden(True)
        Hlayout.addWidget(self.button_stop)
        self.layout.addLayout(Hlayout)

    def CheckImageFilename(self, srcpath):
        # ensure that image filenames contain %d placeholder for the number
        match = re.match(r"%\s*\d*d", srcpath)
        # if not add one, between filename and extension
        if not match:
            path, name = os.path.split(srcpath)
            basename, ext = os.path.splitext(name)
            basename_new = re.sub(r"\d+", "%04d", basename, count=1)
            if basename_new == basename:
                basename_new = basename+"%04d"
            srcpath = os.path.join(path, basename_new+ext)
        return srcpath

    def StopSaving(self):
        # schedule an abortion of the export
        self.abort = True

    def SaveImage(self):
        # hide the start button and display the abort button
        self.abort = False
        self.button_start.setHidden(True)
        self.button_stop.setHidden(False)

        # get the marker handler for marker drawing
        marker_handler = self.window.GetModule("MarkerHandler")

        # get the timeline for start and end frames
        timeline = self.window.GetModule("Timeline")
        # extract start, end and skip
        start = timeline.frameSlider.startValue()
        end = timeline.frameSlider.endValue()
        skip = timeline.skip if timeline.skip >= 1 else 1

        # initialize writer object according to export mode
        writer = None
        if self.cbType.currentIndex() == 0:  # video
            path = str(self.leAName.text())
            writer_params = dict(format="avi", mode="I", fps=timeline.fps, codec=str(self.leCodec.text()), quality=self.sbQuality.value())
        elif self.cbType.currentIndex() == 1:  # image
            path = str(self.leANameI.text())
        elif self.cbType.currentIndex() == 2:  # gif
            path = str(self.leANameG.text())
            writer_params = dict(format="gif", mode="I", fps=timeline.fps)

        # create the output path if it doesn't exist
        if not os.path.exists(os.path.dirname(path)):
            try:
                os.mkdir(os.path.dirname(path))
            except OSError:
                print("ERROR: can't create folder %s", os.path.dirname(path))
                return
        # get timestamp draw parameter
        self.time_drawing = None
        if self.cbTime.isChecked():
            class TimeDrawing: pass
            self.time_drawing = TimeDrawing()
            try:
                self.time_drawing.font = ImageFont.truetype("arial.ttf", self.cbTimeFontSize.value())
            except IOError:
                self.time_drawing.font = ImageFont.truetype(os.path.join(self.window.icon_path, "FantasqueSansMono-Regular.ttf"), self.cbTimeFontSize.value())
            self.time_drawing.start = None
            self.time_drawing.x = 15
            self.time_drawing.y = 10
            self.time_drawing.color = tuple(HTMLColorToRGB(self.cbTimeColor.getColor()))

        # initialize progress bar
        self.progressbar.setMinimum(start)
        self.progressbar.setMaximum(end)

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
            # advance progress bar and load next image
            self.progressbar.setValue(frame)
            self.window.JumpToFrame(frame, threaded=False)

            # get new image and offsets
            image = self.window.ImageDisplay.image
            offset = self.window.ImageDisplay.last_offset
            # split offsets in integer and decimal part
            offset_int = offset.astype("int")
            offset_float = offset - offset_int

            # calculate new slices
            start_x2 = start_x-offset_int[0]
            start_y2 = start_y-offset_int[1]
            end_x2 = end_x-offset_int[0]
            end_y2 = end_y-offset_int[1]
            # adapt new slices to fit in image
            start_x3 = BoundBy(start_x2, 0, image.shape[1])
            start_y3 = BoundBy(start_y2, 0, image.shape[0])
            end_x3 = BoundBy(end_x2, start_x3+1, image.shape[1])
            end_y3 = BoundBy(end_y2, start_y3+1, image.shape[0])

            # extract cropped image
            self.preview_slice[:] = 0
            self.preview_slice[start_y3-start_y2:self.preview_slice.shape[0]+(end_y3-end_y2), start_x3-start_x2:self.preview_slice.shape[1]+(end_x3-end_x2), :] = image[start_y3:end_y3, start_x3:end_x3, :3]
            # apply the subpixel decimal shift
            if offset_float[0] or offset_float[1]:
                self.preview_slice = shift(self.preview_slice, -np.hstack((offset_float, 0)))

            # use min/max & gamma correction
            if self.window.ImageDisplay.conversion is not None:
                self.preview_slice = self.window.ImageDisplay.conversion[self.preview_slice.astype(np.uint8)[:, :, :3]].astype(np.uint8)

            # convert image to PIL draw object
            pil_image = Image.fromarray(self.preview_slice)
            draw = ImageDraw.Draw(pil_image)
            # draw marker on the image
            if marker_handler:
                marker_handler.drawToImage(draw, start_x-offset[0], start_y-offset[1], self.cbMarkerScaleSize.value())
            # draw timestamp
            if self.time_drawing is not None or 0:  # TODO
                time = self.window.data_file.image.timestamp
                if time is not None:
                    if frame == start and self.cbTimeZero.isChecked():
                        self.time_drawing.start = time
                    if self.time_drawing.start is not None:
                        text = str(time-self.time_drawing.start)
                    else:
                        text = time.strftime("%Y-%m-%d %H:%M:%S")
                    draw.text((self.time_drawing.x, self.time_drawing.y), text, self.time_drawing.color, font=self.time_drawing.font)
            # add to video ...
            if self.cbType.currentIndex() == 0:
                if writer is None:
                    writer = imageio.get_writer(path, **writer_params)
                writer.append_data(np.array(pil_image))
            # ... or save image ...
            elif self.cbType.currentIndex() == 1:
                pil_image.save(path % (frame-start))
            # ... or add to gif
            elif self.cbType.currentIndex() == 0 or self.cbType.currentIndex() == 2:
                if writer is None:
                    writer = imageio.get_writer(path, **writer_params)
                writer.append_data(np.array(pil_image))
            # process events so that the program doesn't stall
            self.window.app.processEvents()
            # abort if the user clicked the abort button
            if self.abort:
                break

        # set progress bar to the end and close output file
        self.progressbar.setValue(end)
        if self.cbType.currentIndex() == 2 or self.cbType.currentIndex() == 0:
            writer.close()

        # show the start button again
        self.button_start.setHidden(False)
        self.button_stop.setHidden(True)

class VideoExporter:
    def __init__(self, window, data_file, modules, config=None):
        # default settings and parameters
        self.window = window
        self.data_file = data_file
        self.config = config
        self.modules = modules
        self.ExporterWindow = None

        self.button = QtGui.QPushButton()
        self.button.setIcon(qta.icon('fa.film'))
        self.button.setToolTip("export images as video/image series")
        self.button.clicked.connect(self.showDialog)
        window.layoutButtons.addWidget(self.button)

    def showDialog(self):
        if self.ExporterWindow:
            self.ExporterWindow.raise_()
            self.ExporterWindow.show()
        else:
            self.ExporterWindow = VideoExporterDialog(self, self.window, self.data_file, self.config, self.modules)
            self.ExporterWindow.show()

    def keyPressEvent(self, event):

        # @key Z: Export Video
        if event.key() == QtCore.Qt.Key_Z:
            self.showDialog()

    def closeEvent(self, event):
        if self.ExporterWindow:
            self.ExporterWindow.close()

    @staticmethod
    def file():
        return __file__
