#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Test_MediaHandler.py

# Copyright (c) 2015-2016, Richard Gerum, Sebastian Richter
#
# This file is part of ClickPoints.
#
# ClickPoints is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ClickPoints is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ClickPoints. If not, see <http://www.gnu.org/licenses/>

__key__ = "MEDIA_HANDLER"
__testname__ = "Media Handler"

import sys
import os
import unittest
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from BaseTest import BaseTest
#from includes import ExceptionNoFilesFound, ExceptionExtensionNotSupported, ExceptionPathDoesntExist

class Test_MediaHandler(unittest.TestCase, BaseTest):

    def tearDown(self):
        BaseTest.tearDown(self)

    def test_loadImages(self):
        """ Open an image """
        self.createInstance(os.path.join("ClickPointsExamples", "TweezerVideos", "002", "frame0000.jpg"))
        self.assertEqual(self.db.getImages().count(), 68, "Not all images loaded")

    def test_loadFolder(self):
        """ Open a folder """
        self.createInstance(os.path.join("ClickPointsExamples", "TweezerVideos", "002"))
        self.assertEqual(self.db.getImages().count(), 68, "Not all images loaded")

    '''
    def test_loadEmptyFolder(self):
        """ Test Exception for opening folder without files / valid files """
        print("PATH:", os.getcwd())

        test_folder = os.path.join("..", "..", "ClickPointsExamples","EmptyFolder")
        if not os.path.exists(test_folder):
            os.mkdir(test_folder)

        try:
            self.createInstance(os.path.join("ClickPointsExamples", "EmptyFolder"))
        except ExceptionNoFilesFound:
            pass
        else:
            raise self.failureException("Failed to detect empty folder / invalid files")

        os.chdir("..")
        os.rmdir("EmptyFolder")

    def test_loadInvalidExtension(self):
        """ Test Exception for opening file with invalid extension """
        try:
            self.createInstance(os.path.join("ClickPointsExamples", "TweezerVideos", "Track.py"))
        except ExceptionExtensionNotSupported:
            pass
        else:
            raise self.failureException("Failed to detect invalid extension")

    def test_loadInvalidPath(self):
        """ Test Exception for opening a path that does not exist """
        try:
            self.createInstance(os.path.join("ClickPointsExamples", "TweezerVideos", "TrackingBla"))
        except ExceptionPathDoesntExist:
            pass
        else:
            raise self.failureException("Failed to detect invalid folder")

    def test_loadInvalidFile(self):
        """ Test Exception for opening a file that does not exist """
        try:
            self.createInstance(os.path.join("ClickPointsExamples", "TweezerVideos", "TrackingBla.txt"))
        except ExceptionPathDoesntExist:
            pass
        else:
            raise self.failureException("Failed to detect invalid file")

    def test_loadInvalidTextFile(self):
        """ Test Exception for opening a .txt file that does not contain a list of valid viles """
        try:
            self.createInstance(os.path.join("ClickPointsExamples", "TweezerVideos", "ConfigClickPoints.txt"))
        except ExceptionNoFilesFound:
            pass
        else:
            raise self.failureException("Failed to detect invalid .txt file")
    '''

    def test_loadFolderSlash(self):
        """ Open a folder ending with a slash """
        self.createInstance(os.path.join("ClickPointsExamples", "TweezerVideos", "002")+os.path.sep)
        self.assertEqual(self.db.getImages().count(), 68, "Not all images loaded")

    def test_loadFolderRecursive(self):
        """ Open a folder containing two folders """
        self.createInstance(os.path.join("ClickPointsExamples", "TweezerVideos"))
        self.assertEqual(self.db.getImages().count(), 68+68, "Not all images in two folders loaded")

    def test_loadFolderVideos(self):
        """ Open a folder containing two videos """
        self.createInstance(os.path.join("ClickPointsExamples", "BirdAttack"))
        self.assertEqual(self.db.getImages().count(), 569, "Didn't load two videos properly")

    def test_loadVideo(self):
        """ Open a video """
        self.createInstance(os.path.join("ClickPointsExamples", "BirdAttack", "attack1.avi"))
        self.assertEqual(self.db.getImages().count(), 206, "Didn't load video properly")

    def test_loadTiff(self):
        """ Open tiff files """
        self.createInstance(os.path.join("ClickPointsExamples", "PlantRoot"))
        self.assertEqual(self.db.getImages().count(), 6, "Didn't load tiff properly")
        self.assertEqual(self.window.ImageDisplay.image.shape, (1024, 1024, 3))
        self.assertTrue(8 < np.mean(self.window.ImageDisplay.image) < 128)

if __name__ == '__main__':
    __path__ = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(__path__, 'log_'+__key__+'.txt')
    with open(log_file, "w") as f:
        runner = unittest.TextTestRunner(f)
        unittest.main(testRunner=runner)
