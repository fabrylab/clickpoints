#!/usr/bin/env python
# -*- coding: utf-8 -*-
# CellMeasure.py

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
import os
import json
from qtpy import QtCore, QtGui, QtWidgets
from clickpoints.includes.QtShortCuts import AddQLineEdit, AddQComboBox, QInputNumber
from clickpoints.includes import QtShortCuts
import qtawesome as qta
from skimage.measure import label, regionprops
from skimage.color import rgb2grey
from scipy.ndimage.morphology import binary_erosion, binary_fill_holes
from scipy.ndimage.filters import gaussian_filter
from skimage.filters import threshold_otsu, gaussian, threshold_local
from skimage.morphology import binary_closing, remove_small_objects, opening, disk
from skimage.feature import canny
import pandas as pd
from imageio import imread

REGIONPROPS_TYPE = {"area": "int",
                    "bbox_area": "int",
                    "convex_area": "int",
                    "eccentricity": "float",
                    "equivalent_diameter": "float",
                    "euler_number": "int",
                    "extent": "float",
                    "filled_area": "int",
                    "label": "int",
                    "major_axis_length": "float",
                    "max_intensity": "float",
                    "mean_intensity": "float",
                    "min_intensity": "float",
                    "minor_axis_length": "float",
                    "orientation": "float",
                    "perimeter": "float",
                    "solidity": "float"
                    }
REGIONPROPS_MINMAXDEF = {"area": [0, 10000, 200, 1000],
                         "bbox_area": [0, 10000, 200, 1000],
                         "convex_area": [0, 10000, 200, 1000],
                         "eccentricity": [0., 1., 0.1, 0.9],
                         "equivalent_diameter": [0, 1000, 0, 10],
                         "euler_number": [-100, 100, -100, 100],
                         "extent": [0, 1, 0.1, 0.9],
                         "filled_area": [0, 10000, 200, 1000],
                         "label": [0, 10000, 200, 1000],
                         "major_axis_length": [0., 1000., 0., 10.],
                         "max_intensity": [0., 255., 10., 230.],
                         "mean_intensity": [0., 255., 10., 230.],
                         "min_intensity": [0., 255., 10., 230.],
                         "minor_axis_length": [0., 1000., 0., 10.],
                         "orientation": [-np.pi / 2, np.pi / 2, -np.pi / 2, np.pi / 2],
                         "perimeter": [0., 1000., 0., 10.],
                         "solidity": [0., 1., 0.1, 0.9]
                         }
