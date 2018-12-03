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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ClickPoints. If not, see <http://www.gnu.org/licenses/>

from __future__ import print_function, division
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "clickpoints"))
import clickpoints
current_version = clickpoints.__version__

from optparse import OptionParser

parser = OptionParser()
parser.add_option("-u", "--username", action="store", dest="username")
parser.add_option("-p", "--password", action="store", dest="password")
(options, args) = parser.parse_args()

# upload to conda
os.system("conda install anaconda-client conda-build -y")
os.system("conda update -n root conda-build")
os.system("conda update -n root anaconda-client")

# login is normally cached so you need to login only once
if options.username is not None:
    if options.password is not None:
        os.system("anaconda login --username %s --password %s" % (options.username, options.password))
    else:
        os.system("anaconda login --username %s" % options.username)

os.system("conda config --set anaconda_upload yes")

os.system("conda-build . -c conda-forge")
