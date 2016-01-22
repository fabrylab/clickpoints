# vim: set fileencoding=utf-8 :
# $Header:  $
#
# Copyright 2011 Voom, Inc.
#
# This file is part of the Voom PyQt QTest Example.
# See http://www.voom.net/pyqt-qtest-example/ for documentation.
#
# PyQt QTest Example is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyQt QTest Example is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PyQt QTest Example.  If not, see <http://www.gnu.org/licenses/>.

"""
Test the margarita mixer GUI.
"""

__author__ = "John McGehee, http://johnnado.com/"
__version__ = "$Revision: 1.1 $"
__date__ = "$Date: 2015/07/30 $"
__copyright__ = "Copyright 2011 Voom, Inc."

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

class ClickPointsTest(unittest.TestCase):
    '''Test the margarita mixer GUI'''
    def setUp(self):
        '''Create the GUI'''
        self.test_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", r"ClickPointsExamples\TweezerVideos\002"))
        print("Test Path", self.test_path)
        sys.argv = [sys.argv[1], r"-srcpath="+self.test_path]
        print(sys.argv)
        config = ClickPoints.LoadConfig()
        for addon in config.addons:
            with open(addon + ".py") as f:
                code = compile(f.read(), addon + ".py", 'exec')
                exec(code)
        self.database_path = os.path.join(self.test_path, "clickpoints.db")
        if os.path.exists(self.database_path):
            print("Remove:", self.database_path)
            os.remove(self.database_path)
        self.window = ClickPoints.ClickPointsWindow(config)
        self.window.show()

    def test_jumpframes(self):
        '''Test the GUI in its default state'''
        self.window.JumpFrames(20)
        self.assertFalse(os.path.exists(self.database_path))

    def test_createMarker(self):
        """ Test if creating marker works """
        QTest.keyPress(self.window, Qt.Key_F2)
        self.assertEqual(len(self.window.GetModule("MarkerHandler").points), 0, "At the beginning already some markers where present")

        QTest.mouseClick(self.window.view.viewport(), Qt.LeftButton, pos=self.window.view.mapFromOrigin(50, 50), delay=10)
        self.assertEqual(len(self.window.GetModule("MarkerHandler").points), 1, "Marker wasn't added by clicking")

    def test_moveMarker(self):
        """ Test if moving marker works """
        QTest.keyPress(self.window, Qt.Key_F2)
        self.assertEqual(len(self.window.GetModule("MarkerHandler").points), 0, "At the beginning already some markers where present")

        QTest.mouseClick(self.window.view.viewport(), Qt.LeftButton, pos=self.window.view.mapFromOrigin(50, 50), delay=10)
        self.assertEqual(len(self.window.GetModule("MarkerHandler").points), 1, "Marker wasn't added by clicking")

        # Test moving the marker
        QTest.mousePress(self.window.view.viewport(), Qt.LeftButton, pos=self.window.view.mapFromOrigin(50, 50), delay=10)
        QTest.mouseMove(self.window.view.viewport(), pos=self.window.view.mapFromOrigin(50, 100), delay=10)
        QTest.mouseRelease(self.window.view.viewport(), Qt.LeftButton, pos=self.window.view.mapFromOrigin(50, 100), delay=10)
        # TODO implement test correctly

    def test_deleteMarker(self):
        """ Test if deleting marker works """
        QTest.keyPress(self.window, Qt.Key_F2)
        self.assertEqual(len(self.window.GetModule("MarkerHandler").points), 0, "At the beginning already some markers where present")

        QTest.mouseClick(self.window.view.viewport(), Qt.LeftButton, pos=self.window.view.mapFromOrigin(50, 50), delay=10)
        self.assertEqual(len(self.window.GetModule("MarkerHandler").points), 1, "Marker wasn't added by clicking")

        # Test deletion of marker
        QTest.mouseClick(self.window.view.viewport(), Qt.RightButton, pos=self.window.view.mapFromOrigin(50, 50), delay=10)
        self.assertEqual(len(self.window.GetModule("MarkerHandler").points), 0, "Marker deletion didn't work")

    def test_createDatabase(self):
        """ Test if creating the database on demand works """
        QTest.keyPress(self.window, Qt.Key_F2)
        self.assertEqual(len(self.window.GetModule("MarkerHandler").points), 0, "At the beginning already some markers where present")
        self.assertFalse(os.path.exists(self.database_path), "Database file already present.")

        QTest.mouseClick(self.window.view.viewport(), Qt.LeftButton, pos=self.window.view.mapFromOrigin(50, 50), delay=10)
        self.assertEqual(len(self.window.GetModule("MarkerHandler").points), 1, "Marker wasn't added by clicking")

        self.assertFalse(os.path.exists(self.database_path), "Database file already present.")

        # Test saving database on frame change
        QTest.keyPress(self.window, Qt.Key_Right, delay=10)
        QTest.keyPress(self.window, Qt.Key_Right, delay=10)
        self.assertTrue(os.path.exists(self.database_path), "Database file was not created.")

if __name__ == "__main__":
    unittest.main()
