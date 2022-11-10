#!/usr/bin/env python
# -*- coding: utf-8 -*-
# loadExamples.py

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

from pathlib import Path
from urllib.request import urlretrieve


def downloadFiles(path, files):
    for file in files:
        url = f"https://raw.githubusercontent.com/fabrylab/clickpointsexamples/master/{path}/{file}"
        target = Path(file)
        if not target.exists():
            print("Downloading File", file)
            urlretrieve(str(url), str(file))


def loadExample(name):
    if name == "king_penguins":
        downloadFiles("PenguinCount", ["count.cdb", "20150312-110000_microbs_GoPro.jpg", "20150408-150001_microbs_GoPro.jpg", "20150514-110000_microbs_GoPro.jpg"])
    if name == "magnetic_tweezer":
        downloadFiles("TweezerVideos/001", ["track.cdb"] + [f"frame{i:04d}.jpg" for i in range(68)])
    if name == "plant_root":
        downloadFiles("PlantRoot", ["plant_root.cdb", "1-0min.tif", "1-2min.tif", "1-4min.tif", "1-6min.tif", "1-8min.tif", "1-10min.tif"])
