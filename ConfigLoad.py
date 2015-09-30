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
filename = ""
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
launch_scripts = [r"C:\Users\Richard\Anaconda\python.exe E:\Slack\Navid\TestTrack.py", r"C:\Users\Richard\Anaconda\python.exe E:\Slack\Navid\Evaluation.py"]

# enables .access on dicts
class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    def __getattr__(self, attr):
        return self.get(attr)
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def LoadConfig():
    global auto_mask_update, tracking, tracking_connect_nearest
    global srcpath, filename, outputpath, jumps
    global logname_tag, maskname_tag
    global types, draw_types, addons, max_image_size
    global filterparam
    global play_start, play_end, playing, rotation, rotation_steps
    # Search config recursive in the folder tree or from the command line
    path = os.path.normpath(os.getcwd())
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

    # get global variables from command line
    for arg in sys.argv[1:]:
        if arg[0] == "-" and arg.find("=") != -1 and arg[1] != "_":
            key, value = arg[1:].split("=", 1)
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

    if type(srcpath) == "" and not os.path.isfile(srcpath) and filename:
        srcpath = os.path.join(srcpath, filename)
    del filename
    # parameter pre processing
    if outputpath is not "" and not os.path.exists(outputpath):
        os.makedirs(outputpath)  # recursive path creation

    draw_types = sorted(draw_types, key=lambda x: x[0])

    config = {}
    for key in globals():
        if key not in start_globals.keys():
            config[key] = globals()[key]
    return dotdict(config)
