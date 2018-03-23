#!/usr/bin/env python
# -*- coding: utf-8 -*-
# CellDetector.py

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

import numpy as np
from qtpy import QtCore, QtWidgets
from skimage.measure import label, regionprops

import clickpoints


class QParameterEdit(QtWidgets.QWidget):
    no_edit = False

    def __init__(self, parameter, layout):
        super().__init__()
        self.parameter = parameter
        if layout is not None:
            layout.addWidget(self)

        self.type = parameter.type

        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.label = QtWidgets.QLabel(parameter.name)
        self.layout.addWidget(self.label)

        if self.parameter.desc is not None:
            self.setToolTip(self.parameter.desc)

    def setValue(self, x):
        if self.no_edit:
            return
        self.no_edit = True
        self.doSetValue(x)
        self.parameter.value = self.type(x)
        self.parameter.valueChanged()
        self.no_edit = False

    def doSetValue(self, x):
        self.parameter.value = x


class QNumberChooser(QParameterEdit):
    def __init__(self, parameter, layout, type_int):
        super().__init__(parameter, layout)
        self.slider = QtWidgets.QSlider()
        self.layout.addWidget(self.slider)
        self.slider.setOrientation(QtCore.Qt.Horizontal)

        if type_int:
            self.spinBox = QtWidgets.QSpinBox()
        else:
            self.spinBox = QtWidgets.QDoubleSpinBox()
        self.layout.addWidget(self.spinBox)

        if parameter.min is not None:
            self.spinBox.setMinimum(parameter.min)
            self.slider.setMinimum(parameter.min)
        if parameter.max is not None:
            self.spinBox.setMaximum(parameter.max)
            self.slider.setMaximum(parameter.max)

        self.setValue(parameter.value)

        self.spinBox.valueChanged.connect(self.setValue)
        self.slider.valueChanged.connect(self.setValue)

    def doSetValue(self, x):
        self.spinBox.setValue(x)
        self.slider.setValue(x)


class QStringChooser(QParameterEdit):

    def __init__(self, parameter, layout):
        super().__init__(parameter, layout)
        self.edit = QtWidgets.QLineEdit()
        self.layout.addWidget(self.edit)

        self.setValue(parameter.value)

        self.edit.textChanged.connect(self.setValue)

    def doSetValue(self, x):
        self.edit.setText(x)


class QBoolChooser(QParameterEdit):
    def __init__(self, parameter, layout):
        super().__init__(parameter, layout)
        self.check = QtWidgets.QCheckBox()
        self.layout.addWidget(self.check)

        self.setValue(parameter.value)

        self.check.stateChanged.connect(self.setValue)

    def doSetValue(self, x):
        self.check.setChecked(x)


class QChoiceChooser(QParameterEdit):
    def __init__(self, parameter, layout):
        super().__init__(parameter, layout)
        self.comboBox = QtWidgets.QComboBox()
        self.layout.addWidget(self.comboBox)
        for value in parameter.values:
            self.comboBox.addItem(str(value))

        self.setValue(parameter.value)

        self.comboBox.currentTextChanged.connect(self.setValue)

    def doSetValue(self, x):
        self.comboBox.setCurrentText(str(x))


class Parameter(object):
    def __init__(self, key, default=0, name=None, min=None, max=None, range=None, values=None, value_type=None,
                 desc=None):
        self.key = key
        self.default = default
        self.name = name
        self.min = min
        self.max = max
        if range is not None:
            self.min = range[0]
            self.max = range[1]
        self.values = values
        self.type = value_type
        self.desc = desc

        if value_type is None:
            self.type = type(default)

        self.value = self.default
        if self.name is None:
            self.name = self.key

    def addWidget(self, layout):
        if self.values is not None:
            return QChoiceChooser(self, layout)
        if self.type == int:
            return QNumberChooser(self, layout, type_int=True)
        if self.type == float:
            return QNumberChooser(self, layout, type_int=False)
        if self.type == str:
            return QStringChooser(self, layout)
        if self.type == bool:
            return QBoolChooser(self, layout)
        print("type", self.type, "not recognized")

    def valueChanged(self):
        pass


class ParameterList(object):
    def __init__(self, *parameters):
        self.parameters = parameters
        for parameter in self.parameters:
            parameter.valueChanged = self.valueChanged

    def addWidgets(self, layout):
        group = QtWidgets.QGroupBox("Parameters")
        layout.addWidget(group)
        layout = QtWidgets.QVBoxLayout(group)
        widgets = []
        for parameter in self.parameters:
            widgets.append(parameter.addWidget(layout))
        return group

    def __getitem__(self, item):
        for parameter in self.parameters:
            if parameter.key == item:
                return parameter.value

    def valueChanged(self):
        self.valueChangedEvent()

    def valueChangedEvent(self):
        pass


