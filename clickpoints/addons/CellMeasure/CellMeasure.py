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
import os
import json
from qtpy import QtCore, QtGui, QtWidgets
from clickpoints.includes.QtShortCuts import AddQLineEdit, AddQComboBox, QInputNumber
from clickpoints.includes import QtShortCuts
import qtawesome as qta
from skimage.measure import label, regionprops
from skimage.color import rgb2grey
from scipy.ndimage.filters import gaussian_filter
from skimage.filters import gaussian
from skimage.morphology import binary_closing
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

        """ get or set options """
        layers = ([l.name for l in self.db.getLayers()])
        self.addOption(key="segmentation_layer", display_name="Segmentation Layer", default=layers[0], value_type="choice_string",
                       values=layers, tooltip="The layer on which to segment the image")
        self.addOption(key="segmentation_th", display_name="Threshold Segmentation", default=125, value_type="int",
                       min_value=1, max_value=255, tooltip="Threshold for binary segmentation")
        self.addOption(key="segmentation_slm_size", display_name="Threshold SELEM size", default=2, value_type="int",
                       min_value=0, max_value=255, tooltip="Size of the DISK shaped element for the binary open operation")
        self.addOption(key="segmentation_gauss", display_name="Gauss Sigma", default=1.25, value_type="float",
                       min_value=0, max_value=10, tooltip="Width of the gaussian used to smooth the image")
        self.addOption(key="invert_mask", display_name="invert mask", default=False, value_type="bool",
                       tooltip="If true, inverts the mask, so that darker areas are marked instead of brighter ones.")
        self.addOption(key="auto_apply", display_name="auto apply segmentation", default=False, value_type="bool",
                       tooltip="If true, changes of the parameters will automatically trigger a new segmentation")

        self.addOption(key="evaluation_layer", display_name="Evaluation Layer", default=layers[0], value_type="choice_string",
                       values=layers, tooltip="The layer on which to evaluate the mask",)
        self.addOption(key="min_area", display_name="Min Area", default=200, value_type="int",
                       min_value=0, max_value=10000, tooltip="Exclude all patches with areas smaller than this value.")

        # define options groups for unified callback handling, e.g only call an update if parameter of this group was changed
        self.options_Segmentation = ['segmentation_th', 'segmentation_slm_size','segmentation_gauss','invert_mask','segmentation_layer']
        self.options_Output = ['min_area', 'evaluation_layer']


        """ Setup Marker and Masks """
        # Check if the marker type is present
        self.db.setMarkerType("cell (auto)", [0, 255, 255], self.db.TYPE_Normal)
        self.cp.reloadTypes()

        if self.db.getMaskType('mask'):
            self.db.deleteMaskTypes('mask')

        self.MaskType_auto = self.db.setMaskType("area (auto)", '#009fff')
        self.MaskType_manual = self.db.setMaskType("area (manual)", '#ff00bf')
        self.MaskType_exclude = self.db.setMaskType("exclude (manual)", '#ffbf00')
        self.cp.reloadMaskTypes()

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

        # add a layout for elements
        self.segmentation_layout = QtWidgets.QVBoxLayout()
        self.segmentation_groupbox.setLayout(self.segmentation_layout)

        self.segmentationLayer = self.inputOption("segmentation_layer", self.segmentation_layout)
        self.sliderSegmentationTH = self.inputOption("segmentation_th", self.segmentation_layout, use_slider=True)
        self.sliderSelemSize = self.inputOption("segmentation_slm_size", self.segmentation_layout, use_slider=True)
        self.inputGauss = self.inputOption("segmentation_gauss", self.segmentation_layout, use_slider=True)
        self.checkboxInvert = self.inputOption("invert_mask", self.segmentation_layout)
        self.checkboxSegmentation = self.inputOption("auto_apply", self.segmentation_layout)

        # segment on button press
        self.buttonSegmentation = QtWidgets.QPushButton("Segment")
        self.buttonSegmentation.released.connect(self.updateSegmentation)
        self.checkboxSegmentation.layout().addWidget(self.buttonSegmentation)

        """ groupbox PROPERTIES """
        self.position_groupbox = QtWidgets.QGroupBox("Properties")
        self.layout.addWidget(self.position_groupbox)

        # add a grid layout for elements
        self.position_layout = QtWidgets.QVBoxLayout()
        self.position_groupbox.setLayout(self.position_layout)

        self.evaluationLayer = self.inputOption("evaluation_layer", self.position_layout)
        self.inputMinSize = self.inputOption("min_area", self.position_layout, use_slider=True)

        # button Properties
        self.position_layout2 = QtWidgets.QHBoxLayout()
        self.position_layout.addLayout(self.position_layout2)

        self.buttonProps = QtWidgets.QPushButton('Get Properties')
        self.position_layout2.addWidget(self.buttonProps)
        self.buttonProps.released.connect(self.updateProperties)

        # button Remove Marker
        self.buttonRemoveMarker = QtWidgets.QPushButton('Remove Marker')
        self.position_layout2.addWidget(self.buttonRemoveMarker)
        self.buttonRemoveMarker.released.connect(self.removeMarker)

        self.position_layout2.addStretch()

        """ groupbox BATCH PROCESS"""
        self.batch_groupbox = QtWidgets.QGroupBox("Batch Process")
        self.layout.addWidget(self.batch_groupbox)

        # add a grid layout for elements
        self.batch_layout = QtWidgets.QGridLayout()
        self.batch_groupbox.setLayout(self.batch_layout)

        self.buttonProcAll = QtWidgets.QPushButton('Process all Images')
        self.batch_layout.addWidget(self.buttonProcAll)
        self.buttonProcAll.released.connect(self.processAll)

    def optionsChanged(self, key):
        if key in self.options_Segmentation and self.getOption("auto_apply"):
            self.updateSegmentation()
        elif key in self.options_Output:
            pass

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
            self.qimg = self.db.getImage(frame=self.cframe, layer=self.getOption("segmentation_layer"))
        else:
            self.qimg = qimg

        if self.qimg is None:
            raise IndexError("No image found with sort_index %d and layer %s." % (self.cframe, self.getOption("segmentation_layer")))

        img = self.qimg.data

        # convert rgb to grayscale
        if img.shape[-1] == 3:
            img = rgb2grey(img)
            # convert to 0-255 range if applicable
            if img.max() <= 1.0:
                img*=255

        if self.inputGauss.value() > 0:
            img = gaussian_filter(img, self.getOption("segmentation_gauss"))
            #print("apply Gauss with value", self.getOption("segmentation_gauss"))

        # create binary mask
        mask = np.zeros(img.shape, dtype='uint8')
        if self.getOption("invert_mask"):
            mask[img < self.getOption("segmentation_th")] = 1
        else:
            mask[img > self.getOption("segmentation_th")] = 1

        # use open operation to reduce noise
        if self.getOption("segmentation_slm_size") != 0:
            from skimage.morphology import opening, disk
            mask_open = opening(mask, disk(self.getOption("segmentation_slm_size")))
        else:
            mask_open = mask

        # # use close operation to fill gaps
        # mask_open = binary_closing(mask_open, disk(self.slm_size)).astype('uint8')

        # add user input
        cp_mask = self.db.getMask(image=self.qimg)
        mask_open[mask_open == 1] = self.MaskType_auto.index
        if not cp_mask is None:
            # add additional information
            mask_open[cp_mask.data == self.MaskType_exclude.index] = self.MaskType_exclude.index
            mask_open[cp_mask.data == self.MaskType_manual.index] = self.MaskType_manual.index

        # print(mask_open)

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
            self.qimg = self.db.getImage(frame=self.cframe, layer=self.getOption("evaluation_layer"))
        else:
            self.qimg = qimg

        if self.qimg is None:
            raise IndexError("No image found with sort_index %d and layer %s." % (self.cframe, self.getOption("evaluation_layer")))

        img = self.qimg.data

        # convert rgb to grayscale
        if img.shape[-1] == 3:
            img = rgb2grey(img)
            # convert to 0-255 range if applicable
            if img.max() <= 1.0:
                img*=255

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
        mask[mask == self.MaskType_manual.index] = 1  # set manual marked area to true
        mask[mask == self.MaskType_exclude.index] = 0  # remove manually excluded areas

        # get regionprops
        mask_labeled = label(mask)
        props = regionprops(mask_labeled, img)

        # iterate over properties and set marker for display
        for nr,prop in enumerate(props):
            if prop.area > self.inputMinSize.value():
                self.db.setMarker(image=self.qimg, x=prop.centroid[1], y=prop.centroid[0], text='Cell %d\narea= %.2f' % (nr,prop.area), type='cell (auto)')

        # update CP display to show marker
        self.cp.reloadMarker()

        # store parameters in Pandas DF
        results = []
        for nr, prop in enumerate(props):
            if prop.area > self.inputMinSize.value():
                tmp = dotdict()
                tmp.filename = self.qimg.filename
                tmp.nr = nr
                tmp.centroid_x = prop.centroid[0]
                tmp.centroid_y = prop.centroid[1]
                tmp.area = prop.area
                tmp.mean_intensity = prop.mean_intensity
                tmp.equivalent_diameter = prop.equivalent_diameter
                tmp.axis_minor = prop.minor_axis_length
                tmp.axis_major = prop.major_axis_length

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

            # self.updateSegmentation(qimg=q_img)
            df = self.updateProperties(qimg=q_img)
            results.append(df)

        if save_properties:
            df_all = pd.concat(results)
            df_all.to_excel(os.path.splitext(self.qimg.filename)[0][0:15] + '_eval_summary.xls')

    """ DEFAULT ADDON FUNCTIONS """
    def buttonPressedEvent(self):
        # show the addon window when the button in ClickPoints is pressed
        self.show()
