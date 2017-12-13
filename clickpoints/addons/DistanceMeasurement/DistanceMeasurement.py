#!/usr/bin/env python
# -*- coding: utf-8 -*-
# DriftCorrection.py

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
import numpy as np
import sys
import clickpoints
import CameraTransform as ct

class Addon(clickpoints.Addon):
    camera = None

    def __init__(self, *args, **kwargs):
        clickpoints.Addon.__init__(self, *args, **kwargs)

        # Check if the marker type is present
        if not self.db.getMarkerType("horizon"):
            self.db.setMarkerType("horizon", [0, 255, 255], self.db.TYPE_Normal)
            self.cp.reloadTypes()

        if not self.db.getMarkerType("distance_to_cam"):
            self.db.setMarkerType("distance_to_cam", [255, 255, 0], self.db.TYPE_Normal)
            self.cp.reloadTypes()

        if not self.db.getMarkerType("distance_between"):
            self.db.setMarkerType("distance_between", [255, 0, 255], self.db.TYPE_Line)
            self.cp.reloadTypes()


    def run(self, start_frame=0):

        # try to load marker
        horizon = self.db.getMarkers(type="horizon", frame=start_frame)
        print("Horizon marker count:", horizon.count())

        if horizon.count() < 2:
            print("ERROR: To few horizon markers placed - please add at least to horizon markers")
            sys.exit(-1)

        # get image parameters
        image = self.db.getImage(frame=start_frame)
        data = image.data
        im_height, im_width, channels = data.shape
        print("current image dims:", im_height, im_width, channels)

        # set camera parameter
        image_size = data.shape[0:2][::-1]
        F = 14
        sensor_size = [17.3, 9.731]
        cam_height = 27.5

        self.camera = ct.CameraTransform(F, sensor_size, image_size)
        self.camera.fixHorizon(horizon)
        self.camera.fixHeight(cam_height)

        # get distance to cam markers and calculate distance
        dist2cam = self.db.getMarkers(type="distance_to_cam", frame=start_frame)
        print("nr points:", dist2cam.count())

        for marker in dist2cam:
            self.updateDistMarker(marker)

        # get line markers and calculate distance in between
        dist2pt = self.db.getLines(type="distance_between", frame=start_frame)
        print("nr points:", dist2pt.count())
        for line in dist2pt:
            self.updateDistLine(line)

    def updateDistMarker(self,marker):
        """
        Update distance to observer indicated by marker
        """
        pos = self.camera.transCamToWorld(np.array([marker.x, marker.y]), Z=0).T

        marker.text = "%.2fm" % np.sqrt(pos[0] ** 2 + pos[1] ** 2)
        marker.save()

    def updateDistLine(self,line):
        """
        Update distance indicated by an line marker
        """
        pts = np.round(np.array([line.getPos1(), line.getPos2()]),0)

        #TODO: Why doesnt this work when i supply the same point twice in an array?
        pos1 = self.camera.transCamToWorld(pts[0], Z=0).T
        pos2 = self.camera.transCamToWorld(pts[1], Z=0).T
        dist = np.sqrt(np.sum(((pos1 - pos2)**2)))

        line.text = "%.2fm" % dist
        line.save()

    def markerMoveEvent(self, marker):
        """
        On moving a marker - update the text information
        """

        if marker.type.name == 'distance_to_cam':
            self.updateDistMarker(marker)

        if marker.type.name == 'distance_between':
            self.updateDistLine(marker)


    def markerAddEvent(self, marker):
        """
        On adding a marker - calculate values
        """
        if marker.type.name == 'distance_to_cam':
            self.updateDistMarker(marker)

        if marker.type.name == 'distance_between':
            self.updateDistLine(marker)




