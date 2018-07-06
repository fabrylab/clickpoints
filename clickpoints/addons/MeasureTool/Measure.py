#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Track.py

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

from __future__ import print_function, division
import clickpoints
import json
import os
from qtpy import QtCore, QtGui, QtWidgets
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
        self.scalebar.setPos(-20, -20)
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
        self.scalebar.setRect(0, 0, -pixel, 5)
        self.scalebar_text.setPos(-pixel-20-25, -20-30)
        self.scalebar_text.setTextWidth(pixel+50)
        self.scalebar_text.setHtml(u"<center>%d&thinsp;%s</center>" % (mu, self.unit))

    def drawToImage(self, image, start_x, start_y, scale, image_scale):
        pixel_height = 8
        pixel_offset = 20
        pixel_offset2 = 4
        font_size = 32

        pixel_width, size_in_um = self.getBarParameters(1)
        color = tuple((matplotlib.colors.to_rgba_array(self.color)[0, :3]*255).astype("uint8"))

        image.rectangle([image.pil_image.size[0] -pixel_offset - pixel_width, image.pil_image.size[1] -pixel_offset - pixel_height, image.pil_image.size[0] -pixel_offset, image.pil_image.size[1] -pixel_offset], color)
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
            x = image.pil_image.size[0] - pixel_offset - pixel_width * 0.5 - total_length * 0.5
            y = image.pil_image.size[1] - pixel_offset - pixel_offset2 - pixel_height - height_number
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
        except ValueError:  # invalid tiff file
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
        except ValueError:  # invalid tiff file
            return {}


class Addon(clickpoints.Addon):
    initialized = False

    def __init__(self, *args, **kwargs):
        clickpoints.Addon.__init__(self, *args, **kwargs)

        self.db.setMarkerType("ruler", "#FFFF00", self.db.TYPE_Line)
        self.cp.reloadTypes()

        self.type = self.db.getMarkerType("ruler")
        self.cp.selectMarkerType(self.type)

        self.scaleBar = ModuleScaleBar(self, self.cp.getHUD("lower right"))

        if self.db.image and self.db.image.path:
            self.initializeOptions()

    def initializeOptions(self):
        meta = get_meta(os.path.join(self.db.image.path.path, self.db.image.filename))

        self.addOption(key="pixelSize", display_name="Pixel Size", default=meta.get("PixelSize", 6.45) / (
        meta.get("Magnification", 1) * meta.get("Coupler", 1)), value_type="float", decimals=4,
                       tooltip="The size of a pixel.")
        self.addOption(key="unit", display_name="Length Unit", default=u"µm", value_type="string",
                       tooltip="The unit for this size.")
        self.addOption(key="color", display_name="Color", default="#FFFFFF", value_type="color",
                       tooltip="The color of the scale bar and the text.")

        self.optionsChanged()

        self.initialized = True

    def zoomEvent(self, scale, pos):
        if not self.initialized and self.db.image and self.db.image.path:
            self.initializeOptions()
        self.scaleBar.zoomEvent(scale, pos)

    def drawToImage2(self, image, start_x, start_y, scale, image_scale, rotation):
        self.scaleBar.drawToImage(image, start_x, start_y, scale, image_scale)

    def optionsChanged(self):
        self.scaleBar.setUnit(self.getOption("unit"))
        self.scaleBar.setPixToMu(self.getOption("pixelSize"))
        self.scaleBar.setColor(self.getOption("color"))

    def markerMoveEvent(self, marker):
        if not self.initialized:
            self.initializeOptions()
        if self.initialized and marker.type == self.type:
            marker.text = "%.2f %s" % (marker.length()*self.getOption("pixelSize"), self.getOption("unit"))
            marker.save()

    def run(self, *args, **kwargs):
        self.cp.selectMarkerType(self.type)

    def delete(self):
        self.scaleBar.delete()
