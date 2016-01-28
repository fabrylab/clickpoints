from __future__ import division, print_function
import os
import sys
import subprocess
import shutil
import urllib
import zipfile

try:
    from urllib import urlopen  # python 2
except ImportError:
    from urllib.request import urlopen  # python 3

## parameters
link_server_version=r"http://fabry_biophysics.bitbucket.org/clickpoints/version.html"
link_server_update=r"http://fabry_biophysics.bitbucket.org/clickpoints/link.html"
basedir=os.path.join(os.path.dirname(__file__), "..")
file_local_version=os.path.join(basedir,r"version.txt")
file_local_filelist=os.path.join(basedir, "..", "..", "..", r"files.txt")
path_update="update_tmp"

def copytree(src, dst, symlinks=False, ignore=None):
    #print(os.listdir(src))
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            try:
                shutil.copytree(s, d, symlinks, ignore)
            except WindowsError:
                pass
                #print("Can't copy %s %s" % (s,d))
            copytree(s,d,symlinks,ignore)
        else:
            shutil.copy2(s, d)
            #print("copy %s %s" % (s,d))

def checkForUpdate():
    """" executed from base """
    ## get server version
    r=urlopen(link_server_version)
    if not r.getcode()==200:
        print('Can\'t reach server')
        return False, '',''
    server_version=r.read()
    #print('server version: %s' % server_version)

    ## get local version
    f=open(file_local_version,'r')
    local_version=f.readline()
    f.close()
    #print('local version: %s' % local_version)

    ## check if update is necessary
    if not local_version == server_version:
        print('Update to version %s found!' % server_version)
        update=True
        return update,server_version, local_version
    else:
        #print('no update available')
        update=False
        return update, '',''

def doPrep():
    """" executed from base """
    print("Running PREPARE as PID: %d" % os.getpid())

    ## get local version
    f=open(file_local_version,'r')
    local_version=f.readline()
    f.close()
    print('local version: %s' % local_version)

    ## get server version
    r=urllib.urlopen(link_server_version)
    if not r.getcode()==200:
        raise Exception('Can\'t reach server')

    server_version=r.read()
    print('server version: %s' % server_version)

    ## get server link
    r=urllib.urlopen(link_server_update)
    if not r.getcode()==200:
        raise Exception('Can\'t reach server')
    link_server_dl=r.read()
    link_server_dl=link_server_dl % server_version
    print('server DL link: %s' % link_server_dl)

    ## get files for update
    if not os.path.exists(path_update):
        os.mkdir(path_update)

    ## dowload files
    urllib.urlretrieve("http://"+link_server_dl,os.path.join(path_update,"clickpoints.zip"))

    ## extract files
    with zipfile.ZipFile(os.path.join(path_update,"clickpoints.zip"),'r') as z:
        z.extractall(path_update)

    os.remove(os.path.join(path_update,"clickpoints.zip"))

    # # fork clean process
    subprocess.Popen([sys.executable,os.path.abspath(os.path.join(path_update,'clickpoints','get_update.py')),'update'],close_fds=True)


def doUpdate():
    """" executed from update/ """
    print("Running UPDATE as PID: %d" % os.getpid())

    os.chdir(os.path.dirname(os.path.abspath(os.path.join(__file__, ".."))))
    #print('currentpath: %s' % os.path.abspath(os.path.curdir))

    ## get base path
    base_path = os.path.dirname(os.path.abspath(os.path.join(__file__, ".."))) # update file path
    base_path,tail=os.path.split(base_path)       # main path (thats update tmp)
    base_path,tail=os.path.split(base_path)       # main path (thats clickpoints)
    base_path,tail=os.path.split(base_path)       # main path (thats clickpointspriject)
    base_path=os.path.normpath(base_path)

    ## get update path
    update_path= os.path.dirname(os.path.abspath(os.path.join(__file__, ".."))) # update file path
    update_path,tail=os.path.split(update_path)    # thats update

    #print("base path: %s" % base_path)
    #print("update path: %s" % update_path)

    ## remove local files according to local file list
    with open(file_local_filelist, 'r') as f:
        local_filelist=f.readlines()

    os.chdir(base_path)
    for fl in local_filelist:
        #trim newlines and creat absolut path
        fl=os.path.abspath(fl.strip())

        # verify that its in base path and does exist
        if fl.startswith(base_path) and os.path.isfile(fl):
            #print("remove: %s" %fl)
            os.remove(fl)

    ## copy filess from update folder to local
    #print(os.path.join(base_path,'clickpoints',path_update))
    #print(base_path)
    copytree(os.path.join(base_path,'clickpoints',path_update),base_path)

    # # fork clean process
    os.chdir('clickpoints')
    #print('currentpath: %s' % os.path.abspath(os.path.curdir))
    subprocess.Popen([sys.executable,os.path.normpath(os.path.join('get_update.py')),'clean'],close_fds=True)
    exit(0)

def doCleanUp():
    """" executed from base """
    print("Running CLEAN UP as PID: %d" %os.getpid())
    base_path= os.path.dirname(os.path.abspath(os.path.join(__file__, ".."))) # update file path
    base_path,tail=os.path.split(base_path)       # main path (thats update)

    ## clean up update folder
    shutil.rmtree(os.path.join(base_path,'clickpoints',path_update))

    # remove all .pyc files
    clickpointsproject_path = os.path.dirname(os.path.abspath(os.path.join(__file__, "..", "..")))  # update file path
    matches = []
    for root, dirnames, filenames in os.walk(clickpointsproject_path):
        matches.extend([os.path.join(clickpointsproject_path, root, filename) for filename in filenames if filename.lower().endswith(".pyc")])
    for match in matches:
        os.remove(match)

    print("Update completed")

    
if __name__ == '__main__':
    mode= sys.argv[1]
    #mode='update'

    assert isinstance(mode,str)
    print("Running update script - mode: %s" % mode)

    if mode=='check':
        ret,newversion,localversion=checkForUpdate()
        if ret:
            print('Update available!')
        else:
            print('NO Update available')

    elif mode=='prepare':
        doPrep()

    elif mode=='update':
        doUpdate()

    elif mode=='clean':
        doCleanUp()

    else:
        raise Exception("Unknown mode: %s" % mode)


