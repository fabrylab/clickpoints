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
import argparse
import os
import sys
import socket
import signal
import numpy as np
from MemMap import MemMap


class PrintHook:
    def __init__(self, out, func):
        self.func = func
        self.origOut = None
        self.out = out

        if out:
            sys.stdout = self
            self.origOut = sys.__stdout__
        else:
            sys.stderr = self
            self.origOut = sys.__stderr__

    def __del__(self):
        if self.out:
            sys.stdout = self.origOut
        else:
            sys.stderr = self.origOut
        self.origOut = None

    def write(self, text):
        # write to stdout, file and call the function
        self.origOut.write(text)
        self.func(text)

    def __getattr__(self, name):
        # pass the rest to the original output
        if self.origOut is not None:
            return getattr(self.origOut, name, None)


global hook1, hook2
def StartHooks(func):
    global hook1, hook2
    hook1 = PrintHook(1, func)
    hook2 = PrintHook(0, func)


class Commands:
    """
    The Commands class provides an interface for external scripts to communicate with a currently open ClickPoints
    instance. Communication is done using socket connection. ClickPoints provides the port number for this connection
    when calling an external script. Use clickpoints.GetCommandLineArgs to obtain the port number.

    Parameters
    ----------
    port: int, optional
        the port for the socket connection to communicate with ClickPoints. If it is not provided, a dummy connection is
        used with doesn't pass any commands. This behaviour is provided to enable external scripts to run with and
        without a ClickPoints instance.
    catch_terminate_signal: bool, optional
        whether a terminate signal from ClickPoints should directly terminate the script (default) or if only the
        terminate_signal flag should be set. This flag can later on be queried with HasTerminateSignal()
    """
    def __init__(self, port=None, catch_terminate_signal=False):
        self.HOST = "localhost"
        if port is None:
            print("No port supplied. Returning a dummy connection.")
        self.PORT = port
        if catch_terminate_signal:
            self.CatchTerminateSignal()
        StartHooks(self.log)

    def _send(self, message):
        if self.PORT is None:
            return
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(message.encode(), (self.HOST, self.PORT))

    def _send_and_receive(self, message):
        if self.PORT is None:
            return
        cmd, value = str(message).split(" ", 1)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(message.encode(), (self.HOST, self.PORT))
        # blocking wait for answer
        answer_received = False
        while not answer_received:
            ans = sock.recv(1024).decode()
            if ans.startswith(cmd):
                answer_received = True

        # TODO is it better to send None instead of empty string ""
        value = ""
        try:
            cmd, value = str(ans).split(" ", 1)
        except ValueError:
            pass
        return value

    def log(self, *args):
        """
        Print to the ClickPoints console.

        Parameters
        ----------
        *args : string
            multiple strings to print
        """
        text = " ".join([str(arg) for arg in args])
        self._send("log %s \n" % text)

    def JumpFrames(self, value):
        """
        Let ClickPoints jump the given amount of frames.

        Parameters
        ----------
        value : int
            the amount of frame which ClickPoints should jump.
        """
        self._send("JumpFrames %d \n" % value)

    def JumpToFrame(self, value):
        """
        Let ClickPoints jump to the given frame.

        Parameters
        ----------
        value : int
            the frame to which ClickPoints should jump.
        """
        self._send("JumpToFrame %d \n" % value)

    def JumpFramesWait(self, value):
        """
        Let ClickPoints jump the given amount of frames and wait for it to complete.

        Parameters
        ----------
        value : int
            the amount of frame which ClickPoints should jump.
        """
        self._send_and_receive("JumpFramesWait %d \n" % value)

    def JumpToFrameWait(self, value):
        """
        Let ClickPoints jump to the given frame and wait for it to complete.

        Parameters
        ----------
        value : int
            the frame to which ClickPoints should jump.
        """
        self._send_and_receive("JumpToFrameWait %d \n" % value)

    def GetImage(self, value):
        """
        Get the currently in ClickPoints displayed image.

        Returns
        -------
        image : ndarray
            the image data.
        image_id : int
            the image id in the database.
        image_frame : int
            which frame is used if the image is from a video file. 0 if the source is an image file.
        """
        results = self._send_and_receive("GetImage %d \n" % value)
        try:
            image_path, id = results.split(" ")
        except ValueError:
            return None, None

        memmap = MemMap(image_path)
        shape = memmap.shape
        image = memmap.data[:np.prod(shape)].reshape(shape).copy()
        return image, int(id)

    def updateHUD(self, value):
        """
        """
        return self._send("updateHUD %s \n" % value)

    def ReloadMask(self):
        """
        Reloads the current mask file in ClickPoints.
        """
        return self._send_and_receive("ReloadMask \n")

    def CurrentImage(self):
        """
        Returns the current image.
        """
        string = self._send_and_receive("CurrentImage \n")
        print("Debug4 %s"%string)
        try:
            return int(string)
        except ValueError:
            return 1

    def ReloadMarker(self, frame=None):
        """
        Reloads the marker from the given frame in ClickPoints.

        Parameters
        ----------
        frame : int
            the frame which ClickPoints should reload.
        """
        if frame is None:
            frame = -1
        return self._send_and_receive("ReloadMarker %d \n" % frame)

    def ReloadTypes(self):
        """
        Reloads the marker types.
        """
        return self._send_and_receive("ReloadTypes \n")

    def _signal_handler(self, signal, frame):
        self.terminate_signal = True

    def CatchTerminateSignal(self):
        """
        Catch the terminate signal when ClickPoints wants to close the script execution. When called at the beginning of the
        script, the signal is cached and its status can be queried with `HasTerminateSignal`. This can be used for a gentle
        program termination, where the current progress loop can be finished before stopping the program execution.
        """

        self.terminate_signal = False

        if hasattr(os.sys, 'winver'):
            signal.signal(signal.SIGBREAK, self._signal_handler)
        else:
            signal.signal(signal.SIGTERM, self._signal_handler)

    def HasTerminateSignal(self):
        """
        Whether or not the program has received a terminate signal form ClickPoints. Can only be used if
        `CatchTerminateSignal` was called before.

        Returns
        -------
        terminate_signal : bool
            True if ClickPoints has sent a terminate signal.
        """
        return self.terminate_signal
