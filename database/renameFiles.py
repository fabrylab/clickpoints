#!/usr/bin/env python
# -*- coding: utf-8 -*-
# renameFiles.py

# Copyright (c) 2015-2016, Richard Gerum, Sebastian Richter
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ClickPoints. If not, see <http://www.gnu.org/licenses/>

''' renameFiles.py
VERSION for images
Rename script to default pengu-naming scheme
TS1(_TS2)_SYSTEM_DEVICE.ext with TS format YYYYMMDD-HHMMSS
'''

from __future__ import division, print_function
import os
import shutil
import re
import glob
import numpy as np
import time
import imageio
import cv2
try:
    from cv2.cv import CV_CAP_PROP_POS_FRAMES as CAP_PROP_POS_FRAMES
    from cv2.cv import CV_CAP_PROP_FRAME_COUNT as CAP_PROP_FRAME_COUNT
    from cv2.cv import CV_CAP_PROP_FRAME_WIDTH as CAP_PROP_FRAME_WIDTH
    from cv2.cv import CV_CAP_PROP_FRAME_HEIGHT as CAP_PROP_FRAME_HEIGHT
    from cv2.cv import CV_CAP_PROP_FPS as CAP_PROP_FPS
    from cv2.cv import CV_RGB2BGR as COLOR_RGB2BGR
except ImportError:
    from cv2 import CAP_PROP_POS_FRAMES as CAP_PROP_POS_FRAMES
    from cv2 import CAP_PROP_FRAME_COUNT as CAP_PROP_FRAME_COUNT
    from cv2 import CAP_PROP_FRAME_WIDTH as CAP_PROP_FRAME_WIDTH
    from cv2 import CAP_PROP_FRAME_HEIGHT as CAP_PROP_FRAME_HEIGHT
    from cv2 import CAP_PROP_FPS as CAP_PROP_FPS
    from cv2 import COLOR_RGB2BGR as COLOR_RGB2BGR

from datetime import datetime, timedelta
from PIL import Image
import PIL.ExifTags

class DotDict(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def getExifTime(path):
    img = Image.open(path)
    exif = {
        PIL.ExifTags.TAGS[k]: v
        for k, v in img._getexif().items()
        if k in PIL.ExifTags.TAGS
    }
    return datetime.strptime(exif["DateTime"], '%Y:%m:%d %H:%M:%S')

def getVideoTime(path):
    start_time = datetime.fromtimestamp(int(os.path.getmtime(path)))

    cap = cv2.VideoCapture(path)
    frames = int(cap.get(CAP_PROP_FRAME_COUNT))
    fps = cap.get(CAP_PROP_FPS)

    end_time = start_time+timedelta(seconds=frames/fps)
    return start_time, end_time


#print(getExifTime(r"F:\MicrObs Go-Pro 2015\2015-03-12\100GOPRO\GOPR7642.JPG"))
#getVideoTime(r"F:\MicrObs Go-Pro 2015\2015-06-18\100GOPRO\GO011971.MP4")
#die

''' Parameters'''
# name_scheme = TS1(_TS2)_SYSTEM_DEVICE_DIV.ext
timestamp_scheme = '%Y%m%d-%H%M%S'
name_scheme = '{timestamp}_{system}_{device}{ext}'
path_scheme = os.path.join('{basepath}','{system}','{device}','{year}','{yearmonthday}','{hour}')

#input_folder =
#output_folder=
extensions = ['.jpg', '.png', '.tif', '.tiff']

extensions_vid = ['.mp4']

basepath = r'/mnt/data1/data/' #'\\\\131.188.117.94\data'
meta = DotDict({'system': 'microbsRAT',
                'device': 'D10',
                'timestamp': None,
                'ext': ''})


start_path = r'/media/pengu/microbs_data/microbsRAT/2011/20111126#/jpg/'

# get list of files


''' for each file'''
filecounter = 0
time_start = time.time()
for root, dirs, files in os.walk(start_path, topdown=False):
    print(root)
    print(dirs)
    for file in files:
        # reset values
        meta.timestamp = None
        meta.ext = ''

        # get file type
        name, meta.ext = os.path.splitext(file)

        if meta.ext.lower() in extensions:
            try:
                if meta.ext.lower() in extensions_vid:
                    # get time stamp from exif
                    meta.timestamp, meta.timestamp2 = getVideoTime(os.path.join(root, file))
                    name_timestamp = meta.timestamp.strftime(timestamp_scheme)+"_"+meta.timestamp2.strftime(timestamp_scheme)
                else:
                    # get time stamp from exif
                    meta.timestamp = getExifTime(os.path.join(root, file))
                    name_timestamp = meta.timestamp.strftime(timestamp_scheme)



                #generate new file name
                new_name = name_scheme.format(timestamp=name_timestamp,
                                              system=meta.system,
                                              device=meta.device,
                                              ext=meta.ext.lower())
                #generate new path
                new_path = path_scheme.format(basepath=basepath,
                                              year=meta.timestamp.strftime('%Y'),
                                              system=meta.system,
                                              device=meta.device,
                                              yearmonthday=meta.timestamp.strftime('%Y%m%d'),
                                              hour=meta.timestamp.strftime('%H'))
                new_path=os.path.normpath(new_path)

                output=os.path.join(new_path,new_name)
                print('move {file} to {output}'.format(file=os.path.join(root,file),output=output))

                #copy file
                if not os.path.exists(output):
                    # check dir
                    if not os.path.isdir(new_path):
                        os.makedirs(new_path)
                    shutil.copy(os.path.join(root,file),output)
                else:
                    print('Warning file already exists')

                filecounter+=1
                print("completed: %d"%filecounter)
                time_stop=time.time()
                print("time elapsed: %.2f min" % ((time_stop - time_start)/60))
            except:
                print('Couldn\'t process file: ',file)
