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
            except socket.error:
                self.PORT += 1
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
            name = self.window.media_handler.getCurrentFilename(int(value))
            if name[0] is None:
                socket.sendto("", client_address)
            else:
                socket.sendto(os.path.join(*name), client_address)
        if cmd == "GetMarkerName":
            name = self.window.media_handler.getCurrentFilename(int(value))
            if name[0] is None:
                socket.sendto("", client_address)
            else:
                name = self.window.GetModule("MarkerHandler").GetLogName(os.path.join(*name))
                socket.sendto(name, client_address)

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
                args = [sys.executable, os.path.abspath(script), os.path.abspath(self.config.srcpath), str(self.media_handler.currentPos), str(self.PORT)]
                if hasattr(os.sys, 'winver'):
                    process = subprocess.Popen(args, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
                else:
                    process = subprocess.Popen(args)
                self.running_processes[index] = process

    @staticmethod
    def file():
        return __file__

    @staticmethod
    def can_create_module(config):
        return len(config.launch_scripts) > 0
