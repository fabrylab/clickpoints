# -*- coding: utf-8 -*-
from __future__ import division, print_function
import os, sys
import psutil
import signal

try:
    from PyQt5 import QtCore, QtGui
    from PyQt5.QtCore import pyqtSignal, QThread, QObject
except ImportError:
    from PyQt4 import QtCore, QtGui
    from PyQt4.QtCore import pyqtSignal, QThread, QObject
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

class ThreadedUDPRequestHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        self.server.signal.emit(self.request[0], self.request[1], self.client_address)

def isPortInUse(type,ip,port_nr):
    connection_list = psutil.net_connections(kind=type)
    ipport_list = [[c[3][0],c[3][1]] for c in connection_list]

    if [ip,port_nr] in ipport_list:
        return True
    else:
        return False

class ScriptLauncher(QObject):
    signal = pyqtSignal(str, socketobject, tuple)

    def __init__(self, window, data_file, modules, config=None):
        QObject.__init__(self)
        self.window = window
        self.data_file = data_file
        self.config = config
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

        self.running_processes = [process_dict] * len(self.config.launch_scripts)
        self.memmap = None
        self.memmap_path = None
        self.memmap_size = 0

        self.button = QtGui.QPushButton()
        self.button.setCheckable(True)
        self.button.setIcon(qta.icon("fa.code"))#QtGui.QIcon(os.path.join(self.window.icon_path, "icon_marker.png")))
        #self.button.clicked.connect(self.ToggleInterfaceEvent)
        self.window.layoutButtons.addWidget(self.button)

        #self.running_processes = [None]*len(self.config.launch_scripts)

    def Command(self, command, socket, client_address):
        cmd, value = str(command).split(" ", 1)
        if cmd == "JumpFrames":
            self.window.JumpFrames(int(value))
        if cmd == "JumpToFrame":
            self.window.JumpToFrame(int(value))
        if cmd == "JumpFramesWait":
            self.window.JumpFrames(int(value))
            socket.sendto(cmd, client_address)
        if cmd == "JumpToFrameWait":
            self.window.JumpToFrame(int(value))
            socket.sendto(cmd, client_address)
        if cmd == "ReloadMask":
            BroadCastEvent(self.modules, "ReloadMask")
            socket.sendto(cmd, client_address)
        if cmd == "ReloadMarker":
            frame = int(value)
            if frame == -1:
                frame = self.data_file.get_current_image()
            BroadCastEvent(self.modules, "ReloadMarker", frame)
            socket.sendto(cmd, client_address)
        if cmd == "ReloadTypes":
            BroadCastEvent(self.modules, "UpdateCounter")
            socket.sendto(cmd, client_address)
        if cmd == "GetImage":
            image = self.window.data_file.get_image_data(int(value))
            if image is None:
                socket.sendto(cmd + "", client_address)
                return
            image_id = self.window.data_file.get_image(int(value)).id

            shape = image.shape
            if len(shape) == 2:
                shape = (shape[0], shape[1], 1)

            size = shape[0]*shape[1]*shape[2]
            if sys.platform[:3] == 'win':
                clickpoints_storage_path = os.path.join(os.getenv('APPDATA'), "..", "Local", "Temp", "ClickPoints")
            else:
                clickpoints_storage_path = os.path.expanduser("~/.clickpoints/")
            if not os.path.exists(clickpoints_storage_path):
                os.makedirs(clickpoints_storage_path)
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
            socket.sendto(cmd + " " + self.memmap_path_xml + " " + str(image_id), client_address)
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


    def keyPressEvent(self, event):
        keys = [QtCore.Qt.Key_F12, QtCore.Qt.Key_F11, QtCore.Qt.Key_F10, QtCore.Qt.Key_F9, QtCore.Qt.Key_F8, QtCore.Qt.Key_F7, QtCore.Qt.Key_F6, QtCore.Qt.Key_F5]
        for script, key, index in zip(self.config.launch_scripts, keys, range(len(self.config.launch_scripts))):
            # @key F12: Launch
            if event.key() == key:
                process = self.running_processes[index]['process']
                if process is not None and process.pid in psutil.pids() and process.poll() is None:
                    if hasattr(os.sys, 'winver'):
                        os.kill(process.pid, signal.CTRL_BREAK_EVENT)
                    else:
                        process.send_signal(signal.SIGTERM)
                    continue
                self.window.Save()
                args = [sys.executable, os.path.abspath(script), "--start_frame", str(self.data_file.get_current_image()), "--port", str(self.PORT), "--database", str(self.data_file.database_filename)]
                print('arags:', args)
                if hasattr(os.sys, 'winver'):
                    process = subprocess.Popen(args, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
                else:
                    process = subprocess.Popen(args)
                self.running_processes[index]['process'] = process
                self.running_processes[index]['command_port'] = self.PORT
                self.running_processes[index]['broadcast_port'] = self.PORT + 1
                print("Process",process)

    @staticmethod
    def file():
        return __file__

    @staticmethod
    def can_create_module(config):
        return len(config.launch_scripts) > 0
