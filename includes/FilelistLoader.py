#region includes
from __future__ import division, print_function, unicode_literals
import os
import glob
import sys
from datetime import datetime, timedelta
from distutils.version import LooseVersion
import peewee
import time
import numpy as np

try:
    from itertools import izip_longest as zip_longest  # python 2
except ImportError:
    from itertools import zip_longest  # python 3

from threading import Thread

from PyQt4 import QtCore
from PIL import Image
import PIL

try:
    from natsort import natsorted
except ImportError:
    natsorted = sorted

imgformats = ['jpg', 'png', 'tif', 'tiff']
vidformats = ['mp4', 'avi']

try:
    import imageio
    if LooseVersion(imageio.__version__) < LooseVersion('1.3'):
        print("Imageio version %s is too old, trying to update" % imageio.__version__)
        result = os.system("pip install imageio --upgrade")
        if result == 0:
            print("Please restart clickpoints for the update to take effect.")
            sys.exit(-1)
        else:
            print("Update failed, trying to use alternative backend")
            raise ImportError
    print("Using ImageIO", imageio.__version__)

    imageio_loaded = True
    imgformats = []
    for format in imageio.formats:
        if 'i' in format.modes:
            imgformats.extend(format._extensions)
    imgformats = [fmt if fmt[0] == "." else "."+fmt for fmt in imgformats]
    vidformats = []
    for format in imageio.formats:
        if 'I' in format.modes:
            vidformats.extend(format._extensions)
    vidformats = [fmt if fmt[0] == "." else "."+fmt for fmt in vidformats]
except ImportError:
    imageio_loaded = False

import regexpfilefilter as ref

if imageio_loaded:
    formats = tuple(imgformats+vidformats)
else:
    formats = tuple(imgformats)
imgformats = tuple(imgformats)
#print("Formats Image", imgformats, len(imgformats))
#print("Formats Video", vidformats, len(vidformats))
#endregion

#region directories


def timedelta_mul(self, other):
    if isinstance(other, (int, float)):
        return timedelta(seconds=self.total_seconds()*other)
    else:
        return NotImplemented


def isstring(object):
    PY3 = sys.version_info[0] == 3

    if PY3:
        return isinstance(object, str)
    else:
        return isinstance(object, basestring)


def timedelta_div(self, other):
    if isinstance(other, (int, float)):
        return timedelta(seconds=self.total_seconds()/other)
    else:
        return NotImplemented


def linspace_timestamp(timestamp, timestamp2, frames):
    if timestamp2 is None or timestamp is None:
        return [timestamp]*frames
    return timestamp + np.arange(frames)*timedelta_div(timestamp2-timestamp, frames)


def WalkSubdirectories(path):
    matches = []
    for root, dirnames, filenames in os.walk(path):
        matches.extend([os.path.join(root, filename) for filename in filenames if filename.lower().endswith(formats)])
    return matches


def GetFilesInDirectory(root):
    return [os.path.join(root, filename) for filename in os.listdir(root) if filename.lower().endswith(formats)]


def PathToFilelist(paths):
    if isstring(paths):
        paths = [paths]
    path_list = []
    for path in paths:
        if path[-1] == os.sep:
            path_list.extend(WalkSubdirectories(path))
        elif path.endswith(formats):
            path_list.extend([path])
        elif os.path.exists(path):
            path_list.extend(WalkSubdirectories(path))
    return path_list


def GetFileListFromInput(input, filterparam, config):
    # Single file? put it in an array
    if isstring(input):
        input = [input]

    # if we have a single image, load the whole folder and start with this image as current frame
    if len(input) == 1 and not input[0].lower().endswith(formats) and not os.path.isdir(input[0]) and "*" not in input[0]:
        sys.tracebacklimit = 0
        raise ExceptionExtensionNotSupported("ERROR: file format %s not supported!" % input[0])
    if len(input) == 1 and input[0].lower().endswith(imgformats) and not "*" in input[0]:
        select = input[0]
        path_list = GetFilesInDirectory(os.path.dirname(input[0]))
    else:
        # Go through the inputs and extract all files which can be opened
        select = None
        path_list = []
        for path in input:
            if '*' in path:
                glob_list = glob.glob(path)
                if path[-1] == os.sep:  # Path glob
                    glob_list = PathToFilelist(glob_list)
                else:  # File glob
                    glob_list = [filename for filename in glob_list if filename.lower().endswith(formats)]
                path_list.extend(glob_list)
            else:
                path_list.extend(PathToFilelist(path))
    if config and config.use_natsort:
        path_list = natsorted(path_list)
    else:
        path_list = sorted(path_list)

    # check for filter module
    if filterparam != {}:
        print('init regexpfilefilter')
        filefilter = ref.regexpfilefilter(filterparam)
        path_list = filefilter.apply_filter(path_list)
    path_list = [os.path.normpath(path) for path in path_list]

    return path_list, select


