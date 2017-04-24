#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SendCommands.py

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
import socket
import threading
import subprocess
try:
    import SocketServer  # python 2
    socketobject = socket._socketobject
except ImportError:
    import socketserver as SocketServer  # python 3
    socketobject = socket.socket

class ThreadedUDPRequestHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        msg = self.request[0].decode()
        cmd, value = str(msg).split(" ", 1)
        print(msg, cmd, value)
        #self.server.signal.emit(msg, self.request[1], self.client_address)
        if cmd == "Run":
            self.server.addon.is_running = True
            self.server.addon.run()
            self.server.addon.is_running = False
            self.server.socket.sendto("hexatisch!", self.client_address)
        if cmd == "is_running":
            socket.sendto(cmd.encode()+" %d" % self.server.addon.is_running, self.client_address)


class Command:
    def Command(self, cmd, value):#command, socket, client_address):
        socket = None
        client_address = None
        #cmd, value = str(command).split(" ", 1)
        print("Received command", cmd, value)
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
            #socket.sendto(cmd.encode(), client_address)
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


class Addon:
    def __init__(self, database=None, port=None, command=None):
        return
        self.HOST, self.PORT = "localhost", port
        if self.PORT:
            server = SocketServer.ThreadingUDPServer((self.HOST, self.PORT + 1), ThreadedUDPRequestHandler)
            server.addon = self
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            print("Addon", self.HOST, self.PORT + 1)

    def run(self, start_frame=0):
        pass