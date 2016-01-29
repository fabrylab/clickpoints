__key__ = "ANNOTATION_HANDLER"
__testname__ = "Annotation Handler"

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
__path__ = os.path.dirname(os.path.abspath(__file__))

class Test_AnnotationHandler(unittest.TestCase):

    def createInstance(self, path, database_file, keep_database=False):
        """Create the GUI """
        self.test_path = os.path.normpath(os.path.join(__path__, "..", "..", "..", path))
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
        if os.path.exists(self.database_path) and not keep_database:
            os.remove(self.database_path)
        self.window = ClickPoints.ClickPointsWindow(config)
        self.window.show()

    def test_loadAnnotations(self):
        """ Load existing annotations """
        self.createInstance(os.path.join("ClickPointsExamples", "BirdAttack"), "clickpoints.db", keep_database=True)
        QTest.keyPress(self.window, Qt.Key_Right, Qt.ControlModifier)
        QTest.keyPress(self.window, Qt.Key_A)
        self.assertIsNotNone(self.window.GetModule("AnnotationHandler").AnnotationEditorWindow, "Annotation window was not opened")
        annotationWindow = self.window.GetModule("AnnotationHandler").AnnotationEditorWindow
        self.assertEqual(annotationWindow.pteAnnotation.toPlainText(), "Bird attacks.", "Annotation not loaded properly")

    def test_addAnnotations(self):
        """ Add and remove annotation """
        self.createInstance(os.path.join("ClickPointsExamples", "BirdAttack"), "addAnnotations.db")

        QTest.keyPress(self.window, Qt.Key_A)
        self.assertIsNotNone(self.window.GetModule("AnnotationHandler").AnnotationEditorWindow, "Annotation window was not opened")
        annotationWindow = self.window.GetModule("AnnotationHandler").AnnotationEditorWindow
        annotationWindow.leTag.setText("bird")
        QTest.mouseClick(annotationWindow.leTag.pbAdd, Qt.LeftButton)
        annotationWindow.leRating.setCurrentIndex(2)
        annotationWindow.pteAnnotation.setPlainText("A bird attacks.")
        QTest.mouseClick(annotationWindow.pbConfirm, Qt.LeftButton)
        self.window.JumpFrames(1)
        QTest.keyPress(self.window, Qt.Key_A)
        annotationWindow = self.window.GetModule("AnnotationHandler").AnnotationEditorWindow
        self.assertEqual(annotationWindow.leTag.getTagList(), [], "Tags not empty at default")
        self.assertEqual(annotationWindow.leRating.currentIndex(), 0, "Rating not 0 at default")
        self.assertEqual(annotationWindow.pteAnnotation.toPlainText(), "", "Comment not empty at default")
        QTest.mouseClick(annotationWindow.pbDiscard, Qt.LeftButton)
        self.window.JumpFrames(-1)
        QTest.keyPress(self.window, Qt.Key_A)
        annotationWindow = self.window.GetModule("AnnotationHandler").AnnotationEditorWindow
        self.assertEqual(annotationWindow.leTag.getTagList(), ["bird"], "Tags not saved")
        self.assertEqual(annotationWindow.leRating.currentIndex(), 2, "Rating not saved")
        self.assertEqual(annotationWindow.pteAnnotation.toPlainText(), "A bird attacks.", "Comment not saved")
        QTest.mouseClick(annotationWindow.pbRemove, Qt.LeftButton)

        QTest.keyPress(self.window, Qt.Key_A)
        annotationWindow = self.window.GetModule("AnnotationHandler").AnnotationEditorWindow
        self.assertEqual(annotationWindow.leTag.getTagList(), [], "Tags not empty after remove")
        self.assertEqual(annotationWindow.leRating.currentIndex(), 0, "Rating not 0 after remove")
        self.assertEqual(annotationWindow.pteAnnotation.toPlainText(), "", "Comment not empty after remove")
        QTest.mouseClick(annotationWindow.pbDiscard, Qt.LeftButton)

    def test_jumpToAnnotations(self):
        """ Jumping to next/previous annotation """
        self.createInstance(os.path.join("ClickPointsExamples", "BirdAttack"), "jumpToAnnotations.db")

        QTest.keyPress(self.window, Qt.Key_A)
        self.assertIsNotNone(self.window.GetModule("AnnotationHandler").AnnotationEditorWindow, "Annotation window was not opened")

        annotationWindow = self.window.GetModule("AnnotationHandler").AnnotationEditorWindow
        annotationWindow.pteAnnotation.setPlainText("A bird attacks.")
        QTest.mouseClick(annotationWindow.pbConfirm, Qt.LeftButton)

        self.window.JumpFrames(10)

        QTest.keyPress(self.window, Qt.Key_A)
        annotationWindow = self.window.GetModule("AnnotationHandler").AnnotationEditorWindow
        annotationWindow.pteAnnotation.setPlainText("A bird attacks.")
        QTest.mouseClick(annotationWindow.pbConfirm, Qt.LeftButton)

        QTest.keyPress(self.window, Qt.Key_Left, Qt.ControlModifier)

        self.assertEqual(self.window.media_handler.get_index(), 1, "Didn't jump to annotation in frame 1 in Ctrl+Left")

        QTest.keyPress(self.window, Qt.Key_Right, Qt.ControlModifier)

        self.assertEqual(self.window.media_handler.get_index(), 10, "Didn't jump to annotation in frame 10 in Ctrl+Right")

    def test_addTagsAnnotations(self):
        """ Add and remove annotation """
        self.createInstance(os.path.join("ClickPointsExamples", "BirdAttack"), "addTagsAnnotations.db")

        QTest.keyPress(self.window, Qt.Key_A)
        self.assertIsNotNone(self.window.GetModule("AnnotationHandler").AnnotationEditorWindow, "Annotation window was not opened")

        # Add annotation
        annotationWindow = self.window.GetModule("AnnotationHandler").AnnotationEditorWindow
        annotationWindow.leTag.setText("bird")
        QTest.mouseClick(annotationWindow.leTag.pbAdd, Qt.LeftButton)
        annotationWindow.leRating.setCurrentIndex(2)
        annotationWindow.pteAnnotation.setPlainText("A bird attacks.")
        QTest.mouseClick(annotationWindow.pbConfirm, Qt.LeftButton)
        self.window.JumpFrames(1)
        self.window.JumpFrames(-1)

        # Check Annotation and add tag
        QTest.keyPress(self.window, Qt.Key_A)
        annotationWindow = self.window.GetModule("AnnotationHandler").AnnotationEditorWindow
        self.assertEqual(annotationWindow.leTag.getTagList(), ["bird"], "Tags not saved")
        self.assertEqual(annotationWindow.leRating.currentIndex(), 2, "Rating not saved")
        self.assertEqual(annotationWindow.pteAnnotation.toPlainText(), "A bird attacks.", "Comment not saved")
        annotationWindow.leTag.setText("cheese")
        QTest.mouseClick(annotationWindow.leTag.pbAdd, Qt.LeftButton)
        annotationWindow.leTag.setText("cake")
        QTest.mouseClick(annotationWindow.leTag.pbAdd, Qt.LeftButton)
        QTest.mouseClick(annotationWindow.pbConfirm, Qt.LeftButton)

        self.window.JumpFrames(1)
        self.window.JumpFrames(-1)

        # Check tag and remove tag
        QTest.keyPress(self.window, Qt.Key_A)
        annotationWindow = self.window.GetModule("AnnotationHandler").AnnotationEditorWindow
        self.assertEqual(annotationWindow.leTag.getTagList(), ["bird", "cheese", "cake"], "Tag not added")

        annotationWindow.leTag.layout_list.itemAt(2).widget().setChecked(False)
        annotationWindow.leTag.layout_list.itemAt(1).widget().setChecked(False)
        QTest.mouseClick(annotationWindow.pbConfirm, Qt.LeftButton)

        self.window.JumpFrames(1)
        self.window.JumpFrames(-1)

        # Check tag
        QTest.keyPress(self.window, Qt.Key_A)
        annotationWindow = self.window.GetModule("AnnotationHandler").AnnotationEditorWindow
        self.assertEqual(annotationWindow.leTag.getTagList(), ["bird"], "Tag not removed")

        annotationWindow.leTag.layout_list.itemAt(0).widget().setChecked(False)
        QTest.mouseClick(annotationWindow.pbConfirm, Qt.LeftButton)

        self.window.JumpFrames(1)
        self.window.JumpFrames(-1)

        # Check if all tags are removed
        QTest.keyPress(self.window, Qt.Key_A)
        annotationWindow = self.window.GetModule("AnnotationHandler").AnnotationEditorWindow
        self.assertEqual(annotationWindow.leTag.getTagList(), [], "Tag not removed")
        QTest.mouseClick(annotationWindow.pbConfirm, Qt.LeftButton)

    def test_overviewAnnotations(self):
        """ Add and remove annotation """
        self.createInstance(os.path.join("ClickPointsExamples", "BirdAttack"), "overviewAnnotations.db")

        # Add annotation
        QTest.keyPress(self.window, Qt.Key_A)
        self.assertIsNotNone(self.window.GetModule("AnnotationHandler").AnnotationEditorWindow, "Annotation window was not opened")
        annotationWindow = self.window.GetModule("AnnotationHandler").AnnotationEditorWindow
        annotationWindow.pteAnnotation.setPlainText("A bird attacks.")
        QTest.mouseClick(annotationWindow.pbConfirm, Qt.LeftButton)
        self.window.JumpFrames(10)

        # open overview window
        QTest.keyPress(self.window, Qt.Key_Y)
        AnnotationOverviewWindow = self.window.GetModule("AnnotationHandler").AnnotationOverviewWindow
        self.assertIsNotNone(AnnotationOverviewWindow, "Annotation overview window was not opened")

        self.assertEqual(AnnotationOverviewWindow.table.rowCount(), 1, "Annotation not displayed in overview table")

        # Add another annotation
        QTest.keyPress(self.window, Qt.Key_A)
        annotationWindow = self.window.GetModule("AnnotationHandler").AnnotationEditorWindow
        annotationWindow.pteAnnotation.setPlainText("A bird attacks.")
        QTest.mouseClick(annotationWindow.pbConfirm, Qt.LeftButton)

        self.assertEqual(AnnotationOverviewWindow.table.rowCount(), 2, "Annotation not displayed in overview table")


        self.window.JumpFrames(10)
        xPos = AnnotationOverviewWindow.table.columnViewportPosition( 2 ) + 5
        yPos = AnnotationOverviewWindow.table.rowViewportPosition( 1 ) + 10
        # TODO fix
        print(xPos, yPos)
        QTest.mouseDClick(AnnotationOverviewWindow.table.viewport(), Qt.LeftButton, pos=QtCore.QPoint(xPos, yPos))

        print(self.window.media_handler.get_index())

        QTest.mouseDClick(AnnotationOverviewWindow.table.viewport(), Qt.LeftButton, pos=QtCore.QPoint(10, 200))

        print(self.window.media_handler.get_index())

        self.assertEqual(self.window.media_handler.get_index(), 1, "Jumping to annotation by clicking on the overview does not work.")



if __name__ == '__main__':
    log_file = os.path.join(__path__, 'log_'+__key__+'.txt')
    with open(log_file, "w") as f:
        runner = unittest.TextTestRunner(f)
        unittest.main(testRunner=runner)
