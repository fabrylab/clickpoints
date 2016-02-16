__key__ = "MODULE_MASK"
__testname__ = "Mask Handler"

import sys
import os
import unittest
from PIL import Image
import imageio
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from BaseTest import BaseTest

from PyQt4.QtCore import Qt

class Test_MaskHandler(unittest.TestCase, BaseTest):

    def tearDown(self):
        BaseTest.tearDown(self)

    def test_loadMasks(self):
        """ Load a database with masks """
        self.createInstance(os.path.join("ClickPointsExamples", "Dronpa"), "clickpoints.db", "mask")
        self.window.JumpFrames(1)

    def test_createMask(self):
        """ Test if creating a mask works """
        self.createInstance(os.path.join("ClickPointsExamples", "Dronpa"))
        path = os.path.join(self.mask_folder, "1-0min_tif"+"_mask.png")
        print(path)

        # switch interface on
        self.keyPress(Qt.Key_F2)

        # draw a line
        self.mouseDrag(50, 50, 50, 100)

        # save and check
        self.window.JumpFrames(1)
        self.assertTrue(os.path.exists(path), "Mask was not created")

    def test_missingMask(self):
        """ Test if a mask is missing """
        self.createInstance(os.path.join("ClickPointsExamples", "Dronpa"))
        path = os.path.join(self.mask_folder, "1-0min_tif"+"_mask.png")

        # switch interface on
        self.keyPress(Qt.Key_F2)

        # draw something
        self.mouseClick(50, 50)

        # save and verify
        self.window.JumpFrames(1)
        self.assertTrue(os.path.exists(path), "Mask was not created")

        # remove mask
        os.remove(path)
        self.assertFalse(os.path.exists(path), "Mask was deleted")

        # go to the frame used and see if an error occurs
        self.window.JumpFrames(-1)
        self.window.JumpFrames(-1)
        # If the program can't cope with the deleted mask an error would occur

    def test_maskTypeSelectorKey(self):
        """ Test if the number keys can change the mask draw type """
        self.createInstance(os.path.join("ClickPointsExamples", "Dronpa"))

        # switch interface on
        self.keyPress(Qt.Key_F2)

        # select color 1 by pressing 1
        self.keyPress(Qt.Key_1)
        self.assertEqual(self.window.GetModule("MaskHandler").active_draw_type, 0, "Draw Type selection by pressing 1 doesn't work")

        # select color 2 by pressing 2
        self.keyPress(Qt.Key_2)
        self.assertEqual(self.window.GetModule("MaskHandler").active_draw_type, 1, "Draw Type selection by pressing 2 doesn't work")

        # select color 3 by pressing 3
        self.keyPress(Qt.Key_3)
        self.assertEqual(self.window.GetModule("MaskHandler").active_draw_type, 2, "Draw Type selection by pressing 3 doesn't work")

    def test_maskTypeSelectorClick(self):
        """ Test if the buttons can change the mask draw type """
        self.createInstance(os.path.join("ClickPointsExamples", "Dronpa"))

        # switch interface on
        self.keyPress(Qt.Key_F2)

        # click on first button
        self.mouseClick(-50, 20, coordinates="scene")
        self.assertEqual(self.window.GetModule("MaskHandler").active_draw_type, 0, "Draw Type selection by clicking button 1 doesn't work")

        # click on second button
        self.mouseClick(-50, 40, coordinates="scene")
        self.assertEqual(self.window.GetModule("MaskHandler").active_draw_type, 1, "Draw Type selection by pressing 2 doesn't work")

        # click on third button
        self.mouseClick(-50, 60, coordinates="scene")
        self.assertEqual(self.window.GetModule("MaskHandler").active_draw_type, 2, "Draw Type selection by pressing 3 doesn't work")

    def test_brushSizeMask(self):
        """ Test if increasing and decreasing the brush size works """
        self.createInstance(os.path.join("ClickPointsExamples", "Dronpa"))
        path = os.path.join(self.mask_folder, "1-0min_tif"+"_mask.png")

        # switch interface on
        self.keyPress(Qt.Key_F2)

        ''' Test size of normal circle '''

        # draw circle at 50 50
        self.mouseClick(50, 50)

        # change frame to save mask
        self.window.JumpFrames(1)
        self.window.JumpFrames(-1)

        # check size of circle
        im = np.asarray(Image.open(path))
        self.assertEqual(np.sum(im == 1), 101, "Brush size does not match")

        ''' Test size of increased circle '''

        # increase brush size
        for i in range(3):
            self.keyPress(Qt.Key_Plus)

        # draw again circle at 50 50
        self.mouseClick(50, 50)

        # save mask
        self.window.JumpFrames(1)
        self.window.JumpFrames(-1)

        # check size of bigger circle
        im = np.asarray(Image.open(path))
        self.assertEqual(np.sum(im == 1), 137, "Brush size increasing does not work")

        ''' Test size of decreased circle '''

        # delete circle
        self.keyPress(Qt.Key_1)
        self.mouseClick(50, 50)

        # decrease brush size
        for i in range(3):
            self.keyPress(Qt.Key_Minus)

        # draw again circle at 50 50
        self.keyPress(Qt.Key_2)
        self.mouseClick(50, 50)

        # save mask
        self.window.JumpFrames(1)
        self.window.JumpFrames(-1)

        # check size of smaller circle
        im = np.asarray(Image.open(path))
        self.assertEqual(np.sum(im == 1), 101, "Brush size decreasing does not work")

    def test_colorPickerMask(self):
        """ Test using the color picker to select different colors """
        self.createInstance(os.path.join("ClickPointsExamples", "Dronpa"))

        # switch interface on
        self.keyPress(Qt.Key_F2)

        # draw circle at 50 50 with color 1
        self.keyPress(Qt.Key_1)
        self.mouseClick(50, 50)

        # draw circle at 100 50 with color 2
        self.keyPress(Qt.Key_2)
        self.mouseClick(100, 50)

        # draw circle at 150 50 with color 3
        self.keyPress(Qt.Key_3)
        self.mouseClick(150, 50)

        # move to first circle and pick the color, check if it is the right one
        self.mouseMove(50, 50)
        self.keyPress(Qt.Key_K)
        self.assertEqual(self.window.GetModule("MaskHandler").active_draw_type, 0, "Draw Type 0 selection by color picker doesn't work")

        # move to second circle and pick the color, check if it is the right one
        self.mouseMove(100, 50)
        self.keyPress(Qt.Key_K)
        self.assertEqual(self.window.GetModule("MaskHandler").active_draw_type, 1, "Draw Type 1 selection by color picker doesn't work")

        # move to third circle and pick the color, check if it is the right one
        self.mouseMove(150, 50)
        self.keyPress(Qt.Key_K)
        self.assertEqual(self.window.GetModule("MaskHandler").active_draw_type, 2, "Draw Type 2 selection by color picker doesn't work")

    def test_colorPaletteMask(self):
        """ Test if increasing and decreasing the brush size works """
        self.createInstance(os.path.join("ClickPointsExamples", "Dronpa"))
        path = os.path.join(self.mask_folder, "1-0min_tif"+"_mask.png")

        # switch interface on
        self.keyPress(Qt.Key_F2)

        # draw circle at 50 50 with color 2
        self.keyPress(Qt.Key_2)
        self.mouseClick(50, 50)

        # draw circle at 100 50 with color 3
        self.keyPress(Qt.Key_3)
        self.mouseClick(100, 50)

        # draw circle at 150 50 with color 4
        self.keyPress(Qt.Key_4)
        self.mouseClick(150, 50)

        # save mask
        self.window.JumpFrames(1)

        # read mask and check colors
        im2 = imageio.imread(path)[:, :, :3]
        self.assertEqual(im2[50, 50, :].tolist(), [255, 255, 255], "Palette for color 1 does not match")
        self.assertEqual(im2[50, 100, :].tolist(), [230, 180, 180], "Palette for color 2 does not match")
        self.assertEqual(im2[50, 150, :].tolist(), [210, 210, 140], "Palette for color 3 does not match")


if __name__ == '__main__':
    __path__ = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(__path__, 'log_'+__key__+'.txt')
    with open(log_file, "w") as f:
        runner = unittest.TextTestRunner(f)
        unittest.main(testRunner=runner)
