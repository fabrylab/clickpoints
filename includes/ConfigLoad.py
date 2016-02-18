from __future__ import division, print_function, unicode_literals
import sys
import os
import json

try:
    from PyQt5.QtWidgets import QApplication, QFileDialog
except ImportError:
    from PyQt4.QtGui import QApplication, QFileDialog
    from PyQt4 import QtGui, QtCore

def isstring(object):
    PY3 = sys.version_info[0] == 3

    if PY3:
        return isinstance(object, str)
    else:
        return isinstance(object, basestring)

start_globals = globals().copy()

srcpath = ""
database_file = ""

""" @config General """
# @config `outputpath =` the path where to save the DB and mask files. Set to `None` defaults to the `srcpath`
outputpath = ""
# @config `outputpath_mask =` a sub path of output path where to save mask files. Set to "" to default to outputpath
outputpath_mask = "mask"
# @config `filename_data_regex = ` specify a regular expression to obtain meta-data from filenames
filename_data_regex = r'.*(?P<timestamp>\d{8}-\d{6})_(?P<system>.+?[^_])_(?P<camera>.+)'
# @config `filterparam =` specify additional filters for the files to use
filterparam = {}

# @config `jumps =` specify how many frames the numpad keys `2`,`3`,`5`,`6`,`8`,`9`,`/`,`*` should jump
jumps = (-1, +1, -10, +10, -100, +100, -1000, +1000)

# @config `max_image_size = ` the maximum size of one image before it is internally split into tiles
max_image_size = 2 ** 14

# @config `rotation =` the rotation of the image when starting
rotation = 0
# @config `rotation_steps =` how much to rotate time image when `r` is pressed
rotation_steps = 90

# @config `hide_interfaces =` whether to hide the interfaces a program start. Press F2 to show it again.
hide_interfaces = True

# @config `addons =` a list of additional python files to load
addons = []

threaded_image_display = False
threaded_image_load = False

""" @config Marker """
# @config `logname_tag =` specifies what to append to the log file.
logname_tag = '_pos.txt'

TYPE_Normal = 0
TYPE_Rect = 1
TYPE_Line = 2
TYPE_Track = 4

# @config `types = {0: ["marker", [255, 0, 0], TYPE_Normal]}` specifies what categories to use. Every category is an array with three entires. Name, Color and Type. Types can be 0: normal marker, 1: rectangle markers, 2: line markers
types = {0: ["marker", [255, 0, 0], TYPE_Normal]}

# @config `tracking = ` specify whether to use tracking mode
tracking = False
# @config `tracking_connect_nearest =` if set to true, a new marker will always be connected to the nearest track
tracking_connect_nearest = False
# @config `tracking_show_trailing =` how many track points to show before the current frame, to show all use -1
tracking_show_trailing = -1
# @confing `tracking_show_leading =` how many track points to show after the current frame, to show all use -1
tracking_show_leading = 0

""" @config Mask """
# @config `maskname_tag =` specifies what to append to the mask file.
maskname_tag = '_mask.png'
# @config `auto_mask_update =` whether to update the mask display after each stroke or manually by key press
auto_mask_update = True
# @config `draw_types = [[0,[255,0,0]]` specifies what categories to use for mask drawing. Every category is an array with two entires. Index and Color.
draw_types = [[0, (0, 0, 0)],
              [1, [255, 255, 255]],
              [2, [124, 124, 255]]]

""" @config GammaCorrection """


""" @config Timeline """
# @config `fps =` if not 0 overwrite the frame rate of the video
fps = 0
# @config `play_start =` at which frame to start playback (if > 1) or at what fraction of the video to start playback (if > 0 and < 1)
play_start = 0.0
# @config `playing =` whether to start playback at the program start
play_end = 1.0
# @config `playing =` whether to start playback at the program start
playing = False
# @config `timeline_hide =` whether to hide the timeline at the program start
timeline_hide = False
datetimeline_show = True

