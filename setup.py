#!/usr/bin/env python
# -*- coding: utf-8 -*-
# setup.py

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

from setuptools import setup

import os
if os.path.dirname(__file__) != "":
    os.chdir(os.path.dirname(__file__))  # for call from the installer

try:
    with open("../version.txt") as fp:
        version = fp.read().strip()
except IOError:
    version = "unknown"

setup(name='clickpoints',
      version=version,
      description='The clickpoints package enables communicating with the clickpoints software and to save and load clickpoints files.',
      url='https://bitbucket.org/fabry_biophysics/clickpoints',
      author='FabryLab',
      author_email='richard.gerum@fau.de',
      license='MIT',
      packages=['clickpoints'],
      install_requires=[
          'numpy',
          'peewee',
          'pillow',
          'imageio',
          'sphinxcontrib-bibtex',
      ],
      zip_safe=False)