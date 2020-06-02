#!/usr/bin/env python
# -*- coding: utf-8 -*-
# OptionEditor.py

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

import json
import re
import os
import subprocess
from distutils.version import LooseVersion
from threading import Thread
from typing import Any, List, Union, IO

import natsort
import qtawesome as qta
from qtpy import QtGui, QtCore, QtWidgets

from clickpoints.DataFile import Option
from clickpoints.includes import BroadCastEvent
from clickpoints.includes import LoadConfig
from clickpoints.includes import QtShortCuts
from clickpoints.includes.Database import DataFileExtended

repo_path = "\"" + os.path.join(os.path.dirname(__file__), "..", "..") + "\""

def load_dirty_json(dirty_json):
    regex_replace = [(r"([ \{,:\[])(u)?'([^']+)'", r'\1"\3"'), (r" False([, \}\]])", r' false\1'), (r" True([, \}\]])", r' true\1')]
    for r, s in regex_replace:
        dirty_json = re.sub(r, s, dirty_json)
    clean_json = json.loads(dirty_json)
    return clean_json

def getNewestVersion() -> LooseVersion:
    result = os.popen("conda search -c rgerum -f clickpoints --json").read()
    # result = json.loads(result[:-4])
    result = load_dirty_json(result)
    try:
        version = natsort.natsorted([f["version"] for f in result["clickpoints"]])[-1]
    except KeyError:
        return None
    return LooseVersion(version)


def getCurrentVersion() -> LooseVersion:
    import clickpoints
    return LooseVersion(clickpoints.__version__)


def getCurrentVersionHG() -> None:
    global repo_path
    try:
        result = subprocess.check_output("hg id -n -R " + repo_path, stderr=subprocess.STDOUT).decode("utf-8").strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return result


def getNewestVersionHG() -> str:
    global repo_path
    try:
        result = subprocess.check_output("hg pull -R " + repo_path, stderr=subprocess.STDOUT)
        result = subprocess.check_output("hg log -l 1 --template \"{rev}\" -R " + repo_path,
                                         stderr=subprocess.STDOUT).decode("utf-8").strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return result


def PrittyPrintSize(bytes: int) -> str:
    if bytes > 1e9:
        return "%.1f GB" % (bytes / 1e8)
    if bytes > 1e6:
        return "%.1f MB" % (bytes / 1e6)
    if bytes > 1e3:
        return "%.1f kB" % (bytes / 1e3)
    return "%d bytes" % (bytes)