""" @config Annotations """
# @config `annotation_tag =` specifies what to append to the annotation file.
annotation_tag = '_annot.txt'


# @config `server_annotations=` weather to use local or sql based annotation stoarage
server_annotations=False
# @config `sql_dbname=` database name e.g. annotations
sql_dbname='annotation'
# @config `sql_host=` ip adress of the server
sql_host='131.188.117.94'
# @config `sql_port=` port for mysql service
sql_port=3306
# @config `sql_user =` username for mySQL database
sql_user = 'clickpoints'
# @config `sql_pwd =`  password for mySQL database
sql_pwd = '123456'

""" @config FolderBrowser """
# @config `folder_list =` specify a lists of folder which can be switched with the `path_up` and `page_down` keys.
folder_list = []

""" @config ScriptLauncher """
# @config `launch_scripts = ` specify a list of scripts which can be started by pressing `F12` to `F9`
launch_scripts = []

""" @config InfoHud """
# @config `info_hud_string = ` specify string to display in the hud
info_hud_string = ""

""" @config MediaHandler """
# @config `use_natsort = ` sort the images naturally e.g. 1 before 10 not "10" before "1"
use_natsort = False
auto_contrast = False

dimension_template = "Recording(?P<recording>\d*)_FoW(?P<fov>\d*)_Mode(?P<mode>.*)_z(?P<z>\d*).tif"

# enables .access on dicts
class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    def __getattr__(self, attr):
        return self.get(attr)
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

def getFiles():
    res = FileDialog()
    res.exec_()
    _fnames = res.selectedFiles()
    if len(_fnames) == 1:
        _fnames = _fnames[0]
    print("Input", _fnames)
    return _fnames

class FileDialog(QFileDialog):
    def __init__(self):
        super(FileDialog, self).__init__()
        self.m_btnOpen = None
        self.m_listView = None
        self.m_treeView = None
        self.m_selectedFiles = []

        self.setOption(QFileDialog.DontUseNativeDialog, True)
        self.setFileMode(QFileDialog.Directory)
        self.setWindowTitle("Select Folder, Image/s, Video/s")
        btns = self.findChildren(QtGui.QPushButton)
        for i in range(len(btns)):
            text = btns[i].text()
            if text.toLower().contains("open") or text.toLower().contains("choose"):
                self.m_btnOpen = btns[i]
                break

        if not self.m_btnOpen:
            return

        self.m_btnOpen.installEventFilter(self)
        self.m_btnOpen.clicked.disconnect()
        self.m_btnOpen.clicked.connect(self.chooseClicked)

        self.m_listView = self.findChild(QtGui.QListView, "listView")
        if self.m_listView:
            self.m_listView.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)

        self.m_treeView = self.findChild(QtGui.QTreeView)
        if self.m_treeView:
            self.m_treeView.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)

    def eventFilter(self, btn, event):
        if btn and event.type() == QtCore.QEvent.EnabledChange and not btn.isEnabled():
            btn.setEnabled(True)

        return super(FileDialog, self).eventFilter(btn, event)

    def chooseClicked(self):
        indexList = self.m_listView.selectionModel().selectedIndexes()
        for index in indexList:
            if index.column() == 0:
                self.m_selectedFiles.append(os.path.join(str(self.directory().absolutePath()), str(index.data())))

        QtGui.QDialog.accept(self)

    def selectedFiles(self):
        return self.m_selectedFiles


class ExceptionPathDoesntExist(Exception): pass

