from __future__ import division, print_function
import os
import sys
from sys import platform as _platform
import re
import glob
import numpy as np

from datetime import datetime, timedelta
from databaseFiles import DatabaseFiles, config
from PIL import Image
import PIL.ExifTags

#region imports
# import imageio or opencv
imageio_loaded=False
opencv_loaded=False
try:
    import imageio
    imageio_loaded=True
except:
    print("Image IO not available")

    try:
        import cv2
        opencv_loaded=True
    except:
        raise Exception("Neither opencv nor imageio found!")

#endregion


script_path = os.path.dirname(__file__)

#region functions
def getExifTime(path):
    img = Image.open(path)
    exif = {
        PIL.ExifTags.TAGS[k]: v
        for k, v in img._getexif().items()
        if k in PIL.ExifTags.TAGS
    }
    return datetime.strptime(exif["DateTime"], '%Y:%m:%d %H:%M:%S')

def getFrameNumber(path):
    if imageio_loaded:
        reader = imageio.get_reader(path)
        return reader.get_length()
    elif opencv_loaded:
        cap = cv2.VideoCapture(path)
        return int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT))

def AddPathToDatabase(root):
    root = os.path.normpath(root)
    folder_list = [x for x in root.split(os.sep) if x != ""]
    parent_id = 0
    #print(folder_list)
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

## experimental
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

# usage
def printUsage():
    print("------------------------------------------------------")
    print("PathWalker.py - recursivly adds file to mySQL database")
    print("")
    print("USAGE:")
    print("\tPathWalker.py mode path")
    print("\tmode:\tadd\t- adds files in path")
    print("\t\tremove\t- removes files in path")
    print("\tpath:\ttarget path (relative or absolut)")

# get ip adress of unix system by ethX

def getIpAddress(nic):
    if _platform == "linux" or _platform == "linux2":
        a=os.popen(u"ifconfig %s | grep \"inet\ addr\" | cut -d: -f2 | cut -d\" \" -f1" % str(nic))
        return a.read().strip()
    else:
        raise Exception("Function: getIpAdress(nic) not implemented for your system!")


def getSMBConfig(filename=u"/etc/samba/smb.conf"):
    with open(filename) as f:
        content = f.readlines()

    # search for definition blocks
    smbcfg={}
    smbcfg['mount_points']={}
    #link_name_available=False
    path=[]
    link_name=[]

    for line in content:
        if line.startswith("["):
            reg=re.search('\[(.*)\]',line.strip())
            link_name = reg.group(1)
            #print(line.strip(),link_name)
            #link_name_available=True


        if line.startswith("path="):
            path=line.strip().replace("path=","")
            #print("path:",path)

        if path and link_name:
            #print(path, link_name)
            smbcfg['mount_points'][path]=link_name
            path=[]
            link_name=[]

        if line.startswith("interfaces"):
            tokens=line.strip().split(" ")
            interface = tokens[-1]
            #print("interface:",interface)
            smbcfg['interface']=interface


    return smbcfg

def asSMBPath(ip,mountpoints,path):
    for key in mountpoints:
        if path.startswith(key):
            #print('match',key,mountpoints[key])
            # replace real path with smb mount point
            path=path.replace(key,os.sep+mountpoints[key]+ os.sep)
            # remove leading /
            path=path.replace(os.sep,'',1)
            # add base ip
            path= os.path.join(os.sep,ip,path)


            return path
    return 0
#endregion

filename_data_regex = r''
time_from_exif = False
time_format = ''
fps = 0
delta_t = 0
system_name = ""
device_name = ""
mode="add"
start_path=""

# load mysqlDB
database = DatabaseFiles(config())

## process inline parameters
try:
    if len(sys.argv) < 3:
        raise Exception("Parameters missing!")
except:
    printUsage()
    sys.exit(1)


# get mode
mode_list = ['add','remove']
tmp=sys.argv[1]
if tmp in mode_list:
    mode = tmp
    print("Mode:\t",mode)
else:
        print("Unuspported mode:",tmp)
        printUsage()
        sys.exit(1)


# get target path
tmp=sys.argv[2]
if os.path.exists(tmp):
    start_path=os.path.abspath(tmp)
    print('Path:\t',tmp)
    print('FullPath:\t',start_path)
else:
    print("Path %s does not exist"%tmp)
    sys.exit(1)

# get smb and nic config for mount points
smbcfg=getSMBConfig()
ipaddress=getIpAddress(smbcfg['interface'])

print('Sambacfg:\n',smbcfg)
print('ipaddress:',ipaddress)


#raise Exception('test done')
# for root, dirs, files in os.walk(start_path, topdown=False):
#     print('root:',root)
#     print('dirs:',dirs)
#     print('files:',files)
#
# sys.exit(1)

#start_path = r"\\131.188.117.94\antavia2013-1204to0103"#r"\\131.188.117.94\data\microbsCRO\2012"

for root, dirs, files in os.walk(start_path, topdown=False):
    print(root, files)
    loadConfigs(root)

    # differentiate between real root and network mountpoint root
    # all login files must be associated by their network mountpoint root
    # not their root on the file system!

    folder_id = AddPathToDatabase(asSMBPath(ipaddress,smbcfg['mount_points'],root))
    print("folder_id", folder_id)

    ## check if we're resuming a run
    if os.path.isfile(os.path.join(root,'pathwalker.done')) and mode=="add":
        print('have been here before - continue')
        continue

    ### delete entrys based in this folder
    query = database.SQL_Files.delete().where(database.SQL_Files.path == folder_id)
    print(query.execute(),"items deleted")
    if mode=='remove':
        continue

    ### add entrys
    file_data = []
    for file in files:
        # extract Meta
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

    # write entries to DB
    if len(file_data):
        database.saveFiles(file_data)
        print(len(file_data),"items inserted")

    # create .done file for resume
    fdone = open('pathwalker.done','w')
    fdone.write(len(file_data))
    fdone.close()

# on complete remove resume files
for root, dirs, files in os.walk(start_path, topdown=False):
    if os.path.isfile(os.path.join(root,'pathwalker.done')):
        print(os.path.join(root,'pathwalker.done'))
