#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ScriptLauncher.py

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
import os, sys
import psutil
import signal

from qtpy import QtCore, QtGui, QtWidgets
import qtawesome as qta

import socket, threading, subprocess
try:
    import SocketServer  # python 2
    socketobject = socket._socketobject
except ImportError:
    import socketserver as SocketServer  # python 3
    socketobject = socket.socket

import time
import glob
try:
    import ConfigParser
except ImportError:
    import configparser as ConfigParser
from importlib import import_module
try:
    # python 3
    from importlib import reload
except ImportError:
    # python 2
    reload


# implement the fallback keyword for the ConfigParser in Python 2.7
def wrap_get(function):
    def wrapper(section, name, raw=True, fallback=None):
        try:
            return function(section, name, raw=raw)
        except ConfigParser.NoOptionError:
            return fallback
    return wrapper


class Script(QtCore.QObject):
    active = False
    loaded = False

    addon_class_instance = None

    script_launcher = None
    button = None

    def __init__(self, filename):
        QtCore.QObject.__init__(self)
        self.filename = filename
        parser = ConfigParser.ConfigParser()
        # for python 2 compatibility implement the fallback parameter, which is already there for python 3
        parser.get = wrap_get(parser.get)
        parser.read(filename)
        self.name = parser.get("addon", "name", fallback=os.path.split(os.path.dirname(filename))[1])
        try:
            self.description = parser.get("addon", "description", fallback="")
        except ConfigParser.NoOptionError:
            self.description = ""
        if self.description is "":
            path = os.path.join(os.path.dirname(filename), "Desc.html")
            try:
                with open(path) as fp:
                    self.description = fp.read()
            except IOError:
                self.description = "<i>no description available</i>"
        self.icon = parser.get("addon", "icon", fallback="fa.code")
        self.icon_name = self.icon
        self.script = parser.get("addon", "file", fallback="Script.py")
        self.script = os.path.join(os.path.dirname(filename), self.script)

        if self.icon.startswith("fa.") or self.icon.startswith("ei."):
            self.icon = qta.icon(self.icon)
        else:
            self.icon = QtGui.QIcon(self.icon)

        self.hourglassAnimationTimer = QtCore.QTimer()
        self.hourglassAnimationTimer.timeout.connect(self.displayHourglassAnimation)

    def activate(self, script_launcher):
        self.script_launcher = script_launcher
        path = os.path.abspath(self.script)
        name = os.path.splitext(os.path.basename(path))[0]
        sys.path.insert(0, os.path.dirname(path))
        try:
            if not self.loaded:
                self.addon_module = import_module(name)
                self.loaded = True
            else:
                self.addon_module = reload(self.addon_module)
        finally:
            sys.path.pop(0)
        if "Addon" not in dir(self.addon_module):
            raise NameError("No addon module found in " + path)
        self.addon_class_instance = self.addon_module.Addon(script_launcher.data_file, script_launcher, self.name, icon=self.icon)

        self.active = True

    def deactivate(self):
        self.addon_class_instance.delete()
        self.active = False
        self.button = None

    def displayHourglassAnimation(self):
        spin_icon = qta.icon(self.icon_name, 'fa.hourglass-%d' % (int(self.hourglassAnimationTimer.duration() * 2) % 3 + 1),
                             options=[{}, {'scale_factor': 0.9, 'offset': (0.3, 0.2), 'color': QtGui.QColor(128, 0, 0)}])
        self.button.setIcon(spin_icon)
        self.button.setChecked(True)

    def setStatus(self, status):
        # STATUS_Running
        if status == 2:
            self.hourglassAnimationTimer.start_time = time.time()
            self.hourglassAnimationTimer.duration = lambda: time.time() - self.hourglassAnimationTimer.start_time
            self.hourglassAnimationTimer.start()
        # STATUS_Active
        elif status == 1:
            self.button.setIcon(self.icon)
            self.button.setChecked(True)
            self.hourglassAnimationTimer.stop()
        # STATUS_Idle
        else:
            self.button.setIcon(self.icon)
            self.button.setChecked(False)
            self.hourglassAnimationTimer.stop()

    def run(self):
        self.addon_class_instance.buttonPressedEvent()

    def reload(self):
        button = self.button
        self.deactivate()
        self.activate(self.script_launcher)
        self.button = button


