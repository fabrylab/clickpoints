#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __init__.py

# Copyright (c) 2015-2022, Richard Gerum, Sebastian Richter, Alexander Winterl
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

import importlib.metadata
from importlib import import_module
import os
from typing import Any

os.environ.setdefault("QT_API", "pyside6")

__version__ = importlib.metadata.metadata('clickpoints')['version']

_lazy_imports = {
    "Addon": (".Addon", "Addon"),
    "load": (".includes.loader", "loadUrl"),
    "loadExample": (".includes.loadExamples", "loadExample"),
    "DataFile": (".DataFile", "DataFile"),
    "MaskDtypeMismatch": (".DataFile", "MaskDtypeMismatch"),
    "MaskDimensionMismatch": (".DataFile", "MaskDimensionMismatch"),
    "MaskDimensionUnknown": (".DataFile", "MaskDimensionUnknown"),
    "MarkerTypeDoesNotExist": (".DataFile", "MarkerTypeDoesNotExist"),
    "ImageDoesNotExist": (".DataFile", "ImageDoesNotExist"),
}

__all__ = [
    "__version__",
    "Addon",
    "load",
    "loadExample",
    "DataFile",
    "MaskDtypeMismatch",
    "MaskDimensionMismatch",
    "MaskDimensionUnknown",
    "MarkerTypeDoesNotExist",
    "ImageDoesNotExist",
    "print_status",
    "define_paths",
]


def __getattr__(name: str) -> Any:
    if name not in _lazy_imports:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = _lazy_imports[name]
    module = import_module(module_name, __name__)
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value


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
    print("Using %s" % QT_API_NAME, QtCore._qt_version)

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
