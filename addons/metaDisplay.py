# -*- coding: utf-8 -*-
from __future__ import print_function, division
import sys
import numpy as np
import datetime

from clickpoints.SendCommands import  GetImageName, GetMarkerName, HasTerminateSignal, CatchTerminateSignal, updateHUD
from clickpoints.MarkerLoad import LoadLogIDindexed, SaveLog

# config
db_path = r'C:\Users\fox\Dropbox\PhD\python\atkaSPOT_MetaDB\atkaSPOT_Meta.db'
field_list = ['met_t2','met_ff2','met_Dd2']
display_format = 't:{met_t2}\nws:{met_ff2}\ndir:{met_Dd2}'

# Database access
sys.path.append(r'C:\Users\fox\Dropbox\PhD\python\atkaSPOT_MetaDB')
from accessMetaDB import *
db=atkaSPOT_MetaDB(dbpath=db_path)

# input
start_frame = int(sys.argv[2])
fname = GetImageName(start_frame)
# fname= sys.argv[1]


# extract timestamp
print(fname)
timestring = fname[0:14]
timestamp = datetime.datetime.strptime(timestring, '%Y%m%d-%H%M%S')

# get values according to field list and store in dictionary
field_dict={}
for item in field_list:
    val=db.getFirstValidValue(timestamp,item)
    field_dict[item]=val

print(field_dict)
print(display_format.format(**field_dict))

updateHUD(display_format.format(**field_dict))


