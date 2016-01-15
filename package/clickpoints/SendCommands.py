from __future__ import division, print_function
import sys
import os
import socket
import signal
import imageio

from MemMap import MemMap

def send(message):
    HOST, PORT = "localhost", int(sys.argv[3])
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(message, (HOST, PORT))

def send2(message):
    cmd, value = str(message).split(" ", 1)
    HOST, PORT = "localhost", int(sys.argv[3])
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(message, (HOST, PORT))
    # blocking wait for answer
    answer_received=False
    while not answer_received:
        ans=sock.recv(1024)
        #print("Received: %s" % ans)
        if ans.startswith(cmd):
            answer_received=True
            #print("correct command")
    #split command value
    # TODO is it better to send None instead of empty string ""
    value=""
    try:
        cmd, value = str(ans).split(" ", 1)
        #print("cmd,value:",cmd,value)
    except:
        #print("something went wrong")
        pass
    return value

def JumpFrames(value):
    send("JumpFrames %d \n" % value)

def JumpToFrame(value):
    send("JumpToFrame %d \n" % value)

def JumpFramesWait(value):
    send2("JumpFramesWait %d \n" % value)

def JumpToFrameWait(value):
    send2("JumpToFrameWait %d \n" % value)

def GetImage(value):
    results = send2("GetImage %d \n" % value)
    try:
        image_path, id, frame = results.split(" ")
    except ValueError:
        return None, None, None
    layout_header = (
                dict(name="shape", type="uint32", shape=3),
                dict(name="type", type="|S30"),
                )

    memmap = MemMap(image_path, layout_header)
    shape = memmap.shape

    layout_images = (
            dict(name="data", type=memmap.type, shape=(shape[0]*shape[1]*shape[2])),
    )
    memmap.add(layout_images)
    image = memmap.data.reshape(shape).copy()
    return image, int(id), int(frame)

def GetImageName(value):
    return send2("GetImageName %d \n" % value)

def GetMarkerName(value):
    return send2("GetMarkerName %d \n" % value)

def updateHUD(value):
    return send("updateHUD %s \n" % value)

terminate_signal = False
def CatchTerminateSignal():
    def signal_handler(signal, frame):
        global terminate_signal
        terminate_signal = True

    if hasattr(os.sys, 'winver'):
        signal.signal(signal.SIGBREAK, signal_handler)
    else:
        signal.signal(signal.SIGTERM, signal_handler)

def HasTerminateSignal():
    global terminate_signal
    return terminate_signal