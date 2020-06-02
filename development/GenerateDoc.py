#!/usr/bin/env python
# -*- coding: utf-8 -*-
# GenerateDoc.py

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

from __future__ import print_function, division
import re, glob

def ReadConfigDoc(module):
    file = "ConfigLoad.py"
    if file[-4:] == ".pyc":
        file = file[:-4]+".py"
    text = ""
    write = False
    with open(file) as fp:
        for line in fp.readlines():
            line = line.strip()
            if line == "":
                continue
            if line.startswith("# @"):
                m = re.match(r'# @config (.*)$', line.strip())
                if m:
                    if write:
                        text += "* "+m.groups()[0]+"\n"
            if line.startswith('""" @config'):
                m = re.match(r'""" @config (.*) """$', line.strip())
                if m:
                    if m.groups()[0] == module:
                        write = True
                    else:
                        write = False
                    #text += "\n## "+m.groups()[0] + " ##\n"

    return text

def UpdateText(file):
    text = ""
    if file[-4:] == ".pyc":
        file = file[:-4]+".py"
    with open(file) as fp:
        for line in fp.readlines():
            m = re.match(r'\w*# @key (.*)$', line.strip())
            if m:
                desc = m.groups()[0].replace(":", ":\t", 1)
                if desc.startswith("--"):
                    continue
                text += "* "+ desc + "\n"
    return text

modules = [ ["General", "ClickPointsQT.py"],
            ["Marker", "MarkerHandler.py"],
            ["Mask", "MaskHandler.py"],
            ["GammaCorrection", "GammaCorrection.py"],
            ["Timeline", "Timeline.py"],
            ["Annotations", "AnnotationHandler.py"],
            ["FolderBrowser", "FolderBrowser.py"],
            ["ScriptLauncher", "ScriptLauncher.py"],
            ["InfoHud", "InfoHud.py"],
            ["VideoExporter", "VideoExporter.py"]
            ]

if 0:
    text = ""
    for module in modules:
        text += "\n## "+module[0]+"\n"
        text += UpdateText(module[1])
    print(text)

if 1:
    module = modules[9]
    text = ""
    text += "\n## Config Parameter\n"
    text += ReadConfigDoc(module[0])
    text += "\n## Keys\n"
    text += UpdateText(module[1])
    print(text)

#text = ""
#files = glob.glob("*.py")
#for file in files:
#    UpdateText(file)
#print(text)