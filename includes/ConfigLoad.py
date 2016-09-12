#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ConfigLoad.py

# Copyright (c) 2015-2016, Richard Gerum, Sebastian Richter
#
# This file is part of ClickPoints.
#
# ClickPoints is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ClickPoints is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ClickPoints. If not, see <http://www.gnu.org/licenses/>

from __future__ import division, print_function, unicode_literals
import sys
import os
import json


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
# @config `filterparam =` specify additional filters for the files to use
filterparam = {}

# @config `max_image_size = ` the maximum size of one image before it is internally split into tiles
max_image_size = 2 ** 14

""" @config Marker """
TYPE_Normal = 0
TYPE_Rect = 1
TYPE_Line = 2
TYPE_Track = 4

# @config `types = {0: ["marker", [255, 0, 0], TYPE_Normal]}` specifies what categories to use. Every category is an array with three entires. Name, Color and Type. Types can be 0: normal marker, 1: rectangle markers, 2: line markers
types = {0: ["marker", [255, 0, 0], TYPE_Normal]}


""" @config Mask """
# @config `draw_types = [[0,[255,0,0]]` specifies what categories to use for mask drawing. Every category is an array with two entires. Index and Color.
draw_types = [[1, [124, 124, 255], "mask"]]

""" @config GammaCorrection """


""" @config Annotations """
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

""" @config MediaHandler """
# @config `use_natsort = ` sort the images naturally e.g. 1 before 10 not "10" before "1"
use_natsort = False
auto_contrast = False

""" @config Timestamp Extraction """
# @config `timestamp_formats` and `timestamp_fromats2` lists of timestamp foramts to match
timestamp_formats = [r'%Y%m%d-%H%M%S-%f',
                     r'%Y%m%d-%H%M%S']
timestamp_formats2 = [r'%Y%m%d-%H%M%S_%Y%m%d-%H%M%S']

# enables .access on dicts
class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    def __getattr__(self, attr):
        return self.get(attr)
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

class ExceptionPathDoesntExist(Exception): pass

def LoadConfig():
    global auto_mask_update, tracking, tracking_connect_nearest
    global srcpath, filename, jumps, file_ids, annotation_ids
    global maskname_tag
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
    config_path = "."
    for path in path_list:
        if os.path.exists(path):
            with open(path) as f:
                code = compile(f.read(), path, 'exec')
                config_path = path
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

    """ convert to dict and return """

    config = {}
    for key in globals():
        if key not in start_globals.keys():
            config[key] = globals()[key]
    config["path_config"] = os.path.dirname(config_path)
    config["path_clickpoints"] = os.path.join(os.path.dirname(__file__), "..")
    return dotdict(config)
