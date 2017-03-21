#!/usr/bin/env python
# -*- coding: utf-8 -*-
# make_no_python_installer.py

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

from __future__ import print_function, division
import os, sys
import shutil
import glob
import fnmatch
import re
import zipfile
PY2 = sys.version_info[0] == 2

if os.name == 'nt':
    if PY2:
        import _winreg as winreg
    else:
        import winreg
else:
    winreg = None

from subprocess import call

try:
    import ConfigParser
except ImportError:
    import configparser as ConfigParser

from jinja2 import Environment, FileSystemLoader

class ConfigAccessHelper:
    def __init__(self, parent, section):
        self.parent = parent
        self.section = section

    def __getattr__(self, key):
        import json
        try:
            data = self.parent.get(self.section, key)
        except ConfigParser.NoOptionError:
            return ""
        try:
            return json.loads(data)
        except ValueError:
            return data

class Config(ConfigParser.ConfigParser):
    def __init__(self, filename=None, *args, **kwargs):
        ConfigParser.ConfigParser.__init__(self, *args, **kwargs)
        if filename is not None:
            self.read(filename)

    def __getattr__(self, key):
        if key in self.sections():
            return ConfigAccessHelper(self, key)
        return ConfigParser.ConfigParser.__getattr__(self, key)

folderPath = r"D:\WinPython-64bit-3.6.0.1Zero"
old_path = os.getcwd()
#os.chdir(folderPath)

""" get size of folder """
import win32com.client as com

fso = com.Dispatch("Scripting.FileSystemObject")
folder = fso.GetFolder(".")
KB = 1024.0
folder_size = int(folder.Size/KB)
print("%d KB" % (folder_size))

icon = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "icons", "winpython.ico"))

grouped_files = [["$INSTDIR", []]]
install_files = []
install_dirs = []
if 0:
    for root, dirs, files in os.walk(".", topdown=True):
        if len(files) == 0:
            continue
        #for name in files:
        #    install_files.append([os.path.join(root, name), "$INSTDIR"])
        #    grouped_files[0][1].append(os.path.join(root, name))
        #for name in dirs:
        install_dirs.append([root, "$INSTDIR"])

install_dirs.append([folderPath, "$INSTDIR"])
#for name in glob.glob(folderPath+"\*"):
#    install_files.append([os.path.split(name)[1], "$INSTDIR"])
#    grouped_files[0][1].append(os.path.join(folderPath, name))
#print(grouped_files)
#print(install_files)
#print(install_dirs)

env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))

template = env.get_template("pyapp_python.nsi")
with open("tmp.nsi", 'w') as fp:
    fp.write(template.render(
    appname="WinPython for ClickPoints",
    appname_path="WinPython-ClickPoints",
    version="1.1",
    installer_name=os.path.join(old_path, "WinPython_CP.exe"),
    icon=icon,

    install_dirs=install_dirs,
    grouped_files=grouped_files,
    pjoin=os.path.join,
    install_files=install_files,
    folder_size=folder_size,
    ))

def find_makensis_win():
    """Locate makensis.exe on Windows by querying the registry"""
    try:
        nsis_install_dir = winreg.QueryValue(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\NSIS')
    except OSError:
        nsis_install_dir = winreg.QueryValue(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Wow6432Node\\NSIS')

    return os.path.join(nsis_install_dir, 'makensis.exe')

def run_nsis(nsi_file):
    """Runs makensis using the specified .nsi file

    Returns the exit code.
    """
    try:
        if os.name == 'nt':
            makensis = find_makensis_win()
        else:
            makensis = 'makensis'
        print(makensis, nsi_file)
        return call([makensis, nsi_file])
    except OSError as e:
        # This should catch either the registry key or makensis being absent
        print("makensis was not found. Install NSIS and try again.")
        print("http://nsis.sourceforge.net/Download")
        sys.exit(-1)

run_nsis("tmp.nsi")
print("MakeRelease completed!")