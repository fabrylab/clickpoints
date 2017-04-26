#!/usr/bin/env python
# -*- coding: utf-8 -*-
# GrabPlotData.py

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
import os, sys
import clickpoints


def Remap(value, minmax1, minmax2):
    """ Map from range minmax1 to range minmax2 """
    length1 = minmax1[1]-minmax1[0]
    length2 = minmax2[1]-minmax2[0]
    if length1 == 0:
        return 0
    percentage = (value-minmax1[0])/length1
    return percentage*length2 + minmax2[0]


class Addon(clickpoints.Addon):
    def __init__(self, *args, **kwargs):
        clickpoints.Addon.__init__(self, *args, **kwargs)

        # Check if the marker types are present
        reload_types = False
        if not self.db.getMarkerType("x_axis"):
            self.db.setMarkerType("x_axis", [0, 200, 0], self.db.TYPE_Line, text="0, 1")
            reload_types = True
        if not self.db.getMarkerType("y_axis"):
            self.db.setMarkerType("y_axis", [200, 200, 0], self.db.TYPE_Line, text="0, 1")
            reload_types = True
        if not self.db.getMarkerType("data"):
            self.db.setMarkerType("data", [200, 0, 0], self.db.TYPE_Normal)
            reload_types = True
        if reload_types:
            self.cp.reloadTypes()

    def run(self, start_frame=0):
        # get the current image
        image = next(self.db.getImageIterator(start_frame))

        # try to load axis
        x_axis = self.db.getLines(image=image, type="x_axis")
        y_axis = self.db.getLines(image=image, type="y_axis")
        if len(x_axis) != 1 or len(y_axis) != 1:
            print("ERROR: Please mark exactly one line with type 'x_axis' and exactly one with 'y_axis'.\nFound %d x_axis and %d y_axis" % (len(x_axis), len(y_axis)))
            sys.exit(-1)
        x_axis = x_axis[0]
        y_axis = y_axis[0]

        # create remap functions for x and y axis
        remap_x = lambda x: Remap(x, [min(x_axis.x1, x_axis.x2), max(x_axis.x1, x_axis.x2)], [float(x) for x in x_axis.text.split(",")])
        remap_y = lambda y: Remap(y, [min(y_axis.y1, y_axis.y2), max(y_axis.y1, y_axis.y2)], [float(y) for y in y_axis.text.split(",")])

        # get all markers
        markers = self.db.getMarkers(image=image, type="data")
        # compose the output filename
        filename = os.path.splitext(image.filename)[0]+".txt"
        # iterate over all data markers
        with open(filename, "w") as fp:
            for data in markers:
                print(remap_x(data.x), remap_y(data.y))
                fp.write("%f %f\n" % (remap_x(data.x), remap_y(data.y)))
        # print success
        print("%d datepoints written to file \"%s\"" % (markers.count(), filename))
