from __future__ import division, print_function
import os
import re
import glob

from datetime import datetime
from database import Database

def AddPathToDatabase(root):
    root = os.path.normpath(root)
    folder_list = [x for x in root.split("\\") if x != ""]
    parent_id = 0
    for folder in folder_list[:-1]:
        parent_id = database.savePath(folder, parent_id)
    return parent_id

database = Database()
files = glob.glob(r"\\131.188.117.94\data\microbsDDU\microbs31_3\*")
filename_data_regex = r'.*(?P<timestamp>\d{8})_(?P<device>.+)\.'
time_format = '%Y%m%d'
system_name = "microbsDDU"
device_name = "microbs31_3"

#files = glob.glob(r"\\131.188.117.94\spot2014\campbell\2014\*\*\*SPOT_CAMP.jpg")
start_path = r"\\131.188.117.94\spot2014\mobotix\2014"
#files = glob.glob(r"\\131.188.117.94\spot2014\mobotix\2014\*\*\*SPOT_mobotix.jpg")
filename_data_regex = r'.*(?P<timestamp>\d{8}-\d{6})_(?P<system>.+?[^_])_(?P<device>.+)\.jpg'
time_format = '%Y%m%d-%H%M%S'
system_name = "AtkaSpot"
device_name = "Campbell"
device_name = "Mobotix"
last_folder = ""

for root, dirs, files in os.walk(start_path):
    print(root, files)
    folder_id = AddPathToDatabase(root)
    query = database.SQL_Files.delete().where(database.SQL_Files.path == folder_id)
    print(query.execute(),"items deleted")
    file_data = []
    for file in files:
        basename, ext = os.path.splitext(file)
        match = re.match(filename_data_regex, os.path.basename(file))
        if not match:
            continue
        data = match.groupdict()
        tstamp = datetime.strptime(data["timestamp"], time_format)
        system_id = database.getSystemId(system_name)
        device_id = database.getDeviceId(system_name, device_name)
        file_data.append(dict(timestamp=tstamp, system=system_id, device=device_id, basename=basename, path=folder_id, extension=ext))
    if len(file_data):
        database.saveFiles(file_data)
        print(len(file_data),"items inserted")
