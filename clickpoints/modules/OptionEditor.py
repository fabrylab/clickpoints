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
from includes.QtShortCuts import AddQLabel, AddQSpinBox, AddQCheckBox, AddQHLine, AddQLineEdit, AddQComboBox
from includes import BroadCastEvent
from includes import LoadConfig


def PrittyPrintSize(bytes):
    if bytes > 1e9:
        return "%.1f GB" % ( bytes / 1e8)
    if bytes > 1e6:
        return "%.1f MB" % ( bytes / 1e6)
    if bytes > 1e3:
        return "%.1f kB" % ( bytes / 1e3)
    return "%d bytes" % (bytes)


class OptionEditorWindow(QtWidgets.QWidget):
    def __init__(self, window, data_file):
        QtWidgets.QWidget.__init__(self)
        self.window = window
        self.data_file = data_file

        # Widget
        self.setMinimumWidth(450)
        self.setMinimumHeight(200)
        self.setWindowTitle("Options - ClickPoints")

        self.main_layout = QtWidgets.QVBoxLayout(self)

        self.list_layout = QtWidgets.QVBoxLayout()
        self.stackedLayout = QtWidgets.QStackedLayout()
        self.top_layout = QtWidgets.QHBoxLayout()
        self.top_layout.addLayout(self.list_layout)
        self.main_layout.addLayout(self.top_layout)

        layout = QtWidgets.QHBoxLayout()
        self.button_export = QtWidgets.QPushButton("&Export")
        self.button_export.clicked.connect(self.Export)
        layout.addWidget(self.button_export)
        self.button_import = QtWidgets.QPushButton("&Import")
        self.button_import.clicked.connect(self.Import)
        layout.addWidget(self.button_import)
        layout.addStretch()
        self.button_ok = QtWidgets.QPushButton("&Ok")
        self.button_ok.clicked.connect(self.Ok)
        layout.addWidget(self.button_ok)
        self.button_cancel = QtWidgets.QPushButton("&Cancel")
        self.button_cancel.clicked.connect(self.Cancel)
        layout.addWidget(self.button_cancel)
        self.button_apply = QtWidgets.QPushButton("&Apply")
        self.button_apply.clicked.connect(self.Apply)
        self.button_apply.setDisabled(True)
        layout.addWidget(self.button_apply)
        self.main_layout.addLayout(layout)

        self.list = QtWidgets.QListWidget()
        self.list_layout.addWidget(self.list)
        self.list.setMaximumWidth(80)

        self.list.currentRowChanged.connect(self.stackedLayout.setCurrentIndex)
        self.top_layout.addLayout(self.stackedLayout)

        self.setWindowIcon(qta.icon("fa.gears"))

        self.edits = []
        self.edits_by_name = {}

        options = data_file.getOptionAccess()

        for category in self.data_file._options:
            count = len([option for option in self.data_file._options[category] if not option.hidden])
            if count == 0:
                continue
            item = QtWidgets.QListWidgetItem(category, self.list)

            group = QtWidgets.QGroupBox(category)
            group.setFlat(True)
            self.layout = QtWidgets.QVBoxLayout()
            group.setLayout(self.layout)
            self.stackedLayout.addWidget(group)

            for option in self.data_file._options[category]:
                if option.hidden:
                    continue
                value = option.value if option.value is not None else option.default
                if option.value_type == "int":
                    if option.value_count > 1:
                        edit = AddQLineEdit(self.layout, option.display_name, ", ".join(str(v) for v in value))
                        edit.textChanged.connect(lambda value, edit=edit, option=option: self.Changed(edit, value, option))
                    else:
                        edit = AddQSpinBox(self.layout, option.display_name, int(value), float=False)
                        if option.min_value is not None:
                            edit.setMinimum(option.min_value)
                        if option.max_value is not None:
                            edit.setMaximum(option.max_value)
                        edit.valueChanged.connect(lambda value, edit=edit, option=option: self.Changed(edit, value, option))
                        if getattr(option, "unit", None):
                            edit.setSuffix(" "+option.unit)
                    edit.editingFinished.connect(lambda edit=edit, option=option: self.ChangeFinished(edit, option))
                if option.value_type == "choice":
                    edit = AddQComboBox(self.layout, option.display_name, option.values, selectedValue=option.values[value])
                    edit.currentIndexChanged.connect(lambda value, edit=edit, option=option: self.Changed(edit, value, option))
                if option.value_type == "float":
                    edit = AddQSpinBox(self.layout, option.display_name, float(value), float=True)
                    if option.min_value is not None:
                        edit.setMinimum(option.min_value)
                    if option.max_value is not None:
                        edit.setMaximum(option.max_value)
                    edit.valueChanged.connect(lambda value, edit=edit, option=option: self.Changed(edit, value, option))
                if option.value_type == "bool":
                    edit = AddQCheckBox(self.layout, option.display_name, value)
                    edit.stateChanged.connect(lambda value, edit=edit, option=option: self.Changed(edit, value, option))
                if option.value_type == "string":
                    edit = AddQLineEdit(self.layout, option.display_name, value)
                    edit.textChanged.connect(lambda value, edit=edit, option=option: self.Changed(edit, value, option))
                if option.tooltip:
                    edit.label.setToolTip(option.tooltip)
                    edit.setToolTip(option.tooltip)
                edit.current_value = None
                edit.option = option
                edit.error = None
                edit.has_error = False
                self.edits.append(edit)
                self.edits_by_name[option.key] = edit
            self.layout.addStretch()

        self.edits_by_name["buffer_size"].setDisabled(options.buffer_mode != 1)
        self.edits_by_name["buffer_memory"].setDisabled(options.buffer_mode != 2)

    def updateEditField(self, edit, value, option):
        print(option.value_type, value, edit)
        if option.value_type == "int":
            if option.value_count > 1:
                edit.setText(", ".join(str(v) for v in value))
            else:
                edit.setValue(value)
        if option.value_type == "choice":
            edit.setCurrentIndex(option.values.index(value))
        if option.value_type == "float":
            edit.setValue(value)
        if option.value_type == "bool":
            edit.setChecked(value)
        if option.value_type == "string":
            edit.setText(value)
        edit.current_value = value

    def list_selected(self):
        pass

    def Import(self):
        config_path = QtWidgets.QFileDialog.getOpenFileName(self, "Import config - ClickPoints",
                                                            os.path.join(os.getcwd(), "ConfigClickPoints.txt"),
                                                            "ClickPoints Config *.txt")
        if isinstance(config_path, tuple):
            config_path = config_path[0]
        else:
            config_path = str(config_path)
        if not config_path or not os.path.exists(config_path):
            return
        config = LoadConfig(config_path, just_load=True)
        for key in config:
            if key in self.edits_by_name:
                edit = self.edits_by_name[key]
                # check the new value
                self.Changed(edit, config[key], self.data_file._options_by_key[key])
                # fill in the edit field
                self.updateEditField(edit, edit.current_value, self.data_file._options_by_key[key])
                # set the option in the database
                self.data_file.setOption(edit.option.key, edit.current_value)
            else:
                # if we don't have a field, set it directly
                try:
                    self.data_file.setOption(key, config[key])
                except KeyError:
                    # not a valid option
                    pass
        # notify everyone that the options have changed
        self.data_file.optionsChanged()
        BroadCastEvent(self.window.modules, "optionsChanged")
        self.window.JumpFrames(0)

    def Export(self):
        export_path = QtWidgets.QFileDialog.getSaveFileName(self, "Export config - ClickPoints", os.path.join(os.getcwd(), "ConfigClickPoints.txt"), "ClickPoints Config *.txt")
        if isinstance(export_path, tuple):
            export_path = export_path[0]
        else:
            export_path = str(export_path)
        if not export_path:
            return
        with open(export_path, "w") as fp:
            for category in self.data_file._options:
                count = len([option for option in self.data_file._options[category] if option.value is not None])
                if category == "Marker" or category == "Mask":
                    count += 1
                if count == 0:
                    continue
                fp.write('""" %s """\n\n' % category)
                if category == "Marker":
                    self.ExportMarkerTypes(fp)
                elif category == "Mask":
                    self.ExportMaskTypes(fp)
                for option in self.data_file._options[category]:
                    if option.key == "types" or option.key == "draw_types":
                        continue
                    if option.value is None:
                        continue
                    if option.value_type == "string":
                        fp.write("%s = \"%s\"\n" % (option.key, option.value))
                    else:
                        fp.write("%s = %s\n" % (option.key, option.value))
                fp.write("\n")

    def ExportMarkerTypes(self, fp):
        types = []
        modes = {0: "TYPE_Normal", 1: "TYPE_Rect", 2: "TYPE_Line", 4: "TYPE_Track"}
        for index, type in enumerate(self.data_file.getMarkerTypes()):
            color = type.getColorRGB()
            types.append("%d: [\"%s\", [%d, %d, %d], %s]" % (index, type.name, color[0], color[1], color[2], modes[type.mode]))
        fp.write("types = {%s}\n" % ",\n         ".join(types))

    def ExportMaskTypes(self, fp):
        types = []
        for type in self.data_file.getMaskTypes():
            color = type.getColorRGB()
            types.append("[%d, [%d, %d, %d], \"%s\"]" % (type.index, color[0], color[1], color[2], type.name))
        fp.write("draw_types = [%s]\n" % ",\n             ".join(types))

    def ShowFieldError(self, field, error, width=180, normal_msg=False):
        if field.error is None:
            field.error = QtWidgets.QLabel(error, self)
            field.error.move(field.pos().x() + field.error.width(), field.pos().y() + field.error.height() + 5)
            field.error.setMinimumWidth(width)
        if normal_msg:
            field.error.setStyleSheet(
                "background-color: #FFF; border-width: 1px; border-color: black; border-style: outset;")
        else:
            field.error.setStyleSheet(
                "background-color: #FDD; border-width: 1px; border-color: black; border-style: outset;")
        field.error.setText(error)
        field.error.show()

    def ChangeFinished(self, field, option):
        if field.error is not None:
            field.error.hide()

    def Changed(self, field, value, option):
        if field.error is not None:
            field.error.hide()
        field.has_error = False
        if option.value_type == "int":
            if option.value_count > 1:
                value = value.strip()
                if (value.startswith("(") and value.endswith(")")) or (value.startswith("[") and value.endswith("]")):
                    value = value[1:-1].strip()
                if value.endswith(","):
                    value = value[:-1].strip()
                try:
                    value = [int(v) for v in value.split(",")]
                except ValueError:
                    field.setStyleSheet("background-color: #FDD;")
                    for v in value.split(","):
                        try:
                            int(v)
                        except ValueError:
                            self.ShowFieldError(field, "Only <b>integer</b> values are allowed.<br/>'%s' can't be parsed as an int." % v.strip())
                    field.has_error = True
                    return
                if len(value) != option.value_count:
                    field.setStyleSheet("background-color: #FDD;")
                    self.ShowFieldError(field, "The field needs <b>%d integers</b>,<br/>but %d are provided." % (option.value_count, len(value)))
                    field.has_error = True
                    return
                else:
                    field.setStyleSheet("")
            else:
                value = int(value)
        if option.value_type == "choice":
            value = int(value)
        if option.value_type == "float":
            value = float(value)
        if option.value_type == "bool":
            value = bool(value)
        if option.key == "buffer_size":
            self.ShowFieldError(field, "Estimated memory usage:<br/>%s" % PrittyPrintSize(value*self.window.im.nbytes), width=140, normal_msg=True)
        if option.key == "buffer_mode":
            self.edits_by_name["buffer_size"].setDisabled(value != 1)
            self.edits_by_name["buffer_memory"].setDisabled(value != 2)
        field.current_value = value
        self.button_apply.setDisabled(False)

    def Apply(self):
        for edit in self.edits:
            if edit.has_error:
                QtWidgets.QMessageBox.critical(self, 'Error',
                                               'Input field \'%s\' contain errors, settings can\'t be saved.' % edit.option.display_name,
                                               QtWidgets.QMessageBox.Ok)
                return False
        for edit in self.edits:
            if edit.current_value is not None:
                self.data_file.setOption(edit.option.key, edit.current_value)
        self.button_apply.setDisabled(True)
        self.data_file.optionsChanged()
        BroadCastEvent(self.window.modules, "optionsChanged")
        self.window.JumpFrames(0)
        return True

    def Ok(self):
        if self.Apply():
            self.close()

    def Cancel(self):
        self.close()

class OptionEditor:
    data_file = None
    config = None

    def __init__(self, window, modules, config=None):
        # default settings and parameters
        self.window = window
        self.modules = modules
        self.OptionsWindow = None

        self.button = QtWidgets.QPushButton()
        self.button.setIcon(qta.icon('fa.gears'))
        self.button.setToolTip("change the options for the project")
        self.button.clicked.connect(self.showDialog)
        window.layoutButtons.addWidget(self.button)

    def closeDataFile(self):
        self.data_file = None
        self.config = None

        if self.OptionsWindow:
            self.OptionsWindow.close()

    def updateDataFile(self, data_file, new_database):
        self.data_file = data_file
        self.config = data_file.getOptionAccess()

    def showDialog(self):
        if self.OptionsWindow is not None:
            self.OptionsWindow.close()
            self.OptionsWindow = None
        self.OptionsWindow = OptionEditorWindow(self.window, self.data_file)
        self.OptionsWindow.show()

    def closeEvent(self, event):
        if self.OptionsWindow:
            self.OptionsWindow.close()

    @staticmethod
    def file():
        return __file__
