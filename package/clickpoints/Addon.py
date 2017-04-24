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
    def __init__(self, script_launcher):
        self.script_launcher = script_launcher
        self.window = self.script_launcher.window

    def jumpFrames(self, value):
        self.window.signal_jump.emit(int(value))

    def jumpToFrame(self, value):
        self.window.signal_jumpTo.emit(int(value))

    def jumpFramesWait(self, value):
        self.window.signal_jump.emit(int(value))
        # wait for frame change to be completed
        while self.window.new_frame_number != int(value) or self.window.loading_image:
            time.sleep(0.01)

    def jumpToFrameWait(self, value):
        self.window.signal_jumpTo.emit(int(value))
        # wait for frame change to be completed
        while self.window.new_frame_number != int(value) or self.window.loading_image:
            time.sleep(0.01)

    def reloadMask(self):
        self.window.signal_broadcast.emit("ReloadMask", tuple())

    def reloadMarker(self, value):
        frame = int(value)
        if frame == -1:
            frame = self.data_file.get_current_image()
        self.window.signal_broadcast.emit("ReloadMarker", (frame,))

    def reloadTypes(self):
        self.window.signal_broadcast.emit("UpdateCounter", tuple())

    def getImage(self, value):
        image = self.window.data_file.get_image_data(int(value))
        return image


class Addon:
    def __init__(self, database=None, command=None):
        self.cp = Command(command)
        self.db = clickpoints.DataFile(database)

    def run(self, start_frame=0):
        pass
