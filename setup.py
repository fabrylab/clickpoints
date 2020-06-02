#!/usr/bin/env python
# -*- coding: utf-8 -*-
# setup.py

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

from setuptools import setup


setup(name='clickpoints',
      version="1.9.6",
      description='Scientific toolbox for manual and automatic image evaluation.',
      long_description=open('README.rst').read(),
      url='https://github.com/fabrylab/clickpoints',
      license="GPLv3",
      author='Richard Gerum, Sebastian Richter',
      author_email='richard.gerum@fau.de',
      packages=['clickpoints', 'clickpoints.addons', 'clickpoints.includes', 'clickpoints.modules', 'clickpoints.includes.qextendedgraphicsview'],
      entry_points={
              'console_scripts': ['clickpoints=clickpoints.launch:main'],
              'gui_scripts': ['clickpoints_gui=clickpoints.launch:main'],
          },
      #setup_requires=['numpy'],
      install_requires=['scipy',
                        'matplotlib',
                        'imageio',
                        'scikit-image',
                        'qtpy',
                        'qtawesome',
                        'qimage2ndarray',
                        'pillow',
                        'peewee',
                        'imageio',
                        'natsort',
                        'tifffile>=2020.2.16',
                        'sortedcontainers',
                        'psutil',
                        'imageio-ffmpeg',
                        'quamash',
                        'pyqt5',
                       ],
      include_package_data=True)
