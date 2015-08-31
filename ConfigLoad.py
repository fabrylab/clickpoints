from __future__ import division
import sys
import os

TYPE_Normal = 0
TYPE_Rect = 1
TYPE_Line = 2

use_filedia = True
auto_mask_update = True
tracking = False
srcpath = None
filename = None
outputpath = None
logname_tag = '_pos.txt'
maskname_tag = '_mask.png'

filterparam={}

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

class dotdict(dict):
    def __init__(self, dictionary):
        self.dict = dictionary
    def __getattribute__(self, key):
        if key == "dict" or key not in self.dict.keys():
            return dict.__getattribute__(self, key)
        return self.dict[key]
    def __setattr__(self, key, value):
        if key == "dict" or key not in self.dict.keys():
            return dict.__setattr__(self, key, value)
        self.dict[key] = value
    def __getitem__(self, key):
        return self.dict[key]
    def __str__(self):
        return str(self.dict)

def LoadConfig():
    global use_filedia, auto_mask_update, tracking
    global srcpath, filename, outputpath
    global logname_tag, maskname_tag
    global types, draw_types, addons, max_image_size
    global filterparam
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
                globals()[key] = value
            else:
                print("WARNING: unknown command line argument "+arg)
        else:
            print("WARNING: unknown command line argument "+arg)

    return dotdict(globals())
