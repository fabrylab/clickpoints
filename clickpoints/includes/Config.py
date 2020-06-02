#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Config.py

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

import configparser as ConfigParser
import json

class ConfigAccessHelper:
    def __init__(self, parent, section):
        self.parent = parent
        self.section = section

    def __getattr__(self, key):
        try:
            data = self.parent.get(self.section, key)
        except ConfigParser.NoOptionError:
            return ""
        try:
            return json.loads(data)
        except ValueError:
            return data

class Config(ConfigParser.ConfigParser):
    def __init__(self, filename=None,defaults=None, *args, **kwargs):
        ConfigParser.ConfigParser.__init__(self, defaults=defaults, *args, **kwargs)
        if filename is not None:
            self.read(filename)

    def __getattr__(self, key):
        if key in self.sections():
            return ConfigAccessHelper(self, key)
        #return ConfigParser.ConfigParser.__getattr__(self, key)