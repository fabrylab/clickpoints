#!/usr/bin/env python
# -*- coding: utf-8 -*-
# DistanceMeasurement.py

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

from __future__ import division, print_function
import numpy as np
import sys
import clickpoints
import cameratransform as ct
import os
import json
from qtpy import QtCore, QtGui, QtWidgets
from clickpoints.includes.QtShortCuts import AddQLineEdit, AddQComboBox, AddQCheckBox, AddQOpenFileChoose, AddQSpinBox
import qtawesome as qta
import matplotlibwidget
from skimage.measure import label, regionprops
import re

UNITS = {"mm": 1e-3, "cm":1e-2, "m":1, "km":1e3}
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


def getNumber(input, format):
    try:
        return (format % input)
    except TypeError:
        return "None"

def getFloat(input):
    try:
        return float(input)
    except:
        return None

def getInteger(input):
    try:
        return int(input)
    except:
        return None


class Addon(clickpoints.Addon):
    camera = None
    cam_dict = None
    initialized = False

    def __init__(self, *args, **kwargs):
        clickpoints.Addon.__init__(self, *args, **kwargs)

        # Check if the marker type is present
        if not self.db.getMarkerType("DM_horizon"):
            self.db.setMarkerType("DM_horizon", [0, 255, 255], self.db.TYPE_Normal)
            self.cp.reloadTypes()

        if not self.db.getMarkerType("DM_to_cam"):
            self.db.setMarkerType("DM_to_cam", [255, 255, 0], self.db.TYPE_Normal)
            self.cp.reloadTypes()

        if not self.db.getMarkerType("DM_between"):
            self.db.setMarkerType("DM_between", [255, 0, 255], self.db.TYPE_Line)
            self.cp.reloadTypes()

        if not self.db.getMarkerType("DM_area"):
            self.db.setMarkerType("DM_area", [0, 255, 0], self.db.TYPE_Normal)
            self.cp.reloadTypes()

        if not self.db.getMarkerType("DM_scalebox"):
            self.db.setMarkerType("DM_scalebox", [0, 255, 255], self.db.TYPE_Normal)
            self.cp.reloadTypes()

        # TODO: move to parameter
        self.scalebox_dim = 10 # in meter
        self.scalebox_dict = dict()

        # Check if mask type is present
        if not self.db.getMaskType("area"):
            self.db.setMaskType("area", color='#00FF00')
            self.cp.reloadMaskTypes()

        # store options
        self.addOption(key='DM_last_camera', default=None, hidden=True, value_type='int')
        self.addOption(key='DM_focallength_mm', default=None, hidden=True, value_type='float')
        self.addOption(key='DM_fov_h_deg', default=None, hidden=True, value_type='float')
        self.addOption(key='DM_fov_v_deg', default=None, hidden=True, value_type='float')
        self.addOption(key='DM_sensor_w_mm', default=None, hidden=True, value_type='float')
        self.addOption(key='DM_sensor_h_mm', default=None, hidden=True, value_type='float')
        self.addOption(key='DM_img_w_px', default=None, hidden=True, value_type='int')
        self.addOption(key='DM_img_h_px', default=None, hidden=True, value_type='int')
        self.addOption(key='DM_offset_x_px', default=None, hidden=True, value_type='float')
        self.addOption(key='DM_offset_y_px', default=None, hidden=True, value_type='float')

        self.addOption(key='DM_cam_elevation', default=20, hidden=True, value_type='float')
        self.addOption(key='DM_plane_elevation', default=0, hidden=True, value_type='float')


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
        self.setWindowTitle("Distance - Config")
        self.setWindowIcon(qta.icon("fa.map-signs"))
        # self.setMinimumWidth(400)
        # self.setMinimumHeight(200)
        self.layout = QtWidgets.QGridLayout(self)

        ## camera region
        # use a groupbox for camera parameters
        self.camera_groupbox = QtWidgets.QGroupBox("Camera")
        self.camera_groupbox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))
        self.layout.addWidget(self.camera_groupbox,0,0)

        # add a grid layout for elements
        self.camera_layout = QtWidgets.QVBoxLayout()
        self.camera_groupbox.setLayout(self.camera_layout)

        # combo box to select camera models stored in camera.json
        self.cameraComboBox = AddQComboBox(self.camera_layout,'Model:', values=cam_dict.keys())
        self.cameraComboBox.currentIndexChanged.connect(self.getCameraParametersByJson)

        self.openFile = AddQOpenFileChoose(self.camera_layout, "Input", "", file_type="*.ct")
        self.openFile.textChanged.connect(self.getCameraParametersByCT)

        # self.cameraButton = QtWidgets.QPushButton('Load Cam')
        # self.cameraButton.clicked.connect(self.loadCamerFromFile)
        # self.camera_layout.addWidget(self.cameraButton)

        # self.cameraComboBox.setCurrentIndex(5)
        # self.cameraComboBox.addItems(cam_dict.keys())


        self.cbProjection = AddQComboBox(self.camera_layout, "Camera Projection:", values=["Rectilinear", "Cylindrical", "Equirectangular"])

        self.leFocallength = AddQLineEdit(self.camera_layout,"f (mm):", editwidth=120)
        self.leImage_width = AddQLineEdit(self.camera_layout,"image width (px):", editwidth=120)
        self.leImage_height = AddQLineEdit(self.camera_layout,"image height (px):", editwidth=120)
        self.leSensor_width = AddQLineEdit(self.camera_layout,"sensor width (mm):", editwidth=120)
        self.leSensor_height = AddQLineEdit(self.camera_layout,"sensor height (mm):", editwidth=120)
        self.leFOV_horizontal = AddQLineEdit(self.camera_layout,"FOV horizontal (deg):", editwidth=120)
        self.leFOV_vertical = AddQLineEdit(self.camera_layout,"FOV vertical (deg):", editwidth=120)
        self.leOffsetX = AddQLineEdit(self.camera_layout,"center offset x (px):", "0.", editwidth=120)
        self.leOffsetY = AddQLineEdit(self.camera_layout,"center offset y (px):", "0.", editwidth=120)


        ## position region
        self.position_groupbox = QtWidgets.QGroupBox("Position")
        self.position_groupbox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))

        self.layout.addWidget(self.position_groupbox,1,0)
        # add a grid layout for elements
        self.position_layout = QtWidgets.QVBoxLayout()
        self.position_groupbox.setLayout(self.position_layout)

        self.leCamElevation = AddQLineEdit(self.position_layout,"camera elevation (m):", editwidth=120,value='25')
        self.lePlaneElevation = AddQLineEdit(self.position_layout,"plane elevation (m):", editwidth=120, value='0')
        self.leCamTilt = AddQLineEdit(self.position_layout,"camera tilt:", editwidth=120, value=None)
        self.leCamRoll = AddQLineEdit(self.position_layout,"camera roll:", editwidth=120, value=None)
        self.leCamPan = AddQLineEdit(self.position_layout,"camera pan:", editwidth=120, value=None)
        self.leCamLat = AddQLineEdit(self.position_layout,"camera latitude:", editwidth=120)
        self.leCamLon = AddQLineEdit(self.position_layout,"camera longitude:", editwidth=120)

        # get current frame
        cframe = self.cp.getCurrentFrame()

        # retrieve data
        qimg = self.db.getImage(frame=cframe)
        print(os.path.isfile(os.path.join(qimg.path.path, os.path.splitext(qimg.filename)[0], ".ct")))

        # fill context menu from stored options if available
        if self.getOption('DM_last_camera'):
            # load from DB
            self.cameraComboBox.setCurrentIndex(self.getOption('DM_last_camera'))
            self.getCameraParametersByDB()
            self.getPostionParametersByDB()
            self.updateCameraParameters()
        elif os.path.isfile(os.path.join(qimg.path.path, os.path.splitext(qimg.filename)[0], ".ct")):
            self.getCameraParametersByCT(os.path.isfile(os.path.join(qimg.path.path, os.path.splitext(qimg.filename)[0], ".ct")))
            self.updateCameraParameters()
        else:
            # load from json
            self.getCameraParametersByJson()
            self.updateCameraParameters()

        ## display region
        self.display_groupbox = QtWidgets.QGroupBox("Display and Evaluation")
        self.display_groupbox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))
        self.layout.addWidget(self.display_groupbox,2,0)

        self.display_layout = QtWidgets.QVBoxLayout()
        self.display_groupbox.setLayout(self.display_layout)

        self.cbCalcArea = AddQCheckBox(self.display_layout, "calculate marked area", checked=False, strech=False)
        self.cbCalcArea.setToolTip('NOTE: LUT mode area calculation assumes a cylindrical projection with a straight and horizontal horizon')

        self.cbFitParameters = AddQCheckBox(self.display_layout, "fit camera parameters", checked=False, strech=False)

        self.sbScaleboxDim = AddQSpinBox(self.display_layout, "scale Box size", value=10, strech=False)

        self.cbShowHorizon = AddQCheckBox(self.display_layout, "display horizon", checked=True, strech=False)
        self.horizon_line = None


        ## projection region
        self.projection_groupbox = QtWidgets.QGroupBox("Projection")
        self.projection_groupbox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.layout.addWidget(self.projection_groupbox,0,1,6,6)
        
        self.projection_layout = QtWidgets.QVBoxLayout()
        self.projection_groupbox.setLayout(self.projection_layout)

        self.pltWidget = matplotlibwidget.MatplotlibWidget()
        self.projection_layout.addWidget(self.pltWidget)

        self.leExtent = AddQLineEdit(self.projection_layout, 'Extent','')
        self.leScaling = AddQLineEdit(self.projection_layout, 'Scaling','')

        self.pbRefreshProjection = QtWidgets.QPushButton('Refresh')
        self.pbRefreshProjection.clicked.connect(self.pushbutton_refreshprojction)
        self.projection_layout.addWidget(self.pbRefreshProjection)


        ## stretch area
        self.layout.addItem(QtWidgets.QSpacerItem(1,1,QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding),4,0)


        self.pushbutton_ok = QtWidgets.QPushButton("Ok")
        self.pushbutton_ok.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.layout.addWidget(self.pushbutton_ok,5,0)
        self.pushbutton_ok.clicked.connect(self.run)

        #self.db.addOption('DM_current_cam',self.cameraComboBox.getCurrentIndex())

    def getPostionParametersByDB(self):
        """
        load position parameters
        """
        self.leCamElevation.setText(getNumber( self.getOption('DM_cam_elevation'), '%.2f'))
        self.lePlaneElevation.setText(getNumber( self.getOption('DM_plane_elevation'), '%.2f'))

    def getCameraParametersByDB(self):
        """
        load camera parameters from last run stored in DB
        """

        # set cam parameters
        self.leFocallength.setText("%.2f" %         self.getOption('DM_focallength_mm'))
        self.leImage_width.setText("%d" %           self.getOption('DM_img_w_px'))
        self.leImage_height.setText("%d" %          self.getOption('DM_img_h_px'))
        self.leSensor_width.setText(getNumber(      self.getOption('DM_sensor_w_mm'), "%.2f"))
        self.leSensor_height.setText(getNumber(     self.getOption('DM_sensor_h_mm'), "%.2f"))
        self.leFOV_horizontal.setText(getNumber(    self.getOption('DM_fov_h_deg'),   "%.2f"))
        self.leFOV_vertical.setText(getNumber(      self.getOption('DM_fov_v_deg'),   "%.2f"))
        self.leOffsetX.setText(getNumber(           self.getOption('DM_offset_x_px'), "%.2f"))
        self.leOffsetY.setText(getNumber(           self.getOption('DM_offset_y_px'), "%.2f"))



    def getCameraParametersByJson(self):
        """
        insert camera parameters from camera.json into gui
        """

        self.selected_cam_name = self.cameraComboBox.itemText(self.cameraComboBox.currentIndex())
        print("Selected Cam:", self.selected_cam_name)

        # store to options
        self.setOption('DM_last_camera', self.cameraComboBox.currentIndex())

        cam_by_dict = dotdict(self.cam_dict[self.selected_cam_name])

        def getNumber(input,format):
            try:
                return (format % input)
            except TypeError:
                return "None"

        # set cam parameters in GUI
        self.leFocallength.setText("%.2f" % cam_by_dict['focallength_mm'])
        self.leImage_width.setText("%d" % cam_by_dict['img_w_px'])
        self.leImage_height.setText("%d" % cam_by_dict['img_h_px'])
        self.leSensor_width.setText(getNumber(cam_by_dict['sensor_w_mm'],"%.2f"))
        self.leSensor_height.setText(getNumber(cam_by_dict['sensor_h_mm'],"%.2f"))
        self.leFOV_horizontal.setText(getNumber(cam_by_dict['fov_h_deg'],"%.2f"))
        self.leFOV_vertical.setText(getNumber(cam_by_dict['fov_v_deg'],"%.2f"))

    def getCameraParametersByCT(self, ct_file):
        cam = ct.load_camera(ct_file)
        cam_by_dict = {}

        cam_by_dict['img_w_px'] = cam.image_width_px
        cam_by_dict['img_h_px'] = cam.image_height_px

        cam_by_dict['offset_x_px'] = cam.center_x_px - cam.image_width_px/2
        cam_by_dict['offset_y_px'] = cam.center_y_px - cam.image_height_px/2

        cam_by_dict['sensor_w_mm'] = cam.sensor_width_mm
        cam_by_dict['sensor_h_mm'] = cam.sensor_height_mm

        cam_by_dict['fov_h_deg'] = np.rad2deg(np.arctan2(cam.image_width_px/2, cam.focallength_x_px)*2)
        cam_by_dict['fov_v_deg'] = np.rad2deg(np.arctan2(cam.image_height_px/2, cam.focallength_y_px)*2)

        cam_by_dict['focallength_mm'] = cam.focallength_x_px*cam.sensor_width_mm/cam.image_width_px

        # set cam parameters in GUI
        self.leFocallength.setText("%.2f" % cam_by_dict['focallength_mm'])
        self.leImage_width.setText("%d" % cam_by_dict['img_w_px'])
        self.leImage_height.setText("%d" % cam_by_dict['img_h_px'])
        self.leSensor_width.setText(getNumber(cam_by_dict['sensor_w_mm'],"%.2f"))
        self.leSensor_height.setText(getNumber(cam_by_dict['sensor_h_mm'],"%.2f"))
        self.leFOV_horizontal.setText(getNumber(cam_by_dict['fov_h_deg'],"%.2f"))
        self.leFOV_vertical.setText(getNumber(cam_by_dict['fov_v_deg'],"%.2f"))

        self.leOffsetX.setText(getNumber(cam_by_dict['offset_x_px'],"%.2f"))
        self.leOffsetY.setText(getNumber(cam_by_dict['offset_y_px'],"%.2f"))

        self.leCamElevation.setText(getNumber(cam.elevation_m,"%.2f"))
        self.leCamPan.setText(getNumber(cam.heading_deg,"%.2f"))
        self.leCamTilt.setText(getNumber(cam.tilt_deg,"%.2f"))
        self.leCamRoll.setText(getNumber(cam.roll_deg,"%.2f"))

        self.leCamLat.setText(getNumber(cam.gps_lat,"%.2f"))
        self.leCamLon.setText(getNumber(cam.gps_lon,"%.2f"))

        self.updateCameraParameters()


    def calcSensorDimensionsFromFOV(self):
        self.cam.sensor_w_mm = utilFOVToSensor(self.cam.fov_h_deg,self.cam.focallength_mm)
        self.cam.sensor_h_mm = utilFOVToSensor(self.cam.fov_v_deg,self.cam.focallength_mm)


    def updateCameraParameters(self):
        """
        update camera dictionary for calculation - uses potentially user modified data from gui
        """

        # update current cam parameters
        self.cam = dotdict()
        self.cam.fov_h_deg = getFloat(self.leFOV_horizontal.text())
        self.cam.fov_v_deg = getFloat(self.leFOV_vertical.text())
        self.cam.sensor_w_mm = getFloat(self.leSensor_width.text())
        self.cam.sensor_h_mm = getFloat(self.leSensor_height.text())
        self.cam.focallength_mm = getFloat(self.leFocallength.text())
        self.cam.img_w_px = getInteger(self.leImage_width.text())
        self.cam.img_h_px = getInteger(self.leImage_height.text())
        self.cam.center_x_px = self.cam.img_w_px/2. + getFloat(self.leOffsetX.text())
        self.cam.center_y_px = self.cam.img_h_px/2. + getFloat(self.leOffsetY.text())

        self.cam.heading_deg = getFloat(self.leCamPan.text())
        self.cam.tilt_deg = getFloat(self.leCamTilt.text())
        self.cam.roll_deg = getFloat(self.leCamRoll.text())

        self.cam.elevation_m = getFloat(self.leCamElevation.text())
        self.cam.pos_x_m = 0.
        self.cam.pos_y_m = 0.

        self.cam.projection = self.cbProjection.itemText(self.cbProjection.currentIndex())

        self.cam.gps_lat = getFloat(self.leCamLat.text())
        self.cam.gps_lon = getFloat(self.leCamLon.text())

        if self.cam.sensor_h_mm is None or self.cam.sensor_w_mm is None:
            self.calcSensorDimensionsFromFOV()

        # save parameters as options to DB
        self.setOption('DM_focallength_mm', self.cam.focallength_mm )
        self.setOption('DM_fov_h_deg' , self.cam.fov_h_deg)
        self.setOption('DM_fov_v_deg' ,self.cam.fov_v_deg)
        self.setOption('DM_sensor_w_mm',self.cam.sensor_w_mm)
        self.setOption('DM_sensor_h_mm',self.cam.sensor_h_mm)
        self.setOption('DM_img_w_px', self.cam.img_w_px)
        self.setOption('DM_img_h_px',self.cam.img_h_px)
        self.setOption('DM_offset_x_px', getFloat(self.leOffsetX.text()))
        self.setOption('DM_offset_y_px', getFloat(self.leOffsetY.text()))


        print("Camera:")
        print(json.dumps(self.cam,indent=4,sort_keys=True))

        self.position = dotdict()
        self.position.cam_elevation = getFloat(self.leCamElevation.text())
        self.position.plane_elevation = getFloat(self.lePlaneElevation.text())

        # save parameters to options
        self.setOption('DM_cam_elevation',self.position.cam_elevation)
        self.setOption('DM_plane_elevation',self.position.plane_elevation)

        print("Position:")
        print(json.dumps(self.position,indent=4,sort_keys=True))


        print(self.cam)

        # update camera parameters
        # self.camera = ct.CameraTransform(self.cam.focallength_mm, [self.cam.sensor_w_mm, self.cam.sensor_h_mm],[self.cam.img_w_px, self.cam.img_h_px])
        orientation = ct.SpatialOrientation(heading_deg=self.cam.heading_deg,
                                            tilt_deg=self.cam.tilt_deg,
                                            roll_deg=self.cam.roll_deg,
                                            elevation_m=self.cam.elevation_m,
                                            pos_x_m=self.cam.pos_x_m,
                                            pos_y_m=self.cam.pos_y_m)
        if self.cam.projection == "Cylindrical":
            projection = ct.CylindricalProjection(focallength_mm=self.cam.focallength_mm,
                                                  image_width_px=self.cam.img_w_px,
                                                  image_height_px=self.cam.img_h_px,
                                                  sensor_width_mm=self.cam.sensor_w_mm,
                                                  sensor_height_mm=self.cam.sensor_h_mm,
                                                  center_x_px=self.cam.center_x_px,
                                                  center_y_px=self.cam.center_y_px)
        elif self.cam.projection == "Equirectangular":
            projection = ct.EquirectangularProjection(focallength_mm=self.cam.focallength_mm,
                                                  image_width_px=self.cam.img_w_px,
                                                  image_height_px=self.cam.img_h_px,
                                                  sensor_width_mm=self.cam.sensor_w_mm,
                                                  sensor_height_mm=self.cam.sensor_h_mm,
                                                  center_x_px=self.cam.center_x_px,
                                                  center_y_px=self.cam.center_y_px)

        else: # default to rectilinear projection
            print("Defaulting to rectiliniear")
            projection = ct.RectilinearProjection(focallength_mm=self.cam.focallength_mm,
                                                  image_width_px=self.cam.img_w_px,
                                                  image_height_px=self.cam.img_h_px,
                                                  sensor_width_mm=self.cam.sensor_w_mm,
                                                  sensor_height_mm=self.cam.sensor_h_mm,
                                                  center_x_px=self.cam.center_x_px,
                                                  center_y_px=self.cam.center_y_px)
        self.camera = ct.Camera(orientation=orientation, projection=projection)


    def run(self, start_frame=0):

        self.frame = self.cp.getCurrentFrame()
        print("processing frame nr %d" % self.frame)

        self.updateCameraParameters()

        # # get image parameters
        # image = self.db.getImage(frame=start_frame)
        # data = image.data
        # im_height, im_width, channels = data.shape

        # self.camera = ct.Camera(self.cam.)
        if self.cbFitParameters.isChecked():
            # try to load marker
            horizon = self.db.getMarkers(type="DM_horizon", frame=self.frame)

            if horizon.count() < 2:
                print("ERROR: Too few horizon markers placed - please add at least TWO horizon markers")
                return

            self.camera.fixHorizon(horizon)
            if self.position.cam_elevation:
                self.camera.fixHeight(self.position.cam_elevation)

            # set fit parameter
            self.fit_params = dotdict()
            self.fit_params.horizon_points = horizon.count()
            self.fit_params.cam_elevation = self.camera.height
            self.fit_params.cam_tilt = np.round(self.camera.tilt,2)
            self.fit_params.dist_to_horizon = np.round(self.camera.distanceToHorizon(),2)

            # update params
            self.leCamTilt.setText(getNumber(self.camera.tilt, "%.2f"))
            self.leCamPan.setText(getNumber(self.camera.heading, "%.2f"))
            self.leCamRoll.setText(getNumber(self.camera.roll, "%.2f"))


        # succesfully initialized
        self.initialized = True

        # DEBUG
        # print("Fit Parameter:")
        # print(json.dumps(self.fit_params, indent=4, sort_keys=True))

        # TODO: add region update?
        self.updateAllMarker()

        # mask handling
        if self.cbCalcArea.isChecked():
            q_mask = self.db.getMasks(frame=self.frame)
            print("masks: ", q_mask.count())

            rotation = self.db.getOption('rotation')
            print("rotation ", rotation)

            print(self.camera)

            if q_mask.count() > 0:
                # get mask data
                mask = q_mask[0].data

                # binaryse
                mask[mask > 0] = 1

                mask_labeled = label(mask)
                props = regionprops(mask_labeled)

                # handle rotated images
                if rotation == 180:
                    self.LUT = self.camera.generateLUT(invert=True)
                else:
                    self.LUT = self.camera.generateLUT()

                # calculate corrected area
                for idx,n in enumerate(np.unique(mask_labeled)[1:]):        # we exclude 0
                    area = np.zeros(mask_labeled.shape)
                    area[mask_labeled==n]=1


                    corrected_area = np.sum(np.sum(area, axis=1) * self.LUT)

                    props[idx].corrected_area = corrected_area


                self.db.deleteMarkers(type='DM_area', image=q_mask[0].image)

                # iterate over properties and set marker for display
                for nr, prop in enumerate(props):

                        self.db.setMarker(image=q_mask[0].image, x=prop.centroid[1], y=prop.centroid[0],
                                          text=u'%.2f px²\n%.2f m²' % (prop.area,prop.corrected_area), type='DM_area')



            self.cp.reloadMarker(frame=self.frame)

        # show the horizon line
        self.plotHorizon()

    def plotHorizon(self):

        if self.cbShowHorizon.isChecked():
                # delete old horizon
                self.deleteHorizon()

                # get coordinates
                p1 = self.camera.getImageHorizon()[0]
                p2 = self.camera.getImageHorizon()[-1]
                print(p1, p2)

                # set pen
                pen = QtGui.QPen(QtGui.QColor("#00ffff"))
                pen.setWidth(5)

                # add object
                self.horizon_line = QtWidgets.QGraphicsLineItem(QtCore.QLineF(QtCore.QPointF(*p1),QtCore.QPointF(*p2)))
                self.horizon_line.setPen(pen)
                self.horizon_line.setParentItem(self.cp.window.view.origin)
                self.horizon_line.setZValue(100)

        else:
            self.deleteHorizon()

    def deleteHorizon(self):
        if self.horizon_line:
            print("delete")
            self.horizon_line.scene().removeItem(self.horizon_line)
            self.horizon_line = None


    def updateAllMarker(self):

        # get distance to cam markers and calculate distance
        dist2cam = self.db.getMarkers(type="DM_to_cam", frame=self.frame)
        for marker in dist2cam:
            self.updateDistMarker(marker)

        # get line markers and calculate distance in between
        dist2pt = self.db.getLines(type="DM_between", frame=self.frame)
        for line in dist2pt:
            self.updateDistLine(line)

        # get scalebox markers and update size
        distscalebox = self.db.getMarkers(type="DM_scalebox", frame=self.frame)
        for marker in distscalebox:
            self.updateScalebox(marker)


        self.cp.reloadMarker(frame=self.frame)

    def updateDistMarker(self,marker):
        """
        Update distance to observer indicated by marker
        """
        pos = self.camera.spaceFromImage(np.array([marker.x, marker.y]), Z=0).T

        marker.text = "%.2fm" % np.sqrt(pos[0] ** 2 + pos[1] ** 2)
        marker.save()

    def updateDistLine(self,line):
        """
        Update distance indicated by an line marker
        """
        pts = np.round(np.array([line.getPos1(), line.getPos2()]),0)

        #TODO: Why doesnt this work when i supply the same point twice in an array?
        pos1 = self.camera.spaceFromImage(pts[0], Z=self.position.plane_elevation).T
        pos2 = self.camera.spaceFromImage(pts[1], Z=self.position.plane_elevation).T
        dist = np.sqrt(np.sum(((pos1 - pos2)**2)))

        line.text = "%.2fm" % dist
        line.save()



    def updateScalebox(self,marker):
        scalebox_dim = self.sbScaleboxDim.value()
        if marker.id in self.scalebox_dict:
            sb = self.scalebox_dict[marker.id]
            sb.delete()
            self.scalebox_dict.pop(marker.id)
            if marker.text is not None:
                match = re.match(r"^(?P<dim>\d*\.?\d*)\s*(?P<unit>\S*)?.*", marker.text)
                if match:
                    match= match.groupdict()
                    if match["unit"] in UNITS.keys():
                        scalebox_dim = float(match["dim"])*UNITS[match["unit"]]
                    else:
                        scalebox_dim = float(match["dim"])


        sb = ScaleBox(self.cp.window.view.origin, '#ff5f00', np.array([marker.x,marker.y]), self.camera, scalebox_dim)
        self.scalebox_dict[marker.id] = sb



    def markerMoveEvent(self, marker):
        """
        On moving a marker - update the text information
        """
        if self.initialized:
            if marker.type.name == 'DM_to_cam':
                self.updateDistMarker(marker)

            if marker.type.name == 'DM_between':
                self.updateDistLine(marker)

            if marker.type.name == 'DM_scalebox':
                self.updateScalebox(marker)

    def markerRemoveEvent(self, marker):
        if self.initialized:
            if marker.type.name == 'DM_scalebox':
                self.scalebox_dict[marker.id].delete()
                del self.scalebox_dict[marker.id]

    def markerAddEvent(self, marker):
        """
        On adding a marker - calculate values
        """
        if self.initialized:
            if marker.type.name == 'DM_to_cam':
                self.updateDistMarker(marker)

            if marker.type.name == 'DM_between':
                self.updateDistLine(marker)

            if marker.type.name == 'DM_scalebox':
                self.updateScalebox(marker)

    def pushbutton_refreshprojction(self):
        print("Refresh projection")

        # frame = self.cp.getCurrentFrame()
        img = self.cp.getImage().data
        if not isinstance(img, np.ndarray):
            img = img.image

        rotation = self.db.getOption('rotation')
        print('rotation', rotation)
        if rotation == 180:
            img = img[::-1, ::-1, :]


        extent = self.leExtent.text()
        scaling = getFloat(self.leScaling.text())

        print(extent)
        print(scaling)

        try:
            ex1,ex2,ex3,ex4 = extent.split(',')
            print("Setting custom extent to:", ex1, ex2, ex3, ex4)
            top_view = self.camera.getTopViewOfImage(img, extent=np.array([ex1, ex2, ex3, ex4]).astype(float), scaling=scaling)
        except:
            top_view = self.camera.getTopViewOfImage(img, scaling=scaling)

        self.pltWidget.axes.imshow(top_view)
        self.pltWidget.show()

    def buttonPressedEvent(self):
        # show the addon window when the button in ClickPoints is pressed
        self.show()

        try:
            self.run()
        except:
            pass

    def delete(self):
        # clean up on reload
        self.deleteHorizon()

        # clean scale boxes
        for i,sb in self.scalebox_dict.items():
            sb.delete()