REGIONPROPS_HELP = {"area": "Number of pixels of region.",
                    "bbox_area": "Number of pixels of bounding box.",
                    "convex_area": "Number of pixels of convex hull image. ",
                    "eccentricity": "Eccentricity of the ellipse that has the same second-moments as the region. The eccentricity is the ratio of the focal distance (distance between focal points) over the major axis length. The value is in the interval [0, 1). When it is 0, the ellipse becomes a circle. ",
                    "equivalent_diameter": "The diameter of a circle with the same area as the region. ",
                    "euler_number": "Euler characteristic of region. Computed as number of objects (= 1) subtracted by number of holes (8-connectivity). ",
                    "extent": "Ratio of pixels in the region to pixels in the total bounding box. Computed as ``area / (rows * cols)`` ",
                    "filled_area": "Number of pixels of filled region. ",
                    "label": "The label in the labeled input image. ",
                    "major_axis_length": "The length of the major axis of the ellipse that has the same normalized second central moments as the region. ",
                    "max_intensity": "Value with the greatest intensity in the region. ",
                    "mean_intensity": "Value with the mean intensity in the region. ",
                    "min_intensity": "Value with the least intensity in the region. ",
                    "minor_axis_length": "The length of the minor axis of the ellipse that has the same normalized second central moments as the region. ",
                    "orientation": "In 'rc' coordinates, angle between the 0th axis (rows) and the major axis of the ellipse that has the same second moments as the region, ranging from `-pi/2` to `pi/2` counter-clockwise. In `xy` coordinates, as above but the angle is now measured from the 'x' or horizontal axis. ",
                    "perimeter": "Perimeter of object which approximates the contour as a line through the centers of border pixels using a 4-connectivity. ",
                    "solidity": "Ratio of pixels in the region to pixels of the convex hull image."
                    }





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

        ## fileload
        # Note: file can either be read directly from file or from clickpoints, however in case of 14 bit files these are already converted to 8bit!
        self.addOption(key="file_source", display_name="File Source", default='file', value_type="choice_string",
                       values=["file","clickpoints"], tooltip="Read src data from file or from clickpoints (8 bit only!)")

        ## segmentation
        self.addOption(key="segmentation_layer", display_name="Segmentation Layer", default=layers[0], value_type="choice_string",
                       values=layers, tooltip="The layer on which to segment the image")
        self.addOption(key="segmentation_invert_mask", display_name="Invert Mask", default=False, value_type="bool",
                       tooltip="If true, inverts the mask, so that darker areas are marked instead of brighter ones.")
        self.addOption(key="segmentation_mode", display_name="Segmentation Mode", default="th_simple", value_type="choice_string",
                       values=["th_simple","th_local", "th_lukas", "th_elham"], tooltip="segmentation approach")

        # preprocessing
        self.addOption(key="segmentation_gauss", display_name="Gauss Sigma\t", default=1.25, value_type="float",
                       min_value=0, max_value=25, tooltip="Width of the gaussian used to smooth the image")
        # th_simple
        self.addOption(key="segmentation_th", display_name="Threshold Segmentation", default=125, value_type="int",
                       min_value=1, max_value=255, tooltip="Threshold for binary segmentation")
        # th_local
        self.addOption(key="segmentation_localth_block_size", display_name="Block Radius", default=16, value_type="int",
                       min_value=0, max_value=200, tooltip="Block radius used for local thresholding")
        self.addOption(key="segmentation_localth_min_size", display_name="Min object size", default=31, value_type="int",
                       min_value=0, max_value=100, tooltip="Objects below this size will be removed")

        # th_elham
        self.addOption(key="segmentation_EL_min_size", display_name="Min object size", default=1, value_type="int",
                       min_value=1, max_value=10, tooltip="Size of the DISK shaped element for the binary open operation")
        self.addOption(key="segmentation_EL_max_size", display_name="Max object size", default=1, value_type="int",
                       min_value=1, max_value=10, tooltip="Size of the DISK shaped element for the binary open operation")
        self.addOption(key="segmentation_EL_low_th", display_name="Lower Canny threshold", default=0.9, value_type="float",
                       min_value=0, max_value=1, tooltip="Minimal value for canny clipping")
        self.addOption(key="segmentation_EL_high_th", display_name="Upper Canny threshold", default=0.99, value_type="float",
                       min_value=0, max_value=1, tooltip="Minimal value for canny clipping")

        # post processing
        self.addOption(key="segmentation_slm_size", display_name="opening DISK size", default=2, value_type="int",
                       min_value=0, max_value=10, tooltip="Size of the DISK shaped element for the binary open operation")

        self.addOption(key="segmentation_auto_apply", display_name="Auto Apply", default=False, value_type="bool",
                       tooltip="If enabled, changes of the parameters will automatically trigger a new segmentation")

        ## evaluation
        self.addOption(key="evaluation_layer", display_name="Evaluation Layer", default=layers[0], value_type="choice_string",
                       values=layers, tooltip="The layer on which to evaluate the mask",)

        self.regionsprops_actOptions = {}
        self.regionsprops_minOptions = {}
        self.regionsprops_maxOptions = {}
        for key in REGIONPROPS_TYPE:
            self.addOption(key="evaluation_act_%s"%(key), display_name=key, default=False, value_type="bool",
                           tooltip="Use %s to filter output\n%s : %s"%(key, key, REGIONPROPS_HELP[key]))
            self.regionsprops_actOptions[key] = "evaluation_act_%s"%(key)
            self.addOption(key="evaluation_min_%s"%(key), display_name="Min %s"%key, default=REGIONPROPS_MINMAXDEF[key][2],
                           value_type=REGIONPROPS_TYPE[key], min_value=REGIONPROPS_MINMAXDEF[key][0], max_value=REGIONPROPS_MINMAXDEF[key][1],
                           tooltip="%s :\n %s"%(key, REGIONPROPS_HELP[key]))
            self.regionsprops_minOptions[key] = "evaluation_min_%s"%(key)
            self.addOption(key="evaluation_max_%s"%(key), display_name="Max %s"%key, default=REGIONPROPS_MINMAXDEF[key][3],
                           value_type=REGIONPROPS_TYPE[key], min_value=REGIONPROPS_MINMAXDEF[key][0], max_value=REGIONPROPS_MINMAXDEF[key][1],
                           tooltip="%s :\n %s"%(key, REGIONPROPS_HELP[key]))
            self.regionsprops_maxOptions[key] = "evaluation_max_%s"%(key)
        self.regionsprops_Options = list(self.regionsprops_actOptions.values()) + list(self.regionsprops_maxOptions.values()) + list(self.regionsprops_minOptions.values())

        # define options groups for unified callback handling, e.g only call an update if parameter of this group was changed
        self.options_Segmentation = ['segmentation_th', 'segmentation_slm_size','segmentation_gauss','segmentation_invert_mask','segmentation_layer',
                                     'segmentation_localth_block_size', 'segmentation_localth_min_size',
                                     "segmentation_EL_min_size", "segmentation_EL_max_size","segmentation_EL_low_th","segmentation_EL_high_th"]

        self.options_Output = ['evaluation_min_area', 'evaluation_layer'] + self.regionsprops_Options

        self.addOption(key="batchsegment", display_name="Batch Segment Images", default=False, value_type="bool", tooltip="Create new masks for images while batch processing them.")
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
        self.setMinimumHeight(900)
        self.layout = QtWidgets.QVBoxLayout(self)

        """ groupbox SEGMENTATION"""
        # use a groupbox for each task
        self.segmentation_groupbox = QtWidgets.QGroupBox("Segmentation")
        self.layout.addWidget(self.segmentation_groupbox)

        # add a layout for elements
        self.segmentation_layout = QtWidgets.QVBoxLayout()
        self.segmentation_groupbox.setLayout(self.segmentation_layout)

        self.file_source_mode = self.inputOption("file_source", self.segmentation_layout)
        self.segmentationLayer = self.inputOption("segmentation_layer", self.segmentation_layout)

        self.segmentation_layout.addWidget(QtWidgets.QLabel("<b>Pre-Processing</b>"))
        self.inputGauss = self.inputOption("segmentation_gauss", self.segmentation_layout, use_slider=True)

        self.segmentation_layout.addWidget(QtWidgets.QLabel("<b>Segmentation</b>"))
        self.selectSegMode = self.inputOption("segmentation_mode", self.segmentation_layout)

        # MODE th_simple
        self.sliderSegmentationTH = self.inputOption("segmentation_th", self.segmentation_layout, use_slider=True)

        # MODE th_local
        self.sliderBlocksize = self.inputOption("segmentation_localth_block_size", self.segmentation_layout, use_slider=True)
        self.sliderMinsize = self.inputOption("segmentation_localth_min_size", self.segmentation_layout, use_slider=True)

        # Mode th_elham
        self.sliderELMinsize = self.inputOption("segmentation_EL_min_size", self.segmentation_layout, use_slider=True)
        self.sliderELMaxsize = self.inputOption("segmentation_EL_max_size", self.segmentation_layout, use_slider=True)
        self.sliderELLowThreshold = self.inputOption("segmentation_EL_low_th", self.segmentation_layout, use_slider=True)
        self.sliderELHighThreshold = self.inputOption("segmentation_EL_high_th", self.segmentation_layout, use_slider=True)

        self.segmentation_layout.addWidget(QtWidgets.QLabel("<b>Post-Processing</b>"))
        self.sliderSelemSize = self.inputOption("segmentation_slm_size", self.segmentation_layout, use_slider=True)

        self.checkboxInvert = self.inputOption("segmentation_invert_mask", self.segmentation_layout)
        self.checkboxSegmentation = self.inputOption("segmentation_auto_apply", self.segmentation_layout)

        self.segmode_simpleTH = [self.sliderSegmentationTH ]
        self.segmode_localTH = [self.sliderBlocksize, self.sliderMinsize]
        self.segmode_elhamTH = [self.sliderELMinsize, self.sliderELMaxsize, self.sliderELLowThreshold, self.sliderELHighThreshold]
        self.segmode_all = self.segmode_simpleTH + self.segmode_localTH + self.segmode_elhamTH

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

        self.evalInputs = {}
        self.evalLayouts = {}
        for i, key in enumerate(REGIONPROPS_TYPE):
            self.evalLayouts[key] = QtWidgets.QHBoxLayout()
            self.position_layout.addLayout(self.evalLayouts[key])
            self.evalInputs[key] = [
                self.inputOption(self.regionsprops_actOptions[key], self.evalLayouts[key]),
                self.inputOption(self.regionsprops_minOptions[key], self.evalLayouts[key], use_slider=True),
                self.inputOption(self.regionsprops_maxOptions[key], self.evalLayouts[key], use_slider=True)]


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
        self.buttonSegAll = self.inputOption("batchsegment", self.batch_layout)
        self.batch_layout.addWidget(self.buttonProcAll)
        self.buttonProcAll.released.connect(self.processAll)

        """ update view """
        self.updateSegmentationMode()
        self.updateFilterMode()

    def optionsChanged(self, key):
        print("optionsChanged:\t",key)
        print(key in self.regionsprops_actOptions.values())
        if key in self.options_Segmentation and self.getOption("segmentation_auto_apply"):
            self.updateSegmentation()
        elif key in self.options_Output:
            pass
        elif key == 'segmentation_mode':
            print("Mode changed to ", self.getOption("segmentation_mode"))
            self.updateSegmentationMode()
        if key in self.regionsprops_actOptions.values():
            self.updateFilterMode()

    def updateSegmentationMode(self):
        """
        Trigger on change Mode
        Hide and Show elements related to the current segmentation mode

        """

        if self.getOption("segmentation_mode") == "th_local":
            _ = [ e.setVisible(False) for e in self.segmode_all]
            _ = [ e.setVisible(True) for e in self.segmode_localTH]

        if self.getOption("segmentation_mode") == "th_lukas":
            _ = [e.setVisible(False) for e in self.segmode_all]
            _ = [e.setVisible(True) for e in self.segmode_localTH]

        elif self.getOption("segmentation_mode") == "th_simple":
            _ = [ e.setVisible(False) for e in self.segmode_all]
            _ = [ e.setVisible(True) for e in self.segmode_simpleTH]

        elif self.getOption("segmentation_mode") == "th_elham":
            _ = [ e.setVisible(False) for e in self.segmode_all]
            _ = [ e.setVisible(True) for e in self.segmode_elhamTH]

    def updateFilterMode(self):
        for key in self.regionsprops_actOptions:
            if self.getOption(self.regionsprops_actOptions[key]):
                self.evalInputs[key][1].setVisible(True)
                self.evalInputs[key][2].setVisible(True)
            else:
                self.evalInputs[key][1].setVisible(False)
                self.evalInputs[key][2].setVisible(False)



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

        if self.getOption("file_source") == "clickpoints":
            img = self.qimg.data
        elif self.getOption("file_source") == "file":
            # img = imread(os.path.join(list(self.db.getPaths())[0].path, self.qimg.filename))
            img = imread(os.path.join(self.qimg.path.path, self.qimg.filename))

        # convert rgb to grayscale
        if img.shape[-1] == 3:
            img = rgb2grey(img)
            # convert to 0-255 range if applicable
            if img.max() <= 1.0:
                img*=255

        ### pre processing ###
        if self.inputGauss.value() > 0:
            img = gaussian_filter(img, self.getOption("segmentation_gauss"))
            #print("apply Gauss with value", self.getOption("segmentation_gauss"))


        ### segmentation ###
        """
        NOTE:
        add additional approaches here, please follow the provided samples
        return should be binary mask in uint8 dtype
        """

        mode = self.getOption("segmentation_mode")
        # create binary mask
        mask = np.zeros(img.shape, dtype='uint8')
        if mode == "th_simple":
            if self.getOption("segmentation_invert_mask"):
                mask[img < self.getOption("segmentation_th")] = 1
            else:
                mask[img > self.getOption("segmentation_th")] = 1

        if mode == "th_local":
            local_thresh = threshold_local(img, block_size=self.getOption("segmentation_localth_block_size")*2-1)
            if self.getOption("segmentation_invert_mask"):
                mask[img < local_thresh] = 1
            else:
                mask[img > local_thresh] = 1

        if mode == "th_lukas":
            local_thresh = threshold_local(img, block_size=self.getOption("segmentation_localth_block_size")*2-1)
            img_thresh = (img > local_thresh) + 0
            img_erosion = binary_erosion(img_thresh)
            img_re_small = remove_small_objects(img_erosion, min_size=self.getOption("segmentation_localth_min_size"))
            img_gaus = gaussian(img_re_small)
            otsu_th = threshold_otsu(img_gaus)
            img_otsu = (img_gaus > otsu_th) + 0
            mask = (binary_fill_holes(img_otsu) + 0).astype('uint8')

        if mode == "th_elham":
            struct = disk(self.getOption("segmentation_EL_min_size"))#structural element for binary erosion
            # "segmentation_EL_min_size", "segmentation_EL_max_size","segmentation_EL_low_th","segmentation_EL_high_th"
            mask = canny(img, sigma=1, low_threshold=self.getOption("segmentation_EL_low_th"), high_threshold=self.getOption("segmentation_EL_high_th"),use_quantiles=True)  # edge detection
            mask = binary_fill_holes(mask, structure=struct) #fill holes
            mask = binary_erosion(mask, structure=struct).astype(np.uint8)  # erode to remove lines and small schmutz

        # use open operation to reduce noise
        if self.getOption("segmentation_slm_size") != 0:
            mask_open = opening(mask, disk(self.getOption("segmentation_slm_size")))
        else:
            mask_open = mask

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

        if self.getOption("file_source") == "clickpoints":
            img = self.qimg.data
        elif self.getOption("file_source") == "file":
            img = imread(os.path.join(list(self.db.getPaths())[0].path, self.qimg.filename))

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
        regions = regionprops(mask_labeled, img)

        # iterate over properties and set marker for display
        passed = {}
        cell_markers = {}
        for nr,region in enumerate(regions):
            passed[nr] = True
            text = ""
            for key in self.regionsprops_actOptions:
                if self.getOption(self.regionsprops_actOptions[key]):
                    if self.evalInputs[key][1].value()<=region[key]<=self.evalInputs[key][2].value():
                        text += "\n%s= %.2f"%(key, region[key])
                        pass
                    else:
                        passed[nr] = False
                        break
            if passed[nr]:
                cell_markers[nr] = self.db.setMarker(image=self.qimg, x=region.centroid[1], y=region.centroid[0],
                                  text='Cell $marker_id%s' % (text), type='cell (auto)')

        # update CP display to show marker
        self.cp.reloadMarker()

        # store parameters in Pandas DF
        results = []
        for nr, prop in enumerate(regions):
            # if prop.area > self.inputMinSize.value():
            if passed[nr]:
                tmp = dotdict()
                tmp.frame = cell_markers[nr].image.sort_index
                tmp.nr = cell_markers[nr].id
                tmp.filename = self.qimg.filename
                tmp.centroid_x = prop.centroid[0]
                tmp.centroid_y = prop.centroid[1]

                for key in REGIONPROPS_TYPE:
                    tmp[key]=prop[key]
                # tmp.area = prop.area
                # tmp.mean_intensity = prop.mean_intensity
                # tmp.equivalent_diameter = prop.equivalent_diameter
                # tmp.axis_minor = prop.minor_axis_length
                # tmp.axis_major = prop.major_axis_length

                results.append(tmp)
        columns = ["frame", "nr", "filename", "centroid_x", "centroid_y", *REGIONPROPS_TYPE.keys()]

        df = pd.DataFrame.from_records(results, columns=columns)
        # print(df)

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
            self.cp.jumpToFrameWait(q_img.sort_index)
            print("Batch processing Image Nr %d" % q_img.sort_index)

            if self.getOption("batchsegment"):
                self.updateSegmentation(qimg=q_img)
            df = self.updateProperties(qimg=q_img)
            results.append(df)

        if save_properties:
            df_all = pd.concat(results)
            df_all = df_all.reset_index()
            df_all = df_all.drop(columns=["index"])
            df_all.to_excel(os.path.splitext(self.qimg.filename)[0][0:15] + '_eval_summary.xls')

    """ DEFAULT ADDON FUNCTIONS """
    def buttonPressedEvent(self):
        # show the addon window when the button in ClickPoints is pressed
        self.show()
