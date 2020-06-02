#!/usr/bin/env python
# -*- coding: utf-8 -*-
# RegisterRegistry.py

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

'''
Setup script to add Clickpoints to windows registry
under base key HKEY_CURRENT_USER

Args:
    mode (string): choose install/uninstall
    |  install
    |  uninstall

'''

import sys, ntpath, os

if sys.platform.startswith('win'):
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


    def del_reg(basekey, reg_path):
        try:
	        winreg.DeleteKey(basekey, reg_path)
	        return True
        except WindowsError:
	        return False


    def get_reg(basekey, reg_path, name):
        try:
	        registry_key = winreg.OpenKey(basekey, reg_path, 0,
	                                      winreg.KEY_READ)
	        value, regtype = winreg.QueryValueEx(registry_key, name)
	        winreg.CloseKey(registry_key)
	        return value
        except WindowsError:
	        return None


def createBatFile():
    directory = os.path.dirname(sys.executable)
    script_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "launch.py"))
    icon_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "icons", "ClickPoints.ico"))
    if sys.platform.startswith('win'):
        with open(os.path.join(os.path.dirname(sys.executable), "ClickPoints.bat"), 'w') as fp:
            print("Writing ClickPoints.bat")
            fp.write("@echo off\n")
            fp.write(os.path.join(os.path.dirname(sys.executable), "Scripts", "clickpoints.exe"))
            fp.write(" %1\n")
            fp.write("IF %ERRORLEVEL% NEQ 0 pause\n")
        return os.path.join(os.path.dirname(sys.executable), "ClickPoints.bat"), icon_path
    else:
        sh_file = os.path.join(directory, "clickpoints.sh")
        with open(sh_file, 'w') as fp:
            print("Writing ClickPoints bash file")
            fp.write("#!/bin/bash\n")
            fp.write("echo \"$1\" >> ~/.clickpoints/ClickPoints.txt\n")
            fp.write(sys.executable)
            fp.write(" ")
            fp.write(script_path)
            fp.write(" $1\n")
            fp.write("if [[ $? -ne 0 ]]\n")
            fp.write("then\n")
            fp.write("\tread -n1 -r -p \"Press any key to continue...\" key\n")
            fp.write("fi\n")
            os.system("chmod +x %s" % sh_file)
        return sh_file, icon_path


