from __future__ import division, print_function
import argparse
import os
import socket
import signal
import numpy as np
from MemMap import MemMap


class Commands:
    def __init__(self, port=None, catch_terminate_signal=False):
        self.HOST = "localhost"
        if port is None:
            print("No port supplied. Returning a dummy connection.")
        self.PORT = port
        if catch_terminate_signal:
            self.CatchTerminateSignal()

    def _send(self, message):
        if self.PORT is None:
            return
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(message, (self.HOST, self.PORT))

    def _send_and_receive(self, message):
        if self.PORT is None:
            return
        cmd, value = str(message).split(" ", 1)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(message, (self.HOST, self.PORT))
        # blocking wait for answer
        answer_received = False
        while not answer_received:
            ans = sock.recv(1024)
            if ans.startswith(cmd):
                answer_received = True

        # TODO is it better to send None instead of empty string ""
        value = ""
        try:
            cmd, value = str(ans).split(" ", 1)
        except ValueError:
            pass
        return value


    def JumpFrames(self, value):
        """
        Let ClickPoints jump the given amount of frames.

        Parameters
        ---------
        value : int
            the amount of frame which ClickPoints should jump.
        """
        self._send("JumpFrames %d \n" % value)

    def JumpToFrame(self, value):
        """
        Let ClickPoints jump to the given frame.

        Parameters
        ---------
        value : int
            the frame to which ClickPoints should jump.
        """
        self._send("JumpToFrame %d \n" % value)

    def JumpFramesWait(self, value):
        """
        Let ClickPoints jump the given amount of frames and wait for it to complete.

        Parameters
        ---------
        value : int
            the amount of frame which ClickPoints should jump.
        """
        self._send_and_receive("JumpFramesWait %d \n" % value)

    def JumpToFrameWait(self, value):
        """
        Let ClickPoints jump to the given frame and wait for it to complete.

        Parameters
        ---------
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

    def ReloadMarker(self, frame=None):
        """
        Reloads the marker from the given frame in ClickPoints.

        Parameters
        ---------
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
