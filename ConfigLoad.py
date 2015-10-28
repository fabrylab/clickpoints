from __future__ import division, print_function
import sys
import os
import json
try:
    from PyQt5.QtWidgets import QApplication, QFileDialog
except ImportError:
    from PyQt4.QtGui import QApplication, QFileDialog

start_globals = globals().copy()

""" @config General """
srcpath = ""
# @config `outputpath =` the path where to save the log and mask file. Set to `None` defaults to the `srcpath`
outputpath = ""
# @config `filename_data_regex = ` specify a regular expression to obtain meta-data from filenames
filename_data_regex = r'.*(?P<timestamp>\d{8}-\d{6})_(?P<system>.+?[^_])_(?P<camera>.+)'
# @config `filterparam =` specify additional filters for the files to use
filterparam = {}

# @config `jumps =` specify how many frames the numpad keys `2`,`3`,`5`,`6`,`8`,`9`,`/`,`*` should jump
jumps = (-1, +1, -10, +10, -100, +100, -1000, +1000)

# @config `max_image_size = ` the maximum size of one image before it is internally split into tiles
max_image_size = 2 ** 12

# @config `rotation =` the rotation of the image when starting
rotation = 0
# @config `rotation_steps =` how much to rotate time image when `r` is pressed
rotation_steps = 90

# @config `hide_interfaces =` whether to hide the interfaces a program start. Press F2 to show it again.
hide_interfaces = True

# @config `addons =` a list of additional python files to load
addons = []

""" @config Marker """
# @config `logname_tag =` specifies what to append to the log file.
logname_tag = '_pos.txt'

TYPE_Normal = 0
TYPE_Rect = 1
TYPE_Line = 2

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
              [255, [255, 255, 255]],
              [124, [124, 124, 255]]]

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

""" @config Annotations """
# @config `annotation_tag =` specifies what to append to the annotation file.
annotation_tag = '_annot.txt'

""" @config FolderBrowser """
# @config `folder_list =` specify a lists of folder which can be switched with the `path_up` and `page_down` keys.
folder_list = []

""" @config ScriptLauncher """
# @config `launch_scripts = ` specify a list of scripts which can be started by pressing `F12` to `F9`
launch_scripts = []

""" @config InfoHud """
# @config `info_hud_string = ` specify string to display in the hud
info_hud_string = ""

# enables .access on dicts
class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    def __getattr__(self, attr):
        return self.get(attr)
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def LoadConfig():
    global auto_mask_update, tracking, tracking_connect_nearest
    global srcpath, filename, outputpath, jumps, relative_outputpath
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
                if os.path.exists(value):
                    srcpath = value
                else:
                    print("ERROR: path",value,"does not exist.")
                    sys.exit(-1)

    # if srcpath is a filelist load it
    dont_process_filelist = False
    if type(srcpath) == type("") and srcpath[-4:] == ".txt":
        with open(srcpath, "r") as fp:
            srcpath = [line.strip() for line in fp.readlines()]
            dont_process_filelist = True

    # if no srcpath is given, ask for one
    if srcpath is "":
        srcpath = str(QFileDialog.getExistingDirectory(None, "Choose Image", os.getcwd()))
        if srcpath is "":
            print("No path selected")
            sys.exit(1)
        if not os.path.exists(srcpath):
            print("ERROR: path",srcpath,"does not exist.")
            sys.exit(-1)

    """ Get config data """

    # Search config recursive in the folder tree or from the command line
    if type(srcpath) == type(""):
        # check if srcpath is a directory
        if os.path.isdir(srcpath):
            # append / or \ to mark as DIR
            srcpath=os.path.abspath(srcpath)
            srcpath=srcpath+os.sep

            basepath = srcpath
            path = srcpath
        else:
        # else extract the base path
            path = os.path.normpath(os.path.dirname(srcpath))
            basepath = path
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
    path_list.append(os.path.join(os.path.dirname(__file__), "ConfigClickPoints.txt"))
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
                elif not isinstance(globals()[key], type("")):
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
