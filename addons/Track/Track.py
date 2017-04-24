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
import clickpoints
import numpy as np
import cv2


class Addon(clickpoints.Addon):
    def __init__(self, *args, **kwargs):
        clickpoints.Addon.__init__(self, *args, **kwargs)

        self.lk_params = dict(winSize=(8, 8), maxLevel=0,
                         criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))

        # find a track type
        for type in self.db.getMarkerTypes():
            if type.mode == self.db.TYPE_Track:
                break
        else:
            # if no track type is found, create one
            self.db.setMarkerType("track", "#FFFF00", self.db.TYPE_Track)
            self.cp.reloadTypes()

    def run(self, start_frame=0):
        # get the images
        images = self.db.getImageIterator(start_frame=start_frame)

        # retrieve first image
        image_last = next(images)

        # get points and corresponding tracks
        points = self.db.getMarkers(image=image_last.id, processed=0)
        p0 = np.array([[point.x, point.y] for point in points if point.track_id]).astype(np.float32)
        tracks = [point.track for point in points if point.track_id]

        # if no tracks are supplied, stop
        if len(tracks) == 0:
            print("Nothing to track")
            return

        # start iterating over all images
        for image in images:
            print("Tracking frame number %d, %d tracks" % (image.sort_index, len(tracks)), image.id, image_last.id)

            # calculate next positions
            p1, st, err = cv2.calcOpticalFlowPyrLK(image_last.data8, image.data8, p0, None, **self.lk_params)

            # set the new positions
            self.db.setMarkers(image=image, x=p1[:, 0], y=p1[:, 1], processed=0, track=tracks)

            # mark the marker in the last frame as processed
            self.db.setMarkers(image=image_last, x=p0[:, 0], y=p0[:, 1], processed=1, track=tracks)

            # update ClickPoints
            self.cp.reloadMarker(image.sort_index)
            self.cp.jumpToFrameWait(image.sort_index)

            # store positions and image
            p0 = p1
            image_last = image

            # check if we should terminate
            if self.cp.hasTerminateSignal():
                print("Cancelled Tracking")
                return

if __name__ == "__main__":
    start_frame, database, port = clickpoints.GetCommandLineArgs()
    addon = Addon(database=database)
    addon.run(start_frame)
