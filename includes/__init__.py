#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __init__.py

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

sys.path.insert(0, os.path.dirname(__file__))
from ConfigLoad import LoadConfig, ExceptionPathDoesntExist
from Tools import HelpText, BroadCastEvent, BroadCastEvent2, SetBroadCastModules, rotate_list, HTMLColorToRGB, TextButton
from BigImageDisplay import BigImageDisplay
from Database import DataFile
from MemMap import MemMap
from DependencyChecker import CheckPackages


path = os.path.join(os.path.dirname(__file__), "qextendedgraphicsview")
if os.path.exists(path):
    sys.path.append(path)
from QExtendedGraphicsView import QExtendedGraphicsView