class Detector(object):
    """
    This Class describes the abstract function of a detector in the pengu-track package.
    It is only meant for subclassing.
    """

    def __init__(self):
        super(Detector, self).__init__()
        self.parameters = ParameterList()

    def detect(self, image):
        return np.random.rand((1, 2)), None


class DetectorThreshold(Detector):
    """
    This Class describes the abstract function of a detector in the pengu-track package.
    It is only meant for subclassing.
    """

    def __init__(self):
        super(Detector, self).__init__()

        # define the parameters of the detector
        self.parameters = ParameterList(Parameter("threshold", 128, range=[0, 255]),
                                        Parameter("invert", False),
                                        Parameter("mode", "test", values=["bla", "blub", "test", "heho"]))

    def detect(self, image):
        # threshold the image
        mask = (image > self.parameters["threshold"]).astype("uint8")
        # invert it
        if self.parameters["invert"]:
            mask = 1 - mask
        # find all regions
        props = regionprops(label(mask))
        # get the positions of the regions
        positions = np.array([(prop.centroid[1] + 0.5, prop.centroid[0] + 0.5) for prop in props])
        # return positions and mask
        return positions, mask


class DetectorRandom(Detector):
    """
    This Class describes the abstract function of a detector in the pengu-track package.
    It is only meant for subclassing.
    """

    def __init__(self):
        super(Detector, self).__init__()

        self.parameters = ParameterList(Parameter("count", 128, min=0, max=255))

    def detect(self, image):
        return np.random.rand(self.parameters["count"], 2) * np.array(image.shape)[::-1], None


class Addon(clickpoints.Addon):
    auto_apply = False
    scheduled_run = True

    detector = None
    parameter_widget = None

    def __init__(self, *args, **kwargs):
        clickpoints.Addon.__init__(self, *args, **kwargs)

        self.layout = QtWidgets.QVBoxLayout(self)

        # Check if the marker type is present
        #self.marker_type_truth = self.db.setMarkerType("ground_truth", "#0a2eff", self.db.TYPE_Normal)
        self.marker_type_detection = self.db.setMarkerType("detected_point", "#ff1150", self.db.TYPE_Normal)
        #self.marker_type_hit = self.db.setMarkerType("detected_point (hit)", "#19ff66", self.db.TYPE_Normal)
        self.cp.reloadTypes()

        self.detector_classes = [DetectorThreshold, DetectorRandom]

        self.comboBox = QtWidgets.QComboBox()
        self.layout.addWidget(self.comboBox)
        self.comboBox.addItem("-- select detector --")
        for value in self.detector_classes:
            self.comboBox.addItem(value.__name__)

        self.comboBox.currentTextChanged.connect(self.selectDetector)

        self.layout_parameters = QtWidgets.QVBoxLayout()
        self.layout.addLayout(self.layout_parameters)
        self.layout.addStretch()

        self.layout_buttons = QtWidgets.QHBoxLayout()
        self.layout.addLayout(self.layout_buttons)

        self.button = QtWidgets.QPushButton("apply")
        self.layout_buttons.addWidget(self.button)
        self.button.clicked.connect(self.run_threaded)

        self.button2 = QtWidgets.QPushButton("auto apply")
        self.button2.setCheckable(True)
        self.layout_buttons.addWidget(self.button2)
        self.button2.clicked.connect(self.autoApply)

    def selectDetector(self):
        self.detector = self.detector_classes[self.comboBox.currentIndex()-1]()
        self.detector.parameters.valueChangedEvent = self.valueChanged

        if self.parameter_widget:
            self.parameter_widget.setParent(None)
            self.layout_parameters.removeWidget(self.parameter_widget)
            self.parameter_widget = None

        self.parameter_widget = self.detector.parameters.addWidgets(self.layout_parameters)

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
                self.run_threaded()
            # if not, schedule it
            else:
                self.scheduled_run = True

    def buttonPressedEvent(self):
        self.show()

    def run_stopped(self):
        super(Addon, self).run_stopped()
        if self.scheduled_run:
            # if we have scheduled to run a detection, start it with a single shot timer
            self.timer = QtCore.QTimer()
            self.timer.setSingleShot(0)
            self.timer.timeout.connect(self.run_threaded)
            self.timer.start()

    def run(self, start_frame=0):
        # clear the scheduled run
        self.scheduled_run = False

        # get the current frame
        frame = self.cp.getCurrentFrame()

        # remove all previous markers
        self.db.deleteMarkers(frame=frame, type=self.marker_type_detection)

        # detect the current image with the detector
        positions, mask = self.detector.detect(self.db.getImage(frame).data)

        # if the detector has returned positions, display them
        if len(positions):
            self.db.setMarkers(frame=frame, x=positions[:, 0], y=positions[:, 1], type=self.marker_type_detection)
            self.cp.reloadMarker()

        # if the detector has returned a mask, draw the mask
        if mask is not None:
            self.db.setMask(frame=frame, data=mask)
            self.cp.reloadMask()
