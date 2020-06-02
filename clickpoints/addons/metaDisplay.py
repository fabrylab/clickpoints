#!/usr/bin/env python
# -*- coding: utf-8 -*-
# metaDisplay.py

# Copyright (c) 2015-2020, Richard Gerum, Sebastian Richter, Alexander Winterl
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ClickPoints. If not, see <http://www.gnu.org/licenses/>

from __future__ import print_function, division
import sys,os
import numpy as np
import datetime
import socket
import select
import time
import collections

import clickpoints

sys.path.append(os.path.join(os.path.dirname(__file__),'..','includes'))
from Config import Config

''' Config Section - copy to displayMetaInfo.cfg for personal config
[displayMetaInfo]
db_path = I:\atkaSPOT_Meta.db
field_list = ["met_t2","met_ff2","met_Dd2"]
display_format = meta info:
                 t:    {met_t2:>7}
                 ws:   {met_ff2:>7}
                 dir:  {met_Dd2:>7}
'''

# config default values
cfg_default = collections.OrderedDict()
cfg_default['db_path'] = r'I:\atkaSPOT_Meta.db'
cfg_default['field_list'] = ["met_t2","met_ff2","met_Dd2"]
cfg_default['display_format'] = "t:    {met_t2:>5}\n"\
                 "ws:   {met_ff2:>5}\n"\
                 "dir:  {met_Dd2:>5}"

cfg_file = os.path.join(os.path.dirname(__file__),'displayMetaInfo.cfg')
if os.path.exists(cfg_file):
    print("Using config file at %s" % cfg_file)

    cfg = Config(cfg_file,defaults=cfg_default).displayMetaInfo

    print("db_path:", cfg.db_path)


start_frame, database, port = clickpoints.GetCommandLineArgs()
com = clickpoints.Commands(port, catch_terminate_signal=True)

def displayMetaInfo(ans):
    # print('in function:',ans)
    command,fullname,framenr = ans[0].split(' ',2)
    fpath,fname = os.path.split(fullname)

    # print(com,fname,framenr)

    t_start = time.clock()
    timestring = fname[0:14]
    timestamp = datetime.datetime.strptime(timestring, '%Y%m%d-%H%M%S')

    field_dict=db.getValuesForList(timestamp,cfg.field_list)
    # print(field_dict)

    #print('time: %.3fs' % (time.clock()-t_start))
    if field_dict:
        com.updateHUD(cfg.display_format.format(**field_dict))


print("Stated metaDB Display Addon ...")

# Database access

from metaDB.accessMetaDB import MetaDB
db=MetaDB(dbpath=cfg.db_path)

# input
HOST="localhost"
PORT=port
BROADCAST_PORT = PORT +1

# broadcast socket to listen to
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setblocking(0)
sock.bind(('127.0.0.1',BROADCAST_PORT))


last_img_nr = -1
# main loop
while True:
        ready_to_read, ready_to_write, in_error = select.select([sock],[],[],0)

        # wait for incomming signal
        if ready_to_read:
            ans=sock.recvfrom(1024)

            # print("Received:")
            # print(ans)

            # split information
            # print(ans[0].split()[2])
            img_nr = np.int(ans[0].split()[2])

            if ans[0].startswith('PreLoadImageEvent') and img_nr != last_img_nr:
                # print("nr is:",img_nr)
                displayMetaInfo(ans)
                last_img_nr = img_nr

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
                            if not last_message == ans and not last_message=='' and img_nr != last_img_nr:
                                print("reached this")
                                displayMetaInfo(last_message)
                                last_message=''
                                last_img_nr = img_nr





