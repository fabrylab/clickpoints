from __future__ import division,print_function
import os
import sys
import subprocess
import shutil
import urllib
import zipfile

## parameters
link_server_version=r"http://fabry_biophysics.bitbucket.org/clickpoints/version.html"
link_server_update=r"http://fabry_biophysics.bitbucket.org/clickpoints/clickpoints.zip"
file_local_version=r"version.txt"
file_local_filelist=r"files.txt"
path_update="update"

def copytree(src, dst, symlinks=False, ignore=None):
    print(os.listdir(src))
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            try:
                shutil.copytree(s, d, symlinks, ignore)
            except WindowsError:
                print("Can't copy %s %s" % (s,d))
            copytree(s,d,symlinks,ignore)
        else:
            shutil.copy2(s, d)
            #print("copy %s %s" % (s,d))

def checkForUpdate():
    """" executed from base """
    ## get server version
    r=urllib.urlopen(link_server_version)
    server_version=r.read()
    print('server version: %s' % server_version)

    ## get local version
    f=open(file_local_version,'r')
    local_version=f.readline()
    f.close()
    print('local version: %s' % local_version)

    # TODO: remove always update hack
    local_version='0.0'

    ## check if update is necessary
    if not local_version == server_version:
        print('Update to version %s found!' % server_version)
        update=True
    else:
        print('no update available')
        update=False
    return update

def doPrep():
    """" executed from base """
    ## get files for update
    if not os.path.exists(path_update):
        os.mkdir(path_update)

    ## dowload files
    urllib.urlretrieve(link_server_update, os.path.join(path_update,"clickpoints.zip"))

    ## extract files
    with zipfile.ZipFile(os.path.join(path_update,"clickpoints.zip"),'r') as z:
        z.extractall(path_update)

    # TODO: remove copy for live version!
    shutil.copy('get_update.py','update\clickpoints\get_update.py')

    # # fork clean process
    print(os.path.abspath(os.path.join(path_update,'clickpoints','get_update.py')))
    subprocess.Popen(['python.exe',os.path.abspath(os.path.join(path_update,'clickpoints','get_update.py')),'update'],close_fds=True)
    exit(0)

def doUpdate():
    """" executed from update/ """
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print('currentpath: %s' % os.path.abspath(os.path.curdir))

    ## get base path
    base_path = os.path.dirname(os.path.abspath(__file__)) # update file path
    base_path,tail=os.path.split(base_path)       # main path (thats update)
    base_path,tail=os.path.split(base_path)       # main path (thats clickpoints)
    base_path,tail=os.path.split(base_path)       # main path (thats clickpointspriject)
    base_path=os.path.normpath(base_path)

    ## get update path
    update_path= os.path.dirname(os.path.abspath(__file__)) # update file path
    update_path,tail=os.path.split(update_path)    # thats update

    print("base path: %s" % base_path)
    print("update path: %s" % update_path)

    ## remove local files according to local file list
    with open(os.path.normpath(os.path.join('../../',file_local_filelist)),'r') as f:
        local_filelist=f.readlines()

    os.chdir(base_path)
    for fl in local_filelist:
        #trim newlines and creat absolut path
        fl=os.path.abspath(fl.strip())
        print(fl)
        # verify that its in base path and does exist
        if fl.startswith(base_path) and os.path.isfile(fl):
            print("remove: %s" %fl)
            #os.remove(fl)

    ## copy filess from update folder to local
    print(os.path.join(base_path,'clickpoints',path_update))
    print(base_path)
    copytree(os.path.join(base_path,'clickpoints',path_update),base_path)

    # # fork clean process
    os.chdir('clickpoints')
    print('currentpath: %s' % os.path.abspath(os.path.curdir))
    subprocess.Popen(['python.exe',os.path.normpath(os.path.join('get_update.py')),'clean'],close_fds=True)
    exit(0)

def doCleanUp():
    """" executed from base """
    base_path= os.path.dirname(os.path.abspath(__file__)) # update file path
    base_path,tail=os.path.split(base_path)       # main path (thats update)

    ## clean up update folder
    shutil.rmtree(os.path.join(base_path,'clickpoints',path_update))
    exit(0)
    
if __name__ == '__main__':
    mode= sys.argv[1]
    #mode='update'

    assert isinstance(mode,str)
    print("running update script - mode: %s" % mode)

    if mode=='check':
        print(__file__)
        ret=checkForUpdate()
        if ret:
            print('Update available!')
        else:
            print('NO Update available')

    elif mode=='prep':
        if checkForUpdate():
            doPrep()

    elif mode=='update':
        print('do Update')
        doUpdate()

    elif mode=='clean':
        doCleanUp()

    else:
        raise Exception("Unknown mode: %s" % mode)


