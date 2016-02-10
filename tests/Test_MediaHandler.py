__key__ = "MEDIA_HANDLER"
__testname__ = "Media Handler"

import sys
import os
import unittest
import time
from PyQt4.QtGui import QApplication
from PyQt4.QtTest import QTest
from PyQt4.QtCore import Qt
from PyQt4 import QtCore, QtGui
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import ClickPoints

app = QApplication(sys.argv)

class Test_MediaHandler(unittest.TestCase):

    def createInstance(self, path, database_file):
        global __path__
        """Create the GUI """
        if "__path__" in globals():
            self.test_path = os.path.abspath(os.path.normpath(os.path.join(__path__, "..", "..", "..", path)))
        else:
            __path__ = os.path.dirname(__file__)
            self.test_path = os.path.abspath(os.path.normpath(os.path.join(__path__, "..", "..", "..", path)))
        self.database_file = database_file
        print("Test Path", self.test_path)
        sys.argv = [__file__, r"-srcpath="+self.test_path, r"-database_file="+self.database_file]
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

    def test_loadImages(self):
        """ Open an image """
        self.createInstance(os.path.join("ClickPointsExamples", "TweezerVideos", "002", "frame0000.jpg"), "loadImages.db")
        self.assertEqual(len(self.window.media_handler.id_lookup), 68, "Not all images loaded")

    def test_loadFolder(self):
        """ Open a folder """
        self.createInstance(os.path.join("ClickPointsExamples", "TweezerVideos", "002"), "loadFolder.db")
        self.assertEqual(len(self.window.media_handler.id_lookup), 68, "Not all images loaded")

    def test_loadFolderSlash(self):
        """ Open a folder ending with a slash """
        self.createInstance(os.path.join("ClickPointsExamples", "TweezerVideos", "002")+os.path.sep, "loadFolderSlash.db")
        self.assertEqual(len(self.window.media_handler.id_lookup), 68, "Not all images loaded")

    def test_loadFolderRecursive(self):
        """ Open a folder containing two folders """
        self.createInstance(os.path.join("ClickPointsExamples", "TweezerVideos"), "loadFolderRecursive.db")
        self.assertEqual(len(self.window.media_handler.id_lookup), 68+68, "Not all images in two folders loaded")

    def test_loadFolderVideos(self):
        """ Open a folder containing two videos """
        self.createInstance(os.path.join("ClickPointsExamples", "BirdAttack"), "loadFolderVideos.db")
        self.assertEqual(len(self.window.media_handler.id_lookup), 569, "Didn't load two videos properly")

    def test_loadVideo(self):
        """ Open a video """
        self.createInstance(os.path.join("ClickPointsExamples", "BirdAttack", "attack1.avi"), "loadVideo.db")
        self.assertEqual(len(self.window.media_handler.id_lookup), 206, "Didn't load video properly")

    def test_loadTiff(self):
        """ Open a video """
        self.createInstance(os.path.join("ClickPointsExamples", "Dronpa"), "loadTiff.db")
        self.assertEqual(len(self.window.media_handler.id_lookup), 6, "Didn't load tiff properly")
        self.assertEqual(self.window.ImageDisplay.image.shape, (1024, 1024, 3))
        self.assertTrue(8 < np.mean(self.window.ImageDisplay.image) < 128)

if __name__ == '__main__':
    __path__ = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(__path__, 'log_'+__key__+'.txt')
    with open(log_file, "w") as f:
        runner = unittest.TextTestRunner(f)
        unittest.main(testRunner=runner)
