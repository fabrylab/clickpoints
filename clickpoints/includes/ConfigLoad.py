#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ConfigLoad.py

# Copyright (c) 2015-2020, Richard Gerum, Sebastian Richter, Alexander Winterl
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ClickPoints. If not, see <http://www.gnu.org/licenses/>

import ast
import os
import sys
from datetime import datetime
from typing import Union


def isstring(object: str) -> bool:
    PY3 = sys.version_info[0] == 3

    if PY3:
        return isinstance(object, str)
    else:
        return isinstance(object, basestring)


# enables .access on dicts
class dotdict(dict):
    """dot.notation access to dictionary attributes"""

    def __getattr__(self, attr: str) -> Union[datetime, str, int]:
        return self.get(attr)

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class ExceptionPathDoesntExist(Exception): pass


def LoadConfig(*args, srcpath="", just_load=False) -> dotdict:
    """ Determine the input path """

    if len(args) == 0:
        args = sys.argv
    else:
        args = list(args)
    print("LoadConfig", args, srcpath, just_load)

    replacements = dict(TYPE_Normal=0, TYPE_Rect=1, TYPE_Line=2, TYPE_Track=4)
    config = {}

    if not just_load:
        # get global variables from command line
        for arg in args[1:]:
            if arg[0] == "-" and arg.find("=") != -1 and arg[1] != "_":
                key, value = arg[1:].split("=", 1)
                if key == "srcpath" and value != "":
                    if os.path.exists(value) or "*" in value:
                        srcpath = value
                    else:
                        sys.tracebacklimit = 0
                        raise ExceptionPathDoesntExist("ERROR: path " + value + " does not exist.")

        if srcpath == "" and len(args) > 1 and args[1][0] != "-":
            srcpath = args[1]

        """ Get config data """
        # Search config recursive in the folder tree or from the command line
        if isstring(srcpath):
            # check if srcpath is a directory
            if os.path.isdir(srcpath):
                # append / or \ to mark as DIR
                srcpath = os.path.abspath(srcpath)
                srcpath = srcpath + os.sep

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
        path_list.append(os.path.join(os.path.dirname(__file__), "..", "ConfigClickPoints.txt"))
        config_path = "."
        for path in path_list:
            if os.path.exists(path):
                config.update(replacements)
                with open(path) as f:
                    code = compile(f.read(), path, 'exec')
                    print("Loaded config", path)
                    exec(code, config)
                """
                with open(path) as fp:
                    for line in fp:
                        line = line.strip()
                        if line == "" or line.startswith("#") or line.startswith("'''") or line.startswith('"" "'):
                            continue
                        for replacement in replacements:
                            line = line.replace(replacement, str(replacements[replacement]))
                        key, value = line.split("=", 1)
                        import ast
                        config[key.strip()] = ast.literal_eval(value.strip())
                        #config[key] = json.loads(value)
                    config_path = path
                    print("Loaded config", path)
                """
                break
    else:
        config.update(replacements)
        with open(srcpath) as f:
            code = compile(f.read(), srcpath, 'exec')
            print("Loaded config", srcpath)
            exec(code, config)

    """ get command line data """

    # get global variables from command line
    for arg in args[1:]:
        if arg[0] == "-" and arg.find("=") != -1 and arg[1] != "_":
            key, value = arg[1:].split("=", 1)
            if key == "srcpath":
                continue
            config[key] = ast.literal_eval(value)
    config["srcpath"] = srcpath

    """ convert to dict and return """
    return dotdict(config)
