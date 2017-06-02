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

try:
    import tifffile
    tifffile_loaded = True
except ImportError:
    tifffile_loaded = False


def get_meta(file):
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


class Addon(clickpoints.Addon):
    def __init__(self, *args, **kwargs):
        clickpoints.Addon.__init__(self, *args, **kwargs)

        meta = get_meta(self.db.image.filename)

        self.addOption(key="pixelSize", display_name="Pixel Size", default=meta.get("PixelSize", 6.45)/(meta.get("Magnification", 1)*meta.get("Coupler", 1)), value_type="float",
                       tooltip="The size of a pixel.")
        self.addOption(key="unit", display_name="Length Unit", default="µm", value_type="string",
                       tooltip="The unit for this size.")

        self.db.setMarkerType("ruler", "#FFFF00", self.db.TYPE_Line)
        self.cp.reloadTypes()

        self.type = self.db.getMarkerType("ruler")

    def MarkerMoved(self, marker):
        if marker.data.type == self.type:
            marker.data.text = "%.2f %s" % (marker.data.length()*self.getOption("pixelSize"), self.getOption("unit"))
            marker.data.save()
