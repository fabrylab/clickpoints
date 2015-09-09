from __future__ import division, print_function
import os

try:
    from PyQt5 import QtCore
except ImportError:
    from PyQt4 import QtCore

class ScriptLauncher:
    def __init__(self, window, media_handler, config=None):
        self.window = window
        self.media_handler = media_handler
        self.config = config

    def keyPressEvent(self, event):

        keys = [QtCore.Qt.Key_F12, QtCore.Qt.Key_F11, QtCore.Qt.Key_F10, QtCore.Qt.Key_F9, QtCore.Qt.Key_F8, QtCore.Qt.Key_F7, QtCore.Qt.Key_F6, QtCore.Qt.Key_F5]
        for script, key in zip(self.config.launch_scripts, keys):
            # @key F12: Launch
            if event.key() == key:
                self.window.save()
                os.system(r"%s %s %d" % (script, self.config.srcpath, self.media_handler.currentPos))

    @staticmethod
    def file():
        return __file__

    @staticmethod
    def can_create_module(config):
        return len(config.launch_scripts) > 0
