#!/usr/bin/env python
# -*- coding: utf-8 -*-
# install_bat.py

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

import sys, os
import subprocess

directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
os.chdir("..")
script_path = os.path.join(directory, "ClickPoints.py")
icon_path = os.path.join(directory, "icons", "ClickPoints.ico")
if sys.platform.startswith('win'):
    with open("ClickPoints.bat", 'w') as fp:
        print("Writing ClickPoints.bat")
        fp.write("@echo off\n")
        fp.write("\"")
        fp.write(sys.executable)
        fp.write("\"")
        fp.write(" ")
        fp.write("\"")
        fp.write(script_path)
        fp.write("\"")
        fp.write(" -srcpath=%1\n")
        fp.write("IF %ERRORLEVEL% NEQ 0 pause\n")
else:
    sh_file = os.path.join(directory, "clickpoints")
    with open(sh_file, 'w') as fp:
        print("Writing ClickPoints bash file")
        fp.write("#!/bin/bash\n")
        fp.write("echo \"$1\" >> ~/.clickpoints/ClickPoints.txt\n")
        fp.write("python")
        fp.write(" ")
        fp.write(script_path)
        fp.write(" -srcpath=\"$1\"\n")
        fp.write("if [[ $? -ne 0 ]]\n")
        fp.write("then\n")
        fp.write("\tread -n1 -r -p \"Press any key to continue...\" key\n")
        fp.write("fi\n")
        os.system("chmod +x %s" % sh_file)
        
    print("Copying ClickPoints bash file to /usr/local/bin/")
    os.popen("sudo cp %s /usr/local/bin/" % sh_file)

    application_path = "/home/"+os.popen('whoami').read()[:-1]+"/.local/share/applications/"
    if not os.path.exists(application_path):
        os.mkdir(application_path)
        
    desktop_file = "/home/"+os.popen('whoami').read()[:-1]+"/.local/share/applications/clickpoints.desktop"
    with open(desktop_file, 'w') as fp:
        print("Writing clickpoints.desktop")
        fp.write("[Desktop Entry]\n")
        fp.write("Type=Application\n")
        fp.write("Name=ClickPoints\n")
        fp.write("GenericName=View Images/Videos and Annotate them\n")
        fp.write("Comment=Display images and videos and annotate them\n")
        fp.write("Exec="+sh_file+" \"\"%f\"\"\n")
        fp.write("NoDisplay=false\n")
        fp.write("Terminal=true\n")
        fp.write("Icon="+icon_path+"\n")
        fp.write("Categories=Development;Science;IDE;Qt;\n")
        fp.write("MimeType=inode/directory;video/*;image/*;video/mp4;video/x-msvideo;video/mpeg;image/bmp;image/png;image/jpeg;image/tiff;image/gif;$\n")
        fp.write("InitialPreference=10\n")

    for ext in ["inode/directory", "ideo/mp4", "video/x-msvideo", "video/mpeg", "image/bmp", "image/png", "image/jpeg", "image/gif", "image/tiff"]:
        print("Setting ClickPoints as default application for %s" % ext)
        os.popen("sudo xdg-mime default clickpoints.desktop "+ext)
    
    print("Installing packets via apt-get ...")
    proc = subprocess.Popen('sudo apt-get install -y python-pip python-numpy python-scipy python-qt4 python-opencv python-matplotlib', \
                            shell=True, stdin=None, executable="/bin/bash")
    proc.wait()

    print("Installing packets via pip ...")
    import pip
    pip.main(['install','-r', 'installation/pip_req.txt'])

    os.chdir("package")
    proc = subprocess.Popen("sudo python setup.py develop",shell=True, stdin=None, executable="/bin/bash")
    proc.wait()
    os.chdir("..")
        
