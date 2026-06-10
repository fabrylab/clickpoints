import sys
import unittest

from qtpy import QtCore, QtGui, QtWidgets

from clickpoints.launch import create_clickpoints_application


class FileOpenWindow:
    def __init__(self):
        self.loaded = []

    def loadUrl(self, path, reset=False):
        self.loaded.append((path, reset))


class Test_Launch(unittest.TestCase):
    def setUp(self):
        self.existing_app = QtWidgets.QApplication.instance()
        if self.existing_app is None:
            self.app = create_clickpoints_application(QtCore, QtWidgets, sys.argv)
            self.owns_app = True
        else:
            self.app = self.existing_app
            self.owns_app = False
            if not hasattr(self.app, "open_files"):
                self.skipTest("existing QApplication is not a ClickPoints application")
        self.app.open_files.clear()
        self.app.clickpoints_window = None

    def tearDown(self):
        self.app.open_files.clear()
        self.app.clickpoints_window = None

    def test_file_open_event_is_deferred_until_window_exists(self):
        event = QtGui.QFileOpenEvent("/tmp/example.cdb")

        self.assertTrue(self.app.event(event))
        self.assertEqual(self.app.open_files, ["/tmp/example.cdb"])

    def test_file_open_event_loads_when_window_exists(self):
        window = FileOpenWindow()
        self.app.clickpoints_window = window
        event = QtGui.QFileOpenEvent("/tmp/example.tif")

        self.assertTrue(self.app.event(event))
        self.app.processEvents()

        self.assertEqual(window.loaded, [("/tmp/example.tif", True)])
