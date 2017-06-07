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


def wrap_run(run, script):

    def wrapper(*args, **kwargs):
        script.run_started()
        try:
            run(*args, **kwargs)
        finally:
            script.run_stopped()

    return wrapper


def wrap_get(function):
    def wrapper(section, name, fallback=None):
        try:
            return function(section, name)
        except ConfigParser.NoOptionError:
            return fallback
    return wrapper


class Script(QtCore.QObject):
    loaded = False
    process = None

    active = False
    is_running = False

    button = None
    run_thread = None

    start_timer = QtCore.Signal()

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
            with open(path) as fp:
                self.description = fp.read()
        self.icon = parser.get("addon", "icon", fallback="fa.code")
        self.icon_name = self.icon
        self.script = parser.get("addon", "file", fallback="Script.py")
        self.script = os.path.join(os.path.dirname(filename), self.script)

        if self.icon.startswith("fa."):
            self.icon = qta.icon(self.icon)
        else:
            self.icon = QtGui.QIcon(self.icon)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.checkProcessRunning)
        self.start_timer.connect(self.startTimer)

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
        self.process = self.addon_module.Addon(script_launcher.data_file, script_launcher, self.name)
        self.process.run = wrap_run(self.process.run, self)

        self.active = True

    def deactivate(self):
        self.active = False
        self.button = None

    def run_started(self):
        self.process.cp.stop = False
        self.is_running = True
        self.start_timer.emit()

    def run_stopped(self):
        self.is_running = False

    def startTimer(self):
        self.timer.start_time = time.time()
        self.timer.duration = lambda: time.time() - self.timer.start_time
        self.timer.start(10)

    def checkProcessRunning(self):
        if self.is_running:
            spin_icon = qta.icon(self.icon_name, 'fa.hourglass-%d' % (int(self.timer.duration() * 2) % 3 + 1),
                                 options=[{}, {'scale_factor': 0.9, 'offset': (0.3, 0.2), 'color': QtGui.QColor(128, 0, 0)}])
            self.button.setIcon(spin_icon)
            self.button.setChecked(True)
            return
        self.button.setIcon(self.icon)
        self.button.setChecked(False)
        self.timer.stop()

    def run(self, start_frame):
        if self.run_thread and self.run_thread.isAlive():
            self.process.terminate()
            self.run_thread.join(1)
            self.run_thread = None
        else:
            self.run_thread = threading.Thread(target=self.process.run, args=(start_frame, ))
            self.run_thread.daemon = True
            self.run_thread.start()

    def reload(self):
        button = self.button
        self.deactivate()
        self.activate(self.script_launcher)
        self.button = button


path_addons = os.path.join(os.path.dirname(__file__), "..", "addons")

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

        """ """
        #self.list = QtWidgets.QListWidget(self)
        #self.layout.addWidget(self.list)
        #self.list.itemSelectionChanged.connect(self.list_selected)

        self.list2 = QtWidgets.QListWidget(self)
        self.layout.addWidget(self.list2)
        self.list2.itemSelectionChanged.connect(self.list_selected2)

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

        process_dict = {'process': None, 'command_port': None, 'broadcast_port': None}

        self.running_processes = [process_dict] * 10
        self.memmap = None
        self.memmap_path = None
        self.memmap_size = 0

        self.button = QtWidgets.QPushButton()
        self.button.setIcon(qta.icon("fa.external-link"))
        self.button.clicked.connect(self.showScriptSelector)
        self.button.setToolTip("load/remove addon scripts")
        self.window.layoutButtons.addWidget(self.button)

        self.button_group_layout = QtWidgets.QHBoxLayout()
        self.button_group_layout.setContentsMargins(0, 0, 0, 0)  # setStyleSheet("margin: 0px; padding: 0px;")
        self.script_buttons = []
        self.window.layoutButtons.addLayout(self.button_group_layout)

        self.script_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "addons"))

        self.closeDataFile()

    def loadScripts(self):
        script_path = os.path.join(os.path.dirname(__file__), "..", "addons")
        scripts = glob.glob(os.path.join(script_path, "*", '*.txt'))
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
            self.active_scripts.append(script)
            script.activate(self)

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
            return Script(filename)
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
            if function in dir(script.process):
                eval("script.process." + function + "(*args, **kwargs)")

    def showScriptSelector(self):
        self.scriptSelector = ScriptChooser(self)
        self.scriptSelector.show()

    def launch(self, index):
        self.window.Save()
        script = self.active_scripts[index]
        script.run(self.data_file.get_current_image())
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

    @staticmethod
    def file():
        return __file__

    @staticmethod
    def can_create_module(config):
        return 1
