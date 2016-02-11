__key__ = "MODULE_MASK"
__testname__ = "Mask Handler"

import sys
import os
import shutil
import unittest
from PyQt4.QtGui import QApplication
from PyQt4.QtTest import QTest
from PyQt4.QtCore import Qt
from PyQt4 import QtCore
from PyQt4 import QtGui
from PIL import Image
import imageio
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import ClickPoints

app = QApplication(sys.argv)

def createInstance(self, path, database_file, mask_foldername):
    global __path__
    """ Create the GUI """
    if "__path__" in globals():
        self.test_path = os.path.abspath(os.path.normpath(os.path.join(__path__, "..", "..", "..", path)))
    else:
        __path__ = os.path.dirname(__file__)
        self.test_path = os.path.abspath(os.path.normpath(os.path.join(__path__, "..", "..", "..", path)))
    self.database_file = database_file
    self.mask_folder = mask_foldername

    self.database_path = os.path.join(self.test_path, database_file)
    self.mask_folder_path = os.path.join(self.test_path, mask_foldername)

    print("Test Path", self.test_path)
    sys.argv = [__file__, r"-srcpath="+self.test_path, r"-database_file="+self.database_file, r"-outputpath_mask="+mask_foldername]
    print(sys.argv)
    config = ClickPoints.LoadConfig()
    for addon in config.addons:
        with open(addon + ".py") as f:
            code = compile(f.read(), addon + ".py", 'exec')
            exec(code)


    self.database_already_existed = os.path.exists(self.database_path)
    self.maskfolder_already_existed = os.path.exists(self.mask_folder_path)

    self.window = ClickPoints.ClickPointsWindow(config)

def mouseMove(self, x, y, delay=10, coordinates="origin"):
    v = self.window.view
    w = v.viewport()
    if coordinates == "origin":
        pos = self.window.view.mapFromOrigin(x, y)
    elif coordinates == "scene":
        pos = self.window.view.mapFromScene(x, y)
    event = QtGui.QMouseEvent(QtCore.QEvent.MouseMove, pos, w.mapToGlobal(pos), Qt.NoButton, Qt.NoButton, Qt.NoModifier)
    QApplication.postEvent(w, event)
    QTest.qWait(delay)

def mouseDrag(self, x, y, x2, y2, button=None, delay=10, coordinates="origin"):
    if button is None:
        button = Qt.LeftButton
    v = self.window.view
    w = v.viewport()
    if coordinates == "origin":
        pos = self.window.view.mapFromOrigin(x, y)
        pos2 = self.window.view.mapFromOrigin(x2, y2)
    elif coordinates == "scene":
        pos = self.window.view.mapFromScene(x, y)
        pos2 = self.window.view.mapFromScene(x2, y2)
    event = QtGui.QMouseEvent(QtCore.QEvent.MouseMove, pos, w.mapToGlobal(pos), button, button, Qt.NoModifier)
    QApplication.postEvent(w, event)
    QTest.qWait(delay)
    event = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress, pos, w.mapToGlobal(pos), button, button, Qt.NoModifier)
    QApplication.postEvent(w, event)
    QTest.qWait(delay)
    event = QtGui.QMouseEvent(QtCore.QEvent.MouseMove, pos2, w.mapToGlobal(pos2), button, button, Qt.NoModifier)
    QApplication.postEvent(w, event)
    QTest.qWait(delay)
    event = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonRelease, pos2, w.mapToGlobal(pos2), button, button, Qt.NoModifier)
    QApplication.postEvent(w, event)
    QTest.qWait(delay)

def mouseClick(self, x, y, button=None, delay=10, coordinates="origin"):
    if button is None:
        button = Qt.LeftButton
    if coordinates == "origin":
        pos = self.window.view.mapFromOrigin(x, y)
    elif coordinates == "scene":
        if x < 0:
            x = self.window.local_scene.width()+x
        pos = self.window.view.mapFromScene(x, y)
    QTest.mouseClick(self.window.view.viewport(), button, pos=pos, delay=delay)

def keyPress(self, key, delay=10):
    QTest.keyPress(self.window, key, delay=delay)

class Test_MaskHandler(unittest.TestCase):

    def setUp(self):
        self.createInstance = lambda *args, **kwargs: createInstance(self, *args, **kwargs)
        self.mouseMove = lambda *args, **kwargs: mouseMove(self, *args, **kwargs)
        self.mouseDrag = lambda *args, **kwargs: mouseDrag(self, *args, **kwargs)
        self.mouseClick = lambda *args, **kwargs: mouseClick(self, *args, **kwargs)
        self.keyPress = lambda *args, **kwargs: keyPress(self, *args, **kwargs)
        pass

    def tearDown(self):
        # close window
        QTest.qWait(100)
        self.window.close()
        QTest.qWait(100)
        self.window.data_file.db.close()

        # remove database
        if os.path.exists(self.database_path) and not self.database_already_existed:
            os.remove(self.database_path)
        if os.path.exists(self.mask_folder_path) and not self.maskfolder_already_existed:
            shutil.rmtree(self.mask_folder_path)

    def test_loadMasks(self):
        """ Load a database with masks """
        self.createInstance(os.path.join("ClickPointsExamples", "Dronpa"), "clickpoints.db", "mask")
        self.window.JumpFrames(1)

    def test_createMask(self):
        """ Test if creating a mask works """
        self.createInstance(os.path.join("ClickPointsExamples", "Dronpa"), "CreateMask.db", "mask_createMask")
        path = os.path.join(self.mask_folder, "1-0min_tif"+"_mask.png")

        # switch interface on
        self.keyPress(Qt.Key_F2)

        # draw a line
        self.mouseDrag(50, 50, 50, 100)

        # save and check
        self.window.JumpFrames(1)
        self.assertTrue(os.path.exists(path), "Mask was not created")

    def test_missingMask(self):
        """ Test if a mask is missing """
        self.createInstance(os.path.join("ClickPointsExamples", "Dronpa"), "missingMask.db", "mask_missingMask")
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
        self.createInstance(os.path.join("ClickPointsExamples", "Dronpa"), "masktypeSelector.db", "mask_maskTypeSelectorKey")

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
        self.createInstance(os.path.join("ClickPointsExamples", "Dronpa"), "masktypeSelector.db", "mask_maskTypeSelectorClick")

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
        self.createInstance(os.path.join("ClickPointsExamples", "Dronpa"), "brushSizeMask.db", "mask_bruchSizeMask")
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
        self.createInstance(os.path.join("ClickPointsExamples", "Dronpa"), "colorPickerMask.db", "mask_colorPickerMask")

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
        self.createInstance(os.path.join("ClickPointsExamples", "Dronpa"), "colorPaletteMask.db", "mask_colorPalette")
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
