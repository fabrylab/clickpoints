# -*- coding: utf-8 -*-
from __future__ import print_function, division
import sys
import numpy as np
import datetime
import socket
import select
import time

from clickpoints.SendCommands import  HasTerminateSignal, CatchTerminateSignal, updateHUD

def displayMetaInfo(ans):
    # print('in function:',ans)
    com,fname,framenr = ans[0].split(' ',2)
    # print(com,fname,framenr)

    t_start = time.clock()
    timestring = fname[0:14]
    timestamp = datetime.datetime.strptime(timestring, '%Y%m%d-%H%M%S')

    field_dict=db.getValuesForList(timestamp,field_list)
    # print(field_dict)

    print('time: %.3fs',time.clock()-t_start)

    updateHUD(display_format.format(**field_dict))

# config
db_path = r'I:\atkaSPOT_Meta.db'
field_list = ['met_t2','met_ff2','met_Dd2']
display_format = 't:    {met_t2:>5}\n'\
                 'ws:   {met_ff2:>5}\n'\
                 'dir:  {met_Dd2:>5}'


print("Stated metaDB Display Addon ...")

# Database access
sys.path.append(r'C:\Users\fox\Dropbox\PhD\python\atkaSPOT_MetaDB')
from accessMetaDB import *
db=atkaSPOT_MetaDB(dbpath=db_path)

# input
start_frame = int(sys.argv[2])
HOST, PORT = "localhost", int(sys.argv[3])
BROADCAST_PORT = PORT +1

# broadcast socket to listen to
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setblocking(0)
sock.bind(('127.0.0.1',BROADCAST_PORT))



# main loop
while True:
        ready_to_read, ready_to_write, in_error = select.select([sock],[],[],0)

        # wait for incomming signal
        if ready_to_read:
            ans=sock.recvfrom(1024)

            # print("Received:")
            # print(ans)

            # split information
            if ans[0].startswith('PreLoadImageEvent'):
                displayMetaInfo(ans)

                # annoying buffer part
                # read out and thereby delete all remaining entries
                last_message = ""
                messages_pending=False
                ready_to_read, ready_to_write, in_error = select.select([sock],[],[],0)
                if ready_to_read:
                    messages_pending=True
                    while messages_pending:
                        ready_to_read, ready_to_write, in_error = select.select([sock],[],[],0)
                        # clear incomming buffer
                        if ready_to_read:
                            tmp =sock.recvfrom(1024)
                            # print('message pending', tmp)
                            if tmp[0].startswith('PreLoadImageEvent'):
                                last_message = tmp
                                # print('lastmsg:',last_message)
                        else:
                            messages_pending = False
                            # make sure last message is displayed
                            if not last_message == ans and not last_message=='':
                                displayMetaInfo(last_message)
                                last_message=''





