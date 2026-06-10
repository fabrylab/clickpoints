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

from importlib import import_module
from typing import Any

_lazy_imports = {
    "LoadConfig": (".ConfigLoad", "LoadConfig"),
    "ExceptionPathDoesntExist": (".ConfigLoad", "ExceptionPathDoesntExist"),
    "GraphicsItemEventFilter": (".Tools", "GraphicsItemEventFilter"),
    "HelpText": (".Tools", "HelpText"),
    "BroadCastEvent": (".Tools", "BroadCastEvent"),
    "BroadCastEvent2": (".Tools", "BroadCastEvent2"),
    "SetBroadCastModules": (".Tools", "SetBroadCastModules"),
    "rotate_list": (".Tools", "rotate_list"),
    "HTMLColorToRGB": (".Tools", "HTMLColorToRGB"),
    "TextButton": (".Tools", "TextButton"),
    "StartHooks": (".Tools", "StartHooks"),
    "GetHooks": (".Tools", "GetHooks"),
    "IconFromFile": (".Tools", "IconFromFile"),
    "BigImageDisplay": (".BigImageDisplay", "BigImageDisplay"),
    "MemMap": (".MemMap", "MemMap"),
    "CanvasWindow": (".matplotlibwidget", "CanvasWindow"),
    "ImageQt": (".ImageQt_Stride", "ImageQt"),
    "QExtendedGraphicsView": (".qextendedgraphicsview.QExtendedGraphicsView", "QExtendedGraphicsView"),
}

__all__ = list(_lazy_imports)


def __getattr__(name: str) -> Any:
    if name not in _lazy_imports:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = _lazy_imports[name]
    module = import_module(module_name, __name__)
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value
