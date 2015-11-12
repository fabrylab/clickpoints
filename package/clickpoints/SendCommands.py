import socket, sys

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