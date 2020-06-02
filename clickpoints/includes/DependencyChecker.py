#!/usr/bin/env python
# -*- coding: utf-8 -*-
# DependencyChecker.py

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
import os
import sys
import pip
import importlib
from distutils.version import LooseVersion

IMPORT_SUCCESS = 0
IMPORT_FAILURE = 1
IMPORT_OLD = 2

def CheckPackages():
    class package:
        def __init__(self, name, version_string="__version__", importname=None, install_string=None, min_version=None):
            if importname is None:
                importname = name
            self.name = name
            self.version_string = version_string
            self.importname = importname
            self.install_string = install_string
            self.min_version = min_version

        def do_import(self):
            try:
                self.package = importlib.import_module(self.importname)
                if self.min_version is not None:
                    if LooseVersion(self.version()) < LooseVersion(self.min_version):
                        return IMPORT_OLD
            except ImportError:
                return IMPORT_FAILURE
            else:
                return IMPORT_SUCCESS

        def update(self):
            pip.main(["install", "--upgrade", self.name])
            self.package = importlib.import_module(self.importname)

        def version(self):
            if self.version_string == "":
                return ""
            return getattr(self.package, self.version_string)

        def install(self):
            if self.install_string is None:
                pip.main(['install', self.name])
            else:
                os.system(self.install_string)
            self.package = importlib.import_module(self.importname)


    packages = [
      package('clickpoints', version_string="", install_string="%s %s develop" % (sys.executable, os.path.join(os.path.dirname(__file__), "..", "package", "setup.py"))),
      package('numpy'),
      package('scipy'),
      package('matplotlib'),
      package('sqlite3', version_string="sqlite_version"),

      package('qtawesome'),
      package('sip', version_string="SIP_VERSION_STR"),
      package('qtpy'),
      package('qimage2ndarray'),

      package('peewee'),
      package('playhouse', version_string=""),
      package('pymysql'),

      package('natsort'),
      package('tifffile'),
      package('imageio', min_version='1.3'),
      package('cv2'),  # can't be installed by pip
      package('pillow', importname="PIL", version_string="PILLOW_VERSION"),

      package('sortedcontainers'),

      package('psutil'),
      package('six'),
      package('dateutil'),
      package('pyparsing'),
    ]

    errors = 0
    for package in packages:
        import_status = package.do_import()
        if import_status != IMPORT_SUCCESS:
            if import_status == IMPORT_OLD:
                print("Package %s too old. Version %s but needs version %s" % (package.name, package.version(), package.min_version))
                package.update()
            else:
                print("Package %s not found." % package.name)
                package.install()
                if package.do_import() != IMPORT_SUCCESS:
                    print("ERROR: Installation failed")
                    errors += 1
        else:
            print("Found", package.name, package.version())

    return errors

if __name__ == "__main__":
    CheckPackages()
