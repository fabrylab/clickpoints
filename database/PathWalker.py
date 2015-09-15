from __future__ import division, print_function
import os
import re
import glob

from datetime import datetime
from database import Database

database_instance = Database()
files = glob.glob(r"\\131.188.117.94\data\microbsDDU\microbs31_3\*")
filename_data_regex = r'.*(?P<timestamp>\d{8})_(?P<device>.+)\.'
time_format = '%Y%m%d'
system_name = "microbsDDU"
device_name = "microbs31_3"

files = glob.glob(r"\\131.188.117.94\spot2014\campbell\2014\*\*\*SPOT_CAMP.jpg")
files = glob.glob(r"\\131.188.117.94\spot2014\mobotix\2014\*\*\*SPOT_mobotix.jpg")
filename_data_regex = r'.*(?P<timestamp>\d{8}-\d{6})_(?P<system>.+?[^_])_(?P<camera>.+)'
time_format = '%Y%m%d-%H%M%S'
system_name = "AtkaSpot"
device_name = "Campbell"
device_name = "Mobotix"
last_folder = ""
for index,file in enumerate(files):
    file = os.path.normpath(file)
    folder = os.path.dirname(file)
    print(folder, last_folder)
    if folder != last_folder:
        print("Change Folder")
        paths = [x for x in file.split("\\") if x != ""]
        parent_folder = 0
        for path_folder in paths[:-1]:
            parent_folder = database_instance.savePath(path_folder, parent_folder)
        last_folder = folder
    #print(folder)
    print("%.3f" % (index/len(files)*100), os.path.basename(file))
    match = re.match(filename_data_regex, os.path.basename(file))
    paths = [folder for folder in file.split("\\") if folder != ""]
    #print(paths)
    #die
    basename = os.path.splitext(os.path.split(file)[1])[0]
    ext = os.path.splitext(file)[1]
    if match:
        data = match.groupdict()
        path = os.path.normpath(file)
        tstamp = datetime.strptime(data["timestamp"], time_format)
        database_instance.saveFile(tstamp, system_name, device_name, basename, ext, parent_folder)