class ExceptionNoFilesFound(Exception):
    pass


class ExceptionExtensionNotSupported(Exception):
    pass


def ListFiles(data_file, input, file_ids=[], rettype='img', buffer_size=10, filterparam={}, select=None, mediahandler_instance=None, force_recursive=False, dont_process_filelist=False, exclude_ending=None, config=None):
    # prevent print spam on file list load
    if type(input) is tuple:
        print("Input is file list/multiple directories with %d entries" % len(input))
    else:
        print("Input", input)

    import time
    t = time.time()
    if dont_process_filelist:
        path_list = input
    else:
        path_list, select = GetFileListFromInput(input, filterparam, config)
        if exclude_ending is not None:
            path_list = [filename for filename in path_list if not filename.endswith(exclude_ending)]
    print("Preparation", time.time()-t, "s")

    for file in path_list:#, file_ids:
        extension = os.path.splitext(file)[1]
        frames = getFrameNumber(file, extension)
        data_file.add_image(file, extension, None, frames)
    #filelist = FileList(config)
    #select_index = filelist.add_files(path_list, file_ids, select)

    #if filelist.get_frame_count() == 0:
    #    sys.tracebacklimit = 0
    #    raise ExceptionNoFilesFound("No valid files found!")

    #return filelist, select_index

def getFrameNumber(file, extension):
    if extension.lower() in imgformats:
        frames = 1
    else:
        try:
            reader = imageio.get_reader(file)
        except IOError:
            print("ERROR: can't read file", file)
            return 0
        frames = reader.get_length()
    return frames

import re
filename_data_regex = r'.*(?P<timestamp>\d{8}-\d{6})'
filename_data_regex = re.compile(filename_data_regex)
filename_data_regex2 = r'.*(?P<timestamp>\d{8}-\d{6})_(?P<timestamp2>\d{8}-\d{6})'
filename_data_regex2 = re.compile(filename_data_regex2)
def getTimeStamp(file, extension):
    global filename_data_regex
    if extension.lower() == ".tif" or extension.lower() == ".tiff":
        dt = get_meta(file)
        return dt, dt
    match = filename_data_regex.match(file)
    if match:
        match2 = filename_data_regex2.match(file)
        if match2:
            match = match2
        par_dict = match.groupdict()
        if "timestamp" in par_dict:
            dt = datetime.strptime(par_dict["timestamp"], '%Y%m%d-%H%M%S')
            if "timestamp2" in par_dict:
                dt2 = datetime.strptime(par_dict["timestamp2"], '%Y%m%d-%H%M%S')
            else:
                dt2 = dt
            return dt, dt2
    elif extension.lower() == ".jpg":
        dt = getExifTime(file)
        return dt, dt
    else:
        print("no time", extension)
    return None, None

def getExifTime(path):
    img = Image.open(path)
    try:
        exif = {
            PIL.ExifTags.TAGS[k]: v
            for k, v in img._getexif().items()
            if k in PIL.ExifTags.TAGS
        }
        return datetime.strptime(exif["DateTime"], '%Y:%m:%d %H:%M:%S')
    except (AttributeError, ValueError):
        return None

def get_meta(file):
    import tifffile
    import json
    with tifffile.TiffFile(file) as tif:
        try:
            metadata = tif[0].image_description
        except AttributeError:
            return None
        try:
            t = json.loads(metadata.decode('utf-8'))["Time"]
            return datetime.strptime(t, '%Y%m%d-%H%M%S')
        except (AttributeError, ValueError, KeyError):
            return None
    return None