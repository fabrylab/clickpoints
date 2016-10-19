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

import imageio
from includes import MemMap
from Tools import BroadCastEvent
import re
import time

class ThreadedUDPRequestHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        msg = self.request[0].decode()
        self.server.signal.emit(msg, self.request[1], self.client_address)

def isPortInUse(type,ip,port_nr):
    connection_list = psutil.net_connections(kind=type)
    ipport_list = [[c[3][0],c[3][1]] for c in connection_list]

    if [ip,port_nr] in ipport_list:
        return True
    else:
        return False

path_addons = os.path.join(os.path.dirname(__file__), "..", "addons")


class ScriptEditor(QtWidgets.QWidget):
    def __init__(self, script_launcher):
        QtWidgets.QWidget.__init__(self)
        self.script_launcher = script_launcher

        # Widget
        self.setMinimumWidth(500)
        self.setMinimumHeight(200)
        self.setWindowTitle("Script Selector - ClickPoints")
        self.layout = QtWidgets.QVBoxLayout(self)

        self.setWindowIcon(qta.icon("fa.code"))

        """ """
        self.list = QtWidgets.QListWidget(self)
        self.layout.addWidget(self.list)
        self.list.itemSelectionChanged.connect(self.list_selected)

        group_box = QtWidgets.QGroupBox("Add Folder")
        self.group_box = group_box
        self.layout.addWidget(group_box)
        layout = QtWidgets.QVBoxLayout()
        group_box.setLayout(layout)
        """ """

        horizontal_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(horizontal_layout)

        horizontal_layout.addWidget(QtWidgets.QLabel("Folder:"))

        self.text_input = QtWidgets.QLineEdit(self)
        self.text_input.setDisabled(True)
        horizontal_layout.addWidget(self.text_input)

        self.pushbutton_file = QtWidgets.QPushButton('Select F&ile', self)
        self.pushbutton_file.pressed.connect(self.select_file)
        horizontal_layout.addWidget(self.pushbutton_file)

        self.pushbutton_delete = QtWidgets.QPushButton('Remove', self)
        self.pushbutton_delete.pressed.connect(self.remove_folder)
        horizontal_layout.addWidget(self.pushbutton_delete)

        """ """

        horizontal_layout = QtWidgets.QHBoxLayout()
        self.layout.addLayout(horizontal_layout)

        horizontal_layout.addStretch()

        self.pushbutton_Confirm = QtWidgets.QPushButton('O&k', self)
        self.pushbutton_Confirm.pressed.connect(self.close)
        horizontal_layout.addWidget(self.pushbutton_Confirm)

        self.update_folder_list()
        self.list.setCurrentRow(self.list.count()-1)

    def list_selected(self):
        selections = self.list.selectedItems()
        if len(selections) == 0 or self.list.currentRow() == self.list.count()-1:
            self.text_input.setText("")
            self.group_box.setTitle("Add Script")
            self.pushbutton_file.setHidden(False)
            self.pushbutton_delete.setHidden(True)
        else:
            self.text_input.setText(selections[0].text().rsplit("  ", 1)[0])
            self.group_box.setTitle("Script")
            self.pushbutton_file.setHidden(True)
            self.pushbutton_delete.setHidden(False)

    def update_folder_list(self):
        self.list.clear()
        for index, script in enumerate(self.script_launcher.scripts):
            item = QtWidgets.QListWidgetItem(qta.icon("fa.code"), "%s  (F%d)" % (script, 12-index), self.list)
            item.path_entry = script
        QtWidgets.QListWidgetItem(qta.icon("fa.plus"), "add script", self.list)
        self.script_launcher.updateScripts()

    def select_file(self):
        # ask for a file name
        new_path = str(QtWidgets.QFileDialog.getOpenFileName(None, "Select File", self.script_launcher.script_path))
        # if we got one, set it
        if new_path:
            print(new_path, self.script_launcher.script_path)
            new_path = os.path.relpath(new_path, self.script_launcher.script_path)
            self.script_launcher.scripts.append(new_path)
            self.text_input.setText(new_path)
            self.update_folder_list()

    def remove_folder(self):
        path = self.list.selectedItems()[0].path_entry
        self.script_launcher.scripts.remove(path)
        self.update_folder_list()

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

    def __init__(self, window, modules):
        QtCore.QObject.__init__(self)
        self.window = window
        self.modules = modules

        self.HOST, self.PORT = "localhost", 55005
        # Try to connect the server at the next free port
        while True:
            try:
                server = SocketServer.ThreadingUDPServer((self.HOST, self.PORT), ThreadedUDPRequestHandler)
                # check private boradcast port as self.PORT +1
                if isPortInUse('udp','127.0.0.1',self.PORT +1):
                    raise socket.error
            except socket.error:
                self.PORT += 2
            else:
                break

        server.signal = self.signal
        server.signal.connect(self.Command)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        process_dict = { 'process':None, 'command_port':None, 'broadcast_port':None}

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

        #self.running_processes = [None]*len(self.config.launch_scripts)

        self.closeDataFile()

    def closeDataFile(self):
        self.data_file = None
        self.config = None
        self.scripts = []
        self.updateScripts()
        if self.scriptSelector:
            self.scriptSelector.close()

    def updateDataFile(self, data_file, new_database):
        self.data_file = data_file
        self.config = data_file.getOptionAccess()

        self.scripts = self.data_file.getOption("scripts")[:]

        self.updateScripts()

    def updateScripts(self):
        #self.data_file.setOption("scripts", self.scripts)
        for button in self.script_buttons:
            self.button_group_layout.removeWidget(button)
        self.script_buttons = []
        for index, script in enumerate(self.scripts):
            button = QtWidgets.QPushButton()
            button.setCheckable(True)
            button.icon_name = "fa.bar-chart"
            #if os.path.exists(os.path.join(self.config.path_config, script)):
            #    script_path = os.path.join(self.config.path_config, script)
            # or relative to the clickpoints path
            if os.path.exists(os.path.join(path_addons, script)):
                script_path = os.path.join(path_addons, script)
            with open(script_path) as fp:
                for line in fp:
                    line = line.strip()
                    if line.startswith("__icon__"):
                        match = re.match(r"__[^_]*__\s*=\s*\"(.*)\"\s*$", line)
                        if match:
                            button.icon_name = match.groups()[0]
                        break
            button.setIcon(qta.icon(button.icon_name))
            button.setToolTip(script)
            button.clicked.connect(lambda x, i=index: self.launch(i))
            self.button_group_layout.addWidget(button)
            self.script_buttons.append(button)

    def CheckProcessRunning(self, timer, process, button):
        if process.pid in psutil.pids() and process.poll() is None:
            spin_icon = qta.icon(button.icon_name, 'fa.hourglass-%d' % (int(timer.duration()*2) % 3 +1), options=[{},
                                                                            {'scale_factor': 0.9, 'offset': (0.3, 0.2),
                                                                             'color': QtGui.QColor(128, 0, 0)}])
            button.setIcon(spin_icon)
            button.setChecked(True)
            return
        button.setIcon(qta.icon(button.icon_name))
        button.setChecked(False)
        timer.stop()

    def showScriptSelector(self):
        self.scriptSelector = ScriptEditor(self)
        self.scriptSelector.show()

    def Command(self, command, socket, client_address):
        cmd, value = str(command).split(" ", 1)
        if cmd == "JumpFrames":
            self.window.JumpFrames(int(value))
        if cmd == "log":
            self.window.log(value[:-1], end="")
        if cmd == "JumpToFrame":
            self.window.JumpToFrame(int(value))
        if cmd == "JumpFramesWait":
            self.window.JumpFrames(int(value))
            socket.sendto(cmd.encode(), client_address)
        if cmd == "JumpToFrameWait":
            self.window.JumpToFrame(int(value))
            socket.sendto(cmd.encode(), client_address)
        if cmd == "ReloadMask":
            BroadCastEvent(self.modules, "ReloadMask")
            socket.sendto(cmd.encode(), client_address)
        if cmd == "ReloadMarker":
            frame = int(value)
            if frame == -1:
                frame = self.data_file.get_current_image()
            BroadCastEvent(self.modules, "ReloadMarker", frame)
            socket.sendto(cmd.encode(), client_address)
        if cmd == "ReloadTypes":
            BroadCastEvent(self.modules, "UpdateCounter")
            socket.sendto(cmd.encode(), client_address)
        if cmd == "GetImage":
            image = self.window.data_file.get_image_data(int(value))
            if image is None:
                socket.sendto(cmd.encode(), client_address)
                return
            image_id = self.window.data_file.get_image(int(value)).id

            shape = image.shape
            if len(shape) == 2:
                shape = (shape[0], shape[1], 1)

            size = shape[0]*shape[1]*shape[2]
            clickpoints_storage_path = self.window.storage_path
            if self.memmap is None or size > self.memmap_size:
                self.memmap_path = os.path.normpath(os.path.join(clickpoints_storage_path, "image.dat"))
                self.memmap_path_xml = os.path.normpath(os.path.join(clickpoints_storage_path, "image.xml"))
                layout = (
                    dict(name="shape", type="uint32", shape=(3,)),
                    dict(name="type", type="|S30"),
                    dict(name="data", type=str(image.dtype), shape=(shape[0]*shape[1]*shape[2],)),
                )

                self.memmap = MemMap(self.memmap_path, layout)
                self.memmap.saveXML(self.memmap_path_xml)
                self.memmap_size = size

            self.memmap.shape[:] = shape
            self.memmap.type = str(image.dtype)
            self.memmap.data[:size] = image.flatten()
            socket.sendto((cmd + " " + self.memmap_path_xml + " " + str(image_id)).encode(), client_address)
        if cmd == "updateHUD":
            try:
                self.window.GetModule('InfoHud').updateHUD(value)
            except ValueError:
                print('Module InfoHud not available')

    def LoadImageEvent(self, filename, framenumber):
        # broadcast event to all running processes
        for p in self.running_processes:
            if not p['process'] == None:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                msg = "LoadImageEvent %s %d" % (filename,framenumber)
                sock.sendto(msg.encode(), ('127.0.0.1', p['broadcast_port']))
                sock.close()

    def PreLoadImageEvent(self, filename, framenumber):
        # broadcast event to all running processes
        for p in self.running_processes:
            if not p['process'] == None:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                msg = "PreLoadImageEvent %s %d" % (filename,framenumber)
                sock.sendto(msg.encode(), ('127.0.0.1', p['broadcast_port']))
                sock.close()

    def launch(self, index):
        script = self.scripts[index]
        process = self.running_processes[index]['process']
        if process is not None and process.pid in psutil.pids() and process.poll() is None:
            if hasattr(os.sys, 'winver'):
                os.kill(process.pid, signal.CTRL_BREAK_EVENT)
            else:
                process.send_signal(signal.SIGTERM)
            return
        self.window.Save()
        script_path = None
        # search script relative to the config file
        #print(os.path.join(self.config.path_config, script))
        #print(os.path.join(self.config.path_clickpoints, "addons", script))
        #if os.path.exists(os.path.join(self.config.path_config, script)):
        #    script_path = os.path.join(self.config.path_config, script)
        # or relative to the clickpoints path
        if os.path.exists(os.path.join(path_addons, script)):
            script_path = os.path.join(path_addons, script)
        # print an error message if no file was found
        if script_path is None:
            print("ERROR: script %s not found." % script)
            return
        args = [sys.executable, os.path.abspath(script_path), "--start_frame", str(self.data_file.get_current_image()),
                "--port", str(self.PORT), "--database", str(self.data_file._database_filename)]
        print('arags:', args)
        if hasattr(os.sys, 'winver'):
            process = subprocess.Popen(args, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            process = subprocess.Popen(args)
        self.running_processes[index]['process'] = process
        self.running_processes[index]['command_port'] = self.PORT
        self.running_processes[index]['broadcast_port'] = self.PORT + 1
        print("Process", process)
        self.window.log("Start add-on", script)
        timer = QtCore.QTimer()
        timer.timeout.connect(lambda: self.CheckProcessRunning(timer, process, self.script_buttons[index]))
        timer.start_time = time.time()
        timer.duration = lambda: time.time()-timer.start_time
        timer.start(10)
        self.script_buttons[index].timer = timer

    def keyPressEvent(self, event):
        keys = [QtCore.Qt.Key_F12, QtCore.Qt.Key_F11, QtCore.Qt.Key_F10, QtCore.Qt.Key_F9, QtCore.Qt.Key_F8, QtCore.Qt.Key_F7, QtCore.Qt.Key_F6, QtCore.Qt.Key_F5]
        for index, key in enumerate(keys):
            # @key F12: Launch
            if event.key() == key:
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
