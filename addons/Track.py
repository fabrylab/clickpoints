#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Track.py

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

from __future__ import print_function, division
import sys
import numpy as np
__icon__ = "fa.road"

# define tracking parameter
import cv2
lk_params = dict(winSize=(8, 8), maxLevel=0, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))

# connect to ClickPoints database and the running program instance
# database filename and port for communication are supplied as command line argument when started from ClickPoints
import clickpoints
start_frame, database, port = clickpoints.GetCommandLineArgs()
db = clickpoints.DataFile(database)
com = clickpoints.Commands(port, catch_terminate_signal=True)

# get the images
images = db.getImageIterator(start_frame=start_frame)

# retrieve first image
image_last = next(images)

# get points and corresponding tracks
points = db.getMarkers(image=image_last.id, processed=0)
p0 = np.array([[point.x, point.y] for point in points if point.track_id]).astype(np.float32)
tracks = [point.track for point in points if point.track_id]

# if no tracks are supplied, stop
if len(tracks) == 0:
    print("Nothing to track")
    sys.exit(-1)

# start iterating over all images
for image in images:
    print("Tracking frame number %d, %d tracks" % (image.sort_index, len(tracks)), image.id, image_last.id)

    # calculate next positions
    p1, st, err = cv2.calcOpticalFlowPyrLK(image_last.data8, image.data8, p0, None, **lk_params)

    # set the new positions
    db.setMarkers(image=image, x=p1[:, 0], y=p1[:, 1], processed=0, track=tracks)

    # mark the marker in the last frame as processed
    db.setMarkers(image=image_last, x=p0[:, 0], y=p0[:, 1], processed=1, track=tracks)

    # update ClickPoints
    com.ReloadMarker(image.sort_index)
    com.JumpToFrameWait(image.sort_index)

    # store positions and image
    p0 = p1
    image_last = image

    # check if we should terminate
    if com.HasTerminateSignal():
        print("Cancelled Tracking")
        sys.exit(0)
