#!/usr/bin/env python
# -*- coding: utf-8 -*-
# uninstall_registry_old.py

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

import _winreg,sys, ntpath, os

def set_reg(name, value, type= _winreg.REG_SZ):
    try:
        _winreg.CreateKey(_winreg.HKEY_CLASSES_ROOT, REG_PATH)
        registry_key = _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT, REG_PATH, 0,
                                       _winreg.KEY_WRITE)
        _winreg.SetValueEx(registry_key, name, 0, type, value)
        _winreg.CloseKey(registry_key)
        return True
    except WindowsError:
        return False

def del_reg(basekey,reg_path):
    try:
        _winreg.DeleteKey(basekey,reg_path)
        return True
    except WindowsError:
        return False

def get_reg(name):
    try:
        registry_key = _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT, REG_PATH, 0,
                                       _winreg.KEY_READ)
        value, regtype = _winreg.QueryValueEx(registry_key, name)
        _winreg.CloseKey(registry_key)
        return value
    except WindowsError:
        return None

install= False
uninstall=True

extension = [".png",".jpg",".jpeg",".tiff",".tif",".bmp",".gif",".avi",".mp4"]

if install:
    ### add to DIRECTORYS
    # create entry under HKEY_CLASSES_ROOT\Directory to show in dropdown menu for folders
    REG_PATH = r"Directory\shell\ClickPoint\\"
    set_reg(None,"ClickPoints")
    set_reg("icon", os.path.join(os.path.abspath(os.path.dirname(__file__))+r"\icons\ClickPoints.ico"))
    REG_PATH = r"Directory\shell\ClickPoint\command\\"
    set_reg(None,ntpath.join(os.path.abspath(os.path.dirname(__file__))+r"\ClickPoints.bat %1"))


    ### add for specific file types
    # create entry under HKEY_CLASSES_ROOT\SystemFileAssociations to show in dropdown menu for specific file types
    for ext in extension:
        print(ext)
        REG_PATH = r"SystemFileAssociations\\" + ext + r"\shell\ClickPoint\\"
        set_reg(None,"ClickPoints")
        set_reg("icon", os.path.join(os.path.abspath(os.path.dirname(__file__))+r"\icons\ClickPoints.ico"))
        REG_PATH = r"SystemFileAssociations\\" + ext + r"\shell\ClickPoint\command\\"
        set_reg(None,ntpath.join(os.path.abspath(os.path.dirname(__file__))+r"\ClickPoints.bat %1"))

if uninstall:
    ### remove from DIRECTORY
    REG_PATH = r"Directory\shell\ClickPoint\\"
    del_reg(_winreg.HKEY_CLASSES_ROOT,REG_PATH)

    for ext in extension:
        print(ext)
        REG_PATH = r"SystemFileAssociations\\" + ext + r"\shell\ClickPoint\command\\"
        del_reg(_winreg.HKEY_CLASSES_ROOT,REG_PATH)
        REG_PATH = r"SystemFileAssociations\\" + ext + r"\shell\ClickPoint\\"
        del_reg(_winreg.HKEY_CLASSES_ROOT,REG_PATH)

