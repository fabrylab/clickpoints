from __future__ import division, print_function
import os
import sys
import glob

try:
    from PyQt5 import QtCore
except ImportError:
    from PyQt4 import QtCore

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "mediahandler"))
from mediahandler import MediaHandler

from Tools import BroadCastEvent

class FolderBrowser:
    def __init__(self, window, media_handler, modules, config=None):
        # default settings and parameters
        self.window = window
        self.media_handler = media_handler
        self.config = config
        self.modules = modules
        self.index = 0
        self.folder_list = []
        for folder in config.folder_list:
            if folder.find("*") != -1:
                self.folder_list.extend(glob.glob(folder))
            else:
                self.folder_list.append(folder)

    def LoadFolder(self):
        self.window.save()
        if self.config.relative_outputpath:
            self.config.outputpath = os.path.dirname(self.folder_list[self.index])
        self.config.srcpath = self.folder_list[self.index]
        MediaHandler(self.config.srcpath, filterparam=self.config.filterparam, mediahandler_instance=self.media_handler)
        BroadCastEvent(self.modules, "FolderChangeEvent")
        self.window.JumpToFrame(0)
        self.window.setWindowTitle(self.folder_list[self.index])

    def keyPressEvent(self, event):

        # @key Page Down: Next folder
        if event.key() == QtCore.Qt.Key_PageDown:
            if self.index < len(self.folder_list)-1:
                self.index += 1
            self.LoadFolder()

        # @key Page Up: Previous folder
        if event.key() == QtCore.Qt.Key_PageUp:
            if self.index > 0:
                self.index -= 1
            self.LoadFolder()

    @staticmethod
    def file():
        return __file__

    @staticmethod
    def can_create_module(config):
        return len(config.folder_list) > 0
