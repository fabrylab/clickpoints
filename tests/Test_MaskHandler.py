#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Test_MaskHandler.py

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

__key__ = "MODULE_MASK"
__testname__ = "Mask Handler"

import sys
import os
import unittest
from PIL import Image
import imageio
import numpy as np
import time

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.dirname(__file__))

from BaseTest import BaseTest

from qtpy.QtCore import Qt

class Test_MaskHandler(unittest.TestCase, BaseTest):

    def tearDown(self):
        BaseTest.tearDown(self)

    def test_loadMasks(self):
        """ Load a database with masks """
        self.createInstance(os.path.join("ClickPointsExamples", "PlantRoot", "plant_root.cdb"))
        self.window.JumpFrames(1)
        self.wait_for_image_load()

    def test_createMask(self):
        """ Test if creating a mask works """
        self.createInstance(os.path.join("ClickPointsExamples", "PlantRoot"))

        # switch interface on
        self.keyPress(Qt.Key_F2)
        self.keyPress(Qt.Key_P)
        self.keyPress(Qt.Key_2)

        # draw a line
        self.mouseDrag(200, 200, 250, 200)

        # save and check
        self.window.JumpFrames(1)
        self.wait_for_image_load()
        self.assertTrue(self.db.getMask(frame=0), "Mask was not created")

    def test_missingMask(self):
        """ Test if a mask is missing """
        self.createInstance(os.path.join("ClickPointsExamples", "PlantRoot"))

        # switch interface on
        self.keyPress(Qt.Key_F2)
        self.keyPress(Qt.Key_P)
        self.keyPress(Qt.Key_2)

        # draw something
        self.mouseClick(200, 200)

        # save and verify
        self.window.JumpFrames(1)
        self.wait_for_image_load()
        self.assertTrue(self.db.getMask(frame=0), "Mask was not created")

        # remove mask
        self.db.deleteMasks(frame=0)
        self.assertFalse(self.db.getMask(frame=0), "Mask was deleted")

        # go to the frame used and see if an error occurs
        self.window.JumpFrames(-1)
        self.wait_for_image_load()
        self.window.JumpFrames(-1)
        self.wait_for_image_load()
        # If the program can't cope with the deleted mask an error would occur

    def test_maskTypeSelectorKey(self):
        """ Test if the number keys can change the mask draw type """
        self.createInstance(os.path.join("ClickPointsExamples", "PlantRoot"))

        # switch interface on
        self.keyPress(Qt.Key_F2)
        self.keyPress(Qt.Key_P)

        # select color 1 by pressing 1
        self.keyPress(Qt.Key_1)
        self.assertEqual(self.window.GetModule("MaskHandler").active_draw_type.index, 0, "Draw Type selection by pressing 1 doesn't work")

        # select color 2 by pressing 2
        self.keyPress(Qt.Key_2)
        self.assertEqual(self.window.GetModule("MaskHandler").active_draw_type.index, 1, "Draw Type selection by pressing 2 doesn't work")

        # select color 3 by pressing 3
        #self.keyPress(Qt.Key_3)
        #self.assertEqual(self.window.GetModule("MaskHandler").active_draw_type.index, 2, "Draw Type selection by pressing 3 doesn't work")

    def test_maskTypeSelectorClick(self):
        """ Test if the buttons can change the mask draw type """
        self.createInstance(os.path.join("ClickPointsExamples", "PlantRoot"))

        # switch interface on
        self.keyPress(Qt.Key_F2)
        self.keyPress(Qt.Key_P)

        # click on first button
        self.mouseClick(-50, 20, coordinates="scene")
        self.assertEqual(self.window.GetModule("MaskHandler").active_draw_type.index, 0, "Draw Type selection by clicking button 1 doesn't work")

        # click on second button
        self.mouseClick(-50, 40, coordinates="scene")
        self.assertEqual(self.window.GetModule("MaskHandler").active_draw_type.index, 1, "Draw Type selection by clicking button 2 doesn't work")

        # click on third button
        #self.mouseClick(-50, 60, coordinates="scene")
        #self.assertEqual(self.window.GetModule("MaskHandler").active_draw_type.index, 2, "Draw Type selection by pressing 3 doesn't work")

    def test_brushSizeMask(self):
        """ Test if increasing and decreasing the brush size works """
        self.createInstance(os.path.join("ClickPointsExamples", "PlantRoot"))

        # wait for image to be loaded
        self.wait_for_image_load()

        # switch interface on
        self.keyPress(Qt.Key_F2)
        self.keyPress(Qt.Key_P)
        self.keyPress(Qt.Key_2)

        ''' Test size of normal circle '''

        # draw circle at 50 50
        self.mouseClick(250, 250)

        # change frame to save mask
        self.window.JumpFrames(1)
        self.wait_for_image_load()
        self.window.JumpFrames(-1)
        self.wait_for_image_load()

        # check size of circle
        im = self.db.getMask(frame=0).data
        self.assertEqual(np.sum(im == 1), 101, "Brush size does not match")

        ''' Test size of increased circle '''

        # increase brush size
        for i in range(3):
            self.keyPress(Qt.Key_Plus)

        # draw again circle at 50 50
        self.mouseClick(250, 250)

        # save mask
        self.window.JumpFrames(1)
        self.wait_for_image_load()
        self.window.JumpFrames(-1)
        self.wait_for_image_load()

        # check size of bigger circle
        im = self.db.getMask(frame=0).data
        self.assertEqual(np.sum(im == 1), 137, "Brush size increasing does not work")

        ''' Test size of decreased circle '''

        # delete circle
        self.keyPress(Qt.Key_1)
        self.mouseClick(250, 250)

        # decrease brush size
        for i in range(3):
            self.keyPress(Qt.Key_Minus)

        # draw again circle at 50 50
        self.keyPress(Qt.Key_2)
        self.mouseClick(250, 250)

        # save mask
        self.window.JumpFrames(1)
        self.wait_for_image_load()
        self.window.JumpFrames(-1)
        self.wait_for_image_load()

        # check size of smaller circle
        im = self.db.getMask(frame=0).data
        self.assertEqual(np.sum(im == 1), 101, "Brush size decreasing does not work")

    def test_colorPickerMask(self):
        """ Test using the color picker to select different colors """
        self.createInstance(os.path.join("ClickPointsExamples", "PlantRoot"))

        # switch interface on
        self.keyPress(Qt.Key_F2)
        self.keyPress(Qt.Key_P)

        # wait for image to be loaded
        self.wait_for_image_load()

        # draw circle at 50 50 with color 1
        self.keyPress(Qt.Key_1)
        self.mouseClick(250, 250)

        # draw circle at 100 50 with color 2
        self.keyPress(Qt.Key_2)
        self.mouseClick(450, 250)

        # draw circle at 150 50 with color 3
        self.keyPress(Qt.Key_3)
        self.mouseClick(350, 250)

        # move to first circle and pick the color, check if it is the right one
        self.mouseMove(250, 250)
        self.keyPress(Qt.Key_K)
        self.assertEqual(self.window.GetModule("MaskHandler").active_draw_type.index, 0, "Draw Type 0 selection by color picker doesn't work")

        # move to second circle and pick the color, check if it is the right one
        self.mouseMove(450, 250)
        self.keyPress(Qt.Key_K)
        self.assertEqual(self.window.GetModule("MaskHandler").active_draw_type.index, 1, "Draw Type 1 selection by color picker doesn't work")

        # move to third circle and pick the color, check if it is the right one
        #self.mouseMove(350, 250)
        #self.keyPress(Qt.Key_K)
        #self.assertEqual(self.window.GetModule("MaskHandler").active_draw_type.index, 2, "Draw Type 2 selection by color picker doesn't work")


if __name__ == '__main__':
    __path__ = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(__path__, 'log_'+__key__+'.txt')
    with open(log_file, "w") as f:
        runner = unittest.TextTestRunner(f)
        unittest.main(testRunner=runner)
