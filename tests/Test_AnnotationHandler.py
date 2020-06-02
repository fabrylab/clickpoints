#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Test_AnnotationHandler.py

# Copyright (c) 2015-2020, Richard Gerum, Sebastian Richter, Alexander Winterl
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ClickPoints. If not, see <http://www.gnu.org/licenses/>

__key__ = "ANNOTATION_HANDLER"
__testname__ = "Annotation Handler"

import sys
import os
import unittest
from PIL import Image
import imageio
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.dirname(__file__))

from BaseTest import BaseTest

from qtpy.QtCore import Qt
from qtpy.QtTest import QTest

class Test_AnnotationHandler(unittest.TestCase, BaseTest):

    def tearDown(self):
        BaseTest.tearDown(self)

    def test_loadAnnotations(self):
        """ Load existing annotations """
        self.createInstance(os.path.join("ClickPointsExamples", "BirdAttack", "clickpoints.cdb"))

        # jump to next annotation
        self.wait_for_image_load()
        self.keyPress(Qt.Key_Right, Qt.ControlModifier)
        self.wait_for_image_load()

        # open annotation window
        self.keyPress(Qt.Key_A)
        self.assertIsNotNone(self.window.GetModule("AnnotationHandler").AnnotationEditorWindow, "Annotation window was not opened")

        # check text
        annotationWindow = self.window.GetModule("AnnotationHandler").AnnotationEditorWindow
        self.assertEqual(annotationWindow.pteAnnotation.toPlainText(), "Bird attacks.", "Annotation not loaded properly")

    def test_addAnnotations(self):
        """ Add and remove annotation """
        self.createInstance(os.path.join("ClickPointsExamples", "BirdAttack"))

        # wait for image to be loaded
        self.wait_for_image_load()

        # open annotation window
        self.keyPress(Qt.Key_A)
        self.assertIsNotNone(self.window.GetModule("AnnotationHandler").AnnotationEditorWindow, "Annotation window was not opened")

        # fill window with text
        annotationWindow = self.window.GetModule("AnnotationHandler").AnnotationEditorWindow
        annotationWindow.pteAnnotation.setPlainText("A bird attacks.")
        # add tag
        annotationWindow.leTag.setText("bird")
        QTest.mouseClick(annotationWindow.leTag.pbAdd, Qt.LeftButton)
        # add rating
        annotationWindow.leRating.setCurrentIndex(2)
        # save annotation
        QTest.mouseClick(annotationWindow.pbConfirm, Qt.LeftButton)

        # jump to next frame and open annotation editor
        self.window.JumpFrames(1)
        self.wait_for_image_load()
        self.keyPress(Qt.Key_A)

        # check if the window is empty
        annotationWindow = self.window.GetModule("AnnotationHandler").AnnotationEditorWindow
        self.assertEqual(annotationWindow.leTag.getTagList(), [], "Tags not empty at default")
        self.assertEqual(annotationWindow.leRating.currentIndex(), 0, "Rating not 0 at default")
        self.assertEqual(annotationWindow.pteAnnotation.toPlainText(), "", "Comment not empty at default")
        QTest.mouseClick(annotationWindow.pbDiscard, Qt.LeftButton)

        # jump back and assure the data is still there
        self.window.JumpFrames(-1)
        self.wait_for_image_load()
        self.keyPress(Qt.Key_A)
        annotationWindow = self.window.GetModule("AnnotationHandler").AnnotationEditorWindow
        self.assertEqual(annotationWindow.leTag.getTagList(), ["bird"], "Tags not saved")
        self.assertEqual(annotationWindow.leRating.currentIndex(), 2, "Rating not saved")
        self.assertEqual(annotationWindow.pteAnnotation.toPlainText(), "A bird attacks.", "Comment not saved")

        # remove the annotation and check if it has gone
        QTest.mouseClick(annotationWindow.pbRemove, Qt.LeftButton)
        self.keyPress(Qt.Key_A)
        annotationWindow = self.window.GetModule("AnnotationHandler").AnnotationEditorWindow
        self.assertEqual(annotationWindow.leTag.getTagList(), [], "Tags not empty after remove")
        self.assertEqual(annotationWindow.leRating.currentIndex(), 0, "Rating not 0 after remove")
        self.assertEqual(annotationWindow.pteAnnotation.toPlainText(), "", "Comment not empty after remove")
        QTest.mouseClick(annotationWindow.pbDiscard, Qt.LeftButton)

    def test_jumpToAnnotations(self):
        """ Jumping to next/previous annotation """
        self.createInstance(os.path.join("ClickPointsExamples", "BirdAttack"))

        # wait for image to be loaded
        self.wait_for_image_load()

        # open annotation window
        self.keyPress(Qt.Key_A)
        self.assertIsNotNone(self.window.GetModule("AnnotationHandler").AnnotationEditorWindow, "Annotation window was not opened")

        # add text
        annotationWindow = self.window.GetModule("AnnotationHandler").AnnotationEditorWindow
        annotationWindow.pteAnnotation.setPlainText("A bird attacks.")
        QTest.mouseClick(annotationWindow.pbConfirm, Qt.LeftButton)

        # jump 10 frames
        self.window.JumpFrames(10)
        self.wait_for_image_load()

        # add an annotation
        self.keyPress(Qt.Key_A)
        annotationWindow = self.window.GetModule("AnnotationHandler").AnnotationEditorWindow
        annotationWindow.pteAnnotation.setPlainText("A bird attacks.")
        QTest.mouseClick(annotationWindow.pbConfirm, Qt.LeftButton)

        # jump back to the first annotation
        self.keyPress(Qt.Key_Left, Qt.ControlModifier)
        self.wait_for_image_load()
        self.assertEqual(self.window.target_frame, 0, "Didn't jump to annotation in frame 1 in Ctrl+Left")

        # jump to the second annotation
        self.keyPress(Qt.Key_Right, Qt.ControlModifier)
        self.wait_for_image_load()
        self.assertEqual(self.window.target_frame, 10, "Didn't jump to annotation in frame 10 in Ctrl+Right")

    def test_addTagsAnnotations(self):
        """ Add and remove annotation """
        self.createInstance(os.path.join("ClickPointsExamples", "BirdAttack"))

        # wait for image to be loaded
        self.wait_for_image_load()

        # open annotation window
        self.keyPress(Qt.Key_A)
        self.assertIsNotNone(self.window.GetModule("AnnotationHandler").AnnotationEditorWindow, "Annotation window was not opened")

        # Add annotation
        annotationWindow = self.window.GetModule("AnnotationHandler").AnnotationEditorWindow
        # add tag
        annotationWindow.leTag.setText("bird")
        QTest.mouseClick(annotationWindow.leTag.pbAdd, Qt.LeftButton)
        # add rating
        annotationWindow.leRating.setCurrentIndex(2)
        # add text
        annotationWindow.pteAnnotation.setPlainText("A bird attacks.")
        # configm
        QTest.mouseClick(annotationWindow.pbConfirm, Qt.LeftButton)

        # change frame back and forth to reload this frame
        self.window.JumpFrames(1)
        self.wait_for_image_load()
        self.window.JumpFrames(-1)
        self.wait_for_image_load()

        # Check Annotation tags
        self.keyPress(Qt.Key_A)
        annotationWindow = self.window.GetModule("AnnotationHandler").AnnotationEditorWindow
        self.assertEqual(annotationWindow.leTag.getTagList(), ["bird"], "Tags not saved")
        self.assertEqual(annotationWindow.leRating.currentIndex(), 2, "Rating not saved")
        self.assertEqual(annotationWindow.pteAnnotation.toPlainText(), "A bird attacks.", "Comment not saved")
        # add two tags
        annotationWindow.leTag.setText("cheese")
        QTest.mouseClick(annotationWindow.leTag.pbAdd, Qt.LeftButton)
        annotationWindow.leTag.setText("cake")
        QTest.mouseClick(annotationWindow.leTag.pbAdd, Qt.LeftButton)
        QTest.mouseClick(annotationWindow.pbConfirm, Qt.LeftButton)

        # change frame back and forth to reload this frame
        self.window.JumpFrames(1)
        self.wait_for_image_load()
        self.window.JumpFrames(-1)
        self.wait_for_image_load()

        # Check tag and remove tag
        self.keyPress(Qt.Key_A)
        annotationWindow = self.window.GetModule("AnnotationHandler").AnnotationEditorWindow
        self.assertEqual(annotationWindow.leTag.getTagList(), ["bird", "cheese", "cake"], "Tag not added")
        # remove two tags
        annotationWindow.leTag.layout_list.itemAt(2).widget().setChecked(False)
        annotationWindow.leTag.layout_list.itemAt(1).widget().setChecked(False)
        QTest.mouseClick(annotationWindow.pbConfirm, Qt.LeftButton)

        # change frame back and forth to reload this frame
        self.window.JumpFrames(1)
        self.wait_for_image_load()
        self.window.JumpFrames(-1)
        self.wait_for_image_load()

        # Check tag
        self.keyPress(Qt.Key_A)
        annotationWindow = self.window.GetModule("AnnotationHandler").AnnotationEditorWindow
        self.assertEqual(annotationWindow.leTag.getTagList(), ["bird"], "Tag not removed")
        # remove last tag
        annotationWindow.leTag.layout_list.itemAt(0).widget().setChecked(False)
        QTest.mouseClick(annotationWindow.pbConfirm, Qt.LeftButton)

        # change frame back and forth to reload this frame
        self.window.JumpFrames(1)
        self.wait_for_image_load()
        self.window.JumpFrames(-1)
        self.wait_for_image_load()

        # Check if all tags are removed
        self.keyPress(Qt.Key_A)
        annotationWindow = self.window.GetModule("AnnotationHandler").AnnotationEditorWindow
        self.assertEqual(annotationWindow.leTag.getTagList(), [], "Tag not removed")
        QTest.mouseClick(annotationWindow.pbConfirm, Qt.LeftButton)

    def test_overviewAnnotations(self):
        """ Add and remove annotation """
        self.createInstance(os.path.join("ClickPointsExamples", "BirdAttack"))

        # wait for image to be loaded
        self.wait_for_image_load()

        # Add annotation
        self.keyPress(Qt.Key_A)
        self.assertIsNotNone(self.window.GetModule("AnnotationHandler").AnnotationEditorWindow, "Annotation window was not opened")
        annotationWindow = self.window.GetModule("AnnotationHandler").AnnotationEditorWindow
        annotationWindow.pteAnnotation.setPlainText("A bird attacks.")
        QTest.mouseClick(annotationWindow.pbConfirm, Qt.LeftButton)
        self.window.JumpFrames(10)
        self.wait_for_image_load()

        # open overview window
        self.keyPress(Qt.Key_Y)
        AnnotationOverviewWindow = self.window.GetModule("AnnotationHandler").AnnotationOverviewWindow
        self.assertIsNotNone(AnnotationOverviewWindow, "Annotation overview window was not opened")

        self.assertEqual(AnnotationOverviewWindow.table.rowCount(), 1, "Annotation not displayed in overview table")

        # Add another annotation
        self.keyPress(Qt.Key_A)
        annotationWindow = self.window.GetModule("AnnotationHandler").AnnotationEditorWindow
        annotationWindow.pteAnnotation.setPlainText("A bird attacks.")
        QTest.mouseClick(annotationWindow.pbConfirm, Qt.LeftButton)

        self.assertEqual(AnnotationOverviewWindow.table.rowCount(), 2, "Annotation not displayed in overview table")


        self.window.JumpFrames(10)
        self.wait_for_image_load()
        xPos = AnnotationOverviewWindow.table.columnViewportPosition( 2 ) + 5
        yPos = AnnotationOverviewWindow.table.rowViewportPosition( 1 ) + 10
        # TODO fix
        """
        print(xPos, yPos)
        QTest.mouseDClick(AnnotationOverviewWindow.table.viewport(), Qt.LeftButton, pos=QtCore.QPoint(xPos, yPos))

        print(self.window.media_handler.get_index())

        QTest.mouseDClick(AnnotationOverviewWindow.table.viewport(), Qt.LeftButton, pos=QtCore.QPoint(10, 200))

        print(self.window.media_handler.get_index())

        self.assertEqual(self.window.media_handler.get_index(), 1, "Jumping to annotation by clicking on the overview does not work.")
        """


if __name__ == '__main__':
    __path__ = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(__path__, 'log_'+__key__+'.txt')
    with open(log_file, "w") as f:
        runner = unittest.TextTestRunner(f)
        unittest.main(testRunner=runner)
