__key__ = "DATAFILE"
__testname__ = "Data File"

import sys
import os
import unittest
from PyQt4.QtCore import Qt

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from BaseTest import BaseTest

class Test_DataFile(unittest.TestCase, BaseTest):

    def tearDown(self):
        BaseTest.tearDown(self)

    def test_createDatabase(self):
        """ Test if creating the database on demand works """
        self.createInstance(os.path.join("ClickPointsExamples", "TweezerVideos", "002"))

        # switch interface on
        self.keyPress(Qt.Key_F2)

        # check if no marker is present
        self.assertEqual(len(self.window.GetModule("MarkerHandler").points), 0, "At the beginning already some markers where present")
        self.assertFalse(os.path.exists(self.database_path), "Database file already present.")

        # add a marker, and check if it exists
        self.mouseClick(50, 50)
        self.assertEqual(len(self.window.GetModule("MarkerHandler").points)+len(self.window.GetModule("MarkerHandler").tracks), 1, "Marker wasn't added by clicking")

        # the database should not exist at this point
        self.assertFalse(os.path.exists(self.database_path), "Database file already present.")

        # Test saving database
        self.window.save()
        self.assertTrue(os.path.exists(self.database_path), "Database file was not created.")

if __name__ == '__main__':
    __path__ = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(__path__, 'log_'+__key__+'.txt')
    with open(log_file, "w") as f:
        runner = unittest.TextTestRunner(f)
        unittest.main(testRunner=runner)
