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

import SocketServer, socket, threading, subprocess

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
    signal = pyqtSignal(str, socket._socketobject, tuple)

    def __init__(self, window, media_handler, config=None):
        QObject.__init__(self)
        self.window = window
        self.media_handler = media_handler
        self.config = config

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

    def Command(self, command, socket, client_address):
        cmd, value = str(command).split(" ", 1)
        if cmd == "JumpFrames":
            self.window.JumpFrames(int(value))
        if cmd == "JumpToFrame":
            self.window.JumpToFrame(int(value))
        if cmd == "GetImageName":
            name = self.window.media_handler.get_filename()
            print(name)
            if name[0] is None:
                socket.sendto(cmd + "", client_address)
            else:
                socket.sendto(cmd + " " + name, client_address)
        if cmd == "GetMarkerName":
            name = self.window.media_handler.get_filename()
            if name[0] is None:
                socket.sendto(cmd + "", client_address)
            else:
                # TODO GetLogName doesnt exist in new version
                name = self.window.GetModule("MarkerHandler").GetLogName(os.path.join(*name))
                socket.sendto(cmd + " " + name, client_address)
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
