__key__ = "MODULE_MASK"
__testname__ = "Mask Handler"

import sys
import os
import unittest
from PyQt4.QtGui import QApplication
from PyQt4.QtTest import QTest
from PyQt4.QtCore import Qt
from PIL import Image
import imageio
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import ClickPoints

app = QApplication(sys.argv)

class Test_MaskHandler(unittest.TestCase):

    def createInstance(self, path, database_file, mask_filename):
        global __path__
        """Create the GUI """
        if "__path__" in globals():
            self.test_path = os.path.abspath(os.path.normpath(os.path.join(__path__, "..", "..", "..", path)))
        else:
            __path__ = os.path.dirname(__file__)
            self.test_path = os.path.abspath(os.path.normpath(os.path.join(__path__, "..", "..", "..", path)))
        self.database_file = database_file
        self.mask_filename = mask_filename
        print("Test Path", self.test_path)
        sys.argv = [__file__, r"-srcpath="+self.test_path, r"-database_file="+self.database_file, r"-maskname_tag="+mask_filename]
        print(sys.argv)
        config = ClickPoints.LoadConfig()
        for addon in config.addons:
            with open(addon + ".py") as f:
                code = compile(f.read(), addon + ".py", 'exec')
                exec(code)
        self.database_path = os.path.join(self.test_path, database_file)
        if os.path.exists(self.database_path):
            os.remove(self.database_path)
        self.window = ClickPoints.ClickPointsWindow(config)
        self.window.show()

    def test_loadMasks(self):
        """ Load a database with masks """
        self.createInstance(os.path.join("ClickPointsExamples", "Dronpa"), "clickpoints.db", "_loadMask_mask.png")
        self.window.JumpFrames(1)

    def test_createMask(self):
        """ Test if creating a mask works """
        self.createInstance(os.path.join("ClickPointsExamples", "Dronpa"), "CreateMask.db", "_createMask_mask.png")
        path = os.path.join("mask", "1-0min_tif"+self.mask_filename)
        if os.path.exists(path):
            print("Removing old mask")
            os.remove(path)
        QTest.keyPress(self.window, Qt.Key_F2)
        QTest.mousePress(self.window.view.viewport(), Qt.LeftButton, pos=self.window.view.mapFromOrigin(50, 50), delay=10)
        QTest.mouseMove(self.window.view.viewport(), pos=self.window.view.mapFromOrigin(50, 100), delay=10)
        QTest.mouseRelease(self.window.view.viewport(), Qt.LeftButton, pos=self.window.view.mapFromOrigin(50, 100), delay=10)

        self.window.JumpFrames(1)
        self.assertTrue(os.path.exists(path), "Mask was not created")

    def test_missingMask(self):
        """ Test if a mask is missing """
        self.createInstance(os.path.join("ClickPointsExamples", "Dronpa"), "missingMask.db", "_missingMask_mask.png")

        path = os.path.join("mask", "1-10min_tif"+self.mask_filename)
        print(path)
        if os.path.exists(path):
            print("Removing old mask")
            os.remove(path)

        self.window.JumpFrames(1)

        QTest.keyPress(self.window, Qt.Key_F2)
        QTest.mousePress(self.window.view.viewport(), Qt.LeftButton, pos=self.window.view.mapFromOrigin(50, 50), delay=10)
        QTest.mouseMove(self.window.view.viewport(), pos=self.window.view.mapFromOrigin(50, 100), delay=10)
        QTest.mouseRelease(self.window.view.viewport(), Qt.LeftButton, pos=self.window.view.mapFromOrigin(50, 100), delay=10)

        self.window.JumpFrames(1)
        self.assertTrue(os.path.exists(path), "Mask was not created")

        os.remove(path)
        self.assertFalse(os.path.exists(path), "Mask was deleted")

        self.window.JumpFrames(-1)
        self.window.JumpFrames(-1)
        # If the program can't cope with the deleted mask an error would occur

    def test_maskTypeSelectorKey(self):
        """ Test if the number keys can change the mask draw type """
        self.createInstance(os.path.join("ClickPointsExamples", "Dronpa"), "masktypeSelector.db", "_maskTypeSelectorKey_mask.png")

        QTest.keyPress(self.window, Qt.Key_F2)
        QTest.keyPress(self.window, Qt.Key_1)
        self.assertEqual(self.window.GetModule("MaskHandler").active_draw_type, 0, "Draw Type selection by pressing 1 doesn't work")
        QTest.keyPress(self.window, Qt.Key_2)
        self.assertEqual(self.window.GetModule("MaskHandler").active_draw_type, 1, "Draw Type selection by pressing 2 doesn't work")
        QTest.keyPress(self.window, Qt.Key_3)
        self.assertEqual(self.window.GetModule("MaskHandler").active_draw_type, 2, "Draw Type selection by pressing 3 doesn't work")

    def test_maskTypeSelectorClick(self):
        """ Test if the buttons can change the mask draw type """
        self.createInstance(os.path.join("ClickPointsExamples", "Dronpa"), "masktypeSelector.db", "_maskTypeSelectorClick_mask.png")

        QTest.keyPress(self.window, Qt.Key_F2)
        QTest.mouseClick(self.window.view.viewport(), Qt.LeftButton, pos=self.window.view.mapFromScene(self.window.local_scene.width()-50, 20), delay=10)
        self.assertEqual(self.window.GetModule("MaskHandler").active_draw_type, 0, "Draw Type selection by clicking button 1 doesn't work")
        QTest.mouseClick(self.window.view.viewport(), Qt.LeftButton, pos=self.window.view.mapFromScene(self.window.local_scene.width()-50, 40), delay=10)
        self.assertEqual(self.window.GetModule("MaskHandler").active_draw_type, 1, "Draw Type selection by pressing 2 doesn't work")
        QTest.mouseClick(self.window.view.viewport(), Qt.LeftButton, pos=self.window.view.mapFromScene(self.window.local_scene.width()-50, 60), delay=10)
        self.assertEqual(self.window.GetModule("MaskHandler").active_draw_type, 2, "Draw Type selection by pressing 3 doesn't work")

    def test_brushSizeMask(self):
        """ Test if increasing and decreasing the brush size works """
        self.createInstance(os.path.join("ClickPointsExamples", "Dronpa"), "brushSizeMask.db", "_bruchSizeMask_mask.png")

        path = os.path.join("mask", "1-0min_tif"+self.mask_filename)
        QTest.keyPress(self.window, Qt.Key_F2)

        QTest.mouseClick(self.window.view.viewport(), Qt.LeftButton, pos=self.window.view.mapFromOrigin(50, 50), delay=10)

        self.window.JumpFrames(1)
        im = np.asarray(Image.open(path))
        self.assertEqual(np.sum(im == 1), 101, "Brush size does not match")

        self.window.JumpFrames(-1)
        QTest.keyPress(self.window, Qt.Key_Plus)
        QTest.keyPress(self.window, Qt.Key_Plus)
        QTest.keyPress(self.window, Qt.Key_Plus)
        QTest.mouseClick(self.window.view.viewport(), Qt.LeftButton, pos=self.window.view.mapFromOrigin(50, 50), delay=10)
        self.window.JumpFrames(1)

        im = np.asarray(Image.open(path))
        self.assertEqual(np.sum(im == 1), 137, "Brush size increasing does not work")

        self.window.JumpFrames(-1)
        QTest.keyPress(self.window, Qt.Key_1)
        QTest.mouseClick(self.window.view.viewport(), Qt.LeftButton, pos=self.window.view.mapFromOrigin(50, 50), delay=10)
        QTest.keyPress(self.window, Qt.Key_2)
        QTest.keyPress(self.window, Qt.Key_Minus)
        QTest.keyPress(self.window, Qt.Key_Minus)
        QTest.keyPress(self.window, Qt.Key_Minus)
        QTest.mouseClick(self.window.view.viewport(), Qt.LeftButton, pos=self.window.view.mapFromOrigin(50, 50), delay=10)
        self.window.JumpFrames(1)

        im = np.asarray(Image.open(path))
        self.assertEqual(np.sum(im == 1), 101, "Brush size decreaseing does not work")

    def test_colorPickerMask(self):
        """ Test using the color picker to select different colors """
        self.createInstance(os.path.join("ClickPointsExamples", "Dronpa"), "colorPickerMask.db", "_colorPickerMask_mask.png")

        QTest.keyPress(self.window, Qt.Key_F2)
        QTest.keyPress(self.window, Qt.Key_1)
        QTest.mouseClick(self.window.view.viewport(), Qt.LeftButton, pos=self.window.view.mapFromOrigin(50, 50), delay=10)
        QTest.keyPress(self.window, Qt.Key_2)
        QTest.mouseClick(self.window.view.viewport(), Qt.LeftButton, pos=self.window.view.mapFromOrigin(100, 50), delay=10)
        QTest.keyPress(self.window, Qt.Key_3)
        QTest.mouseClick(self.window.view.viewport(), Qt.LeftButton, pos=self.window.view.mapFromOrigin(150, 50), delay=10)

        QTest.mouseMove(self.window.view.viewport(), pos=self.window.view.mapFromOrigin(50, 50), delay=10)
        QTest.keyPress(self.window, Qt.Key_K)
        self.assertEqual(self.window.GetModule("MaskHandler").active_draw_type, 0, "Draw Type selection by color picker doesn't work")

        QTest.mouseMove(self.window.view.viewport(), pos=self.window.view.mapFromOrigin(100, 50), delay=10)
        QTest.keyPress(self.window, Qt.Key_K)
        self.assertEqual(self.window.GetModule("MaskHandler").active_draw_type, 1, "Draw Type selection by color picker doesn't work")

        QTest.mouseMove(self.window.view.viewport(), pos=self.window.view.mapFromOrigin(150, 50), delay=10)
        QTest.keyPress(self.window, Qt.Key_K)
        self.assertEqual(self.window.GetModule("MaskHandler").active_draw_type, 2, "Draw Type selection by color picker doesn't work")

    def test_colorPaletteMask(self):
        """ Test if increasing and decreasing the brush size works """
        self.createInstance(os.path.join("ClickPointsExamples", "Dronpa"), "colorPaletteMask.db", "_colorPalette_mask.png")

        path = os.path.join("mask", "1-0min_tif"+self.mask_filename)
        QTest.keyPress(self.window, Qt.Key_F2)
        QTest.keyPress(self.window, Qt.Key_2)
        QTest.mouseClick(self.window.view.viewport(), Qt.LeftButton, pos=self.window.view.mapFromOrigin(50, 50), delay=10)
        QTest.keyPress(self.window, Qt.Key_3)
        QTest.mouseClick(self.window.view.viewport(), Qt.LeftButton, pos=self.window.view.mapFromOrigin(100, 50), delay=10)
        QTest.keyPress(self.window, Qt.Key_4)
        QTest.mouseClick(self.window.view.viewport(), Qt.LeftButton, pos=self.window.view.mapFromOrigin(150, 50), delay=10)

        self.window.JumpFrames(1)

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
