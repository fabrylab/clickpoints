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
from clickpoints.includes.QtShortCuts import AddQLineEdit, AddQComboBox
import qtawesome as qta


# define default dicts, enables .access on dicts
class dotdict(dict):
    def __getattr__(self, attr):
        if attr.startswith('__'):
            raise AttributeError
        return self.get(attr, None)

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

# convert between focal length + sensor dimension & fov

def utilFOVToSensor(fov, f):
    return 2 * f * np.tan(np.deg2rad(fov)/2)

def utilSensorToFOV(d,f ):
    return np.rad2deg(2 * np.arctan(d / (2*f)))


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

        """ Default entries for Cameras """
        #region
        # atkaSPOT
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
        Canon_D10.img_w_px = 4000
        Canon_D10.img_h_px = 3000

        # add all cameras to one dictionary
        cam_dict = dotdict()
        cam_dict['MobotixM12_Day'] = MobotixM12_Day
        cam_dict['MobotixM12_Night'] = MobotixM12_Night
        cam_dict['CampbellMpx5'] = CampbellMpx5
        cam_dict['GE4000C_400mm'] = GE4000C_400mm
        cam_dict['GE4000C_400mm_crop05'] = GE4000C_400mm_crop05
        cam_dict['Panasonic_DMC_G5'] = Panasonic_DMC_G5
        cam_dict['Canon_D10'] = Canon_D10
        # endregion

        camera_json = os.path.join(os.path.dirname(__file__),'camera.json')
        if not os.path.exists(camera_json):
            print("DistanceMeasure Addon: no default camera.json found - creating ...")
            with open(camera_json, 'w') as fd:
                json.dump(cam_dict, fd, indent=4, sort_keys=True)
        else:
            # read from json file
            print("DistanceMeasure Addon: loading camera.json")
            with open(camera_json, 'r') as fd:
                self.cam_dict = json.load(fd)

        ## Widget
        # set the title and layout
        self.setWindowTitle("DistnaceMeasure - Config")
        self.setWindowIcon(qta.icon("fa.map-signs"))
        # self.setMinimumWidth(400)
        # self.setMinimumHeight(200)
        self.layout = QtWidgets.QVBoxLayout(self)

        ## camera region
        # use a groupbox for camera parameters
        self.camera_groupbox = QtWidgets.QGroupBox("Camera")
        self.layout.addWidget(self.camera_groupbox)

        # add a grid layout for elements
        self.camera_layout = QtWidgets.QVBoxLayout()
        self.camera_groupbox.setLayout(self.camera_layout)

        # combo box to select camera models stored in camera.json
        self.cameraComboBox = AddQComboBox(self.camera_layout,'Model:', values=cam_dict.keys())
        self.cameraComboBox.currentIndexChanged.connect(self.insertCameraParameters)
        # self.cameraComboBox.addItems(cam_dict.keys())

        # self.camera_layout.addWidget(QtWidgets.QLabel('Model:'))
        # self.camera_layout.addWidget(self.cameraComboBox,0,1)

        self.leFocallength = AddQLineEdit(self.camera_layout,"f (mm):", editwidth=120)
        self.leImage_width = AddQLineEdit(self.camera_layout,"image width (px):", editwidth=120)
        self.leImage_height = AddQLineEdit(self.camera_layout,"image height (px):", editwidth=120)
        self.leSensor_width = AddQLineEdit(self.camera_layout,"sensor width (mm):", editwidth=120)
        self.leSensor_height = AddQLineEdit(self.camera_layout,"sensor width (mm):", editwidth=120)
        self.leFOV_horizontal = AddQLineEdit(self.camera_layout,"FOV horizontal (deg):", editwidth=120)
        self.leFOV_vertical = AddQLineEdit(self.camera_layout,"FOV vertical (deg):", editwidth=120)



        ## position region
        self.position_groupbox = QtWidgets.QGroupBox("Position")
        self.layout.addWidget(self.position_groupbox)
        # add a grid layout for elements
        self.position_layout = QtWidgets.QVBoxLayout()
        self.position_groupbox.setLayout(self.position_layout)

        self.leCamElevation = AddQLineEdit(self.position_layout,"camera elevation (m):", editwidth=120,value='25')
        self.lePlaneElevation = AddQLineEdit(self.position_layout,"plane elevation (m):", editwidth=120, value='0')
        self.leCamLat = AddQLineEdit(self.position_layout,"camera latitude:", editwidth=120)
        self.leCamLon = AddQLineEdit(self.position_layout,"camera longitude:", editwidth=120)


        self.insertCameraParameters()


        self.pushbutton_ok = QtWidgets.QPushButton("Ok")
        self.layout.addWidget(self.pushbutton_ok)
        self.pushbutton_ok.clicked.connect(self.run)



    def insertCameraParameters(self):
        """
        insert camera parameters from camera.json into gui
        """

        self.selected_cam_name = self.cameraComboBox.itemText(self.cameraComboBox.currentIndex())
        print("Selected Cam:", self.selected_cam_name)

        cam_by_dict = dotdict(self.cam_dict[self.selected_cam_name])

        def getNumber(input,format):
            try:
                return (format % input)
            except TypeError:
                return "None"

        # set cam parameters
        self.leFocallength.setText("%.2f" % cam_by_dict['focallength_mm'])
        self.leImage_width.setText("%d" % cam_by_dict['img_w_px'])
        self.leImage_height.setText("%d" % cam_by_dict['img_h_px'])
        self.leSensor_width.setText(getNumber(cam_by_dict['sensor_w_mm'],"%.2f"))
        self.leSensor_height.setText(getNumber(cam_by_dict['sensor_h_mm'],"%.2f"))
        self.leFOV_horizontal.setText(getNumber(cam_by_dict['fov_h_deg'],"%.2f"))
        self.leFOV_vertical.setText(getNumber(cam_by_dict['fov_v_deg'],"%.2f"))



        self.updateCameraParameters()


    def calcSensorDimensionsFromFOV(self):
        self.cam.sensor_w_mm = utilFOVToSensor(self.cam.fov_h_deg,self.cam.focallength_mm)
        self.cam.sensor_h_mm = utilFOVToSensor(self.cam.fov_v_deg,self.cam.focallength_mm)


    def updateCameraParameters(self):
        """
        update camera dictionary for calculation - uses potentially user modified data from gui
        """

        def getFloat(input):
            try:
                return float(input)
            except:
                return None

        # update current cam parameters
        self.cam = dotdict()
        self.cam.fov_h_deg = getFloat(self.leFOV_horizontal.text())
        self.cam.fov_v_deg = getFloat(self.leFOV_vertical.text())
        self.cam.sensor_w_mm = getFloat(self.leSensor_width.text())
        self.cam.sensor_h_mm = getFloat(self.leSensor_height.text())
        self.cam.focallength_mm = getFloat(self.leFocallength.text())
        self.cam.img_w_px = getFloat(self.leImage_width.text())
        self.cam.img_h_px = getFloat(self.leImage_height.text())

        if self.cam.sensor_h_mm is None or self.cam.sensor_w_mm is None:
            self.calcSensorDimensionsFromFOV()

        print("Camera:")
        print(json.dumps(self.cam,indent=4,sort_keys=True))

        self.position = dotdict()
        self.position.cam_elevation = getFloat(self.leCamElevation.text())
        self.position.plane_elevation = getFloat(self.lePlaneElevation.text())

        print("Position:")
        print(json.dumps(self.position,indent=4,sort_keys=True))


    def run(self, start_frame=0):

        self.frame = start_frame

        self.updateCameraParameters()

        # try to load marker
        horizon = self.db.getMarkers(type="horizon", frame=start_frame)

        if horizon.count() < 2:
            print("ERROR: To few horizon markers placed - please add at least to horizon markers")
            return

        # # get image parameters
        # image = self.db.getImage(frame=start_frame)
        # data = image.data
        # im_height, im_width, channels = data.shape

        self.camera = ct.CameraTransform(self.cam.focallength_mm, [self.cam.sensor_w_mm, self.cam.sensor_h_mm],[self.cam.img_w_px, self.cam.sensor_h_mm])

        self.camera.fixHorizon(horizon)

        if self.position.cam_elevation:
            self.camera.fixHeight(self.position.cam_elevation)

        self.fit_params = dotdict()
        self.fit_params.horizon_points = horizon.count()
        self.fit_params.cam_elevation = self.camera.height
        self.fit_params.cam_tilt = np.round(self.camera.tilt,2)
        self.fit_params.dist_to_horizon = np.round(self.camera.distanceToHorizon(),2)

        print("Fit Parameter:")
        print(json.dumps(self.fit_params, indent=4, sort_keys=True))

        self.updateAllMarker()

    def updateAllMarker(self):

        # get distance to cam markers and calculate distance
        dist2cam = self.db.getMarkers(type="distance_to_cam", frame=self.frame)
        for marker in dist2cam:
            self.updateDistMarker(marker)

        # get line markers and calculate distance in between
        dist2pt = self.db.getLines(type="distance_between", frame=self.frame)
        for line in dist2pt:
            self.updateDistLine(line)

        self.cp.reloadMarker(frame=self.frame)

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
        pos1 = self.camera.transCamToWorld(pts[0], Z=self.position.plane_elevation).T
        pos2 = self.camera.transCamToWorld(pts[1], Z=self.position.plane_elevation).T
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

