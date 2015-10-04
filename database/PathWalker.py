from __future__ import division, print_function
import os
import re
import glob
import numpy as np

from datetime import datetime, timedelta
from database import Database
from PIL import Image
import PIL.ExifTags
import cv2

script_path = os.path.dirname(__file__)

def getExifTime(path):
    img = Image.open(path)
    exif = {
        PIL.ExifTags.TAGS[k]: v
        for k, v in img._getexif().items()
        if k in PIL.ExifTags.TAGS
    }
    return datetime.strptime(exif["DateTime"], '%Y:%m:%d %H:%M:%S')

def getFrameNumber(path):
    cap = cv2.VideoCapture(path)
    return int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT))

def AddPathToDatabase(root):
    root = os.path.normpath(root)
    folder_list = [x for x in root.split("\\") if x != ""]
    parent_id = 0
    print(folder_list)
    for folder in folder_list[:]:
        parent_id = database.savePath(folder, parent_id)
    return parent_id

def loadConfigs(folder_path):
    global fps, delta_t
    path = os.path.normpath(folder_path)
    parent = os.path.join(path, ".")
    path_list = []
    while parent != path:
        path = parent
        parent = os.path.normpath(os.path.join(path, ".."))
        path_list.append(os.path.normpath(os.path.join(path, "ConfigPathWalker.txt")))
    path_list.append(os.path.join(script_path, "ConfigPathWalker.txt"))
    for path in path_list[::-1]:
        if os.path.exists(path):
            with open(path) as f:
                print(path)
                code = compile(f.read(), path, 'exec')
                exec(code, globals())
    if fps != 0:
        delta_t = 1./fps

def EstimateFps(folder):
    files = sorted(glob.glob(folder))
    frames = -1
    time = 0
    fps = []
    for file in files:
        r = re.match(filename_data_regex, os.path.basename(file))
        data = r.groupdict()
        print(data)
        time_new = datetime.strptime(data["timestamp"], time_format)
        if frames != -1:
            fps.append( frames/(time_new-time).total_seconds())
        frames = getFrameNumber(r"\\131.188.117.94\data\microbsDDU\microbs31_1\20140407_microbs31_1.mp4")
        time = time_new
    print(1./np.array(fps))

filename_data_regex = r''
time_from_exif = False
time_format = ''
fps = 0
delta_t = 0
system_name = ""
device_name = ""

database = Database()

start_path = r"\\131.188.117.94\antavia2013-1204to0103"#r"\\131.188.117.94\data\microbsCRO\2012"

for root, dirs, files in os.walk(start_path, topdown=False):
    print(root, files)
    loadConfigs(root)
    folder_id = AddPathToDatabase(root)
    print("folder_id", folder_id)
    query = database.SQL_Files.delete().where(database.SQL_Files.path == folder_id)
    print(query.execute(),"items deleted")
    file_data = []
    for file in files:
        basename, ext = os.path.splitext(file)
        match = re.match(filename_data_regex, os.path.basename(file))
        if not match:
            continue
        data = match.groupdict()
        # Frames
        try:
            frames = getFrameNumber(os.path.join(root, file))
        except:
            frames = 1
        # First timestamp
        if "timestamp" in data:
            tstamp = datetime.strptime(data["timestamp"], time_format)
            if "micros" in data:
                tstamp = tstamp + timedelta(microseconds=int(data["micros"])*1e5)
        elif time_from_exif:
            tstamp = getExifTime(os.path.join(root, file))
        else:
            raise NameError("No time information available. Use timestamp in regex or use time_from_exif")
        # Second timestamp
        if "timestamp2" in data:
            tstamp2 = datetime.strptime(data["timestamp2"], time_format)
            if "micros2" in data:
                tstamp2 = tstamp2 + timedelta(microseconds=int(data["micros2"])*1e5)
        elif delta_t != 0:
            tstamp2 = tstamp + timedelta(seconds=delta_t)*frames
        else:
            tstamp2 = tstamp
        # System id
        try:
            system_id = database.getSystemId(system_name)
        except KeyError:
            system_id = database.newSystem(system_name)
        # Device id
        try:
            device_id = database.getDeviceId(system_name, device_name)
        except KeyError:
            device_id = database.newDevice(system_id, device_name)
        # Append to list
        print("frames", frames)
        file_data.append(dict(timestamp=tstamp, timestamp2=tstamp2, frames=frames, system=system_id, device=device_id, basename=basename, path=folder_id, extension=ext))
    if len(file_data):
        database.saveFiles(file_data)
        print(len(file_data),"items inserted")
