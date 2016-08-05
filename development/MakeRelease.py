#!/usr/bin/env python
# -*- coding: utf-8 -*-
# MakeRelease.py

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

from jinja2 import Environment, FileSystemLoader

def LoadIgnorePatterns(file):
    ignore_pattern = []
    with open(file) as fp:
        syntax = "glob"
        for line in fp.readlines():
            line = line.strip()
            if line == "":
                continue
            if line[0] == "#":
                continue
            if line.startswith("syntax"):
                syntax = line.split(" ", 1)[1]
                continue
            if syntax == "glob":
                ignore_pattern.append(lambda name, pattern=line: fnmatch.fnmatch(name, pattern))
            elif syntax == "regexp":
                ignore_pattern.append(lambda name, pattern=line: re.match(pattern, name) is not None)
            else:
                print("WARNING: unknown syntax", syntax)
    return ignore_pattern

def CheckIgnoreMatch(file):
    for pattern in ignore_pattern:
        if pattern(file):
            return True
    return False

def CopyDirectory(directory, dest_directory):
    global myzip, file_list
    old_dir = os.getcwd()
    os.chdir(directory)

    filelist = [file[2:] for file in os.popen("hg status -m -c").read().split("\n") if file != ""]
    for file in filelist:
        if CheckIgnoreMatch(file):
            continue
        print(file, os.path.join(directory, file))
        dest_path = os.path.normpath(os.path.join(dest_directory, file))
        if file != "files.txt":
            myzip.write(file, dest_path)
        file_list.write(dest_path+"\n")
        print(file, os.path.join(path_to_temporary_installer, dest_path))
        if not os.path.exists(os.path.join(path_to_temporary_installer, os.path.dirname(dest_path))):
            os.makedirs(os.path.join(path_to_temporary_installer, os.path.dirname(dest_path)))
        shutil.copy(file, os.path.join(path_to_temporary_installer, dest_path))
    os.chdir(old_dir)

def CopyInstallerFilesNoPython(directory):
    global myzip, file_list
    old_dir = os.getcwd()
    os.chdir("clickpoints")

    for file in ["make_no_python_installer.py", "pyapp_clickpoints_no_python.nsi"]:
        src = os.path.join("development", "nsis", file)
        dst = os.path.join(path_to_temporary_installer, file)
        print(os.path.abspath(src))
        shutil.copy(src, dst)
    for file in ["sqlite3.dll", "_sqlite3.pyd"]:
        src = os.path.join("development", "pynsist", "pynsist_pkgs", file)
        dst = os.path.join(path_to_temporary_installer, file)
        print(os.path.abspath(src))
        shutil.copy(src, dst)

    os.chdir(path_to_temporary_installer)
    os.system(sys.executable+" make_no_python_installer.py")
    os.chdir(old_dir)

def CopyInstallerFiles(directory):
    global myzip, file_list
    old_dir = os.getcwd()
    os.chdir("clickpoints")
    subfolder = r"development\pynsist"

    env = Environment(loader=FileSystemLoader(subfolder))

    filelist = [file[2:] for file in os.popen("hg status -m -c").read().split("\n") if file != ""]
    for file in filelist:
        if not file.startswith(subfolder):
            continue
        target = file[len(subfolder)+1:]
        if not os.path.exists(os.path.join(path_to_temporary_installer, os.path.dirname(target))):
            os.makedirs(os.path.join(path_to_temporary_installer, os.path.dirname(target)))
        if target.endswith(".nsi"):
            template = env.get_template(target)
            with open(os.path.join(path_to_temporary_installer, target), 'w') as fp:
                fp.write(template.render(extension_list=[".cdb", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".gif", ".avi", ".mp4"]))
        elif target.endswith(".cfg"):
            template = env.get_template(target)
            with open(os.path.join(path_to_temporary_installer, target), 'w') as fp:
                fp.write(template.render(version=new_version, version2=new_version.replace(" ", "_")))
        else:
            shutil.copy(file, os.path.join(path_to_temporary_installer, target))

    os.chdir(path_to_temporary_installer)
    os.system(sys.executable+" -m nsist installer.cfg")
    os.chdir(old_dir)

def CheckForUncommitedChanges(directory):
    old_dir = os.getcwd()
    os.chdir(directory)
    uncommited = os.popen("hg status -m").read().strip()
    if uncommited != "":
        print("ERROR: uncommited changes in repository", directory)
        sys.exit(1)
    os.system("hg pull -u")
    os.chdir(old_dir)

from optparse import OptionParser

