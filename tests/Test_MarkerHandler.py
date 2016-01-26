__key__ = "MODULE_MARKER"
__testname__ = "Marker Handler"

import sys
import os
import unittest
import time
from PyQt4.QtGui import QApplication
from PyQt4.QtTest import QTest
from PyQt4.QtCore import Qt
from PyQt4 import QtCore, QtGui

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import ClickPoints

app = QApplication(sys.argv)

class Test_MarkerHandler(unittest.TestCase):

    def createInstance(self, path, database_file):
        """Create the GUI """
        self.test_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", path))
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
        self.window.show()

    def test_jumpframes(self):
        """Test the GUI in its default state"""
        self.createInstance(r"ClickPointsExamples\TweezerVideos\002", "JumpFrames.db")
        self.window.JumpFrames(20)
        self.assertFalse(os.path.exists(self.database_path))

    def test_createMarker(self):
        """ Test if creating marker works """
        self.createInstance(r"ClickPointsExamples\TweezerVideos\002", "CreateMarker.db")
        QTest.keyPress(self.window, Qt.Key_F2)
        self.assertEqual(len(self.window.GetModule("MarkerHandler").points), 0, "At the beginning already some markers where present")

        QTest.mouseClick(self.window.view.viewport(), Qt.LeftButton, pos=self.window.view.mapFromOrigin(50, 50), delay=10)
        self.assertEqual(len(self.window.GetModule("MarkerHandler").points), 1, "Marker wasn't added by clicking")

    def test_moveMarker(self):
        """ Test if moving marker works """
        self.createInstance(r"ClickPointsExamples\TweezerVideos\002", "MoveMarker.db")
        QTest.keyPress(self.window, Qt.Key_F2)
        self.assertEqual(len(self.window.GetModule("MarkerHandler").points), 0, "At the beginning already some markers where present")

        QTest.mouseClick(self.window.view.viewport(), Qt.LeftButton, pos=self.window.view.mapFromOrigin(50, 50), delay=10)
        self.assertEqual(len(self.window.GetModule("MarkerHandler").points), 1, "Marker wasn't added by clicking")

        # Test moving the marker
        QTest.mousePress(self.window.view.viewport(), Qt.LeftButton, pos=self.window.view.mapFromOrigin(50, 50), delay=10)
#        QTest.mouseMove(self.window.view.viewport(), pos=self.window.view.mapFromOrigin(50, 100), delay=1000)
        QTest.mouseRelease(self.window.view.viewport(), Qt.LeftButton, pos=self.window.view.mapFromOrigin(50, 100), delay=10)
        time.sleep(1)
        # TODO implement test correctly

    def test_deleteMarker(self):
        """ Test if deleting marker works """
        self.createInstance(r"ClickPointsExamples\TweezerVideos\002", "DeleteMarker.db")
        QTest.keyPress(self.window, Qt.Key_F2)
        self.assertEqual(len(self.window.GetModule("MarkerHandler").points), 0, "At the beginning already some markers where present")

        QTest.mouseClick(self.window.view.viewport(), Qt.LeftButton, pos=self.window.view.mapFromOrigin(50, 50), delay=10)
        self.assertEqual(len(self.window.GetModule("MarkerHandler").points), 1, "Marker wasn't added by clicking")

        # Test deletion of marker
        QTest.mouseClick(self.window.view.viewport(), Qt.RightButton, pos=self.window.view.mapFromOrigin(50, 50), delay=10)
        self.assertEqual(len(self.window.GetModule("MarkerHandler").points), 0, "Marker deletion didn't work")

if __name__ == '__main__':
    log_file = 'log_'+__key__+'.txt'
    with open(log_file, "w") as f:
        runner = unittest.TextTestRunner(f)
        unittest.main(testRunner=runner)
