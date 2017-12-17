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
import os
import json
from qtpy import QtCore, QtGui, QtWidgets
import qtawesome as qta

class Addon(clickpoints.Addon):
    camera = None
    cam_dict = None

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

        # get json files if available else create defaults
        # define default dicts
        # enables .access on dicts
        class dotdict(dict):
            def __getattr__(self, attr):
                if attr.startswith('__'):
                    raise AttributeError
                return self.get(attr, None)

            __setattr__ = dict.__setitem__
            __delattr__ = dict.__delitem__

        """ Default entries for Cameras """
        #region
        ## atkaSPOT
        # Mobotic D12 Day as used in atkaSPOT
        MobotixM12_Day = dotdict()
        MobotixM12_Day.fov_h_deg = 45
        MobotixM12_Day.fov_v_deg = 34
        MobotixM12_Day.sensor_w_mm = None
        MobotixM12_Day.sensor_h_mm = None
        MobotixM12_Day.focallength_mm = 22
        MobotixM12_Day.img_w_px = 2048
        MobotixM12_Day.img_h_px = 1536

        MobotixM12_Night = dotdict()
        MobotixM12_Night.fov_h_deg = 45
        MobotixM12_Night.fov_v_deg = 34
        MobotixM12_Night.sensor_w_mm = None
        MobotixM12_Night.sensor_h_mm = None
        MobotixM12_Night.focallength_mm = 22
        MobotixM12_Night.img_w_px = 2048
        MobotixM12_Night.img_h_px = 1536

        CampbellMpx5 = dotdict()
        CampbellMpx5.fov_h_deg = 80
        CampbellMpx5.fov_v_deg = 65
        CampbellMpx5.sensor_w_mm = None
        CampbellMpx5.sensor_h_mm = None
        CampbellMpx5.focallength_mm = 12
        CampbellMpx5.img_w_px = 2470
        CampbellMpx5.img_h_px = 1800

        GE4000C_400mm = dotdict()
        GE4000C_400mm.fov_h_deg = None
        GE4000C_400mm.fov_v_deg = None
        GE4000C_400mm.sensor_w_mm = 36
        GE4000C_400mm.sensor_h_mm = 24
        GE4000C_400mm.focallength_mm = 400
        GE4000C_400mm.img_w_px = 4008
        GE4000C_400mm.img_h_px = 2672

        GE4000C_400mm_crop05 = dotdict()
        GE4000C_400mm_crop05.fov_h_deg = None
        GE4000C_400mm_crop05.fov_v_deg = None
        GE4000C_400mm_crop05.sensor_w_mm = 36
        GE4000C_400mm_crop05.sensor_h_mm = 24
        GE4000C_400mm_crop05.focallength_mm = 400
        GE4000C_400mm_crop05.img_w_px = 2004
        GE4000C_400mm_crop05.img_h_px = 1336

        Panasonic_DMC_G5 = dotdict()
        Panasonic_DMC_G5.fov_h_deg = None
        Panasonic_DMC_G5.fov_v_deg = None
        Panasonic_DMC_G5.sensor_w_mm = 17.3
        Panasonic_DMC_G5.sensor_h_mm = 13.0
        Panasonic_DMC_G5.focallength_mm = 14
        Panasonic_DMC_G5.img_w_px = 4608
        Panasonic_DMC_G5.img_h_px = 3456

        Canon_D10 = dotdict()
        Canon_D10.fov_h_deg = None
        Canon_D10.fov_v_deg = None
        Canon_D10.sensor_w_mm = 6.17
        Canon_D10.sensor_h_mm = 4.55
        Canon_D10.focallength_mm = 6.2
        # TODO: add values here!
        Canon_D10.img_w_px = 0
        Canon_D10.img_h_px = 0

        # add all cameras to one dictionary
        cam_dict = dotdict()
        cam_dict['MobotixM12_Day'] = MobotixM12_Day
        cam_dict['MobotixM12_Night'] = MobotixM12_Night
        cam_dict['CampbellMpx5'] = CampbellMpx5
        cam_dict['GE4000C_4000mm'] = GE4000C_400mm
        cam_dict['GE4000C_4000mm_crop05'] = GE4000C_400mm_crop05
        cam_dict['Panasonic_DMC_G5'] = Panasonic_DMC_G5
        cam_dict['Canon_D10'] = Canon_D10
        # endregion

        if not os.path.exists(r"camera.json"):
            print("DistanceMeasure Addon: no default camera.json found - creating ...")
            with open(r"camera.json", 'w') as fd:
                json.dump(cam_dict, fd, indent=4, sort_keys=True)
        else:
            # read from json file
            print("DistanceMeasure Addon: loading camera.json")
            with open(r"camera.json", 'r') as fd:
                self.cam_dict = json.load(fd)

        # Widget
        # set the title and layout
        self.setWindowTitle("DistnaceMeasure - Config")
        self.setWindowIcon(qta.icon("fa.map-signs"))
        self.setMinimumWidth(400)
        self.setMinimumHeight(200)
        self.layout = QtWidgets.QVBoxLayout(self)

        # camera region
        self.camera_layout = QtWidgets.QGridLayout()
        self.layout.addLayout(self.camera_layout)


        self.cameraComboBox = QtWidgets.QComboBox()
        self.cameraComboBox.addItems(cam_dict.keys())

        self.camera_layout.addWidget(QtWidgets.QLabel('Camera:'),0,0)
        self.camera_layout.addWidget(self.cameraComboBox,0,1)


        self.pushbutton_ok = QtWidgets.QPushButton("Ok")
        self.layout.addWidget(self.pushbutton_ok)


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


    def buttonPressedEvent(self):
        # show the addon window when the button in ClickPoints is pressed
        self.show()

        try:
            self.run()
        except:
            pass

