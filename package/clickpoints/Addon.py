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
import time
import clickpoints


class Command:
    script_launcher = None
    stop = False

    def __init__(self, script_launcher=None):
        self.script_launcher = script_launcher
        if self.script_launcher is not None:
            self.window = self.script_launcher.window

    def jumpFrames(self, value):
        # only if we are not a dummy connection
        if self.script_launcher is None:
            return
        self.window.signal_jump.emit(int(value))

    def jumpToFrame(self, value):
        # only if we are not a dummy connection
        if self.script_launcher is None:
            return
        self.window.signal_jumpTo.emit(int(value))

    def jumpFramesWait(self, value):
        # only if we are not a dummy connection
        if self.script_launcher is None:
            return
        self.window.signal_jump.emit(int(value))
        # wait for frame change to be completed
        while self.window.new_frame_number != int(value) or self.window.loading_image:
            time.sleep(0.01)

    def jumpToFrameWait(self, value):
        # only if we are not a dummy connection
        if self.script_launcher is None:
            return
        self.window.signal_jumpTo.emit(int(value))
        # wait for frame change to be completed
        while self.window.new_frame_number != int(value) or self.window.loading_image:
            time.sleep(0.01)

    def reloadMask(self):
        # only if we are not a dummy connection
        if self.script_launcher is None:
            return
        self.window.signal_broadcast.emit("ReloadMask", tuple())

    def reloadMarker(self, value):
        # only if we are not a dummy connection
        if self.script_launcher is None:
            return
        frame = int(value)
        if frame == -1:
            frame = self.data_file.get_current_image()
        self.window.signal_broadcast.emit("ReloadMarker", (frame,))

    def reloadTypes(self):
        # only if we are not a dummy connection
        if self.script_launcher is None:
            return
        self.window.signal_broadcast.emit("UpdateCounter", tuple())

    def getImage(self, value):
        # only if we are not a dummy connection
        if self.script_launcher is None:
            return
        image = self.window.data_file.get_image_data(int(value))
        return image

    def hasTerminateSignal(self):
        return self.stop


class Addon:
    def __init__(self, database, command=None):
        self.cp = Command(command)
        self.db = clickpoints.DataFile(database)

    def terminate(self):
        self.cp.stop = True

    def run(self, start_frame=0):
        pass