def install(mode="install", extension=None):
    assert isinstance(mode, str)
    print("running install registry script - mode: %s" % mode)

    # file extensions for which to add to ClickPoints shortcut
    if extension is None:
        extension = [".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".gif", ".avi", ".mp4"]

    if mode == 'install':

        bat_sh_file, icon_path = createBatFile()

        if sys.platform.startswith('win'):
            ### add to DIRECTORY
            # create entry under HKEY_CURRENT_USER to show in dropdown menu for folders
            print("setup for directory")
            icon_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "icons",
                                     "ClickPoints.ico")
            bat_path = ntpath.join(os.path.join(os.path.dirname(sys.executable), "ClickPoints.bat \"%1\""))

            reg_path = r"Software\Classes\Directory\shell\1ClickPoint\\"
            set_reg(winreg.HKEY_CURRENT_USER, reg_path, None, "ClickPoints")
            set_reg(winreg.HKEY_CURRENT_USER, reg_path, "icon", icon_path)
            reg_path = r"Software\Classes\Directory\shell\1ClickPoint\command\\"
            set_reg(winreg.HKEY_CURRENT_USER, reg_path, None, bat_path)

            # ### add for specific file types
            # # create entry under HKEY_CLASSES_ROOT\SystemFileAssociations to show in dropdown menu for specific file types
            for ext in extension:
                print("install for extension:%s" % ext)
                reg_path = r"SOFTWARE\Classes\SystemFileAssociations\\" + ext + r"\shell\1ClickPoint\\"
                set_reg(winreg.HKEY_CURRENT_USER, reg_path, None, "ClickPoints")
                set_reg(winreg.HKEY_CURRENT_USER, reg_path, "icon", icon_path)
                reg_path = r"SOFTWARE\Classes\SystemFileAssociations\\" + ext + r"\shell\1ClickPoint\command\\"
                set_reg(winreg.HKEY_CURRENT_USER, reg_path, None, bat_path)

            # ### add to open WithLIST # damn you ICON!
            # register application
            reg_path = r"Software\Classes\Applications\ClickPoints.bat\shell\open\command\\"
            set_reg(winreg.HKEY_CURRENT_USER, reg_path, None, bat_path)
            reg_path = r"Software\Classes\Applications\ClickPoints.bat\DefaultIcon\\"
            set_reg(winreg.HKEY_CURRENT_USER, reg_path, None, icon_path)

            for ext in extension:
                print("install for extension:%s" % ext)
                reg_path = r"SOFTWARE\Classes\\" + ext + r"\OpenWithList\ClickPoints.bat\\"
                set_reg(winreg.HKEY_CURRENT_USER, reg_path, None, None)
        else:
            application_path = "/home/" + os.popen('whoami').read()[:-1] + "/.local/share/applications/"
            if not os.path.exists(application_path):
                os.mkdir(application_path)

            desktop_file = "/home/" + os.popen('whoami').read()[:-1] + "/.local/share/applications/clickpoints.desktop"
            with open(desktop_file, 'w') as fp:
                print("Writing clickpoints.desktop")
                fp.write("[Desktop Entry]\n")
                fp.write("Type=Application\n")
                fp.write("Name=ClickPoints\n")
                fp.write("GenericName=View Images/Videos and Annotate them\n")
                fp.write("Comment=Display images and videos and annotate them\n")
                fp.write("Exec=" + bat_sh_file + " \"\"%f\"\"\n")
                fp.write("NoDisplay=false\n")
                fp.write("Terminal=true\n")
                fp.write("Icon=" + icon_path + "\n")
                fp.write("Categories=Development;Science;IDE;Qt;\n")
                fp.write(
                    "MimeType=video/*;image/*;video/mp4;video/x-msvideo;video/mpeg;image/bmp;image/png;image/jpeg;image/tiff;image/gif;$\n")
                fp.write("InitialPreference=10\n")

            for ext in ["application/cdb", "ideo/mp4", "video/x-msvideo", "video/mpeg", "image/bmp", "image/png",
                        "image/jpeg", "image/gif", "image/tiff"]:
                print("Setting ClickPoints as default application for %s" % ext)
                os.popen("sudo xdg-mime default clickpoints.desktop " + ext)

    elif mode == 'uninstall':
        if sys.platform.startswith('win'):
            ### remove from DIRECTORY
            print("remove for directory")
            reg_path = r"Software\Classes\Directory\shell\1ClickPoint\command\\"
            del_reg(winreg.HKEY_CURRENT_USER, reg_path)
            reg_path = r"Software\Classes\Directory\shell\1ClickPoint\\"
            del_reg(winreg.HKEY_CURRENT_USER, reg_path)

            ### remove from types
            for ext in extension:
                print("remove for extension:%s" % ext)
                reg_path = r"SOFTWARE\Classes\SystemFileAssociations\\" + ext + r"\shell\1ClickPoint\command\\"
                del_reg(winreg.HKEY_CURRENT_USER, reg_path)
                reg_path = r"SOFTWARE\Classes\SystemFileAssociations\\" + ext + r"\shell\1ClickPoint\\"
                del_reg(winreg.HKEY_CURRENT_USER, reg_path)

            ## remove from OpenWithList
            reg_path = r"Software\Classes\Applications\ClickPoints.bat\shell\open\command\\"
            del_reg(winreg.HKEY_CURRENT_USER, reg_path)
            reg_path = r"Software\Classes\Applications\ClickPoints.bat\shell\open\\"
            del_reg(winreg.HKEY_CURRENT_USER, reg_path)
            reg_path = r"Software\Classes\Applications\ClickPoints.bat\shell\\"
            del_reg(winreg.HKEY_CURRENT_USER, reg_path)
            reg_path = r"Software\Classes\Applications\ClickPoints.bat\DefaultIcon\\"
            del_reg(winreg.HKEY_CURRENT_USER, reg_path)
            reg_path = r"Software\Classes\Applications\ClickPoints.bat\\"
            del_reg(winreg.HKEY_CURRENT_USER, reg_path)

            for ext in extension:
                reg_path = r"SOFTWARE\Classes\\" + ext + r"\OpenWithList\ClickPoints.bat\\"
                del_reg(winreg.HKEY_CURRENT_USER, reg_path)
        else:
            application_path = "/home/" + os.popen('whoami').read()[:-1] + "/.local/share/applications/"
            if not os.path.exists(application_path):
                os.mkdir(application_path)

            desktop_file = "/home/" + os.popen('whoami').read()[:-1] + "/.local/share/applications/clickpoints.desktop"
            os.remove(desktop_file)
    else:
        raise Exception('Unknown mode: %s' % mode)


if __name__ == '__main__':
    mode = sys.argv[1]
