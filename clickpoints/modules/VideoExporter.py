#!/usr/bin/env python
# -*- coding: utf-8 -*-
# VideoExporter.py

# Copyright (c) 2015-2016, Richard Gerum, Sebastian Richter
#
# This file is part of ClickPoints.
#
# ClickPoints is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ClickPoints is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ClickPoints. If not, see <http://www.gnu.org/licenses/>

from __future__ import division, print_function
import os

from qtpy import QtCore, QtGui, QtWidgets
import qtawesome as qta

import imageio
import numpy as np
import re
from PIL import ImageDraw, Image, ImageFont
from scipy.ndimage import shift

from includes.Tools import HTMLColorToRGB, BoundBy, BroadCastEvent
from includes.QtShortCuts import AddQSaveFileChoose, AddQLineEdit, AddQSpinBox, AddQLabel, AddQCheckBox, AddQColorChoose


def MakePathRelative(abs_path):
    try:
        path = os.path.relpath(abs_path)
    except ValueError:
        path = abs_path
    else:
        # not more than one path up, the rest should stay with an absolute path
        if path.find("../..") != -1 or path.find("..\\..") != -1:
            path = abs_path
    path = path.replace("\\", "/")
    return path


class VideoExporterDialog(QtWidgets.QWidget):
    def __init__(self, parent, window, data_file, config, modules):
        QtWidgets.QWidget.__init__(self)
        # default settings and parameters
        self.window = window
        self.data_file = data_file
        self.config = config
        self.modules = modules
        options = data_file.getOptionAccess()
        self.options = options

        # widget layout and elements
        self.setMinimumWidth(700)
        self.setMinimumHeight(300)
        self.setWindowIcon(qta.icon('fa.film'))
        self.setWindowTitle('Video Export - ClickPoints')
        self.layout = QtWidgets.QVBoxLayout(self)
        self.parent = parent

        # add combo box to choose export mode
        Hlayout = QtWidgets.QHBoxLayout()
        self.cbType = QtWidgets.QComboBox(self)
        self.cbType.insertItem(0, "Video")
        self.cbType.insertItem(1, "Images")
        self.cbType.insertItem(2, "Gif")
        self.cbType.insertItem(3, "Single Image")
        Hlayout.addWidget(self.cbType)
        self.layout.addLayout(Hlayout)

        # add stacked widget to store export mode parameter
        self.StackedWidget = QtWidgets.QStackedWidget(self)
        self.layout.addWidget(self.StackedWidget)

        self.cbType.currentIndexChanged.connect(self.StackedWidget.setCurrentIndex)

        """ Video """
        videoWidget = QtWidgets.QGroupBox("Video Settings")
        self.StackedWidget.addWidget(videoWidget)
        Vlayout = QtWidgets.QVBoxLayout(videoWidget)

        self.leAName = AddQSaveFileChoose(Vlayout, 'Filename:', os.path.abspath(options.export_video_filename), "Choose Video - ClickPoints", "Videos (*.avi)", lambda name: self.checkExtension(name, ".avi"))
        self.leCodec = AddQLineEdit(Vlayout, "Codec:", options.video_codec, strech=True)
        self.sbQuality = AddQSpinBox(Vlayout, 'Quality (0 lowest, 10 highest):', options.video_quality, float=False, strech=True)
        self.sbQuality.setRange(0, 10)

        Vlayout.addStretch()

        """ Image """
        imageWidget = QtWidgets.QGroupBox("Image Settings")
        self.StackedWidget.addWidget(imageWidget)
        Vlayout = QtWidgets.QVBoxLayout(imageWidget)

        self.leANameI = AddQSaveFileChoose(Vlayout, 'Filename:', os.path.abspath(options.export_image_filename), "Choose Image - ClickPoints", "Images (*.jpg *.png *.tif)", self.CheckImageFilename)
        AddQLabel(Vlayout, 'Image names have to contain %d as a placeholder for the image number.')

        Vlayout.addStretch()

        """ Gif """
        gifWidget = QtWidgets.QGroupBox("Animated Gif Settings")
        self.StackedWidget.addWidget(gifWidget)
        Vlayout = QtWidgets.QVBoxLayout(gifWidget)

        self.leANameG = AddQSaveFileChoose(Vlayout, 'Filename:', os.path.abspath(options.export_gif_filename), "Choose Gif - ClickPoints", "Animated Gifs (*.gif)", lambda name: self.checkExtension(name, ".gif"))

        Vlayout.addStretch()

        """ Single Image """
        imageWidget = QtWidgets.QGroupBox("Single Image Settings")
        self.StackedWidget.addWidget(imageWidget)
        Vlayout = QtWidgets.QVBoxLayout(imageWidget)

        self.leANameIS = AddQSaveFileChoose(Vlayout, 'Filename:', os.path.abspath(options.export_single_image_filename),
                                           "Choose Image - ClickPoints", "Images (*.jpg *.png *.tif)", lambda name: self.checkExtension(name, ".jpg"))
        AddQLabel(Vlayout, 'Single Image will only export the current frame. Optionally, a %d placeholder will be filled with the frame number')

        Vlayout.addStretch()

        """ Time """
        timeWidget = QtWidgets.QGroupBox("Time")
        self.layout.addWidget(timeWidget)
        Vlayout = QtWidgets.QVBoxLayout(timeWidget)

        self.cbTime = AddQCheckBox(Vlayout, 'Display time:', options.export_display_time, strech=True)
        self.cbTimeZero = AddQCheckBox(Vlayout, 'Start from zero:', options.export_time_from_zero, strech=True)
        self.cbTimeFontSize = AddQSpinBox(Vlayout, 'Font size:', options.export_time_font_size, float=False, strech=True)
        self.cbTimeColor = AddQColorChoose(Vlayout, "Color:", options.export_time_font_color, strech=True)

        Vlayout.addStretch()

        """ Scale """
        scaleWidget = QtWidgets.QGroupBox("Scale")
        self.layout.addWidget(scaleWidget)
        Vlayout = QtWidgets.QVBoxLayout(scaleWidget)

        self.cbImageScaleSize = AddQSpinBox(Vlayout, 'Image scale:', options.export_image_scale, float=True, strech=True)
        self.cbMarkerScaleSize = AddQSpinBox(Vlayout, 'Marker scale:', options.export_marker_scale, float=True, strech=True)

        Vlayout.addStretch()

        self.cbType.setCurrentIndex(options.export_type)

        """ Progress bar """

        Hlayout = QtWidgets.QHBoxLayout()
        self.progressbar = QtWidgets.QProgressBar()
        Hlayout.addWidget(self.progressbar)
        self.button_start = QtWidgets.QPushButton("Start")
        self.button_start.pressed.connect(self.SaveImage)
        Hlayout.addWidget(self.button_start)
        self.button_stop = QtWidgets.QPushButton("Stop")
        self.button_stop.pressed.connect(self.StopSaving)
        self.button_stop.setHidden(True)
        Hlayout.addWidget(self.button_stop)
        self.layout.addLayout(Hlayout)

    def checkExtension(self, name, ext):
        # in some versions the Qt file dialog doesn't automatically add an extension
        basename, current_extension = os.path.splitext(name)
        if current_extension == "":
            return name+ext
        return name

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
        return self.checkExtension(srcpath, ".jpg")

    def StopSaving(self):
        # schedule an abortion of the export
        self.abort = True

    def SaveImage(self):
        # hide the start button and display the abort button
        self.abort = False
        self.button_start.setHidden(True)
        self.button_stop.setHidden(False)

        # save options
        options = self.options
        options.export_video_filename = MakePathRelative(str(self.leAName.text()))
        options.export_image_filename = MakePathRelative(str(self.leANameI.text()))
        options.export_gif_filename = MakePathRelative(str(self.leANameG.text()))
        options.export_single_image_filename = MakePathRelative(str(self.leANameIS.text()))
        options.export_type = self.cbType.currentIndex()
        options.video_codec = str(self.leCodec.text())
        options.video_quality = self.sbQuality.value()
        options.export_display_time = self.cbTime.isChecked()
        options.export_time_from_zero = self.cbTimeZero.isChecked()
        options.export_time_font_size = self.cbTimeFontSize.value()
        options.export_time_font_color = self.cbTimeColor.getColor()
        options.export_image_scale = self.cbImageScaleSize.value()
        options.export_marker_scale = self.cbMarkerScaleSize.value()

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
            writer_params = dict(format="avi", mode="I", fps=timeline.fps, codec=options.video_codec, quality=options.video_quality)
        elif self.cbType.currentIndex() == 1:  # image
            path = str(self.leANameI.text())
        elif self.cbType.currentIndex() == 2:  # gif
            path = str(self.leANameG.text())
            writer_params = dict(format="gif", mode="I", fps=timeline.fps)
        elif self.cbType.currentIndex() == 3:  # single image
            path = str(self.leANameIS.text())

        # create the output path if it doesn't exist
        if not os.path.exists(os.path.dirname(path)):
            try:
                os.mkdir(os.path.dirname(path))
            except OSError:
                print("ERROR: can't create folder %s", os.path.dirname(path))
                return
        # get timestamp draw parameter
        self.time_drawing = None
        if options.export_display_time:
            class TimeDrawing: pass
            self.time_drawing = TimeDrawing()
            try:
                self.time_drawing.font = ImageFont.truetype("arial.ttf", options.export_time_font_size)
            except IOError:
                self.time_drawing.font = ImageFont.truetype(os.path.join(self.window.icon_path, "FantasqueSansMono-Regular.ttf"), self.cbTimeFontSize.value())
            self.time_drawing.start = None
            self.time_drawing.x = 15
            self.time_drawing.y = 10
            self.time_drawing.color = tuple(HTMLColorToRGB(options.export_time_font_color))

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
        iter_range = range(start, end+1, skip)
        if self.cbType.currentIndex() == 3:
            iter_range = [self.window.target_frame]
        for frame in iter_range:
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
                self.preview_slice = shift(self.preview_slice, [offset_float[1], offset_float[0], 0])

            # use min/max & gamma correction
            if self.window.ImageDisplay.conversion is not None:
                self.preview_slice = self.window.ImageDisplay.conversion[self.preview_slice.astype(np.uint8)[:, :, :3]].astype(np.uint8)

            # convert image to PIL draw object
            pil_image = Image.fromarray(self.preview_slice)
            if options.export_image_scale != 1:
                shape = np.array([self.preview_slice.shape[1], self.preview_slice.shape[0]])*options.export_image_scale
                pil_image = pil_image.resize(shape.astype(int), Image.ANTIALIAS)
            draw = ImageDraw.Draw(pil_image)
            draw.pil_image = pil_image
            # draw marker on the image
            BroadCastEvent(self.window.modules, "drawToImage", draw, start_x-offset[0], start_y-offset[1], options.export_marker_scale, options.export_image_scale, options.rotation)
            # rotate the image
            if self.data_file.getOption("rotation") != 0:
                angle = self.data_file.getOption("rotation")
                if angle == 90:
                    pil_image = pil_image.transpose(Image.ROTATE_270)
                elif angle == 180:
                    pil_image = pil_image.transpose(Image.ROTATE_180)
                elif angle == 270:
                    pil_image = pil_image.transpose(Image.ROTATE_90)
                else:
                    pil_image = pil_image.rotate(-angle)
                draw = ImageDraw.Draw(pil_image)
                draw.pil_image = pil_image
            # draw marker on the image
            BroadCastEvent(self.window.modules, "drawToImage2", draw, start_x - offset[0], start_y - offset[1],
                               options.export_marker_scale, options.export_image_scale, options.rotation)
            # draw timestamp
            if self.time_drawing is not None:
                time = self.window.data_file.image.timestamp
                if time is not None:
                    if frame == start and options.export_time_from_zero:
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
            elif self.cbType.currentIndex() == 3:
                try:
                    pil_image.save(path % frame)
                except TypeError:
                    pil_image.save(path)
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

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.parent.ExporterWindow = None
            self.close()

class VideoExporter:
    data_file = None
    config = None

    def __init__(self, window, modules, config=None):
        # default settings and parameters
        self.window = window
        self.modules = modules
        self.ExporterWindow = None

        self.button = QtWidgets.QPushButton()
        self.button.setIcon(qta.icon('fa.film'))
        self.button.setToolTip("export images as video/image series")
        self.button.clicked.connect(self.showDialog)
        window.layoutButtons.addWidget(self.button)

    def closeDataFile(self):
        self.data_file = None
        self.config = None

        if self.ExporterWindow:
            self.ExporterWindow.close()

    def updateDataFile(self, data_file, new_database):
        self.data_file = data_file
        self.config = data_file.getOptionAccess()

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