def LoadConfig():
    global auto_mask_update, tracking, tracking_connect_nearest
    global srcpath, filename, outputpath, jumps, relative_outputpath, file_ids, annotation_ids
    global logname_tag, maskname_tag
    global types, draw_types, addons, max_image_size
    global filterparam, dont_process_filelist
    global play_start, play_end, playing, rotation, rotation_steps

    """ Determine the input path """

    # get global variables from command line
    for arg in sys.argv[1:]:
        if arg[0] == "-" and arg.find("=") != -1 and arg[1] != "_":
            key, value = arg[1:].split("=", 1)
            if key == "srcpath" and value != "":
                if os.path.exists(value) or "*" in value:
                    srcpath = value
                else:
                    sys.tracebacklimit = 0
                    raise ExceptionPathDoesntExist("ERROR: path "+value+" does not exist.")

    # if no srcpath is given, ask for one
    if srcpath is "":
        srcpath = getFiles()
        if srcpath is "":
            print("No path selected")
            sys.exit(1)
        if isstring(srcpath) and not os.path.exists(srcpath):
            sys.tracebacklimit = 0
            raise ExceptionPathDoesntExist("ERROR: path "+srcpath+" does not exist.")

    # if srcpath is a filelist load it
    dont_process_filelist = False
    file_ids=[]
    annotation_ids=[]
    # extract file paths and ids if applicable
    if isstring(srcpath) and srcpath[-4:] == ".txt":
        try:
            with open(srcpath, "r") as fp:
                srcpath,file_ids,annotation_ids = zip(*[line.strip().split() for line in fp.readlines()])
                annotation_ids=[int(nr) for nr in annotation_ids]
                file_ids=[int(nr) for nr in file_ids]
            dont_process_filelist = True
            print("filelist: path file_id annotation_id")
        except ValueError:
            with open(srcpath, "r") as fp:
                srcpath = [line.strip() for line in fp.readlines()]
            dont_process_filelist = True
            print("filelist: path")

    """ Get config data """

    # Search config recursive in the folder tree or from the command line
    if isstring(srcpath):
        # check if srcpath is a directory
        if os.path.isdir(srcpath):
            # append / or \ to mark as DIR
            srcpath=os.path.abspath(srcpath)
            srcpath=srcpath+os.sep

            basepath = srcpath
            path = srcpath
            os.chdir(srcpath)
        else:  # else extract the base path
            path = os.path.normpath(os.path.dirname(srcpath))
            basepath = path
            os.chdir(basepath)
    elif len(srcpath) > 0:
        path = os.path.normpath(os.path.dirname(srcpath[0]))
        basepath = path
    else:
        path = os.path.normpath(os.getcwd())
        basepath = path
    path = os.path.abspath(path)
    parent = os.path.join(path, ".")
    path_list = []
    while parent != path:
        path = parent
        parent = os.path.normpath(os.path.join(path, ".."))
        path_list.append(os.path.normpath(os.path.join(path, "ConfigClickPoints.txt")))
    if len(sys.argv) >= 2:
        path_list.insert(0, sys.argv[1])
    path_list.append(os.path.join(os.path.dirname(__file__), "..", "ConfigClickPoints.txt"))
    for path in path_list:
        if os.path.exists(path):
            with open(path) as f:
                code = compile(f.read(), path, 'exec')
                print("Loaded config",path)
                exec(code, globals())
            break

    """ get command line data """

    # get global variables from command line
    for arg in sys.argv[1:]:
        if arg[0] == "-" and arg.find("=") != -1 and arg[1] != "_":
            key, value = arg[1:].split("=", 1)
            if key == "srcpath":
                continue
            if key in globals():
                if isinstance(globals()[key], type(True)):
                    value = type(True)(value)
                elif not isstring(globals()[key]):
                    value = json.loads(value)
                globals()[key] = value

            else:
                print("WARNING: unknown command line argument "+arg)
        else:
            print("WARNING: unknown command line argument "+arg)

    """ some fallbacks """

    # parameter pre processing
    if outputpath is not "" and not os.path.exists(outputpath):
        os.makedirs(outputpath)  # recursive path creation

    if outputpath is "":
        relative_outputpath = True
        outputpath = basepath
    else:
        relative_outputpath = False

    draw_types = sorted(draw_types, key=lambda x: x[0])

    """ convert to dict and return """

    config = {}
    for key in globals():
        if key not in start_globals.keys():
            config[key] = globals()[key]
    return dotdict(config)
