from __future__ import division, print_function
import os
import sys
from sys import platform as _platform
import re
import glob
import numpy as np

from datetime import datetime, timedelta
import time

from databaseFiles import DatabaseFiles
from PIL import Image
import PIL.ExifTags


sys.path.append(os.path.dirname(__file__))
from Config import Config
config = Config(os.path.join(os.path.dirname(__file__),'sql.cfg')).sql


#region imports
# import imageio or opencv
imageio_loaded=False
opencv_loaded=False
imgformats = []
try:
    import imageio
    imageio_loaded=True
    for format in imageio.formats:
        if 'i' in format.modes:
            imgformats.extend(format._extensions)
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
        nrframes = reader.get_length()
        reader.close()
        return nrframes
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
                #print(path)
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
    # link_name_available=False
    path=[]
    link_name=[]

    for line in content:
        if line.lstrip().startswith("["):
            reg=re.search('\[(.*)\]',line.strip())
            link_name = reg.group(1)
            # print(line.strip(),link_name)
            # link_name_available=True

        if line.lstrip().startswith("path"):
            # path=line.strip().replace("path=","")
            path=line.split("=")[-1].strip()
            # print("path:",path)

        if path and link_name:
            # print(path, link_name)
            smbcfg['mount_points'][path]=link_name
            path=[]
            link_name=[]

        if line.lstrip().startswith("interfaces"):
            tokens=line.strip().split(" ")
            print("interflisen",line)
            interface = tokens[-1]
            # print("interface:",interface)
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
ignore=False
mode="add"
start_path=""

max_block_commit_size=10000
verbose = False

# load mysqlDB
database = DatabaseFiles(config)

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

# check for keyword parameters
for item in sys.argv[3::]:
    if item=='--verbose':
        verbose=True
        print('verbose-mode enabled')

# get smb and nic config for mount points
smbcfg=getSMBConfig()
ipaddress=getIpAddress(smbcfg['interface'])

# differentiate between real root and network mountpoint root
# all login files must be associated by their network mountpoint root
# not their root on the file system!

print('Sambacfg:\n',smbcfg)
print('ipaddress:',ipaddress)

smb_start_path=os.path.normpath(asSMBPath(ipaddress,smbcfg['mount_points'],start_path))

if mode=='remove':
    ### 1) remove all child files and folders from DB
    # get path ids - based on the checked in smb path
    try:
        path_id_list=database.getIdListForPath(smb_start_path)
        path_id = path_id_list[-1]

        # delete file and path entries from DB
        database.deleteFilesByPathID(path_id)
    except:
        print("No DB entries found, continue clearing .done files!")

    ### 2) remove all check in *.done files
    for root, dirs, files in os.walk(start_path, topdown=False):
        # check for *.done files and remove them
        done_file = os.path.join(root,'.pathwalker.done')
        if os.path.exists(done_file):
            os.remove(done_file)
            print('removing *.done:',done_file)

if mode=='add':
    print("add")
    file_counter=0
    skipped_counter=0
    path_done_list = []
    file_skip_list = []
    file_list = []
    time_start=time.time()
    for root, dirs, files in os.walk(start_path, topdown=False):
        #print(root, files)
        file_skip_per_path = []
        loadConfigs(root)

        if ignore:
            print("Ignoring folder:", root)
            continue


        # differentiate between real root and network mountpoint root
        # all login files must be associated by their network mountpoint root
        # not their root on the file system!
        folder_id = AddPathToDatabase(asSMBPath(ipaddress,smbcfg['mount_points'],root))
        print("Processing path:",root, folder_id)

        ## check if we're resuming a run
        if os.path.isfile(os.path.join(root,'.pathwalker.done')):
           print('*.done exists - continue')
           continue

        ### add entrys
        for file in files:

            # extract Meta
            basename, ext = os.path.splitext(file)

            # add functionalty to handel single regexp string or list of regexp strings
            # if single string
            if type(filename_data_regex) is str:
                match = re.match(filename_data_regex, os.path.basename(file))
            # if list - iterate over all proposed regexps
            elif type(filename_data_regex) is list:
                for regexp in filename_data_regex:
                    match = re.match(regexp, os.path.basename(file))
                    if match: break # found a match - exit loop

            if not match:
                print("no match for %s" % file)
                file_skip_per_path.append(file)
                continue

            data = match.groupdict()

            # First timestamp
            if "timestamp" in data:
                tstamp = datetime.strptime(data["timestamp"], time_format)
                if "micros" in data:
                    tstamp = tstamp + timedelta(microseconds=int(data["micros"])*1e5)
            elif time_from_exif:
                tstamp = getExifTime(os.path.join(root, file))
            else:
                #raise NameError("No time information available. Use timestamp in regex or use time_from_exif")
                continue

            # Second timestamp
            if "timestamp2" in data:
                tstamp2 = datetime.strptime(data["timestamp2"], time_format)
                if "micros2" in data:
                    tstamp2 = tstamp2 + timedelta(microseconds=int(data["micros2"])*1e5)
            else:
                tstamp2 = tstamp

            # Frames
            if tstamp2 != tstamp and fps != 0:
                frames = np.floor((tstamp2 - tstamp).total_seconds() * fps)
            elif not ext.lower() in imgformats:
                try:
                    frames = getFrameNumber(os.path.join(root, file))
                except:
                    frames = 1
            else:
                frames = 1

            # adjust second timestamp if frame rate was extracted
            if delta_t != 0 and tstamp2 == tstamp:
                tstamp2 = tstamp + timedelta(seconds=delta_t)*frames

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
            if verbose:
                print("Adding: %s %d" % (file,frames))
            file_list.append(dict(timestamp=tstamp, timestamp2=tstamp2, frames=frames, system=system_id, device=device_id, basename=basename, path=folder_id, extension=ext))

        # append to done_list to write done files after commit to DB
        path_done_list.append(os.path.join(root,'.pathwalker.done'))
        file_skip_list.append(file_skip_per_path)

        # write entries to DB in larger blocks
        if len(file_list) > max_block_commit_size:
            database.saveFiles(file_list)
            print(len(file_list), "items inserted")
            file_counter+=len(file_list)
            file_list=[]

            # create .done file for resume
            for idx, done in enumerate(path_done_list):
                fdone = open(done,'w')
                fdone.write("skipped files:\n")
                for line in file_skip_list[idx]:
                    fdone.write(line + "\n")
                fdone.close()
                skipped_counter+= len(file_skip_list[idx])

            path_done_list=[]
            file_skip_list=[]

            # some runtime information
            time_stop=time.time()
            print("%.2fk files in  %.2f min" % (file_counter/1000,(time_stop - time_start)/60))
            print("%d files skipped" % skipped_counter)

    # write entries to DB on final pass
    if len(file_list) > 0:
        database.saveFiles(file_list)
        print(len(file_list), "items inserted")
        file_counter+=len(file_list)
        file_list=[]

        # create .done file for resume
        for idx,done in enumerate(path_done_list):
            fdone = open(done,'w')
            fdone.write("skipped files:\n")
            for line in file_skip_list[idx]:
                fdone.write(line + "\n")
            print("write to:",done)
            fdone.close()
            skipped_counter += len(file_skip_list[idx])
        path_done_list=[]
        file_skip_list=[]

        # some runtime information
        time_stop=time.time()
        print("%.2fk files in  %.2f min" % (file_counter/1000,(time_stop - time_start)/60))
        print("%d files skipped" % skipped_counter)