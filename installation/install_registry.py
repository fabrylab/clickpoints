#!/usr/bin/env python
# -*- coding: utf-8 -*-
# install_registry.py

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

'''
Setup script to add Clickpoints to windows registry
under base key HKEY_CURRENT_USER

Args:
    mode (string): choose install/uninstall
    |  install
    |  uninstall

'''


import sys, ntpath, os
try:
    import _winreg as winreg  # python 2
except ImportError:
    import winreg  # python 3

def set_reg(basekey, reg_path, name, value, type=winreg.REG_SZ):
    try:
        winreg.CreateKey(basekey, reg_path)
        registry_key = winreg.OpenKey(basekey, reg_path, 0,
                                       winreg.KEY_WRITE)
        winreg.SetValueEx(registry_key, name, 0, type, value)
        winreg.CloseKey(registry_key)
        return True
    except WindowsError:
        return False

def del_reg(basekey,reg_path):
    try:
        winreg.DeleteKey(basekey,reg_path)
        return True
    except WindowsError:
        return False

def get_reg(basekey,reg_path,name):
    try:
        registry_key = winreg.OpenKey(basekey, reg_path, 0,
                                       winreg.KEY_READ)
        value, regtype = winreg.QueryValueEx(registry_key, name)
        winreg.CloseKey(registry_key)
        return value
    except WindowsError:
        return None


if __name__ == '__main__':
    mode= sys.argv[1]
    assert isinstance(mode,str)
    print("running install registry script - mode: %s" % mode)

    # file extentions for which to add to Clickpoint shortcut
    extension = [".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".gif", ".avi", ".mp4"]

    if mode == 'install':
        ### add to DIRECTORYS
        # create entry under HKEY_CURRENT_USER to show in dropdown menu for folders
        print("setup for directory")
        icon_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "clickpoints", "icons", "ClickPoints.ico")
        bat_path = ntpath.join(os.path.abspath(os.path.dirname(__file__)), "..", "clickpoints", "ClickPoints.bat \"%1\"")

        reg_path = r"Software\Classes\Directory\shell\1ClickPoint\\"
        set_reg(winreg.HKEY_CURRENT_USER,reg_path,None,"ClickPoints")
        set_reg(winreg.HKEY_CURRENT_USER,reg_path,"icon", icon_path)
        reg_path = r"Software\Classes\Directory\shell\1ClickPoint\command\\"
        set_reg(winreg.HKEY_CURRENT_USER,reg_path,None, bat_path)

        # ### add for specific file types
        # # create entry under HKEY_CLASSES_ROOT\SystemFileAssociations to show in dropdown menu for specific file types
        for ext in extension:
            print("install for extension:%s" % ext)
            reg_path = r"SOFTWARE\Classes\SystemFileAssociations\\" + ext + r"\shell\1ClickPoint\\"
            set_reg(winreg.HKEY_CURRENT_USER,reg_path,None,"ClickPoints")
            set_reg(winreg.HKEY_CURRENT_USER,reg_path,"icon", icon_path)
            reg_path = r"SOFTWARE\Classes\SystemFileAssociations\\"  + ext + r"\shell\1ClickPoint\command\\"
            set_reg(winreg.HKEY_CURRENT_USER,reg_path,None,bat_path)

        # ### add to open WithLIST # damn you ICON!
        # register application
        reg_path = r"Software\Classes\Applications\ClickPoints.bat\shell\open\command\\"
        set_reg(winreg.HKEY_CURRENT_USER,reg_path,None,bat_path)
        reg_path = r"Software\Classes\Applications\ClickPoints.bat\DefaultIcon\\"
        set_reg(winreg.HKEY_CURRENT_USER,reg_path,None,icon_path)

        for ext in extension:
            print("install for extension:%s" % ext)
            reg_path = r"SOFTWARE\Classes\\"  + ext + r"\OpenWithList\ClickPoints.bat\\"
            set_reg(winreg.HKEY_CURRENT_USER,reg_path,None,None)

    elif mode == 'uninstall':
        ### remove from DIRECTORY
        print("remove for directory")
        reg_path = r"Software\Classes\Directory\shell\1ClickPoint\command\\"
        del_reg(winreg.HKEY_CURRENT_USER,reg_path)
        reg_path = r"Software\Classes\Directory\shell\1ClickPoint\\"
        del_reg(winreg.HKEY_CURRENT_USER,reg_path)

        ### remove from types
        for ext in extension:
            print("remove for extension:%s" % ext)
            reg_path = r"SOFTWARE\Classes\SystemFileAssociations\\"  + ext + r"\shell\1ClickPoint\command\\"
            del_reg(winreg.HKEY_CURRENT_USER,reg_path)
            reg_path = r"SOFTWARE\Classes\SystemFileAssociations\\"  + ext + r"\shell\1ClickPoint\\"
            del_reg(winreg.HKEY_CURRENT_USER,reg_path)

        ## remove from OpenWithList
        reg_path = r"Software\Classes\Applications\ClickPoints.bat\shell\open\command\\"
        del_reg(winreg.HKEY_CURRENT_USER,reg_path)
        reg_path = r"Software\Classes\Applications\ClickPoints.bat\shell\open\\"
        del_reg(winreg.HKEY_CURRENT_USER,reg_path)
        reg_path = r"Software\Classes\Applications\ClickPoints.bat\shell\\"
        del_reg(winreg.HKEY_CURRENT_USER,reg_path)
        reg_path = r"Software\Classes\Applications\ClickPoints.bat\DefaultIcon\\"
        del_reg(winreg.HKEY_CURRENT_USER,reg_path)
        reg_path = r"Software\Classes\Applications\ClickPoints.bat\\"
        del_reg(winreg.HKEY_CURRENT_USER,reg_path)

        for ext in extension:
            reg_path = r"SOFTWARE\Classes\\"  + ext + r"\OpenWithList\ClickPoints.bat\\"
            del_reg(winreg.HKEY_CURRENT_USER,reg_path)
    else:
        raise Exception('Uknown mode: %s' % mode)