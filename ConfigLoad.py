from __future__ import division, print_function
import sys
import os
import json
try:
    from PyQt5.QtWidgets import QApplication, QFileDialog
except ImportError:
    from PyQt4.QtGui import QApplication, QFileDialog

start_globals = globals().copy()

""" General """
srcpath = ""
outputpath = ""
filename_data_regex = r'.*(?P<timestamp>\d{8}-\d{6})_(?P<system>.+?[^_])_(?P<camera>.+)'
filterparam = {}

jumps = (-1, +1, -10, +10, -100, +100, -1000, +1000)

max_image_size = 2 ** 12

rotation = 0
rotation_steps = 90

addons = []

""" Marker """
logname_tag = '_pos.txt'

TYPE_Normal = 0
TYPE_Rect = 1
TYPE_Line = 2

types = {0: ["marker", [255, 0, 0], TYPE_Normal]}

tracking = False
tracking_connect_nearest = False
tracking_show_trailing = -1
tracking_show_leading = 0

""" Mask """
maskname_tag = '_mask.png'
auto_mask_update = True
draw_types = [[0, (0, 0, 0)],
              [255, [255, 255, 255]],
              [124, [124, 124, 255]]]

""" GammaCorrection """
gamma_corretion_hide = False

""" Timeline """
fps = 0
play_start = 0.0
play_end = 1.0
playing = False
timeline_hide = False

""" Annotations """
annotation_tag = '_annot.txt'

""" FolderBrowser """
folder_list = []

""" ScriptLauncher """
launch_scripts = []

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
    global filterparam
    global play_start, play_end, playing, rotation, rotation_steps

    """ Determine the input path """

    # get global variables from command line
    for arg in sys.argv[1:]:
        if arg[0] == "-" and arg.find("=") != -1 and arg[1] != "_":
            key, value = arg[1:].split("=", 1)
            if key == "srcpath":
                srcpath = value

    # if srcpath is a filelist load it
    if type(srcpath) == type("") and srcpath[-4:] == ".txt":
        with open(srcpath, "r") as fp:
            srcpath = [line.strip() for line in fp.readlines()]

    # if no srcpath is given, ask for one
    if srcpath is "":
        srcpath = str(QFileDialog.getOpenFileName(None, "Choose Image", os.getcwd()))
        if srcpath is "":
            sys.exit(1)
        print(srcpath)

    """ Get config data """

    # Search config recursive in the folder tree or from the command line
    if type(srcpath) == type(""):
        path = os.path.normpath(os.path.dirname(srcpath))
        basepath = path
    elif len(srcpath) > 0:
        path = os.path.normpath(os.path.dirname(srcpath[0]))
        basepath = path
    else:
        path = os.path.normpath(os.getcwd())
        basepath = path
    parent = os.path.join(path, ".")
    path_list = []
    while parent != path:
        path = parent
        parent = os.path.normpath(os.path.join(path, ".."))
        path_list.append(os.path.normpath(os.path.join(path, "ConfigClickPoints.txt")))
    if len(sys.argv) >= 2:
        path_list.insert(0, sys.argv[1])
    for path in path_list:
        if os.path.exists(path):
            with open(path) as f:
                code = compile(f.read(), path, 'exec')
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
