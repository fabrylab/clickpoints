from __future__ import division, print_function
import sys
import os
import socket
import signal

from MemMap import MemMap


def send(message):
    HOST, PORT = "localhost", int(sys.argv[3])
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(message, (HOST, PORT))


def send_and_receive(message):
    cmd, value = str(message).split(" ", 1)
    HOST, PORT = "localhost", int(sys.argv[3])
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(message, (HOST, PORT))
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


def JumpFrames(value):
    """
    Let ClickPoints jump the given amount of frames.
    
    Parameters
    ---------
    value : int
        the amount of frame which ClickPoints should jump.
    """
    send("JumpFrames %d \n" % value)


def JumpToFrame(value):
    """
    Let ClickPoints jump to the given frame.
    
    Parameters
    ---------
    value : int
        the frame to which ClickPoints should jump.
    """
    send("JumpToFrame %d \n" % value)


def JumpFramesWait(value):
    """
    Let ClickPoints jump the given amount of frames and wait for it to complete.
    
    Parameters
    ---------
    value : int
        the amount of frame which ClickPoints should jump.
    """
    send_and_receive("JumpFramesWait %d \n" % value)


def JumpToFrameWait(value):
    """
    Let ClickPoints jump to the given frame and wait for it to complete.
    
    Parameters
    ---------
    value : int
        the frame to which ClickPoints should jump.
    """
    send_and_receive("JumpToFrameWait %d \n" % value)


def GetImage(value):
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
    results = send_and_receive("GetImage %d \n" % value)
    try:
        image_path, id, frame = results.split(" ")
    except ValueError:
        return None, None, None

    memmap = MemMap(image_path)
    shape = memmap.shape
    image = memmap.data.reshape(shape).copy()
    return image, int(id), int(frame)


def updateHUD(value):
    """
    """
    return send("updateHUD %s \n" % value)


def ReloadMask():
    """
    Reloads the current mask file in ClickPoints.
    """
    return send_and_receive("ReloadMask \n")


def CatchTerminateSignal():
    """
    Catch the terminate signal when ClickPoints wants to close the script execution. When called at the beginning of the
    script, the signal is cached and its status can be queried with `HasTerminateSignal`. This can be used for a gentle
    program termination, where the current progress loop can be finished before stopping the program execution.
    """
    global terminate_signal
    
    def signal_handler(signal, frame):
        global terminate_signal
        terminate_signal = True
        
    terminate_signal = False

    if hasattr(os.sys, 'winver'):
        signal.signal(signal.SIGBREAK, signal_handler)
    else:
        signal.signal(signal.SIGTERM, signal_handler)


def HasTerminateSignal():
    """
    Whether or not the program has received a terminate signal form ClickPoints. Can only be used if
    `CatchTerminateSignal` was called before.
    
    Returns
    -------
    terminate_signal : bool
        True if ClickPoints has sent a terminate signal.
    """
    global terminate_signal
    return terminate_signal
