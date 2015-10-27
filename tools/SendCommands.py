import socket, sys

def send(message):
    HOST, PORT = "localhost", int(sys.argv[3])
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(message, (HOST, PORT))

def JumpFrames(value):
    send("JumpFrames %d \n" % value)