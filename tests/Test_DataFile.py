__key__ = "DATAFILE"
__testname__ = "Data File"

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

class Test_DataFile(unittest.TestCase):

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

    def test_createDatabase(self):
        """ Test if creating the database on demand works """
        self.createInstance(os.path.join("ClickPointsExamples", "TweezerVideos", "002"), "CreateDatabase.db")
        QTest.keyPress(self.window, Qt.Key_F2)
        self.assertEqual(len(self.window.GetModule("MarkerHandler").points), 0, "At the beginning already some markers where present")
        self.assertFalse(os.path.exists(self.database_path), "Database file already present.")

        QTest.mouseClick(self.window.view.viewport(), Qt.LeftButton, pos=self.window.view.mapFromOrigin(50, 50), delay=10)
        self.assertEqual(len(self.window.GetModule("MarkerHandler").points)+len(self.window.GetModule("MarkerHandler").tracks), 1, "Marker wasn't added by clicking")

        self.assertFalse(os.path.exists(self.database_path), "Database file already present.")

        # Test saving database on frame change
        QTest.keyPress(self.window, Qt.Key_Right, delay=10)
        QTest.keyPress(self.window, Qt.Key_Right, delay=10)
        self.assertTrue(os.path.exists(self.database_path), "Database file was not created.")

if __name__ == '__main__':
    log_file = 'log_'+__key__+'.txt'
    with open(log_file, "w") as f:
        runner = unittest.TextTestRunner(f)
        unittest.main(testRunner=runner)
