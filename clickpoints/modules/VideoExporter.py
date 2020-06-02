#!/usr/bin/env python
# -*- coding: utf-8 -*-
# VideoExporter.py

# Copyright (c) 2015-2020, Richard Gerum, Sebastian Richter, Alexander Winterl
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ClickPoints. If not, see <http://www.gnu.org/licenses/>

import datetime
import os
import re
from typing import Any, List

import imageio
import numpy as np
import qtawesome as qta
from PIL import ImageDraw, Image, ImageFont
from qtpy import QtCore, QtGui, QtWidgets
from scipy.ndimage import shift
import asyncio

from clickpoints.DataFile import OptionAccess
from clickpoints.includes import QtShortCuts
from clickpoints.includes.Database import DataFileExtended
from clickpoints.includes.Tools import HTMLColorToRGB, BoundBy, BroadCastEvent


def MakePathRelative(abs_path: str) -> str:
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


def formatTimedelta(t: datetime.timedelta, fmt: str) -> str:
    sign = 1
    if t.total_seconds() < 0:
        sign = -1
        t = -t
    seconds = t.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    parts = {"d": t.days, "H": hours, "M": minutes, "S": seconds,
             "s": t.total_seconds(), "m": t.microseconds // 1000, "f": t.microseconds}

    max_level = None
    if fmt.find("%d") != -1:
        max_level = "d"
    elif fmt.find("%H") != -1:
        max_level = "H"
    elif fmt.find("%M") != -1:
        max_level = "M"
    elif fmt.find("%S") != -1:
        max_level = "S"
    elif fmt.find("%m") != -1:
        max_level = "m"
    elif fmt.find("%f") != -1:
        max_level = "f"

    fmt = fmt.replace("%d", str(parts["d"]))
    if max_level == "H":
        fmt = fmt.replace("%H", "%d" % (parts["H"] + parts["d"] * 24))
    else:
        fmt = fmt.replace("%H", "%02d" % parts["H"])
    if max_level == "M":
        fmt = fmt.replace("%M", "%2d" % (parts["M"] + parts["H"] * 60 + parts["d"] * 60 * 24))
    else:
        fmt = fmt.replace("%M", "%02d" % parts["M"])

    if max_level == "S":
        fmt = fmt.replace("%S", "%d" % parts["s"])
    else:
        fmt = fmt.replace("%S", "%02d" % parts["S"])

    if max_level == "m":
        fmt = fmt.replace("%m", "%3d" % (parts["m"] + parts["s"] * 1000))
    else:
        fmt = fmt.replace("%m", "%03d" % parts["m"])
    if max_level == "f":
        fmt = fmt.replace("%f", "%6d" % (parts["f"] + parts["s"] * 1000 * 1000))
    else:
        fmt = fmt.replace("%f", "%06d" % parts["f"])
    if sign == -1:
        for i in range(len(fmt)):
            if fmt[i] != " ":
                break
        if i == 0:
            fmt = "-" + fmt
        else:
            fmt = fmt[:i - 1] + "-" + fmt[i:]
    return fmt


class VideoExporterDialog(QtWidgets.QWidget):
    def __init__(self, parent: "VideoExporter", window: "ClickPointsWindow", data_file: DataFileExtended,
                 config: OptionAccess, modules: List[Any]) -> None:
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

        self.leAName = QtShortCuts.QInputFilename(Vlayout, 'Filename:', os.path.abspath(options.export_video_filename),
                                                  "Choose Video - ClickPoints", "Videos (*.mp4 *.mpeg *.avi)",
                                                  lambda name: self.checkExtension(name, ".mp4"))
        self.leCodec = QtShortCuts.QInputString(Vlayout, "Codec:", options.video_codec, stretch=True)
        self.sbQuality = QtShortCuts.QInputNumber(Vlayout, 'Quality (0 lowest, 10 highest):', options.video_quality,
                                                  min=0, max=10, float=False, stretch=True)

        Vlayout.addStretch()

        """ Image """
        imageWidget = QtWidgets.QGroupBox("Image Settings")
        self.StackedWidget.addWidget(imageWidget)
        Vlayout = QtWidgets.QVBoxLayout(imageWidget)

        self.leANameI = QtShortCuts.QInputFilename(Vlayout, 'Filename:', os.path.abspath(options.export_image_filename),
                                                   "Choose Image - ClickPoints", "Images (*.jpg *.png *.tif, *.svg)",
                                                   self.CheckImageFilename)
        QtShortCuts.QInput(Vlayout, 'Image names have to contain %d as a placeholder for the image number.')

        Vlayout.addStretch()

        """ Gif """
        gifWidget = QtWidgets.QGroupBox("Animated Gif Settings")
        self.StackedWidget.addWidget(gifWidget)
        Vlayout = QtWidgets.QVBoxLayout(gifWidget)

        self.leANameG = QtShortCuts.QInputFilename(Vlayout, 'Filename:', os.path.abspath(options.export_gif_filename),
                                                   "Choose Gif - ClickPoints", "Animated Gifs (*.gif)",
                                                   lambda name: self.checkExtension(name, ".gif"))

        Vlayout.addStretch()

        """ Single Image """
        imageWidget = QtWidgets.QGroupBox("Single Image Settings")
        self.StackedWidget.addWidget(imageWidget)
        Vlayout = QtWidgets.QVBoxLayout(imageWidget)

        self.leANameIS = QtShortCuts.QInputFilename(Vlayout, 'Filename:',
                                                    os.path.abspath(options.export_single_image_filename),
                                                    "Choose Image - ClickPoints", "Images (*.jpg *.png *.tif *.svg)",
                                                    lambda name: self.checkExtension(name, ".jpg"))
        QtShortCuts.QInput(Vlayout,
                           'Single Image will only export the current frame. Optionally, a %d placeholder will be filled with the frame number')

        Vlayout.addStretch()

        """ Time """
        timeWidget = QtWidgets.QGroupBox("Time")
        self.layout.addWidget(timeWidget)
        Hlayout = QtWidgets.QHBoxLayout(timeWidget)
        Vlayout = QtWidgets.QVBoxLayout()
        Hlayout.addLayout(Vlayout)

        self.cbTime = QtShortCuts.QInputBool(Vlayout, 'Display time:', options.export_display_time, stretch=True)
        self.cbTimeZero = QtShortCuts.QInputBool(Vlayout, 'Start from zero:', options.export_time_from_zero,
                                                 stretch=True)
        self.cbTimeFontSize = QtShortCuts.QInputNumber(Vlayout, 'Font size:', options.export_time_font_size,
                                                       float=False, stretch=True)
        self.cbTimeColor = QtShortCuts.QInputColor(Vlayout, "Color:", options.export_time_font_color, stretch=True)
        self.cbTimeFormat = QtShortCuts.QInputString(Vlayout, "Format:", options.export_time_format, stretch=True)
        self.cbTimeDeltaFormat = QtShortCuts.QInputString(Vlayout, "Format:", options.export_timedelta_format,
                                                          stretch=True)

        def updateTimeFormat(self):
            if self.cbTimeZero.value():
                self.cbTimeDeltaFormat.show()
                self.cbTimeFormat.hide()
            else:
                self.cbTimeDeltaFormat.hide()
                self.cbTimeFormat.show()

        self.cbTimeZero.checkbox.stateChanged.connect(lambda x, self=self: updateTimeFormat(self))
        updateTimeFormat(self)

        Vlayout = QtWidgets.QVBoxLayout()
        Hlayout.addLayout(Vlayout)

        self.cbCustomTime = QtShortCuts.QInputBool(Vlayout, 'Custom time:', options.export_custom_time)
        self.cbCustomTimeDelta = QtShortCuts.QInputNumber(Vlayout, 'Time between two frames (s):',
                                                          options.export_custom_time_delta)

        Vlayout.addStretch()

        """ Scale """
        scaleWidget = QtWidgets.QGroupBox("Scale")
        self.layout.addWidget(scaleWidget)
        Vlayout = QtWidgets.QVBoxLayout(scaleWidget)

        self.cbImageScaleSize = QtShortCuts.QInputNumber(Vlayout, 'Image scale:', options.export_image_scale,
                                                         float=True, stretch=True)
        self.cbMarkerScaleSize = QtShortCuts.QInputNumber(Vlayout, 'Marker scale:', options.export_marker_scale,
                                                          float=True, stretch=True)

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

    def checkExtension(self, name: str, ext: str) -> str:
        # in some versions the Qt file dialog doesn't automatically add an extension
        basename, current_extension = os.path.splitext(name)
        if current_extension == "":
            return name + ext
        return name

    def CheckImageFilename(self, srcpath: str) -> str:
        # ensure that image filenames contain %d placeholder for the number
        match = re.match(r"%\s*\d*d", srcpath)
        # if not add one, between filename and extension
        if not match:
            path, name = os.path.split(srcpath)
            basename, ext = os.path.splitext(name)
            basename_new = re.sub(r"\d+", "%04d", basename, count=1)
            if basename_new == basename:
                basename_new = basename + "%04d"
            srcpath = os.path.join(path, basename_new + ext)
        return self.checkExtension(srcpath, ".jpg")

    def StopSaving(self) -> None:
        # schedule an abortion of the export
        self.abort = True

    def SaveImage(self) -> None:
        asyncio.ensure_future(self.SaveImage_async(), loop=self.window.app.loop)

    async def SaveImage_async(self) -> None:
        # hide the start button and display the abort button
        self.abort = False
        self.button_start.setHidden(True)
        self.button_stop.setHidden(False)

        # save options
        options = self.options
        options.export_video_filename = MakePathRelative(str(self.leAName.value()))
        options.export_image_filename = MakePathRelative(str(self.leANameI.value()))
        options.export_gif_filename = MakePathRelative(str(self.leANameG.value()))
        options.export_single_image_filename = MakePathRelative(str(self.leANameIS.value()))
        options.export_type = self.cbType.currentIndex()
        options.video_codec = str(self.leCodec.value())
        options.video_quality = self.sbQuality.value()
        options.export_display_time = self.cbTime.value()
        options.export_time_from_zero = self.cbTimeZero.value()
        options.export_time_font_size = self.cbTimeFontSize.value()
        options.export_time_font_color = self.cbTimeColor.value()
        options.export_image_scale = self.cbImageScaleSize.value()
        options.export_marker_scale = self.cbMarkerScaleSize.value()
        options.export_custom_time = self.cbCustomTime.value()
        options.export_custom_time_delta = self.cbCustomTimeDelta.value()
        options.export_time_format = self.cbTimeFormat.value()
        options.export_timedelta_format = self.cbTimeDeltaFormat.value()

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
        svg = False
        if self.cbType.currentIndex() == 0:  # video
            path = str(self.leAName.value())
            writer_params = dict(format="avi", mode="I", fps=timeline.fps, codec=options.video_codec,
                                 quality=options.video_quality)
        elif self.cbType.currentIndex() == 1:  # image
            path = str(self.leANameI.value())
            if path.endswith(".svg"):
                svg = True
        elif self.cbType.currentIndex() == 2:  # gif
            path = str(self.leANameG.value())
            writer_params = dict(format="gif", mode="I", fps=timeline.fps)
        elif self.cbType.currentIndex() == 3:  # single image
            path = str(self.leANameIS.value())
            if path.endswith(".svg"):
                svg = True

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
            class TimeDrawing:
                pass

            self.time_drawing = TimeDrawing()
            try:
                self.time_drawing.font = ImageFont.truetype("arial.ttf", options.export_time_font_size)
            except IOError:
                self.time_drawing.font = ImageFont.truetype(
                    os.path.join(os.environ["CLICKPOINTS_ICON"], "FantasqueSansMono-Regular.ttf"),
                    self.cbTimeFontSize.value())
            self.time_drawing.start = None
            self.time_drawing.x = 15
            self.time_drawing.y = 10
            self.time_drawing.color = tuple(HTMLColorToRGB(options.export_time_font_color))
            if options.export_custom_time:
                self.custom_time = 0

        # initialize progress bar
        self.progressbar.setMinimum(start)
        self.progressbar.setMaximum(end)

        # determine export rect
        image = self.window.ImageDisplay.image
        offset = self.window.ImageDisplay.last_offset
        start_x, start_y, end_x, end_y = np.array(self.window.view.GetExtend(True)).astype("int") + np.hstack(
            (offset, offset)).astype("int")
        # constrain start points
        start_x = BoundBy(start_x, 0, image.shape[1])
        start_y = BoundBy(start_y, 0, image.shape[0])
        # constrain end points
        end_x = BoundBy(end_x, start_x + 1, image.shape[1])
        end_y = BoundBy(end_y, start_y + 1, image.shape[0])
        if (end_y - start_y) % 2 != 0: end_y -= 1
        if (end_x - start_x) % 2 != 0: end_x -= 1
        self.preview_slice = np.zeros((end_y - start_y, end_x - start_x, 3), self.window.ImageDisplay.image.dtype)

        # iterate over frames
        iter_range = range(start, end + 1, skip)
        if self.cbType.currentIndex() == 3:
            iter_range = [self.window.target_frame]
        for frame in iter_range:
            # advance progress bar and load next image
            self.progressbar.setValue(frame)
            await self.window.load_frame(frame)

            # get new image and offsets
            image = self.window.ImageDisplay.image
            offset = self.window.ImageDisplay.last_offset
            # split offsets in integer and decimal part
            offset_int = offset.astype("int")
            offset_float = offset - offset_int

            # calculate new slices
            start_x2 = start_x - offset_int[0]
            start_y2 = start_y - offset_int[1]
            end_x2 = end_x - offset_int[0]
            end_y2 = end_y - offset_int[1]
            # adapt new slices to fit in image
            start_x3 = BoundBy(start_x2, 0, image.shape[1])
            start_y3 = BoundBy(start_y2, 0, image.shape[0])
            end_x3 = BoundBy(end_x2, start_x3 + 1, image.shape[1])
            end_y3 = BoundBy(end_y2, start_y3 + 1, image.shape[0])

            # extract cropped image
            self.preview_slice = np.zeros((end_y - start_y, end_x - start_x, 3), self.window.ImageDisplay.image.dtype)
            self.preview_slice[start_y3 - start_y2:self.preview_slice.shape[0] + (end_y3 - end_y2),
            start_x3 - start_x2:self.preview_slice.shape[1] + (end_x3 - end_x2), :] = image[start_y3:end_y3,
                                                                                      start_x3:end_x3, :3]

            # draw mask on the image
            BroadCastEvent(self.window.modules, "drawToImage0", self.preview_slice, slice(start_y3, end_y3),
                           slice(start_x3, end_x3))

            # apply the subpixel decimal shift
            if offset_float[0] or offset_float[1]:
                self.preview_slice = shift(self.preview_slice, [offset_float[1], offset_float[0], 0])

            # use min/max & gamma correction
            if self.window.ImageDisplay.image_pixMapItem.conversion is not None:
                self.preview_slice = self.window.ImageDisplay.image_pixMapItem.conversion[self.preview_slice[:, :, :3]]

            # convert image to PIL draw object
            pil_image = Image.fromarray(self.preview_slice)
            if options.export_image_scale != 1:
                shape = np.array(
                    [self.preview_slice.shape[1], self.preview_slice.shape[0]]) * options.export_image_scale
                pil_image = pil_image.resize(shape.astype(int), Image.ANTIALIAS)
            draw = ImageDraw.Draw(pil_image)
            draw.pil_image = pil_image
            # init svg
            if svg:
                import svgwrite
                dwg = svgwrite.Drawing(path % (frame - start), profile='full',
                                       size=(self.preview_slice.shape[1], self.preview_slice.shape[0]))

            # draw marker on the image
            BroadCastEvent(self.window.modules, "drawToImage", draw, start_x - offset[0], start_y - offset[1],
                           options.export_marker_scale, options.export_image_scale, options.rotation)
            if svg:
                BroadCastEvent(self.window.modules, "drawToImageSvg", dwg, start_x - offset[0], start_y - offset[1],
                               options.export_marker_scale, options.export_image_scale, options.rotation)
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
            if svg:
                BroadCastEvent(self.window.modules, "drawToImage2Svg", dwg, start_x - offset[0], start_y - offset[1],
                               options.export_marker_scale, options.export_image_scale, options.rotation)
            # draw timestamp
            if self.time_drawing is not None:
                if options.export_custom_time:
                    text = str(datetime.timedelta(seconds=self.custom_time))
                    draw.text((self.time_drawing.x, self.time_drawing.y), text, self.time_drawing.color,
                              font=self.time_drawing.font)
                    self.custom_time += options.export_custom_time_delta
                else:
                    time = self.window.data_file.image.timestamp
                    if time is not None:
                        if frame == start and options.export_time_from_zero:
                            self.time_drawing.start = time
                        if self.time_drawing.start is not None:
                            text = formatTimedelta(time - self.time_drawing.start, options.export_timedelta_format)
                        else:
                            text = time.strftime(options.export_time_format)
                        draw.text((self.time_drawing.x, self.time_drawing.y), text, self.time_drawing.color,
                                  font=self.time_drawing.font)
            # add to video ...
            if svg:
                dwg.save()
            else:
                if self.cbType.currentIndex() == 0:
                    if writer is None:
                        writer = imageio.get_writer(path, **writer_params)
                    writer.append_data(np.array(pil_image))
                # ... or save image ...
                elif self.cbType.currentIndex() == 1:
                    pil_image.save(path % (frame - start))
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

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() == QtCore.Qt.Key_Escape:
            self.parent.ExporterWindow = None
            self.close()


class VideoExporter:
    data_file = None
    config = None

    def __init__(self, window: "ClickPointsWindow", modules: List[QtCore.QObject], config: None = None) -> None:
        # default settings and parameters
        self.window = window
        self.modules = modules
        self.ExporterWindow = None

        self.button = QtWidgets.QPushButton()
        self.button.setIcon(qta.icon('fa.film'))
        self.button.setToolTip("export images as video/image series")
        self.button.clicked.connect(self.showDialog)
        window.layoutButtons.addWidget(self.button)

    def closeDataFile(self) -> None:
        self.data_file = None
        self.config = None

        if self.ExporterWindow:
            self.ExporterWindow.close()

    def updateDataFile(self, data_file: DataFileExtended, new_database: bool) -> None:
        self.data_file = data_file
        self.config = data_file.getOptionAccess()

    def showDialog(self) -> None:
        if self.ExporterWindow:
            self.ExporterWindow.raise_()
            self.ExporterWindow.show()
        else:
            self.ExporterWindow = VideoExporterDialog(self, self.window, self.data_file, self.config, self.modules)
            self.ExporterWindow.show()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:

        # @key Z: Export Video
        if event.key() == QtCore.Qt.Key_Z:
            self.showDialog()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self.ExporterWindow:
            self.ExporterWindow.close()

    @staticmethod
    def file() -> str:
        return __file__