class ScriptChooser(QtWidgets.QWidget):
    def __init__(self, script_launcher):
        QtWidgets.QWidget.__init__(self)
        self.script_launcher = script_launcher

        # Widget
        self.setMinimumWidth(700)
        self.setMinimumHeight(400)
        self.setWindowTitle("Script Chooser - ClickPoints")
        self.layout_main = QtWidgets.QHBoxLayout(self)
        self.layout = QtWidgets.QVBoxLayout()
        self.layout_main.addLayout(self.layout)
        self.layout2 = QtWidgets.QVBoxLayout()
        self.layout_main.addLayout(self.layout2)

        self.setWindowIcon(qta.icon("fa.code"))

        self.list2 = QtWidgets.QListWidget(self)
        self.layout.addWidget(self.list2)
        self.list2.itemSelectionChanged.connect(self.list_selected2)

        layout = QtWidgets.QHBoxLayout()
        self.layout.addLayout(layout)
        self.button_import = QtWidgets.QPushButton("Import")
        self.button_import.clicked.connect(self.importScript)
        layout.addWidget(self.button_import)
        layout.addStretch()

        self.nameDisplay = QtWidgets.QLabel(self)
        self.nameDisplay.setStyleSheet("font-weight: bold;")
        self.layout2.addWidget(self.nameDisplay)

        self.imageDisplay = QtWidgets.QLabel(self)
        self.layout2.addWidget(self.imageDisplay)

        self.textDisplay = QtWidgets.QTextEdit(self)
        self.textDisplay.setReadOnly(True)
        self.layout2.addWidget(self.textDisplay)

        self.layout_buttons = QtWidgets.QHBoxLayout()
        self.layout2.addLayout(self.layout_buttons)
        self.layout_buttons.addStretch()

        self.button_removeAdd = QtWidgets.QPushButton("Remove")
        self.button_removeAdd.clicked.connect(self.add_script)
        self.layout_buttons.addWidget(self.button_removeAdd)

        self.selected_script = None

        self.update_folder_list2()

    def importScript(self):
        srcpath = QtWidgets.QFileDialog.getOpenFileName(None, "Import script - ClickPoints", os.getcwd(), "ClickPoints Scripts *.txt")
        if isinstance(srcpath, tuple):
            srcpath = srcpath[0]
        else:
            srcpath = str(srcpath)
        if srcpath:
            try:
                script = Script(srcpath)
            except ConfigParser.NoSectionError:
                reply = QtWidgets.QMessageBox.critical(self, 'Error', "Can not import selected file:\n%s\nThe selected file is no valid ClickPoints add-on file." % srcpath,
                                                       QtWidgets.QMessageBox.Ok)
            else:
                self.script_launcher.scripts.append(script)
                self.update_folder_list2()

    def list_selected2(self):
        selections = self.list2.selectedItems()
        if len(selections) == 0:
            self.button_removeAdd.setDisabled(True)
            self.selected_script = None
            return
        script = selections[0].entry
        self.selected_script = script
        self.nameDisplay.setText(script.name)
        self.textDisplay.setHtml(script.description)
        if script.active:
            self.button_removeAdd.setText("Remove")
            self.button_removeAdd.setDisabled(False)
        else:
            self.button_removeAdd.setText("Add")
            self.button_removeAdd.setDisabled(False)
        return

    def update_folder_list2(self):
        self.list2.clear()
        for index, script in enumerate(self.script_launcher.scripts):
            text = script.name
            if script.active:
                text += " (active)"
            item = QtWidgets.QListWidgetItem(script.icon, text, self.list2)
            item.entry = script

    def add_script(self):
        if self.selected_script.active:
            self.script_launcher.deactivateScript(self.selected_script)
        else:
            self.script_launcher.activateScript(self.selected_script)
        self.update_folder_list2()
        self.script_launcher.updateScripts()

    def keyPressEvent(self, event):
        # close the window with esc
        if event.key() == QtCore.Qt.Key_Escape:
            self.close()


