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
from skimage.measure import label, regionprops
import pandas as pd


# define default dicts, enables .access on dicts
class dotdict(dict):
    def __getattr__(self, attr):
        if attr.startswith('__'):
            raise AttributeError
        return self.get(attr, None)

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__



class Addon(clickpoints.Addon):

    def __init__(self, *args, **kwargs):
        clickpoints.Addon.__init__(self, *args, **kwargs)

        """ Setup Marker and Masks """
        # Check if the marker type is present
        if not self.db.getMarkerType("cell (auto)"):
            self.db.setMarkerType("cell (auto)", [0, 255, 255], self.db.TYPE_Normal)
            self.cp.reloadTypes()

        if not self.db.getMaskType("area (auto)"):
            self.MaskType_auto = self.db.setMaskType("area (auto)", '#00ff3f', id=1)
            self.cp.reloadTypes()

        if not self.db.getMaskType("area (manual)"):
            self.MaskType_manual = self.db.setMaskType("area (manual)", '#ff00bf', id=2)
            self.cp.reloadTypes()

        if not self.db.getMaskType("exclude (manual)"):
            self.MaskType_exclude = self.db.setMaskType("exclude (manual)", '#ffbf00', id=3)
            self.cp.reloadTypes()

        """ default parameter """
        # start param
        self.th = 125
        self.slm_size = 3

        """ GUI Widgets"""
        # set the title and layout
        self.setWindowTitle("Cell Measurement")
        self.setWindowIcon(qta.icon("fa.compress"))
        self.setMinimumWidth(400)
        self.setMinimumHeight(200)
        self.layout = QtWidgets.QVBoxLayout(self)

        """ groupbox SEGMENTATION"""
        # use a groupbox for each task
        self.segmentation_groupbox = QtWidgets.QGroupBox("Segmentation")
        self.layout.addWidget(self.segmentation_groupbox)

        # add a grid layout for elements
        self.segmentation_layout = QtWidgets.QVBoxLayout()
        self.segmentation_groupbox.setLayout(self.segmentation_layout)

        # Note: for each parameter a combination of label / slider / spinbox is used
        # changing slider or spinbox values updates the other via signals

        ## threshold parameter
        self.layout_TH = QtWidgets.QGridLayout()
        self.segmentation_layout.addLayout(self.layout_TH)
        self.sliderSegmentationTH = QtWidgets.QSlider()
        self.sliderSegmentationTH.setOrientation(1)
        self.sliderSegmentationTH.setMinimum(1)
        self.sliderSegmentationTH.setMaximum(255)
        self.sliderSegmentationTH.setValue(self.th)
        self.leSegmentationTH = QtWidgets.QSpinBox()
        self.leSegmentationTH.setMinimum(1)
        self.leSegmentationTH.setMaximum(255)
        self.leSegmentationTH.setValue(self.th)

        # connect signals and slots
        self.sliderSegmentationTH.sliderReleased.connect(self.sliderTHUpdate)
        self.leSegmentationTH.valueChanged.connect(self.spinnTHUpdate)

        # add to horizontal layout
        self.layout_TH.addWidget(QtWidgets.QLabel("TH:"),0,0)
        self.layout_TH.addWidget(self.sliderSegmentationTH,0,1)
        self.layout_TH.addWidget(self.leSegmentationTH,0,2)


        ## open parameter
        self.sliderSelemSize = QtWidgets.QSlider()
        self.sliderSelemSize.setOrientation(1)
        self.sliderSelemSize.setMinimum(0)
        self.sliderSelemSize.setMaximum(10)
        self.sliderSelemSize.setValue(self.slm_size)
        self.sbSlemSize = QtWidgets.QSpinBox()
        self.sbSlemSize.setMinimum(0)
        self.sbSlemSize.setMaximum(10)
        self.sbSlemSize.setValue(self.slm_size)

        # add to layout
        self.layout_TH.addWidget(QtWidgets.QLabel("SELEM:"),1,0)
        self.layout_TH.addWidget(self.sliderSelemSize, 1, 1)
        self.layout_TH.addWidget(self.sbSlemSize,1,2)

        # connect signals and slots
        self.sliderSelemSize.sliderReleased.connect(self.sliderSELEMUpdate)
        self.sbSlemSize.valueChanged.connect(self.spinnSELEMUpdate)

        ## auto apply checkbox
        self.checkboxSegmentation = QtWidgets.QCheckBox()
        self.checkboxSegmentation.setEnabled(True)
        self.layout_TH.addWidget(QtWidgets.QLabel('auto apply segmentation'),2,1)
        self.layout_TH.addWidget(self.checkboxSegmentation,2,0)

        ## segment on button press
        self.buttonSegmentation = QtWidgets.QPushButton("Segment")
        self.buttonSegmentation.released.connect(self.updateSegmentation)
        self.layout_TH.addWidget(self.buttonSegmentation,2,2)



        """ groupbox PROPERTIES """
        self.position_groupbox = QtWidgets.QGroupBox("Properties")
        self.layout.addWidget(self.position_groupbox)

        # add a grid layout for elements
        self.position_layout = QtWidgets.QGridLayout()
        self.position_groupbox.setLayout(self.position_layout)

        # button Properties
        self.buttonProps = QtWidgets.QPushButton('Get Properties')
        self.position_layout.addWidget(self.buttonProps)
        self.buttonProps.released.connect(self.updateProperties)

        # button Remove Marker
        self.buttonRemoveMarker = QtWidgets.QPushButton('Remove Marker')
        self.position_layout.addWidget(self.buttonRemoveMarker)
        self.buttonRemoveMarker.released.connect(self.removeMarker)

        """ groupbox BATCH PROCESS"""
        self.batch_groupbox = QtWidgets.QGroupBox("Batch Process")
        self.layout.addWidget(self.batch_groupbox)

        # add a grid layout for elements
        self.batch_layout = QtWidgets.QGridLayout()
        self.batch_groupbox.setLayout(self.batch_layout)

        self.buttonProcAll = QtWidgets.QPushButton('Process all Images')
        self.batch_layout.addWidget(self.buttonProcAll)
        self.buttonProcAll.released.connect(self.processAll)

    """ slider spinbox SELEM updates"""
    def spinnSELEMUpdate(self, value):
        """
        Update internal selem size and set slider value
        Trigger display update if auto apply checkbox is set
        """
        # store slm
        self.slm_size = value
        self.sliderSelemSize.setValue(self.slm_size)

        # update segmentation
        if self.checkboxSegmentation.isChecked():
            self.updateSegmentation()

    def sliderSELEMUpdate(self):
        """
        Update internal selem size and set spinbox value
        Trigger display update if auto apply checkbox is set
        """

        # store slm
        self.slm_size = self.sliderSelemSize.value()

        self.sbSlemSize.setValue( self.slm_size)

        # update segmentation
        if self.checkboxSegmentation.isChecked():
            self.updateSegmentation()

    """ slider spinbox TH updates"""
    def spinnTHUpdate(self, value):
        """
        Update internal TH value and set slider value
        Trigger display update if auto apply checkbox is set
        """

        # store th
        self.th = value
        self.sliderSegmentationTH.setValue(self.th)

        # update segmentation
        if self.checkboxSegmentation.isChecked():
            self.updateSegmentation()

    def sliderTHUpdate(self):
        """
        Update internal TH value and set spinnbox value
        Trigger display update if auto apply checkbox is set
        """

        # store th
        self.th = self.sliderSegmentationTH.value()

        # update spin box
        self.leSegmentationTH.setValue(self.th)

        # update segmentation
        if self.checkboxSegmentation.isChecked():
            self.updateSegmentation()

    """ PROCESSING """
    def updateSegmentation(self, qimg=None):
        """
        Update segmentation according to parameters TH and SELEM and display results in CP
        The qimg parameter allows to call this function for batch processing by providing
        the target image (insted of the currently shown image in CP)

        :param qimg: cp.Image query object
        """

        # if no qimg object is provided - get the currently displayed image from CP
        if qimg is None:
            # get current frame
            self.cframe = self.cp.getCurrentFrame()

            # retrieve data
            self.qimg = self.db.getImage(frame=self.cframe)
        else:
            self.qimg = qimg

        img = self.qimg.data

        # create binary mask
        mask = np.zeros(img.shape, dtype='uint8')
        mask[img > self.th] = 1

        # use close operation to reduce noise
        from skimage.morphology import opening, disk
        mask_open = opening(mask, disk(self.slm_size))

        # add user input
        cp_mask = self.db.getMask(image=self.qimg)
        if not cp_mask is None:
            # add additional information
            mask_open[cp_mask.data==2]=2
            mask_open[cp_mask.data==3]=3

        self.db.setMask(image=self.qimg, data=mask_open)
        self.cp.reloadMask()


    def updateProperties(self, qimg=None, save_properties=True):
        """
        Extracts the properties (regionprops) based on the current segmentation, incorporating
        manually added and excluded regions.
        The qimg parameter allows to call this function for batch processing by providing
        the target image (insted of the currently shown image in CP)

        :param qimg: cp.Image query object
        """

        # if no qimg object is provided - get the currently displayed image from CP
        if qimg is None:
            # get current frame
            self.cframe = self.cp.getCurrentFrame()

            # retrieve data
            self.qimg = self.db.getImage(frame=self.cframe)
        else:
            self.qimg = qimg

        img = self.qimg.data

        # cleanup
        self.db.deleteMarkers(image=self.qimg, type='cell (auto)')

        # get current mask
        cp_mask = self.db.getMask(image=self.qimg)

        # skip processing if no mask is found
        if cp_mask is None:
            print("Addon CellMeasure: No mask found for current image!")
            return

        # get mask data and apply filter for user data
        mask = np.array(cp_mask.data).copy()
        mask[mask==2]=1 # set manual marked area to true
        mask[mask==3]=0 # remove manually excluded areas


        # get regionprops
        mask_labeled = label(mask)
        props = regionprops(mask_labeled, img)

        # iterate over properties and set marker for display
        for nr,prop in enumerate(props):
            self.db.setMarker(image=self.qimg, x=prop.centroid[1], y=prop.centroid[0], text='Cell %d\narea= %.2f' % (nr,prop.area), type='cell (auto)')

        # update CP display to show marker
        self.cp.reloadMarker()

        # store parameters in Pandas DF
        results = []
        for nr,prop in enumerate(props):
            tmp = dotdict()
            tmp.filename = self.qimg.filename
            tmp.nr = nr
            tmp.centroid_x = prop.centroid[0]
            tmp.centroid_y = prop.centroid[1]
            tmp.area = prop.area
            tmp.mean_intensity = prop.mean_intensity

            results.append(tmp)

        df = pd.DataFrame.from_records(results)
        print(df)

        # if the save flag is set - store results to file
        if save_properties:
            df.to_excel(os.path.splitext(self.qimg.filename)[0] + '_eval.xls')

        return df

    def removeMarker(self):
        """
        Deletes all markers from the current image
        """

        # get current frame
        self.cframe = self.cp.getCurrentFrame()
        self.qimg = self.db.getImage(frame=self.cframe)

        # cleanup
        self.db.deleteMarkers(image=self.qimg, type='cell (auto)')

        self.cp.reloadMarker()


    def processAll(self, save_properties=True):
        """
        Iterates over all available images in the current CP project,
        perform segmentation, extract region properties.
        """

        q_images = self.db.getImages()

        results = []
        for q_img in q_images:
            self.q_img = q_img
            print("Batch processing Image Nr %d" % q_img.sort_index)

            self.updateSegmentation(qimg=q_img)
            df = self.updateProperties(qimg=q_img)
            results.append(df)

        if save_properties:
            df_all = pd.concat(results)
            df_all.to_excel(os.path.splitext(self.qimg.filename)[0][0:15] + '_eval_summary.xls')




    """ DEFAULT ADDON FUNCTIONS """
    def run(self, start_frame=0):

        self.frame = start_frame

        # # get image parameters
        # image = self.db.getImage(frame=start_frame)
        # data = image.data
        # im_height, im_width, channels = data.shape


    def buttonPressedEvent(self):
        # show the addon window when the button in ClickPoints is pressed
        self.show()

        try:
            self.run()
        except:
            pass

