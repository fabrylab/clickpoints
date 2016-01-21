# -*- coding: utf-8 -*-
from __future__ import division, print_function
import os, sys
import psutil
import signal

try:
    from PyQt5 import QtCore
    from PyQt5.QtCore import pyqtSignal, QThread, QObject
except ImportError:
    from PyQt4 import QtCore
    from PyQt4.QtCore import pyqtSignal, QThread, QObject

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

    def __init__(self, window, media_handler, modules, config=None):
        QObject.__init__(self)
        self.window = window
        self.media_handler = media_handler
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

        self.running_processes = [None]*len(self.config.launch_scripts)
        self.memmap = None
        self.memmap_path = None

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
            BroadCastEvent(self.modules, "ReloadMarker", int(value))
            socket.sendto(cmd, client_address)
        if cmd == "GetImage":
            try:
                file_entry, image_id, image_frame = self.window.media_handler.get_file_entry(int(value))
                #image_id, image_frame = self.window.media_handler.id_lookup[int(value)]
            except IndexError:
                socket.sendto(cmd + "", client_address)
                return
            image_entry = self.window.data_file.get_image(file_entry, image_frame, self.window.media_handler.get_timestamp(int(value)))
            image_id = image_entry.id
            image = self.window.media_handler.get_file(int(value))

            shape = image.shape
            if len(shape) == 2:
                shape = (shape[0], shape[1], 1)

            # TODO check for size change
            if sys.platform[:3] == 'win':
                clickpoints_storage_path = os.path.join(os.getenv('APPDATA'), "..", "Local", "Temp", "ClickPoints")
            else:
                clickpoints_storage_path = os.path.expanduser("~/.clickpoints/")
            if not os.path.exists(clickpoints_storage_path):
                os.makedirs(clickpoints_storage_path)
            if self.memmap is None:
                self.memmap_path = os.path.normpath(os.path.join(clickpoints_storage_path, "image.dat"))
                self.memmap_path_xml = os.path.normpath(os.path.join(clickpoints_storage_path, "image.xml"))
                layout = (
                    dict(name="shape", type="uint32", shape=(3,)),
                    dict(name="type", type="|S30"),
                    dict(name="data", type=str(image.dtype), shape=(shape[0]*shape[1]*shape[2],)),
                )

                self.memmap = MemMap(self.memmap_path, layout)
                self.memmap.saveXML(self.memmap_path_xml)

            self.memmap.shape[:] = shape
            self.memmap.type = str(image.dtype)
            self.memmap.data[:] = image.flatten()
            socket.sendto(cmd + " " + self.memmap_path_xml + " " + str(image_id) + " " + str(image_frame), client_address)
        if cmd == "updateHUD":
            try:
                self.window.GetModule('InfoHud').updateHUD(value)
            except ValueError:
                print('Module InfoHud not available')

    def LoadImageEvent(self, filename, framenumber):
        # TODO add generic ports for multiple scripts
        # for p in self.process:
        #     port = p.
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto("LoadImageEvent %s %d" % (filename,framenumber), ('127.0.0.1', self.PORT+1))
        sock.close()

    def PreLoadImageEvent(self, filename, framenumber):
        print("ScriptLauncher PreLoadImage Event triggered")
        # TODO add generic ports for multiple scripts
        # for p in self.process:
        #     port = p.
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto("PreLoadImageEvent %s %d" % (filename,framenumber), ('127.0.0.1', self.PORT+1))
        sock.close()


    def keyPressEvent(self, event):
        keys = [QtCore.Qt.Key_F12, QtCore.Qt.Key_F11, QtCore.Qt.Key_F10, QtCore.Qt.Key_F9, QtCore.Qt.Key_F8, QtCore.Qt.Key_F7, QtCore.Qt.Key_F6, QtCore.Qt.Key_F5]
        for script, key, index in zip(self.config.launch_scripts, keys, range(len(self.config.launch_scripts))):
            # @key F12: Launch
            if event.key() == key:
                process = self.running_processes[index]
                if process is not None and process.pid in psutil.pids():
                    if hasattr(os.sys, 'winver'):
                        os.kill(process.pid, signal.CTRL_BREAK_EVENT)
                    else:
                        process.send_signal(signal.SIGTERM)
                    continue
                self.window.save()
                args = [sys.executable, os.path.abspath(script), " ", str(self.media_handler.get_index()), str(self.PORT)]
                print('arags:', args)
                if hasattr(os.sys, 'winver'):
                    process = subprocess.Popen(args, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
                else:
                    process = subprocess.Popen(args)
                self.running_processes[index] = process
                print("Process",process)

    @staticmethod
    def file():
        return __file__

    @staticmethod
    def can_create_module(config):
        return len(config.launch_scripts) > 0
