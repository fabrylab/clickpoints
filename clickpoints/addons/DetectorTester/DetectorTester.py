#!/usr/bin/env python
# -*- coding: utf-8 -*-
# DetectorTester.py

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

import numpy as np
import qtawesome as qta
from qtpy import QtCore, QtWidgets

import clickpoints
from clickpoints.includes.QtShortCuts import AddQSpinBox, AddQOpenFileChoose
from clickpoints.includes import QtShortCuts

from inspect import getdoc
from PenguTrack import Detectors
import traceback
import os
import sys
from importlib import import_module, reload


def loadModule(path, module=None):
    folder, filename = os.path.split(path)
    path, folder = os.path.split(folder)
    basefilename, ext = os.path.splitext(filename)

    sys.path.insert(0, path)

    try:
        if module is None:
            try:
                print("import", folder + "." + basefilename)
                addon_module = import_module(folder + "." + basefilename)
            except Exception as err:
                raise err
            loaded = True
        else:
            addon_module = reload(module)
    finally:
        sys.path.pop(0)
    return addon_module


def getClassDefinitions(module, baseclass):
    class_definitions = []
    for name in dir(module):
        current_class_definition = getattr(module, name)
        try:
            if issubclass(current_class_definition, baseclass) and current_class_definition != baseclass:
                class_definitions.append(current_class_definition)
        except TypeError:
            pass
    return class_definitions


def getEvalValuesGT(groundtruth_pos, pos_program, distance_cost_parameter):
    from scipy.optimize import linear_sum_assignment
    from scipy.spatial import distance

    # if no detections are found
    if len(pos_program) == 0:
        tp_ind = np.array([], dtype="uint64")
        fp_ind = np.array([], dtype="uint64")
        fn_ind = np.arange(len(groundtruth_pos), dtype="uint64")
    elif len(groundtruth_pos) == 0:
        tp_ind = np.array([], dtype="uint64")
        fp_ind = np.arange(len(pos_program), dtype="uint64")
        fn_ind = np.array([], dtype="uint64")
    else:
        # calculate all distances
        cost = distance.cdist(pos_program, groundtruth_pos, 'sqeuclidean')

        # solve the assignment to optimize the pairing
        # row_ind, col_ind = linear_sum_assignment(cost)
        from PenguTrack.Assignment import network_assignment
        row_ind, col_ind = network_assignment(cost, threshold=distance_cost_parameter**2)

        # get the distances for the matches
        distance_cost = cost[row_ind, col_ind]

        # filter by distance
        row_ind = row_ind[np.array(distance_cost) < distance_cost_parameter**2]
        col_ind = col_ind[np.array(distance_cost) < distance_cost_parameter**2]

        # true positives = objects that have both been clicked by the user and were found by the detector
        tp_ind = row_ind.astype("uint64")
        # false positive = objects, which were found by the detector, but were not clicked by the user
        fp_ind = np.array(list(set(np.arange(0, len(pos_program))) - set(tp_ind)), dtype="uint64")
        # false negatives = objects, which were clicked by the user, but were not found by the detector
        fn_ind = np.array(list(set(np.arange(0, len(groundtruth_pos))) - set(col_ind)), dtype="uint64")

    # count
    fp = len(fp_ind)
    fn = len(fn_ind)
    tp = len(tp_ind)

    # calculate the values
    try:
        FAR = fp / (tp + fp)  # False Alarm Rate - Anzahl, wie oft ein Objekt falsch vom Detektor erkannt wird
    except ZeroDivisionError:
        FAR = 0
    try:
        DR = tp / (tp + fn)  # Detection Rate - Anzahl, wie viele Objektive richtig detektiert wurden (Prozent)
    except ZeroDivisionError:
        DR = 0
    try:
        PR = tp / (tp + fp)  # precision - Anzahl, wie viele Objekte von Detektor gefunden wurde, aber nicht geklickt
    except ZeroDivisionError:
        PR = 0
    eval_values = {}
    eval_values.update(False_Alarm_Rate=np.round(FAR, decimals=2), Detection_Rate=np.round(DR, decimals=2),
                       Precision=np.round(PR, decimals=2), fp=fp, fn=fn, tp=tp)

    return eval_values, tp_ind, fp_ind, fn_ind



