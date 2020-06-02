#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Measure.py

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

from __future__ import print_function, division
import clickpoints
import json
import os
from qtpy import QtCore, QtGui, QtWidgets
from clickpoints.includes import QtShortCuts
from PIL import Image, ImageDraw, ImageFont
import matplotlib

try:
    import tifffile
    tifffile_loaded = True
except ImportError:
    tifffile_loaded = False


class ModuleScaleBar(QtWidgets.QWidget):

    def __init__(self, parent, parentItem):
        QtWidgets.QWidget.__init__(self, parent)
        self.parent = parent

        self.font = QtGui.QFont()
        self.font.setPointSize(16)

        self.pixtomu = 0
        self.scale = 1
        self.unit = u"µm"

        self.scalebar = QtWidgets.QGraphicsRectItem(0, 0, 1, 1, parentItem)
        self.scalebar.setBrush(QtGui.QBrush(QtGui.QColor("white")))
        self.scalebar.setPen(QtGui.QPen(QtGui.QColor("white")))
        self.scalebar.setPos(0, 0)
        self.scalebar_text = QtWidgets.QGraphicsTextItem("", parentItem)
        self.scalebar_text.setFont(self.font)
        self.scalebar_text.setDefaultTextColor(QtGui.QColor("white"))

    def setPixToMu(self, value):
        self.pixtomu = value
        self.updateBar()

    def setUnit(self, text):
        self.unit = text

    def setColor(self, color):
        self.scalebar.setBrush(QtGui.QBrush(QtGui.QColor(color)))
        self.scalebar.setPen(QtGui.QPen(QtGui.QColor(color)))
        self.scalebar_text.setDefaultTextColor(QtGui.QColor(color))
        self.color = color

    def zoomEvent(self, scale, pos):
        if self.pixtomu:
            self.scale = scale
            self.updateBar()

    def getBarParameters(self, scale):
        if self.parent.getOption("length") != 0:
            mu = self.parent.getOption("length")
            pixel = mu / self.pixtomu * self.scale
            return pixel, mu
        mu = 100 * self.pixtomu / scale
        values = [1, 5, 10, 25, 50, 75, 100, 150, 200, 250, 500, 1000, 1500, 2000, 2500, 5000, 10000]
        old_v = mu
        for v in values:
            if mu < v:
                mu = old_v
                break
            old_v = v
        pixel = mu / (self.pixtomu) * scale
        return pixel, mu

    def updateBar(self):
        pixel, mu = self.getBarParameters(self.scale)
        x, y = self.parent.getOption("xpos"), self.parent.getOption("ypos")
        if x > 0:
            self.scalebar.setRect(-x, -y-self.parent.getOption("width"), -pixel, self.parent.getOption("width"))
            self.scalebar_text.setPos(-pixel-x-25, - y - self.parent.getOption("width") - self.parent.getOption("fontsize")*2)
        else:
            self.scalebar.setRect(-x, -y - self.parent.getOption("width"), pixel, self.parent.getOption("width"))
            self.scalebar_text.setPos(- x - 25,
                                      - y - self.parent.getOption("width") - self.parent.getOption("fontsize") * 2)
        self.scalebar_text.setTextWidth(pixel+50)
        self.scalebar_text.setHtml(u"<center>%d&thinsp;%s</center>" % (mu, self.unit))

        self.font = QtGui.QFont()
        self.font.setPointSize(self.parent.getOption("fontsize"))
        self.scalebar_text.setFont(self.font)

    def drawToImage(self, image, start_x, start_y, scale, image_scale):
        pixel_height = self.parent.getOption("width")
        pixel_offset_x = self.parent.getOption("xpos")
        pixel_offset_y = self.parent.getOption("ypos")
        pixel_offset2 = 3
        font_size = int(round(self.parent.getOption("fontsize")*scale*4/3))  # the 4/3 appears to be a factor of "converting" screel dpi to image dpi

        pixel_width, size_in_um = self.getBarParameters(1)
        pixel_width *= image_scale
        color = tuple((matplotlib.colors.to_rgba_array(self.color)[0, :3]*255).astype("uint8"))

        if pixel_offset_x > 0:
            image.rectangle([image.pil_image.size[0] -pixel_offset_x - pixel_width, image.pil_image.size[1] -pixel_offset_y - pixel_height, image.pil_image.size[0] -pixel_offset_x, image.pil_image.size[1] -pixel_offset_y], color)
        else:
            image.rectangle([-pixel_offset_x,
                             image.pil_image.size[1] - pixel_offset_y - pixel_height,
                             -pixel_offset_x + pixel_width,
                             image.pil_image.size[1] - pixel_offset_y], color)
        if True:
            # get the font
            try:
                font = ImageFont.truetype("tahoma.ttf", font_size)
            except IOError:
                font = ImageFont.truetype(os.path.join(os.environ["CLICKPOINTS_ICON"], "FantasqueSansMono-Regular.ttf"), font_size)
            # width and height of text elements
            text = "%d" % size_in_um
            length_number = image.textsize(text, font=font)[0]
            length_space = 0.5*image.textsize(" ", font=font)[0] # here we emulate a half-sized whitespace
            length_unit = image.textsize(self.unit, font=font)[0]
            height_number = image.textsize(text+self.unit, font=font)[1]

            total_length = length_number + length_space + length_unit

            # find the position for the text to have it centered and bottom aligned
            if pixel_offset_x > 0:
                x = image.pil_image.size[0] - pixel_offset_x - pixel_width * 0.5 - total_length * 0.5
            else:
                x = - pixel_offset_x + pixel_width * 0.5 - total_length * 0.5
            y = image.pil_image.size[1] - pixel_offset_y - pixel_offset2 - pixel_height - height_number
            # draw the text for the number and the unit
            image.text((x, y), text, color, font=font)
            image.text((x+length_number+length_space, y), self.unit, color, font=font)

    def delete(self):
        self.scalebar.scene().removeItem(self.scalebar)
        self.scalebar_text.scene().removeItem(self.scalebar_text)


