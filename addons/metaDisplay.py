# -*- coding: utf-8 -*-
from __future__ import print_function, division
import sys
import numpy as np
import datetime
import socket
import select

from clickpoints.SendCommands import  GetImageName, GetMarkerName, HasTerminateSignal, CatchTerminateSignal, updateHUD
from clickpoints.MarkerLoad import LoadLogIDindexed, SaveLog

# config
db_path = r'C:\Users\fox\Dropbox\PhD\python\atkaSPOT_MetaDB\atkaSPOT_Meta.db'
field_list = ['met_t2','met_ff2','met_Dd2']
display_format = 't:\t{met_t2}\nws:\t{met_ff2}\ndir:\t{met_Dd2}'

# Database access
sys.path.append(r'C:\Users\fox\Dropbox\PhD\python\atkaSPOT_MetaDB')
from accessMetaDB import *
db=atkaSPOT_MetaDB(dbpath=db_path)

# input
start_frame = int(sys.argv[2])
HOST, PORT = "localhost", int(sys.argv[3])
fname = GetImageName(start_frame)

# fname= sys.argv[1]

# extract timestamp
print('metaDisplay: fname',fname)


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('127.0.0.1',PORT+1))




print('PORT:',PORT+1)
print("listening ...")
while True:
        # wait for incomming signal
        ans=sock.recvfrom(1024)
        print("got something")

        print("Received:")
        print(ans)

        # split information
        if ans[0].startswith('PreLoadImageEvent'):
            com,fname,framenr = ans[0].split(' ',2)
            print(com,fname,framenr)

            timestring = fname[0:14]
            timestamp = datetime.datetime.strptime(timestring, '%Y%m%d-%H%M%S')

            # get values according to field list and store in dictionary
            field_dict={}
            for item in field_list:
                val=db.getFirstValidValue(timestamp,item)
                field_dict[item]=val

            updateHUD(display_format.format(**field_dict))