parser = OptionParser()
parser.add_option("-v", "--version", action="store", type="string", dest="version")
parser.add_option("-t", "--test", action="store_false", dest="release", default=False)
parser.add_option("-r", "--release", action="store_true", dest="release")
(options, args) = parser.parse_args()
if options.version is None and len(args):
    options.version = args[0]

print("MakeRelease started ...")
# go to parent directory ClickPointsProject
os.chdir("..")
os.chdir("..")
path_to_clickpointsproject = os.getcwd()
path_to_temporary_installer = os.path.normpath(os.path.join(os.getenv('APPDATA'), "..", "Local", "Temp", "ClickPoints", "Installer"))
if not os.path.exists(path_to_temporary_installer):
    os.makedirs(path_to_temporary_installer)

# define paths to website, zipfile and version file
path_to_website = r"fabry_biophysics.bitbucket.org\clickpoints"
zip_file = 'clickpoints_v%s.zip'
version_file = os.path.join("clickpoints", "version.txt")

#paths = [".", "clickpoints", "mediahandler", "qextendedgraphicsview"]
#path_destinations = ["installation", ".", "includes", "includes"]
paths = ["clickpoints", os.path.join("clickpoints", "includes", "qextendedgraphicsview")]
path_destinations = [".", "includes"]

""" Checks """
# get old version name
with open(version_file, "r") as fp:
    old_version = fp.read().strip()

# check for new version name as command line argument
new_version = ""
try:
    new_version = options.version
except IndexError:
    pass
if new_version == "":
    if options.release == False:
        new_version = old_version
    else:
        print("ERROR: no version number supplied. Use 'MakeRelease.py 0.9' to release as version 0.9")
        sys.exit(1)
zip_file = zip_file % new_version

# check if new version name differs
if options.release and old_version == new_version:
    print("ERROR: new version is the same as old version")
    sys.exit(1)

# check for uncommited changes
if options.release:
    for path in paths:
        CheckForUncommitedChanges(path)
    CheckForUncommitedChanges(path_to_website)
else:
    os.chdir("clickpoints")
    revision = os.popen("hg id").read().strip()[:12]
    os.chdir("..")
    new_version = "%s (%s)" % (new_version, revision)

""" Let's go """
# write new version to version.txt
with open(version_file, "w") as fp:
    fp.write(new_version)

# Create filelist and zip file
file_list = open("files.txt", "w")
myzip = zipfile.ZipFile(zip_file, 'w', compression=zipfile.ZIP_DEFLATED)

# Gather files repository files and add them to zip file
ignore_pattern = LoadIgnorePatterns(os.path.join("clickpoints", ".releaseignore"))
for path, path_dest in zip(paths, path_destinations):
    CopyDirectory(path, path_dest)

# Put installer files to temporary directory
CopyInstallerFiles(os.path.join(path_to_clickpointsproject, "clickpoints", "development", "pynsist"))

# Put installer files to temporary directory
CopyInstallerFilesNoPython(os.path.join(path_to_clickpointsproject, "clickpoints", "development", "nsis"))

print("finished zip")
# Close
file_list.close()
myzip.write("files.txt", "installation/files.txt")
myzip.write("clickpoints/development/pynsist/pynsist_pkgs/sqlite3.dll", "sqlite3.dll")
myzip.write("clickpoints/development/pynsist/pynsist_pkgs/_sqlite3.pyd", "_sqlite3.pyd")
myzip.close()

# Copy files to website
print("Move Files")
shutil.move(zip_file, os.path.join(path_to_website, zip_file))
shutil.copy(version_file, os.path.join(path_to_website, "version.html"))
new_version_ = new_version.replace(" ", "_")
shutil.copy(os.path.join(path_to_temporary_installer, "build", "nsis", "ClickPoints_v"+new_version_+".exe" ), os.path.join(path_to_website, "ClickPoints_v"+new_version_+".exe"))
shutil.copy(os.path.join(path_to_temporary_installer, "ClickPoints_v"+new_version_+"_no_python.exe" ), os.path.join(path_to_website, "ClickPoints_v"+new_version_+"_no_python.exe"))

if options.release:
    # Commit changes to ClickPoints
    os.chdir("clickpoints")
    os.system("hg commit -m \"set version to %s\"" % new_version)
    os.chdir("..")

    # Commit changes in ClickPointsRelease
    os.system("hg commit -m \"Release v%s\"" % new_version)
    os.system("hg tag \"v%s\"" % new_version)

    # Commit changes in website
    os.chdir(path_to_website)
    os.system("hg add "+zip_file)
    os.system("hg commit -m \"Release v%s\"" % new_version)

    # Push everything
    os.system("hg push")
    os.chdir(path_to_clickpointsproject)
    os.system("hg push")
    os.chdir("clickpoints")
    os.system("hg push")

print("MakeRelease completed!")