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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "clickpoints"))
import clickpoints
current_version = clickpoints.__version__

def CheckForUncommitedChanges(directory):
    old_dir = os.getcwd()
    os.chdir(directory)
    uncommited = os.popen("hg status -m").read().strip()
    if uncommited != "":
        print("ERROR: uncommited changes in repository", directory)
        sys.exit(1)
    os.system("hg pull -u")
    os.chdir(old_dir)

def RelaceVersion(file, version_old, version_new):
    with open(file, "r") as fp:
        data = fp.readlines()
    with open(file, "w") as fp:
        for line in data:
            fp.write(line.replace(version_old, version_new))

from optparse import OptionParser

parser = OptionParser()
parser.add_option("-v", "--version", action="store", type="string", dest="version")
parser.add_option("-t", "--test", action="store_false", dest="release", default=False)
parser.add_option("-r", "--release", action="store_true", dest="release")
parser.add_option("-u", "--username", action="store", dest="username")
parser.add_option("-p", "--password", action="store", dest="password")
(options, args) = parser.parse_args()
if options.version is None and len(args):
    options.version = args[0]

print("MakeRelease started ...")
# go to parent directory ClickPointsProject
os.chdir("..")
path_to_clickpointsproject = os.getcwd()

# check for new version name as command line argument
new_version = None
try:
    new_version = options.version
except IndexError:
    pass
if new_version is None:
    if options.release is False:
        new_version = current_version
    else:
        print("ERROR: no version number supplied. Use 'MakeRelease.py 0.9' to release as version 0.9")
        sys.exit(1)

# check if new version name differs
if options.release and current_version == new_version:
    print("ERROR: new version is the same as old version")
    sys.exit(1)

print("Setting version number to", new_version)

# check for uncommited changes
#if options.release:
#    for path in paths:
#        CheckForUncommitedChanges(path)
#    CheckForUncommitedChanges(path_to_website)

""" Let's go """
RelaceVersion("setup.py", current_version, new_version)
RelaceVersion("meta.yaml", current_version, new_version)
RelaceVersion("docs/conf.py", current_version, new_version)
RelaceVersion("clickpoints/__init__.py", current_version, new_version)

if options.release:
    # upload to pipy
    os.system("pip install twine")
    os.system("python setup.py sdist")
    #os.system("twine upload dist/clickpoints-%s.tar.gz --username %s --password %s" % (new_version, options.username, options.password))

    # upload to conda
    os.system("conda install anaconda-client conda-build -y")
    os.system("conda update -n root conda-build")
    os.system("conda update -n root anaconda-client")

    #os.system("anaconda login --username %s --password %s" % (options.username, options.password))

    os.system("conda config --set anaconda_upload yes")

    os.system("conda-build . -c conda-forge")

    # Commit changes to ClickPoints
    os.system("hg commit -m \"set version to %s\"" % new_version)
    os.system("hg tag \"v%s\"" % new_version)

    # Push everything
    os.system("hg push")

print("MakeRelease completed!")
