#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __init__.py

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

__version__ = '1.9.6'

# Try to import the addon library, but for only working with the database, we don't need the Addon
# definition which is based on Qt
try:
    from .Addon import Addon
except ImportError as err:
    pass

from .DataFile import DataFile, MaskDtypeMismatch, MaskDimensionMismatch, MaskDimensionUnknown
from .DataFile import MarkerTypeDoesNotExist, ImageDoesNotExist

def print_status():
    # ClickPoints Version
    print("ClickPoints", __version__)

    # Python Version
    import sys
    print("Using Python", "%d.%d.%d" % (sys.version_info.major, sys.version_info.minor, sys.version_info.micro),
          sys.version_info.releaselevel, "64bit" if sys.maxsize > 2 ** 32 else "32bit")

    # Qt Version
    from qtpy import API_NAME as QT_API_NAME
    from qtpy import QtCore
    print("Using %s" % QT_API_NAME, QtCore.PYQT_VERSION_STR)

def define_paths():
    import os
    import sys

    directory = os.path.dirname(__file__)
    os.environ["CLICKPOINTS_PATH"] = directory
    os.environ["CLICKPOINTS_ICON"] = os.path.join(directory, "icons")
    os.environ["CLICKPOINTS_ADDON"] = os.path.join(directory, "addons")

    if sys.platform[:3] == 'win':
        os.environ["CLICKPOINTS_TMP"] = os.path.join(os.getenv('APPDATA'), "..", "Local", "Temp", "ClickPoints")
    else:
        os.environ["CLICKPOINTS_TMP"] = os.path.expanduser("~/.clickpoints/")
    if not os.path.exists(os.environ["CLICKPOINTS_TMP"]):
        os.makedirs(os.environ["CLICKPOINTS_TMP"])