class ScaleBox():
    def __init__(self, parent, color, base_pt, camera, scalebox_dim):
        # get the base position in the plane
        base_pos = camera.spaceFromImage(base_pt, Z=0).T
        print("### base", base_pos, base_pt)

        # get the top position
        top_pos = base_pos + np.array([0, 0, scalebox_dim])
        top_pt = camera.imageFromSpace(top_pos)
        print("### top", top_pos, top_pt)

        # get the left position
        left_pos = base_pos + np.array([scalebox_dim, 0, 0])
        left_pt = camera.imageFromSpace(left_pos)
        print("### left", left_pos, left_pt)

        # get the back position
        back_pos = base_pos + np.array([0, scalebox_dim, 0])
        back_pt = camera.imageFromSpace(back_pos)
        print("### back", back_pos, back_pt)

        ## draw element
        # set pen
        pen = QtGui.QPen(QtGui.QColor("#ff5f00"))
        pen.setWidth(5)
        pen.setCosmetic(True)

        # add object
        line_top = QtWidgets.QGraphicsLineItem(QtCore.QLineF(QtCore.QPointF(*base_pt), QtCore.QPointF(*top_pt)))
        line_left = QtWidgets.QGraphicsLineItem(QtCore.QLineF(QtCore.QPointF(*base_pt), QtCore.QPointF(*left_pt)))
        line_back = QtWidgets.QGraphicsLineItem(QtCore.QLineF(QtCore.QPointF(*base_pt), QtCore.QPointF(*back_pt)))

        self.lines = [line_top, line_left, line_back]

        _ = [line.setPen(pen) for line in self.lines]
        _ = [line.setParentItem(parent) for line in self.lines]
        _ = [line.setZValue(100) for line in self.lines]

    def delete(self):
        _ = [line.scene().removeItem(line) for line in self.lines]

