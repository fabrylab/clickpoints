from __future__ import print_function, division
import numpy as np
import cv2
from pylab import *
from scipy import ndimage
from os import path
import os, re

def ReadTypeDict(string):
    dictionary = {}
    matches = re.findall(
        r"(\d*):\s*\[\s*\'([^']*?)\',\s*\[\s*([\d.]*)\s*,\s*([\d.]*)\s*,\s*([\d.]*)\s*\]\s*,\s*([\d.]*)\s*\]", string)
    for match in matches:
        dictionary[int(match[0])] = [match[1], map(float, match[2:5]), int(match[5])]
    return dictionary

def LoadLog(logname):
    global types
    points = []
    types = {}
    #print("Loading " + logname)
    with open(logname) as fp:
        for index, line in enumerate(fp.readlines()):
            line = line.strip()
            if line[:7] == "#@types":
                type_string = line[7:].strip()
                if type_string[0] == "{":
                    try:
                        types = ReadTypeDict(line[7:])
                    except:
                        print("ERROR: Type specification in %s broken, use types from config instead" % logname)
                    continue
            if line[0] == '#':
                continue
            line = line.split(" ")
            x = float(line[0])
            y = float(line[1])
            marker_type = int(line[2])
            if marker_type not in types.keys():
                np.random.seed(marker_type)
                types[marker_type] = ["id%d" % marker_type, np.random.randint(0, 255, 3), 0]
            if len(line) == 3:
                points.append(dict(x=x, y=y, type=marker_type))
                continue
            active = int(line[3])
            if marker_type == -1 or active == 0:
                continue
            marker_id = line[4]
            partner_id = None
            if len(line) >= 6:
                partner_id = line[5]
            points.append(dict(x=x, y=y, type=marker_type, id=marker_id, partner_id=partner_id))
    return points, types

def SaveLog(filename, points, types={}):
    data = ["%f %f %d %d %s %s\n" % (point["x"], point["y"], point["type"], 1, point["id"], point["partner_id"]) for point in points]
    with open(filename, 'w') as fp:
        fp.write("#@types " + str(types) + "\n")
        for line in data:
            fp.write(line)
    #print(filename + " saved")