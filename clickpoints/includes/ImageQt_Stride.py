#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ImageQt_Stride.py

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

from PIL import Image
from PIL._util import isPath
import sys

if 'PyQt4.QtGui' not in sys.modules:
    try:
        from PyQt5.QtGui import QImage, qRgba
    except:
        try:
            from PyQt4.QtGui import QImage, qRgba
        except:
            from PySide.QtGui import QImage, qRgba

else: #PyQt4 is used
    from PyQt4.QtGui import QImage, qRgba

##
# (Internal) Turns an RGB color into a Qt compatible color integer.

def rgb(r, g, b, a=255):
    # use qRgb to pack the colors, and then turn the resulting long
    # into a negative integer with the same bitpattern.
    return (qRgba(r, g, b, a) & 0xffffffff)


##
# An PIL image wrapper for Qt.  This is a subclass of PyQt4's QImage
# class.
#
# @param im A PIL Image object, or a file name (given either as Python
#     string or a PyQt string object).

class ImageQt(QImage):

    def __init__(self, im):

        data = None
        colortable = None
        stride = None

        # handle filename, if given instead of image name
        if hasattr(im, "toUtf8"):
            # FIXME - is this really the best way to do this?
            im = unicode(im.toUtf8(), "utf-8")
        if isPath(im):
            im = Image.open(im)

        if im.mode == "1":
            format = QImage.Format_Mono
        elif im.mode == "L":
            format = QImage.Format_Indexed8
            colortable = []
            for i in range(256):
                colortable.append(rgb(i, i, i))
            stride = im.size[0]
        elif im.mode == "P":
            format = QImage.Format_Indexed8
            colortable = []
            palette = im.getpalette()
            for i in range(0, len(palette), 3):
                colortable.append(rgb(*palette[i:i+3]))
            stride = im.size[0]
        elif im.mode == "RGB":
            data = im.tobytes("raw", "BGRX")
            format = QImage.Format_RGB32
        elif im.mode == "RGBA":
            try:
                data = im.tobytes("raw", "BGRA")
            except SystemError:
                # workaround for earlier versions
                r, g, b, a = im.split()
                im = Image.merge("RGBA", (b, g, r, a))
            format = QImage.Format_ARGB32
        else:
            raise ValueError("unsupported image mode %r" % im.mode)

        # must keep a reference, or Qt will crash!
        self.__data = data or im.tobytes()

        if stride is not None:
            QImage.__init__(self, self.__data, im.size[0], im.size[1], stride, format)
        else:
            QImage.__init__(self, self.__data, im.size[0], im.size[1], format)
        if colortable:
            self.setColorTable(colortable)
