#!/usr/bin/env python
# -*- coding: utf-8 -*-
# DriftCorrection.py

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

from __future__ import division, print_function
import cv2
import numpy as np
from scipy.ndimage.measurements import center_of_mass
import peewee
import sys
import clickpoints
from qtpy import QtWidgets, QtCore, QtGui


class Addon(clickpoints.Addon):
    def __init__(self, *args, **kwargs):
        clickpoints.Addon.__init__(self, *args, **kwargs)

        self.matchFunctions = ["TM_CCOR", "TM_CCOR_NORMED", "TM_CCOEFF", "TM_CCOEFF_NORMED"]

        self.addOption(key="borderSize", display_name="Border", default=[20, 20], value_count=2, value_type="int",
                       tooltip="How much border in pixel the search window is allowed to move during the search in the new image.")
        self.addOption(key="compareToFirst", display_name="Compare to first image", default=False, value_type="bool",
                       tooltip="Weather each image should be compared to the first image or the previous image.")
        self.addOption(key="matchFunction", display_name="Match Function", default=3, value_type="choice", values=self.matchFunctions)

        # Check if the marker type is present
        if not self.db.getMarkerType("drift_rect"):
            self.db.setMarkerType("drift_rect", [0, 255, 255], self.db.TYPE_Rect)
            self.cp.reloadTypes()

        # the flow overlay over the image
        self.image = QtWidgets.QGraphicsPixmapItem(self.cp.window.view.origin)
        self.image.setZValue(5)
        self.overlays = {}

    def updateMarker(self, marker):
        if marker.type.name != "drift_rect":
            return
        if marker.id not in self.overlays:
            overlay = QtWidgets.QGraphicsPolygonItem(self.image)
            overlay.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 255, 128)))
            overlay.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 0)))
            self.overlays[marker.id] = overlay
        else:
            overlay = self.overlays[marker.id]
        border_x, border_y = self.getOption("borderSize")
        poly = []
        poly.append(QtCore.QPoint(marker.x-border_x, marker.y-border_y))
        poly.append(QtCore.QPoint(marker.x+marker.width+border_x, marker.y-border_y))
        poly.append(QtCore.QPoint(marker.x+marker.width+border_x, marker.y+marker.height+border_y))
        poly.append(QtCore.QPoint(marker.x-border_x, marker.y+marker.height+border_y))
        poly.append(QtCore.QPoint(marker.x-border_x, marker.y-border_y))

        poly.append(QtCore.QPoint(marker.x, marker.y))
        poly.append(QtCore.QPoint(marker.x + marker.width, marker.y))
        poly.append(QtCore.QPoint(marker.x + marker.width, marker.y + marker.height))
        poly.append(QtCore.QPoint(marker.x, marker.y + marker.height))
        poly.append(QtCore.QPoint(marker.x, marker.y))

        overlay.setPolygon(QtGui.QPolygonF(poly))

    def deleteOverlay(self, marker):
        if marker.type.name != "drift_rect":
            return
        if marker.id in self.overlays:
            overlay = self.overlays[marker.id]
            overlay.scene().removeItem(overlay)
            del self.overlays[marker.id]

    def markerMoveEvent(self, marker):
        self.updateMarker(marker)

    def markerAddEvent(self, entry):
        self.updateMarker(entry)

    def markerRemoveEvent(self, entry):
        self.deleteOverlay(entry)

    def delete(self):
        ids = [id for id in self.overlays.keys()]
        for id in ids:
            overlay = self.overlays[id]
            overlay.scene().removeItem(overlay)
            del self.overlays[id]
        self.image.scene.removeItem(self.image)

    def run(self, start_frame=0):
        # Define parameters
        compare_to_first = self.getOption("compareToFirst")
        border_x, border_y = self.getOption("borderSize")

        # get range
        start_frame, end_frame, skip = self.cp.getFrameRange()

        # try to load marker
        rect = self.db.getRectangles(type="drift_rect", frame=start_frame)
        print(rect)
        print("count:", rect.count())
        if rect.count() < 1:
            print("ERROR: no rectangle selected.\nPlease mark a rectangle with type 'drift_rect'.")
            sys.exit(-1)
        rect = rect[0]

        # Get images and template
        images = self.db.getImageIterator(start_frame=start_frame, end_frame=end_frame)
        template = next(images).data[rect.slice((border_y, border_x))]

        # get the match function
        match_func = getattr(cv2, self.matchFunctions[self.getOption("matchFunction")])

        # start iteration
        last_shift = np.array([0, 0])
        for image in images:
            # template matching for drift correction
            res = cv2.matchTemplate(image.data[rect.slice()], template, match_func)
            res += np.amin(res)
            res = res ** 4.

            # get 2D max
            shift = np.array(np.unravel_index(res.argmax(), res.shape)).astype("float")

            # get sub pixel accurate center of mass
            try:
                # fail if there it is too close to border
                if not (shift[0] > 2 and shift[1] > 2):
                    raise ValueError

                subres = res[int(shift[0] - 2):int(shift[0] + 3), int(shift[1] - 2):int(shift[1] + 3)]
                subshift = center_of_mass(subres)

                # calculate coordinates of sub shift
                shift = shift + (subshift - np.array([2., 2.]))

                # calculate full image coordinates of shift
                shift = shift - np.array([border_y, border_x])

            except ValueError:
                # calculate full image coordinates of shift
                shift = shift - np.array([border_y, border_x])

            # get new template if compare_to_first is off
            if not compare_to_first:
                template = image.data[rect.slice_y().start - border_y: rect.slice_y().stop + border_y,
                           rect.slice_x().start - border_x: rect.slice_x().stop + border_x]
                shift += last_shift.astype("float")
                last_shift = shift

            # save the offset to the database
            self.db.setOffset(image=image, x=float(shift[1]), y=float(shift[0]))
            print("Drift Correction Frame", image.sort_index, shift)

            # Check if ClickPoints wants to terminate us
            if self.cp.hasTerminateSignal():
                print("Cancel Stabilization")
                return