def get_meta(file):
    import tifffile
    import json
    from distutils.version import LooseVersion

    if LooseVersion(tifffile.__version__) > LooseVersion("0.13"):
        try:
            with tifffile.TiffFile(file) as tif:
                metadata = tif.shaped_metadata
                if metadata is None:
                    return {}
                return tif.shaped_metadata[0]
        except (ValueError, tifffile.tifffile.TiffFileError):  # invalid tiff file
            return {}
    else:
        try:
            with tifffile.TiffFile(file) as tif:
                try:
                    tif.shaped_metadata[0]
                except AttributeError:
                    try:
                        metadata = tif[0].image_description
                    except (TypeError, AttributeError):
                        return {}
                try:
                    return json.loads(metadata.decode('utf-8'))
                except (AttributeError, ValueError, KeyError):
                    return {}
        except (ValueError, tifffile.tifffile.TiffFileError):  # invalid tiff file
            return {}


class Addon(clickpoints.Addon):
    initialized = False

    def __init__(self, *args, **kwargs):
        clickpoints.Addon.__init__(self, *args, **kwargs)

        QtWidgets.QVBoxLayout(self)
        self.setWindowTitle("Measurement Tool - ClickPoints")

        self.db.setMarkerType("ruler", "#FFFF00", self.db.TYPE_Line)
        self.cp.reloadTypes()

        self.type = self.db.getMarkerType("ruler")
        self.cp.selectMarkerType(self.type)

        self.scaleBar = ModuleScaleBar(self, self.cp.getHUD("lower right"))

        self.addOption(key="pixelSize", display_name="Pixel Size", default=1, value_type="float", decimals=4,
                       tooltip="The size of a pixel.", unit="µm")
        self.addOption(key="magnification", display_name="Magnification", default=1, min=1, value_type="float",
                       tooltip="The magnification with which the image has been recorded.", unit="x")
        self.addOption(key="unit", display_name="Length Unit", default=u"µm", value_type="string",
                       tooltip="The unit for this size.")
        self.addOption(key="color", display_name="Color", default="#FFFFFF", value_type="color",
                       tooltip="The color of the scale bar and the text.")
        self.addOption(key="from_metadata", hidden=True, default=False, value_type="bool")

        self.addOption(key="fontsize", display_name="Fontsize", default=16, value_type="int",
                       tooltip="The size of the font for the description of the scalebar")
        self.addOption(key="length", display_name="Length", default=0, value_type="int", unit="µm",
                       tooltip="The length of the scalebar in µm. 0 for an automatically choosen length.")

        self.addOption(key="width", display_name="Width", default=3, value_type="int",
                       tooltip="The width of the scalebar in pixel.")
        self.addOption(key="xpos", display_name="X-Offset", default=20, value_type="int",
                       tooltip="The x offset of the scalebar in pixel.", min_value=-10000, max_value=10000)
        self.addOption(key="ypos", display_name="Y-Offset", default=15, value_type="int",
                       tooltip="The yoffset of the scalebar in pixel.")

        if self.db.image and self.db.image.path:
            self.initializeOptions()

        self.input_pixelsize = self.inputOption("pixelSize")
        self.input_magnification = self.inputOption("magnification")
        self.input_color = self.inputOption("color")
        self.input_fontsize = self.inputOption("fontsize")
        self.input_length = self.inputOption("length")
        self.input_width = self.inputOption("width")
        self.input_xpos = self.inputOption("xpos")
        self.input_ypos = self.inputOption("ypos")

        self.button = QtWidgets.QPushButton("test")
        self.layout().addWidget(self.button)

        self.button.clicked.connect(self.test)

    def test(self):
        self.db.setMaskType("bla", "#FF00FF", 3)
        self.cp.reloadMaskTypes()

    def initializeOptions(self):
        if not self.getOption("from_metadata"):
            meta = get_meta(os.path.join(self.db.image.path.path, self.db.image.filename))
            self.setOption("pixelSize", meta.get("PixelSize", 6.45))
            self.setOption("magnification", meta.get("Magnification", 1) * meta.get("Coupler", 1))
            self.setOption("from_metadata", True)
        self.optionsChanged()

        self.initialized = True

    def zoomEvent(self, scale, pos):
        if not self.initialized and self.db.image and self.db.image.path:
            self.initializeOptions()
        self.scaleBar.zoomEvent(scale, pos)

    def drawToImage2(self, image, start_x, start_y, scale, image_scale, rotation):
        self.scaleBar.drawToImage(image, start_x, start_y, scale, image_scale)

    def optionsChanged(self, key=None):
        self.scaleBar.setUnit(self.getOption("unit"))
        self.scaleBar.setPixToMu(self.getOption("pixelSize") / self.getOption("magnification"))
        self.scaleBar.setColor(self.getOption("color"))
        if self.getOption("xpos") < 0:
            self.scaleBar.scalebar.setParentItem(self.cp.getHUD("lower left"))
            self.scaleBar.scalebar_text.setParentItem(self.cp.getHUD("lower left"))
        else:
            self.scaleBar.scalebar.setParentItem(self.cp.getHUD("lower right"))
            self.scaleBar.scalebar_text.setParentItem(self.cp.getHUD("lower right"))

    def markerMoveEvent(self, marker):
        if not self.initialized:
            self.initializeOptions()
        if self.initialized and marker.type == self.type:
            marker.text = "%.2f %s" % (marker.length()*(self.getOption("pixelSize") / self.getOption("magnification")), self.getOption("unit"))
            marker.save()

    def run(self, *args, **kwargs):
        self.cp.selectMarkerType(self.type)

    def delete(self):
        self.scaleBar.delete()

    def buttonPressedEvent(self):
        self.show()
