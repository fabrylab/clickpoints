from __future__ import division, print_function
import sys
import os
import socket
import signal

def send(message):
    HOST, PORT = "localhost", int(sys.argv[3])
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(message, (HOST, PORT))

def send2(message):
    HOST, PORT = "localhost", int(sys.argv[3])
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(message, (HOST, PORT))
    return sock.recv(1024)

def JumpFrames(value):
    send("JumpFrames %d \n" % value)

def JumpToFrame(value):
    send("JumpToFrame %d \n" % value)

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