#!/usr/bin/env python
# -*- coding: utf-8 -*-
# FilelistLoader.py

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

from __future__ import division, print_function, unicode_literals
import os
import glob
import time
from datetime import datetime

from includes import BroadCastEvent2

from qtpy import QtGui, QtCore, QtWidgets
import qtawesome as qta
from QtShortCuts import AddQLabel, AddQSpinBox, AddQCheckBox, AddQHLine, AddQLineEdit

class OptionEditor(QtWidgets.QWidget):
    def __init__(self, window, data_file):
        QtWidgets.QWidget.__init__(self)
        self.window = window
        self.data_file = data_file

        # Widget
        self.setMinimumWidth(500)
        self.setMinimumHeight(200)
        self.setWindowTitle("Options - ClickPoints")
        self.layout = QtWidgets.QVBoxLayout(self)

        self.setWindowIcon(qta.icon("fa.gears"))

        for category in self.data_file._options:
            AddQHLine(self.layout)
            AddQLabel(self.layout, category)

            for option in self.data_file._options[category]:
                value = option.value if option.value is not None else option.default
                if option.value_type == "int":
                    if option.value_count > 1:
                        edit = AddQLineEdit(self.layout, option.key, ", ".join(str(v) for v in value))
                        edit.textChanged.connect(lambda value, edit=edit, option=option: self.Changed(edit, value, option))
                    else:
                        edit = AddQSpinBox(self.layout, option.key, int(value), float=False)
                        edit.valueChanged.connect(lambda value, edit=edit, option=option: self.Changed(edit, value, option))
                if option.value_type == "float":
                    edit = AddQSpinBox(self.layout, option.key, float(value), float=True)
                    edit.valueChanged.connect(lambda value, edit=edit, option=option: self.Changed(edit, value, option))
                if option.value_type == "bool":
                    edit = AddQCheckBox(self.layout, option.key, value)
                    edit.stateChanged.connect(lambda value, edit=edit, option=option: self.Changed(edit, value, option))
                if option.value_type == "string":
                    edit = AddQLineEdit(self.layout, option.key, value)
                    edit.textChanged.connect(lambda value, edit=edit, option=option: self.Changed(edit, value, option))

    def Changed(self, field, value, option):
        if option.value_type == "int":
            if option.value_count > 1:
                value = value.strip()
                if (value.startswith("(") and value.endswith(")")) or (value.startswith("[") and value.endswith("]")):
                    value = value[1:-1].strip()
                try:
                    value = [int(v) for v in value.split(",")]
                except ValueError:
                    field.setStyleSheet("background-color: #FDD;")
                    return
                if len(value) != option.value_count:
                    field.setStyleSheet("background-color: #FDD;")
                    return
                else:
                    field.setStyleSheet("")
            else:
                value = int(value)
        if option.value_type == "float":
            value = float(value)
        if option.value_type == "bool":
            value = bool(value)
        self.data_file.setOption(option.key, value)