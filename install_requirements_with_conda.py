#!/usr/bin/env python
# -*- coding: utf-8 -*-
# install_requirements_with_conda.py

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

import os
import time

start_time = time.time()

def check_packages_installed(package_name):
    """ check if a package is installed"""

    # some packages have other names when they are imported compared to the install name
    translation_names = {"pillow": "PIL", "scikit-image": "skimage", "opencv": "cv2"}

    # translate the package name if it is in the list
    if package_name in translation_names:
        package_name = translation_names[package_name]

    # use importlib for python3
    try:
        # python 3
        import importlib.util
    except ImportError:
        # python 2
        import pip
        # or pip for python 2
        installed_packages = pip.get_installed_distributions()
        return package_name in [p.project_name for p in installed_packages]

    # try to find the package and return True if it was found
    spec = importlib.util.find_spec(package_name)
    if spec is None:
        return False
    return True


# gather the packages from the meta.yaml file which is also used to create the conda package
packages = []
with open("meta.yaml", 'r') as fp:
    active = False
    # iterate over the lines in the file
    for line in fp:
        line = line.strip()
        # find the section "run"
        if line == "run:":
            active = True
        # if we are in the "run" section
        elif active is True:
            # find lines with "-"
            if line.startswith("-"):
                # strip the "-" and we have the package name
                package = line[2:]
                if package != "python":
                    # if the package is not installed, add it to the list
                    if not check_packages_installed(package):
                        packages.append(package)
            else:
                active = False

# if there are packages which are not installed
if len(packages):
    # start a conda installation with the list of packages
    print("Install packages:", packages)
    os.system("conda install -c conda-forge -c rgerum -y "+" ".join(packages))

# as there was a problem with PyQt5, try to install it with pip
try:
    # try to import qtpy
    import qtpy
except (ImportError, ModuleNotFoundError):
    # if it did not manage to import itself with a backend, install pyqt5
    os.system("pip install pyqt5")

# and finally install clickpoints usind no-dependencies
os.system("pip install -e . --no-dependencies")

print("Clickpoints installed (took %.2fs)" % (time.time()-start_time))
