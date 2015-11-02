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


''' Parameters'''
# name_scheme = TS1(_TS2)_SYSTEM_DEVICE_DIV.ext
timestamp_scheme= '%Y%m%d-%H%M%S'
name_scheme = '{timestamp}_{system}_{device}{ext}'
path_scheme = os.path.join('{basepath}','{year}','{system}','{device}','{yearmonthday}','{hour}')

#input_folder =
#output_folder=
extensions=['.jpg', '.png', '.tif', '.tiff']

basepath = '\\\\131.188.117.94\data'
meta = DotDict({'system':'microbsDDU',
                'device':'32n1',
                'timestamp':None,
                'ext':''})


start_path=r'G:\microbs31_1'

# get list of files


''' for each file'''
filecounter=0
time_start = time.time()
for root, dirs, files in os.walk(start_path, topdown=False):
    print(root)
    print(dirs)
    for file in files:
        # reset values
        meta.timestamp=None
        meta.ext=''

        # get file type
        name, meta.ext = os.path.splitext(file)

        if meta.ext.lower() in extensions:
            try:
                # get time stamp from exif
                meta.timestamp = getExifTime(os.path.join(root,file))



                #generate new file name
                new_name = name_scheme.format(timestamp=meta.timestamp.strftime(timestamp_scheme),
                                              system=meta.system,
                                              device=meta.device,
                                              ext=meta.ext)
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























