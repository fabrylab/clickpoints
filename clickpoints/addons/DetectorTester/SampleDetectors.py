#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SampleDetectors.py

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

from PenguTrack.Detectors import Detector, detection_parameters
from PenguTrack.Parameters import ParameterList, Parameter
from skimage.measure import label, regionprops
import numpy as np
import pandas as pd


class DetectorThreshold(Detector):
    """
    This Class describes the abstract function of a detector in the pengu-track package.
    It is only meant for subclassing.
    """

    def __init__(self, threshold=128):
        super(Detector, self).__init__()

        # define the parameters of the detector
        self.ParameterList = ParameterList(Parameter("threshold", threshold, range=[0, 255], desc="the threshold"),
                                           Parameter("invert", False),
                                           Parameter("mode", "test", values=["bla", "blub", "test", "heho"]))

    @detection_parameters(image=dict(frame=0))
    def detect(self, image):
        # threshold the image
        mask = (image > self.ParameterList["threshold"]).astype("uint8")
        # invert it
        if self.ParameterList["invert"]:
            mask = 1 - mask
        # find all regions
        props = regionprops(label(mask))
        # get the positions of the regions
        positions = pd.DataFrame([(prop.centroid[1] + 0.5, prop.centroid[0] + 0.5) for prop in props], columns=["PositionX", "PositionY"])
        # return positions and mask
        return positions, mask


class DetectorRandom(Detector):
    """
    This Class describes the abstract function of a detector in the pengu-track package.
    It is only meant for subclassing.
    """

    def __init__(self):
        super(Detector, self).__init__()

        self.ParameterList = ParameterList(Parameter("count", 128, min=0, max=255))

    @detection_parameters(image=dict(frame=0))
    def detect(self, image):
        df = pd.DataFrame(np.random.rand(self.ParameterList["count"], 2) * np.array(image.shape)[::-1], columns=["PositionX", "PositionY"])
        return df, None
