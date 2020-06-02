#!/usr/bin/env python
# -*- coding: utf-8 -*-
# InfoHud.py

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

import json
import os
import re
from typing import Any

from PIL import Image
from PIL.ExifTags import TAGS
from qtpy import QtCore, QtGui, QtWidgets

from clickpoints.includes.Database import DataFileExtended
from clickpoints.includes.Tools import BoxGrabber

try:
    import tifffile

    tifffile_loaded = True
except ImportError:
    tifffile_loaded = False

import string


class PartialFormatter(string.Formatter):
    def __init__(self, missing: str = '~', bad_fmt: str = '!!'):
        self.missing, self.bad_fmt = missing, bad_fmt

    def get_field(self, field_name: str, args: list, kwargs: dict) -> Any:
        # Handle a key not found
        try:
            val = super(PartialFormatter, self).get_field(field_name, args, kwargs)
            # Python 3, 'super().get_field(field_name, args, kwargs)' works
        except (KeyError, AttributeError):
            val = None, field_name
        return val

    def format_field(self, value: str, spec: str) -> str:
        # handle an invalid format
        if value is None: return self.missing
        try:
            return super(PartialFormatter, self).format_field(value, spec)
        except ValueError:
            if self.bad_fmt is not None:
                return self.bad_fmt
            else:
                raise


def get_exif(file: str) -> dict:
    if not file.lower().endswith((".jpg", ".jpeg")):
        return {}
    ret = {}
    i = Image.open(file)
    info = i._getexif()
    if info:
        for tag, value in info.items():
            decoded = TAGS.get(tag, tag)
            ret[decoded] = value
    return ret


def get_meta(file: str) -> dict:
    if not file.lower().endswith((".tif", ".tiff")):
        return {}
    if not tifffile_loaded:
        return {}
    with tifffile.TiffFile(file) as tif:
        try:
            metadata = tif[0].image_description
        except AttributeError:
            return {}
        return json.loads(metadata.decode('utf-8'))


class InfoHud(QtWidgets.QGraphicsRectItem):
    data_file = None
    config = None

    def __init__(self, parent_hud: QtWidgets.QGraphicsPathItem, window: "ClickPointsWindow") -> None:
        QtWidgets.QGraphicsRectItem.__init__(self, parent_hud)

        self.window = window
        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))

        self.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 128)))
        self.setPos(20, -140)
        self.setZValue(19)

        self.font = QtGui.QFont()
        self.font.setPointSize(12)
        self.font.setStyleHint(QtGui.QFont.Monospace)
        self.font.setFixedPitch(True)

        self.text = QtWidgets.QGraphicsSimpleTextItem(self)
        self.text.setFont(self.font)
        self.text.setBrush(QtGui.QBrush(QtGui.QColor("white")))
        self.text.setZValue(10)
        self.text.setPos(5, 10)

        self.setRect(QtCore.QRectF(0, 0, 110, 110))
        BoxGrabber(self)
        self.dragged = False

        self.closeDataFile()

    def closeDataFile(self) -> None:
        self.data_file = None
        self.config = None

        self.setVisible(False)
        self.hidden = True

    def updateDataFile(self, data_file: DataFileExtended, new_database: bool) -> None:
        self.data_file = data_file
        self.config = data_file.getOptionAccess()

        if self.config.info_hud_string != "":
            self.setVisible(True)
            self.hidden = False
            self.ToggleInterfaceEvent(self.hidden)

    def imageLoadedEvent(self, filename: str = "", frame_number: int = 0) -> None:
        if not self.data_file.getOption("info_hud_string") == "@script" and self.data_file.getOption(
                "info_hud_string").strip():
            image = self.window.data_file.image
            file = os.path.join(image.path.path, image.filename)
            regex = re.match(self.data_file.getOption("filename_data_regex"), file)
            if regex:
                regex = regex.groupdict()
            else:
                regex = dict()
            values = dict(exif=get_exif(file), regex=regex, meta=get_meta(file))
            fmt = PartialFormatter()
            text = fmt.format(self.data_file.getOption("info_hud_string"), **values)
            text = text.replace("\\n", "\n")
            self.text.setText(text)
            rect = self.text.boundingRect()
            rect.setWidth(rect.width() + 10)
            rect.setHeight(rect.height() + 10)
            self.setRect(rect)

    def optionsChanged(self, key) -> None:
        if not self.hidden and self.data_file.getOption("info_hud_string") == "":
            self.ToggleInterfaceEvent()
        elif self.hidden and self.data_file.getOption("info_hud_string") != "":
            self.ToggleInterfaceEvent()

    def ToggleInterfaceEvent(self, hidden: bool = None) -> None:
        if hidden is None:
            # invert hidden status
            self.hidden = not self.hidden
        else:
            self.hidden = hidden
        if self.config is not None and self.config.info_hud_string == "":
            self.hidden = True
        self.setVisible(not self.hidden)
        if self.config is not None:
            self.config.infohud_interface_hidden = self.hidden

    def updateHUD(self, info_string: str) -> None:
        fmt = PartialFormatter()
        self.text.setText(fmt.format(info_string))
        rect = self.text.boundingRect()
        rect.setWidth(rect.width() + 10)
        rect.setHeight(rect.height() + 10)
        self.setRect(rect)

    @staticmethod
    def file() -> str:
        return __file__