class VersionDisplay(QtWidgets.QWidget):
    version_changed = QtCore.Signal()

    def __init__(self, parent: "OptionEditorWindow", layout: QtWidgets.QVBoxLayout, window: "ClickPointsWindow") -> None:
        QtWidgets.QWidget.__init__(self, parent)
        self.clickpoints_main_window = window
        layout.addWidget(self)
        self.version_layout = QtWidgets.QHBoxLayout(self)
        self.version_layout.setContentsMargins(0, 0, 0, 0)

        self.version_layout.addStretch()
        self.label_version = QtWidgets.QLabel()
        self.label_version.linkActivated.connect(self.updateClicked)
        self.version_layout.addWidget(self.label_version)

        self.current_version = getCurrentVersion()
        self.current_version_hg = getCurrentVersionHG()
        self.newestet_version = None
        self.newestet_version_hg = None

        # self.updateVersionDisplay()
        self.version_changed.connect(self.updateVersionDisplay)
        self.version_changed.emit()
        self.thread = Thread(target=self.queryNewestVersion, args=tuple())
        self.thread.start()
        self.thread2 = Thread(target=self.queryNewestVersionHG, args=tuple())
        self.thread2.start()

    def queryNewestVersion(self):
        self.newestet_version = getNewestVersion()
        self.version_changed.emit()

    def queryNewestVersionHG(self):
        self.newestet_version_hg = getNewestVersionHG()
        self.version_changed.emit()

    def updateVersionDisplay(self) -> None:
        text = "v" + self.current_version.vstring
        if self.current_version_hg:
            text += " (rev %s)" % self.current_version_hg
            if self.newestet_version_hg is not None:
                text = text[:-1]
                if int(self.current_version_hg.strip("+")) < int(self.newestet_version_hg):
                    text += ", update to version <a href='update.html'>v%s</a>)" % self.newestet_version_hg
                else:
                    text += ", up to date)"
        elif self.newestet_version is not None:
            if self.newestet_version > self.current_version:
                text += " (update to version <a href='update.html'>v%s</a>)" % self.newestet_version.vstring
            else:
                text += " (up to date)"

        self.label_version.setText(text)

    def updateClicked(self):
        if self.newestet_version_hg is None:
            text = 'Do you want to update ClickPoints to version v%s?\nThe current instance will be closed.' % self.newestet_version.vstring
        else:
            text = 'Do you want to update ClickPoints to revision rev%s?\nThe current instance will be closed.' % self.newestet_version_hg
        reply = QtWidgets.QMessageBox.question(self, 'Update', text,
                                               QtWidgets.QMessageBox.Yes,
                                               QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.No:
            return
        self.clickpoints_main_window.close()
        if self.newestet_version_hg is None:
            subprocess.Popen(["conda", "update", "clickpoints", "-c", "rgerum", "-c", "conda-forge", "-y"])
        else:
            subprocess.Popen(["hg", "update", self.newestet_version_hg, "-R", repo_path[1:-1]])


def getOptionInputWidget(option: Option, layout: QtWidgets.QVBoxLayout, **kwargs) -> QtWidgets.QWidget:
    value = option.value if option.value is not None else option.default
    if option.value_type == "int":
        if option.value_count > 1:
            edit = QtShortCuts.QInputString(layout, option.display_name, value=", ".join(str(v) for v in value),
                                            tooltip=option.tooltip, **kwargs)
        else:
            edit = QtShortCuts.QInputNumber(layout, option.display_name, value=float(value),
                                            min=option.min_value, max=option.max_value,
                                            decimals=option.decimals, float=False, unit=option.unit,
                                            tooltip=option.tooltip, **kwargs)
    if option.value_type == "choice":
        edit = QtShortCuts.QInputChoice(layout, option.display_name, value=value, values=option.values,
                                        tooltip=option.tooltip, reference_by_index=True, **kwargs)
    if option.value_type == "choice_string":
        edit = QtShortCuts.QInputChoice(layout, option.display_name, value=value, values=option.values,
                                        tooltip=option.tooltip, reference_by_index=False, **kwargs)

    if option.value_type == "float":
        edit = QtShortCuts.QInputNumber(layout, option.display_name, value=float(value), min=option.min_value,
                                        max=option.max_value, decimals=option.decimals, float=True, unit=option.unit,
                                        tooltip=option.tooltip, **kwargs)
    if option.value_type == "bool":
        edit = QtShortCuts.QInputBool(layout, option.display_name, value=value, tooltip=option.tooltip, **kwargs)
    if option.value_type == "string":
        edit = QtShortCuts.QInputString(layout, option.display_name, value=value, tooltip=option.tooltip, **kwargs)
    if option.value_type == "color":
        edit = QtShortCuts.QInputColor(layout, option.display_name, value=value, tooltip=option.tooltip, **kwargs)
    return edit


class OptionEditorWindow(QtWidgets.QWidget):

    def __init__(self, window: "ClickPointsWindow", data_file: DataFileExtended) -> None:
        QtWidgets.QWidget.__init__(self)
        self.window = window
        self.data_file = data_file

        # Widget
        self.setMinimumWidth(450)
        self.setMinimumHeight(200)
        self.setWindowTitle("Options - ClickPoints")

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.version_widget = VersionDisplay(self, self.main_layout, window)

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
                edit = getOptionInputWidget(option, self.layout)
                edit.valueChanged.connect(lambda value, edit=edit, option=option: self.Changed(edit, value, option))
                edit.current_value = None
                edit.option = option
                edit.error = None
                edit.has_error = False
                self.edits.append(edit)
                self.edits_by_name[option.key] = edit
            self.layout.addStretch()

        self.edits_by_name["buffer_size"].setDisabled(options.buffer_mode != 1)
        self.edits_by_name["buffer_memory"].setDisabled(options.buffer_mode != 2)

    def updateEditField(self, edit: QtWidgets.QWidget, value: Any, option: Option) -> None:
        print(option.value_type, value, edit)
        edit.setValue(value)
        edit.current_value = value

    def list_selected(self) -> None:
        pass

    def Import(self) -> None:
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
        self.data_file.optionsChanged(None)
        BroadCastEvent(self.window.modules, "optionsImported")
        BroadCastEvent(self.window.modules, "optionsChanged", None)
        self.window.JumpFrames(0)

    def Export(self) -> None:
        export_path = QtWidgets.QFileDialog.getSaveFileName(self, "Export config - ClickPoints",
                                                            os.path.join(os.getcwd(), "ConfigClickPoints.txt"),
                                                            "ClickPoints Config *.txt")
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

    def ExportMarkerTypes(self, fp: IO) -> None:
        types = []
        modes = {0: "TYPE_Normal", 1: "TYPE_Rect", 2: "TYPE_Line", 4: "TYPE_Track", 8: "TYPE_Ellipse", 16: "TYPE_Polygon"}
        for index, type in enumerate(self.data_file.getMarkerTypes()):
            color = type.getColorRGB()
            types.append("%d: [\"%s\", [%d, %d, %d], %s, '%s', '%s']" % (
            index, type.name, color[0], color[1], color[2], modes[type.mode],
            type.style if type.style is not None else "", type.text if type.text is not None else ""))
        fp.write("types = {%s}\n" % ",\n         ".join(types))

    def ExportMaskTypes(self, fp: IO) -> None:
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

    def ChangeFinished(self, field: QtWidgets.QWidget, option: Option) -> None:
        if field.error is not None:
            field.error.hide()

    def Changed(self, field: QtWidgets.QWidget, value: str, option: Option) -> None:
        if field.error is not None:
            field.error.hide()
        field.has_error = False
        if option.value_type == "int":
            if option.value_count > 1:
                value = str(value).strip()
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
                            self.ShowFieldError(field,
                                                "Only <b>integer</b> values are allowed.<br/>'%s' can't be parsed as an int." % v.strip())
                    field.has_error = True
                    return
                if len(value) != option.value_count:
                    field.setStyleSheet("background-color: #FDD;")
                    self.ShowFieldError(field, "The field needs <b>%d integers</b>,<br/>but %d are provided." % (
                    option.value_count, len(value)))
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
            self.ShowFieldError(field,
                                "Estimated memory usage:<br/>%s" % PrittyPrintSize(value * self.window.im.nbytes),
                                width=140, normal_msg=True)
        if option.key == "buffer_mode":
            self.edits_by_name["buffer_size"].setDisabled(value != 1)
            self.edits_by_name["buffer_memory"].setDisabled(value != 2)
        field.current_value = value
        self.button_apply.setDisabled(False)

    def Apply(self) -> bool:
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
        self.data_file.optionsChanged(None)
        BroadCastEvent(self.window.modules, "optionsChanged", None)
        self.window.JumpFrames(0)
        return True

    def Ok(self) -> None:
        if self.Apply():
            self.close()

    def Cancel(self) -> None:
        self.close()


class OptionEditor:
    data_file = None
    config = None

    def __init__(self, window: "ClickPointsWindow", modules: List[Any], config: None = None) -> None:
        # default settings and parameters
        self.window = window
        self.modules = modules
        self.OptionsWindow = None

        self.button = QtWidgets.QPushButton()
        self.button.setIcon(qta.icon('fa.gears'))
        self.button.setToolTip("change the options for the project")
        self.button.clicked.connect(self.showDialog)
        window.layoutButtons.addWidget(self.button)

    def closeDataFile(self) -> None:
        self.data_file = None
        self.config = None

        if self.OptionsWindow:
            self.OptionsWindow.close()

    def updateDataFile(self, data_file: DataFileExtended, new_database: bool) -> None:
        self.data_file = data_file
        self.config = data_file.getOptionAccess()

    def showDialog(self) -> None:
        if self.OptionsWindow is not None:
            self.OptionsWindow.close()
            self.OptionsWindow = None
        self.OptionsWindow = OptionEditorWindow(self.window, self.data_file)
        self.OptionsWindow.show()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self.OptionsWindow:
            self.OptionsWindow.close()

    @staticmethod
    def file() -> str:
        return __file__
