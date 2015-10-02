from __future__ import division, print_function
import os
import re
import glob

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

database = Database()

"""
files = glob.glob(r"\\131.188.117.94\data\microbsDDU\microbs31_3\*")
filename_data_regex = r'.*(?P<timestamp>\d{8})_(?P<device>.+)\.'
time_format = '%Y%m%d'
system_name = "microbsDDU"
device_name = "microbs31_3"

#files = glob.glob(r"\\131.188.117.94\spot2014\campbell\2014\*\*\*SPOT_CAMP.jpg")
start_path = r"\\131.188.117.94\spot2014\mobotix\2014"
start_path = r"\\131.188.117.94\spot2014\mobotix_south\2014"
start_path = r"\\131.188.117.94\spot2014\ge"
#files = glob.glob(r"\\131.188.117.94\spot2014\mobotix\2014\*\*\*SPOT_mobotix.jpg")


filename_data_regex = r'.*(?P<timestamp>\d{8}-\d{6})-(?P<micros>\d)_(?P<system>.+?[^_])_(?P<device>.+)\.jpg'
time_format = '%Y%m%d-%H%M%S'
system_name = "AtkaSpot"
device_name = "Campbell"

time_from_exif = True
if time_from_exif:
    time_format = '%Y:%m:%d %H:%M:%S'

device_name = "GE4000"
"""

start_path = r"\\131.188.117.94\data\microbsCRO\2012"

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
        if "timestamp" in data:
            tstamp = datetime.strptime(data["timestamp"], time_format)
            tstamp = tstamp + timedelta(microseconds=int(data["micros"])*1e5)
        elif time_from_exif:
            tstamp = getExifTime(os.path.join(root, file))
        else:
            raise NameError("No time information available. Use timestamp in regex or use time_from_exif")
        try:
            system_id = database.getSystemId(system_name)
        except KeyError:
            system_id = database.newSystem(system_name)
        try:
            device_id = database.getDeviceId(system_name, device_name)
        except KeyError:
            device_id = database.newDevice(system_id, device_name)
        file_data.append(dict(timestamp=tstamp, system=system_id, device=device_id, basename=basename, path=folder_id, extension=ext))
    if len(file_data):
        database.saveFiles(file_data)
        print(len(file_data),"items inserted")