class ScriptLauncher(QtCore.QObject):
    signal = QtCore.Signal(str, socketobject, tuple)

    scriptSelector = None

    data_file = None
    config = None

    scripts = None
    active_scripts = None

    def __init__(self, window, modules):
        QtCore.QObject.__init__(self)
        self.window = window
        self.modules = modules

        self.button = QtWidgets.QPushButton()
        self.button.setIcon(qta.icon("fa.external-link"))
        self.button.clicked.connect(self.showScriptSelector)
        self.button.setToolTip("load/remove addon scripts")
        self.window.layoutButtons.addWidget(self.button)

        self.button_group_layout = QtWidgets.QHBoxLayout()
        self.button_group_layout.setContentsMargins(0, 0, 0, 0)  # setStyleSheet("margin: 0px; padding: 0px;")
        self.script_buttons = []
        self.window.layoutButtons.addLayout(self.button_group_layout)

        self.script_path = os.path.normpath(os.environ["CLICKPOINTS_ADDON"])

        self.closeDataFile()

    def loadScripts(self):
        scripts = glob.glob(os.path.join(os.environ["CLICKPOINTS_ADDON"], "*", '*.txt'))
        return [Script(filename) for filename in scripts]

    def closeDataFile(self):
        self.data_file = None
        self.config = None
        self.scripts = self.loadScripts()
        self.active_scripts = []
        self.updateScripts()
        if self.scriptSelector:
            self.scriptSelector.close()

    def updateDataFile(self, data_file, new_database):
        self.data_file = data_file
        self.config = data_file.getOptionAccess()
        self.scripts = self.loadScripts()

        for script in self.data_file.getOption("scripts"):
            self.activateScript(script)

        self.updateScripts()

    def activateScript(self, script):
        script = self.getScriptByFilename(script)
        if script is not None:
            script.activate(self)
            self.active_scripts.append(script)

    def deactivateScript(self, script):
        script = self.getScriptByFilename(script)
        if script is not None:
            self.active_scripts.remove(script)
            script.deactivate()

    def getScriptByFilename(self, filename):
        if isinstance(filename, Script):
            return filename
        filename = os.path.normpath(filename)
        if self.scripts:
            filenames = [os.path.normpath(s.filename) for s in self.scripts]
            if filename in filenames:
                return self.scripts[filenames.index(filename)]
        try:
            script = Script(filename)
            self.scripts.append(script)
            return script
        except FileNotFoundError:
            return None

    def updateScripts(self):
        if self.data_file is not None:
            self.data_file.setOption("scripts", [os.path.normpath(s.filename) for s in self.active_scripts])
        for button in self.script_buttons:
            self.button_group_layout.removeWidget(button)
            button.setParent(None)
            del button
        self.script_buttons = []
        for index, script in enumerate(self.active_scripts):
            button = QtWidgets.QPushButton()
            button.setCheckable(True)
            button.setIcon(script.icon)
            button.setToolTip(script.name)
            button.clicked.connect(lambda x, i=index: self.launch(i))
            self.button_group_layout.addWidget(button)
            self.script_buttons.append(button)
            script.button = button

    def receiveBroadCastEvent(self, function, *args, **kwargs):
        for script in self.scripts:
            if function in dir(script.addon_class_instance):
                eval("script.addon_class_instance." + function + "(*args, **kwargs)")

    def showScriptSelector(self):
        self.scriptSelector = ScriptChooser(self)
        self.scriptSelector.show()

    def launch(self, index):
        self.window.Save()
        script = self.active_scripts[index]
        script.run()
        print("Launch", index)

    def reload(self, index):
        script = self.active_scripts[index]
        script.reload()
        print("Reload", index)

    def keyPressEvent(self, event):
        keys = [QtCore.Qt.Key_F12, QtCore.Qt.Key_F11, QtCore.Qt.Key_F10, QtCore.Qt.Key_F9, QtCore.Qt.Key_F8, QtCore.Qt.Key_F7, QtCore.Qt.Key_F6, QtCore.Qt.Key_F5]
        for index, key in enumerate(keys):
            # @key F12: Launch
            if event.key() == key:
                if event.modifiers() & QtCore.Qt.ControlModifier:
                    self.reload(index)
                else:
                    self.launch(index)

    def closeEvent(self, event):
        if self.scriptSelector:
            self.scriptSelector.close()
        for script in self.active_scripts:
            script.addon_class_instance.close()

    def setStatus(self, name, status):
        for script in self.active_scripts:
            if script.name == name:
                script.setStatus(status)

    @staticmethod
    def file():
        return __file__

    @staticmethod
    def can_create_module(config):
        return 1
