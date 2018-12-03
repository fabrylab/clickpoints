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

# upgrade twine (used for uploading)
os.system("pip install twine --upgrade")

# pack clickpoints
os.system("python setup.py sdist")

# the command
command_string = "twine upload dist/clickpoints-%s.tar.gz" % current_version
# optionally add the username
if options.username:
    command_string += " --username %s" % options.username
# optionally add the password
if options.password:
    command_string += " --password %s" % options.password
# print the command string
print(command_string)
# and execute it
os.system(command_string)
