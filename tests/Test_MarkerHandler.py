#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Test_MarkerHandler.py

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

__key__ = "MODULE_MARKER"
__testname__ = "Marker Handler"

import sys
import os
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from BaseTest import BaseTest

from qtpy.QtCore import Qt

class Test_MarkerHandler(unittest.TestCase, BaseTest):

    def tearDown(self):
        BaseTest.tearDown(self)

    def test_createMarker(self):
        """ Test if creating marker works """
        self.createInstance(os.path.join("ClickPointsExamples", "TweezerVideos", "002"))

        # switch interface on
        self.keyPress(Qt.Key_F2)

        # wait for image to be loaded
        self.wait_for_image_load()

        # check if no marker is present
        self.assertEqual(len(self.window.GetModule("MarkerHandler").points), 0, "At the beginning already some markers where present")

        # try to add one
        self.mouseClick(50, 50)
        self.assertEqual(len(self.window.GetModule("MarkerHandler").points), 1, "Marker wasn't added by clicking")

    def test_moveMarker(self):
        """ Test if moving marker works """
        self.createInstance(os.path.join("ClickPointsExamples", "TweezerVideos", "002"))

        # switch interface on
        self.keyPress(Qt.Key_F2)

        # wait for image to be loaded
        self.wait_for_image_load()

        # check if no marker is present
        self.assertEqual(len(self.window.GetModule("MarkerHandler").points), 0, "At the beginning already some markers where present")

        # add a marker
        self.mouseClick(50, 50)
        self.assertEqual(len(self.window.GetModule("MarkerHandler").points), 1, "Marker wasn't added by clicking")

        # check position
        data = self.window.GetModule("MarkerHandler").points[0].data
        self.assertTrue(45 < data.x < 55, "Marker x position is added wrong")
        self.assertTrue(45 < data.y < 55, "Marker y position is added wrong")

        # Test moving the marker
        self.mouseDrag(50, 50, 100, 100)

        # check position
        data = self.window.GetModule("MarkerHandler").points[0].data
        self.assertTrue(45 < data.x < 105, "Marker x position move didn't work.")
        self.assertTrue(95 < data.y < 105, "Marker y position move didn't work.")

    def test_deleteMarker(self):
        """ Test if deleting marker works """
        self.createInstance(os.path.join("ClickPointsExamples", "TweezerVideos", "002"))

        # switch interface on
        self.keyPress(Qt.Key_F2)

        # wait for image to be loaded
        self.wait_for_image_load()

        # check if no marker is present
        self.assertEqual(len(self.window.GetModule("MarkerHandler").points), 0, "At the beginning already some markers where present")

        # add a marker
        self.mouseClick(50, 50)
        self.assertEqual(len(self.window.GetModule("MarkerHandler").points), 1, "Marker wasn't added by clicking")

        # Test deletion of marker
        self.mouseClick(50, 50, modifier=Qt.ControlModifier)
        self.assertEqual(len(self.window.GetModule("MarkerHandler").points), 0, "Marker deletion didn't work")

if __name__ == '__main__':
    __path__ = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(__path__, 'log_'+__key__+'.txt')
    with open(log_file, "w") as f:
        runner = unittest.TextTestRunner(f)
        unittest.main(testRunner=runner)