class Addon(clickpoints.Addon):
    auto_apply = False
    scheduled_run = True

    detector = None
    parameter_widget = None

    display_ranges = False

    def __init__(self, *args, **kwargs):
        clickpoints.Addon.__init__(self, *args, **kwargs)

        self.layout = QtWidgets.QVBoxLayout(self)

        # Check if the marker type is present
        self.marker_type_truth = self.db.setMarkerType("ground truth", "#0a2eff", self.db.TYPE_Normal)
        self.marker_type_truth_region = self.db.setMarkerType("ground truth region", "#035bff", self.db.TYPE_Rect)
        self.marker_type_true_positive = self.db.setMarkerType("true positive", "#19ff66", self.db.TYPE_Normal)
        self.marker_type_false_positive = self.db.setMarkerType("false positive", "#ff1150", self.db.TYPE_Normal)
        self.marker_type_false_negative = self.db.setMarkerType("false negative", "#ff730f", self.db.TYPE_Normal, style='{"shape":"ring", "scale":2}')
        self.cp.reloadTypes()

        self.input_groundtruth_marktertype = QtShortCuts.QInputChoice(self.layout, "Groundtruth Markertype", value="ground truth", value_names=[n.name for n in self.db.getMarkerTypes()], values=[n for n in self.db.getMarkerTypes()])

        self.distance_cost_parameter = QtShortCuts.QInputNumber(self.layout, "Max Distance to Groundtruth", 10, False)

        self.detector_file = QtShortCuts.QInputFilename(self.layout, "Detector File:", "", file_type="Python File (*.py)", existing=True)
        self.detector_file.valueChanged.connect(self.detectorFileSelected)
        self.detector_file_button_reload = QtWidgets.QPushButton()
        self.detector_file_button_reload.setIcon(qta.icon("fa.repeat"))
        self.detector_file_button_reload.clicked.connect(self.detectorFileSelected)
        self.detector_file.layout().addWidget(self.detector_file_button_reload)

        self.detector_classes = getClassDefinitions(Detectors, Detectors.Detector)#[DetectorThreshold, DetectorRandom]

        self.comboBox = QtWidgets.QComboBox()
        self.layout.addWidget(self.comboBox)

        self.detectorModuleChanged(Detectors)

        self.comboBox.currentTextChanged.connect(self.selectDetector)

        self.label_description = QtWidgets.QLabel()
        self.layout.addWidget(self.label_description)

        self.layout_parameters = QtWidgets.QVBoxLayout()
        self.layout.addLayout(self.layout_parameters)
        self.layout.addStretch()

        self.layout_buttons = QtWidgets.QHBoxLayout()
        self.layout.addLayout(self.layout_buttons)

        self.optimization_count = QtShortCuts.QInputNumber(self.layout, "Optimizer iterations", 100, float=False)
        self.optimization_count.setHidden(True)

        self.button = QtWidgets.QPushButton("apply")
        self.layout_buttons.addWidget(self.button)
        self.button.clicked.connect(self.start_detect_and_show)

        self.button2 = QtWidgets.QPushButton("auto apply")
        self.button2.setCheckable(True)
        self.layout_buttons.addWidget(self.button2)
        self.button2.clicked.connect(self.autoApply)

        self.button4 = QtWidgets.QPushButton("run optimisation")
        self.button4.setHidden(True)
        self.layout_buttons.addWidget(self.button4)
        self.button4.clicked.connect(self.start_optimize)

        self.button3 = QtWidgets.QPushButton("optimize")
        self.button3.setCheckable(True)
        self.layout_buttons.addWidget(self.button3)
        self.button3.clicked.connect(self.display_optimize)

        self.progressbar = QtWidgets.QProgressBar()
        self.layout.addWidget(self.progressbar)

    def detectorModuleChanged(self, module):
        for i in range(len(self.detector_classes)+1):
            self.comboBox.removeItem(0)
        self.detector_classes = getClassDefinitions(module, Detectors.Detector)
        self.comboBox.addItem("-- select detector --")
        for value in self.detector_classes:
            self.comboBox.addItem(value.__name__)

    def detectorFileSelected(self):
        filename = self.detector_file.value()
        module = loadModule(filename)
        module = loadModule(filename, module)
        self.detectorModuleChanged(module)


    def selectDetector(self):
        print("-->", self.detector_classes[self.comboBox.currentIndex() - 1])
        if self.comboBox.currentIndex() == 0:
            self.detector = None
            self.label_description.setText("No detector selected.")
        else:
            try:
                self.detector = self.detector_classes[self.comboBox.currentIndex() - 1]()
                self.detector.ParameterList.valueChangedEvent = self.valueChanged
            except Exception:
                traceback.print_exc()
                self.detector = None
                self.label_description.setText("Detector cannot be loaded.")

        if self.parameter_widget:
            self.parameter_widget.setParent(None)
            self.layout_parameters.removeWidget(self.parameter_widget)
            self.parameter_widget = None

        if self.detector is not None:
            self.label_description.setText(getdoc(self.detector))
            self.parameter_widget = self.detector.ParameterList.addWidgets(self.layout_parameters)
            self.detector.ParameterList.displayRanges(self.display_ranges)

    def autoApply(self):
        # toggle the auto-apply status
        self.auto_apply = not self.auto_apply
        # and (de)activate the apply button
        self.button.setDisabled(self.auto_apply)

    def valueChanged(self):
        # if the parameters were changed and we have auto-apply enabled, start a detection
        if self.auto_apply:
            # if the thread is not running, start to detect
            if not self.is_running():
                self.start_detect_and_show()
            # if not, schedule it
            else:
                self.scheduled_run = True

    def getGroundTruthPositions(self, frame):
        self.marker_type_truth = self.input_groundtruth_marktertype.value()
        return np.array([x for x in self.db.getMarkers(frame=frame, type=self.marker_type_truth).select(self.db.table_marker.x, self.db.table_marker.y).tuples().execute()])

    def checkGroundTruth(self, detections, frame):
        # get the ground-truth data
        groundtruth_pos = self.getGroundTruthPositions(frame)
        # compare it to the detections
        eval_values, tp_ind, fp_ind, fn_ind = getEvalValuesGT(groundtruth_pos, detections, self.distance_cost_parameter.value())
        # print the evaluation
        print(eval_values)
        return eval_values, detections[tp_ind], detections[fp_ind], groundtruth_pos[fn_ind]

    def buttonPressedEvent(self):
        self.show()

    def run_stopped(self):
        super(Addon, self).run_stopped()
        print("run_stopped", self.scheduled_run)
        if self.scheduled_run:
            # if we have scheduled to run a detection, start it with a single shot timer
            self.timer = QtCore.QTimer()
            self.timer.setSingleShot(0)
            self.timer.timeout.connect(self.start_detect_and_show)
            self.timer.start()
        else:
            if self.detector is not None:
                self.detector.ParameterList.updateWidgets()

    def start_detect_and_show(self):
        print("start_detect_and_show")
        self.run_threaded(function=self.detect_and_show)

    def filter_inside(self, positions, rectangles):
        if rectangles.count() == 0:
            return np.ones(len(positions), dtype="bool")
        valid = np.zeros(len(positions), dtype="bool")
        for rect in rectangles:
            valid += (rect.x <= positions[:, 0]) * (rect.x+rect.width >= positions[:, 0]) * \
                     (rect.y <= positions[:, 1]) * (rect.y+rect.height >= positions[:, 1])
        return valid

    def prepareDetectionParameters(self, current_frame, current_layer, detect):
        arguments = {}
        for parameter in detect.detection_parameters:
            name = parameter
            parameter = detect.detection_parameters[name]
            if "layer" in parameter:
                layer = parameter["layer"]
            else:
                layer = current_layer
            if "frame" in parameter:
                frame = parameter["frame"]
            else:
                frame = 0
            image = self.db.getImage(frame=(current_frame+frame), layer=layer)
            if image is None:
                arguments[name] = None
                continue
            if "mask" in parameter and parameter["mask"]:
                if image.mask is not None:
                    arguments[name] = image.mask.data
                else:
                    arguments[name] = None
            else:
                arguments[name] = image.data
        return arguments

    def detect_and_show(self, start_frame=0):
        self.progressbar.setRange(0, 0)
        # clear the scheduled run
        self.scheduled_run = False

        # get the current frame
        frame = self.cp.getCurrentFrame()
        layer = self.cp.window.layer

        # remove all previous markers
        self.db.deleteMarkers(frame=frame, type=self.marker_type_true_positive)
        self.db.deleteMarkers(frame=frame, type=self.marker_type_false_positive)
        self.db.deleteMarkers(frame=frame, type=self.marker_type_false_negative)

        # detect the current image with the detector
        arguments = self.prepareDetectionParameters(frame, layer, self.detector.detect)
        try:
            positions, mask = self.detector.detect(**arguments)
            positions = np.array(positions[["PositionX", "PositionY"]])
        except Exception:
            traceback.print_exc()
            positions = []
            mask = None

        # if the detector has returned positions, display them
        if len(positions):
            rectangles = self.db.getRectangles(frame=frame, type=self.marker_type_truth_region)
            inside = self.filter_inside(positions, rectangles)
            positions = positions[inside]
            eval_values, tp, fp, fn = self.checkGroundTruth(positions, frame)
            if len(tp):
                self.db.setMarkers(frame=frame, x=tp[:, 0], y=tp[:, 1], type=self.marker_type_true_positive)
            if len(fp):
                self.db.setMarkers(frame=frame, x=fp[:, 0], y=fp[:, 1], type=self.marker_type_false_positive)
            if len(fn):
                self.db.setMarkers(frame=frame, x=fn[:, 0], y=fn[:, 1], type=self.marker_type_false_negative)
            self.cp.reloadMarker()

        # if the detector has returned a mask, draw the mask
        if mask is not None:
            self.db.setMask(frame=frame, data=mask.astype("uint8"))
            self.cp.reloadMask()

        self.progressbar.setRange(0, 1)

    def start_optimize(self):
        self.run_threaded(function=self.do_optimize)

    def display_optimize(self):
        # toggle the auto-apply status
        self.display_ranges = not self.display_ranges
        # and (de)activate the apply button
        self.button.setHidden(self.display_ranges)
        self.button2.setHidden(self.display_ranges)
        self.button4.setHidden(not self.display_ranges)
        self.optimization_count.setHidden(not self.display_ranges)
        self.detector.ParameterList.displayRanges(self.display_ranges)

    def do_optimize(self, start=0):
        import skopt
        # get the current frame
        frame = self.cp.getCurrentFrame()
        layer = self.cp.window.layer
        arguments = self.prepareDetectionParameters(frame, layer, self.detector.detect)

        # get the ground-truth data
        groundtruth_pos = self.getGroundTruthPositions(frame)

        rectangles = self.db.getRectangles(frame=frame, type=self.marker_type_truth_region)

        self.iteration = 0
        self.max_iterations = self.optimization_count.value()
        #self.progressbar.setRange(0, self.max_iterations)

        def error(p):
            self.detector.ParameterList.setOptimisationValues(p)
            detections, mask = self.detector.detect(**arguments)
            detections = np.array(detections[["PositionX", "PositionY"]])

            if len(detections):
                inside = self.filter_inside(detections, rectangles)
                detections = detections[inside]

            # compare it to the detections
            eval_values, tp_ind, fp_ind, fn_ind = getEvalValuesGT(groundtruth_pos, detections,
                                                                  self.distance_cost_parameter.value())

            print("Iteration:", self.iteration, "Parameters:", p, "Precision", eval_values["Precision"])
            self.iteration += 1
            #self.progressbar.setValue(self.iteration)
            print("progress set")
            return 1-eval_values["Precision"]

        print("ranges", self.detector.ParameterList.getRanges())
        res = skopt.gp_minimize(error, self.detector.ParameterList.getRanges(), verbose=False, n_calls=self.max_iterations)
        print("update values")
        if self.auto_apply:
            self.auto_apply = False
        self.detector.ParameterList.setOptimisationValues(res.x, update_widgets=True)
        print("Result:", "Parameters:", res.x, "Precision", 1-res.fun)
        self.detect_and_show()
        #print(res)
