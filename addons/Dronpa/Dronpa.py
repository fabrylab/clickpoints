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
from GetIntensities import getIntensities
from FitDiffusionConstants import fitDiffusionConstants
from matplotlib import pyplot as plt


class Addon(clickpoints.Addon):

    def __init__(self, *args, **kwargs):
        clickpoints.Addon.__init__(self, *args, **kwargs)

        self.addOption(key="delta_t", display_name="Delta t", default=2, value_type="int")
        self.addOption(key="color_channel", display_name="Color Channel", default=1, value_type="int")
        self.addOption(key="output_folder", display_name="Output Folder", default="output", value_type="string")

        # create a line type "connect"
        if not self.db.getMarkerType("connect"):
            self.db.setMarkerType("connect", [0, 255, 255], self.db.TYPE_Line)
            self.cp.reloadTypes()

        # prepare two figures
        plt.figure(0)
        plt.figure(1)

    def run(self, start_frame=0):
        getIntensities(self.db, self.getOption("delta_t"), self.getOption("color_channel"), self.getOption("output_folder"))
        fitDiffusionConstants(self.db, self.getOption("output_folder"))
