from __future__ import division
import sys
import os

TYPE_Normal = 0
TYPE_Rect = 1
TYPE_Line = 2

use_filedia = True
auto_mask_update = True
tracking = True
tracking_connect_nearest = False
srcpath = None
filename = None
outputpath = None
logname_tag = '_pos.txt'
maskname_tag = '_mask.png'
annotation_tag = '_annot.txt'

filename_data_regex = r'.*(?P<timestamp>\d{8}-\d{6})_(?P<system>.+?[^_])_(?P<camera>.+)'

filterparam={}

play_start = 0.0
play_end   = 1.0
playing = False

rotation = 0
rotation_steps = 90

jumps = (-1, +1, -24, +24, -100, +100, -1000, +1000)

# marker types
types = {0: ["juveniles", [255, 0, 0], TYPE_Normal],
         1: ["adults", [0, 204, 0], TYPE_Rect],
         2: ["beak", [204, 204, 0], TYPE_Line]
         }
# painter types
draw_types = [[0, (0, 0, 0)],
              [255, [255, 255, 255]],
              [124, [124, 124, 255]]]

# possible addons
addons = []

max_image_size = 2 ** 12

# enables .access on dicts
class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    def __getattr__(self, attr):
        return self.get(attr)
    __setattr__= dict.__setitem__
    __delattr__= dict.__delitem__

def LoadConfig():
    global use_filedia, auto_mask_update, tracking, tracking_connect_nearest
    global srcpath, filename, outputpath, jumps
    global logname_tag, maskname_tag
    global types, draw_types, addons, max_image_size
    global filterparam
    global play_start, play_end, playing, rotation, rotation_steps
    # overwrite defaults with personal cfg if available
    config_filename = 'cp_cfg.txt'
    if len(sys.argv) >= 2:
        config_filename = sys.argv[1]
    if os.path.exists(config_filename):
        with open(config_filename) as f:
            code = compile(f.read(), config_filename, 'exec')
            exec(code, globals())

    # parameter pre processing
    if srcpath is None:
        srcpath = os.getcwd()
    if outputpath is not None and not os.path.exists(outputpath):
        os.makedirs(outputpath)  # recursive path creation

    draw_types = sorted(draw_types, key=lambda x: x[0])

    # get global variables from command line
    for arg in sys.argv[2:]:
        if arg[0] == "-" and arg.find("=") != -1 and arg[1] != "_":
            key, value = arg[1:].split("=")
            if key in globals():
                print(globals()[key])
                print(type(globals()[key]))
                if type(globals()[key]) is not type(None):
                    value = type(globals()[key])(value)
                globals()[key] = type(globals()[key])(value)

            else:
                print("WARNING: unknown command line argument "+arg)
        else:
            print("WARNING: unknown command line argument "+arg)

    return dotdict(globals())
