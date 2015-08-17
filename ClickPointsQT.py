from __future__ import division
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "mediahandler"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "qextendedgraphicsview"))
try:
    from PyQt5 import QtGui, QtCore
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except ImportError:
    from PyQt4 import QtGui, QtCore
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

from QExtendedGraphicsView import QExtendedGraphicsView

from os.path import join

from mediahandler import MediaHandler

from MaskHandler import MaskHandler
from MarkerHandler import MarkerHandler

from Tools import *
from ConfigLoad import *

LoadConfig()


class ClickPointsWindow(QMainWindow):
    def zoomEvent(self, scale, pos):
        if self.MarkerHandler is not None:
            self.MarkerHandler.zoomEvent(scale, pos)

    def __init__(self, parent=None):
        super(QMainWindow, self).__init__(parent)
        self.setWindowTitle('Select Window')

        self.view = QExtendedGraphicsView()
        self.view.zoomEvent = self.zoomEvent
        self.setCentralWidget(self.view)
        self.local_scene = self.view.scene
        self.origin = self.view.origin

        self.ImageDisplay = BigImageDisplay(self.origin, self)

        self.modules = []
        if len(types):
            self.MarkerHandler = MarkerHandler(self.view.origin, self.view.hud, self.view, self.ImageDisplay, outputpath, self.modules)
            self.modules.append(self.MarkerHandler)
        else:
            self.MarkerHandler = None
        if len(draw_types):
            self.MaskHandler = MaskHandler(self.view.origin, self.view.hud_upperRight, self.view, self.ImageDisplay, outputpath, self.modules)
            self.modules.append(self.MaskHandler)
            if len(types) == 0:
                self.MaskHandler.changeOpacity(0.5)
        else:
            self.MaskHandler = None
        self.modules[0].setActive(True)

        self.MediaHandler = MediaHandler(join(srcpath, filename),filterparam=filterparam)

        self.HelpText = HelpText(self, __file__)

        self.slider = SliderBox(self.view.hud_lowerRight, self.ImageDisplay)
        self.slider.setPos(-140, -140)

        self.UpdateImage()

    def UpdateImage(self):
        filename = self.MediaHandler.getCurrentFilename()[1]
        frame_number = self.MediaHandler.getCurrentPos()

        self.setWindowTitle(filename)

        self.LoadImage()
        if self.MarkerHandler:
            self.MarkerHandler.LoadImageEvent(filename, frame_number)
        if self.MaskHandler:
            self.MaskHandler.LoadImageEvent(filename)
        self.slider.LoadImageEvent()

    def LoadImage(self):
        self.ImageDisplay.SetImage(self.MediaHandler.getCurrentImg())

    def SaveMaskAndPoints(self):
        if self.MarkerHandler is not None:
            self.MarkerHandler.SavePoints()
        if self.MaskHandler is not None:
            self.MaskHandler.SaveMask()

    def JumpFrames(self, amount):
        QApplication.setOverrideCursor(QCursor(QtCore.Qt.WaitCursor))
        self.SaveMaskAndPoints()
        if self.MediaHandler.setCurrentPos(self.MediaHandler.getCurrentPos() + amount):
            self.UpdateImage()
        QApplication.restoreOverrideCursor()

    def keyPressEvent(self, event):
        sys.stdout.flush()

        # @key ---- General ----
        if event.key() == QtCore.Qt.Key_F1:
            # @key F1: toggle help window
            self.HelpText.ShowHelpText()

        if event.key() == QtCore.Qt.Key_F:
            # @key F: fit image to view
            self.view.fitInView()

        numberkey = event.key() - 49

        if event.key() == QtCore.Qt.Key_S:
            # @key S: save marker and mask
            self.SaveMaskAndPoints()

        if event.key() == QtCore.Qt.Key_L:
            # @key L: load marker and mask from last image
            if (self.MarkerHandler and self.MarkerHandler.last_logname) or \
                    (self.MaskHandler and self.MaskHandler.last_maskname):
                # saveguard/confirmation with MessageBox
                reply = QMessageBox.question(None, 'Warning', 'Load Mask & Points of last Image?', QMessageBox.Yes,
                                             QMessageBox.No)
                if reply == QMessageBox.Yes:
                    print('Loading last mask & points ...')
                    # load mask and log of last image
                    if self.MarkerHandler:
                        self.MarkerHandler.LoadLog(self.MarkerHandler.last_logname)
                        self.MarkerHandler.PointsUnsaved = True
                    if self.MaskHandler:
                        self.MaskHandler.LoadMask(self.MaskHandler.last_maskname)
                        self.MaskHandler.MaskUnsaved = True
                        self.MaskHandler.RedrawMask()

        # @key ---- Marker ----
        if self.MarkerHandler is not None:
            if self.MarkerHandler.active and 0 <= numberkey < 9 and event.modifiers() != Qt.KeypadModifier:
                # @key 0-9: change marker type
                self.MarkerHandler.SetActiveMarkerType(numberkey)

            if event.key() == QtCore.Qt.Key_T:
                # @key T: toggle marker shape
                self.MarkerHandler.toggleMarkerShape()

        # @key ---- Painting ----
        if event.key() == QtCore.Qt.Key_P:
            # @key P: toogle brush mode
            if self.MarkerHandler is not None and self.MaskHandler is not None:
                self.MarkerHandler.setActive(not self.MarkerHandler.active)
                self.MaskHandler.setActive(not self.MaskHandler.active)

        if self.MaskHandler is not None:
            if self.MaskHandler.active and 0 <= numberkey < len(draw_types) and event.modifiers() != Qt.KeypadModifier:
                # @key 0-9: change brush type
                self.MaskHandler.SetActiveDrawType(numberkey)

            if event.key() == QtCore.Qt.Key_K:
                # @key K: pick color of brush
                self.MaskHandler.PickColor()

            if event.key() == QtCore.Qt.Key_Plus:
                # @key +: increase brush radius
                self.MaskHandler.changeCursorSize(+1)
            if event.key() == QtCore.Qt.Key_Minus:
                # @key -: decrease brush radius
                self.MaskHandler.changeCursorSize(-1)
            if event.key() == QtCore.Qt.Key_O:
                # @key O: increase mask transparency
                self.MaskHandler.changeOpacity(+0.1)

            if event.key() == QtCore.Qt.Key_I:
                # @key I: decrease mask transparency
                self.MaskHandler.changeOpacity(-0.1)

            if event.key() == QtCore.Qt.Key_M:
                # @key M: redraw the mask
                self.MaskHandler.RedrawMask()

        # @key ---- Frame jumps ----
        if event.key() == QtCore.Qt.Key_Left:
            # @key Left: previous image
            self.JumpFrames(-1)
        if event.key() == QtCore.Qt.Key_Right:
            # @key Right: next image
            self.JumpFrames(+1)

        # JUMP keys
        if event.key() == Qt.Key_2 and event.modifiers() == Qt.KeypadModifier:
            # @key Numpad 2: Jump -1 frame
            self.JumpFrames(-1)
            print('-1')
        if event.key() == Qt.Key_3 and event.modifiers() == Qt.KeypadModifier:
            # @key Numpad 3: Jump +1 frame
            self.JumpFrames(+1)
            print('+1')
        if event.key() == Qt.Key_5 and event.modifiers() == Qt.KeypadModifier:
            # @key Numpad 5: Jump -10 frame
            self.JumpFrames(-10)
            print('-10')
        if event.key() == Qt.Key_6 and event.modifiers() == Qt.KeypadModifier:
            # @key Numpad 6: Jump +10 frame
            self.JumpFrames(+10)
            print('+10')
        if event.key() == Qt.Key_8 and event.modifiers() == Qt.KeypadModifier:
            # @key Numpad 8: Jump -100 frame
            self.JumpFrames(-100)
            print('-100')
        if event.key() == Qt.Key_9 and event.modifiers() == Qt.KeypadModifier:
            # @key Numpad 9: Jump +100 frame
            self.JumpFrames(+100)
            print('+100')
        if event.key() == Qt.Key_Slash and event.modifiers() == Qt.KeypadModifier:
            # @key Numpad /: Jump -1000 frame
            self.JumpFrames(-1000)
            print('-1000')
        if event.key() == Qt.Key_Asterisk and event.modifiers() == Qt.KeypadModifier:
            # @key Numpad *: Jump +1000 frame
            self.JumpFrames(+1000)
            print('+1000')

        # @key ---- Gamma/Brightness Adjustment ---
        if event.key() == Qt.Key_Space:
            # @key Space: update rect
            QApplication.setOverrideCursor(QCursor(QtCore.Qt.WaitCursor))
            self.ImageDisplay.PreviewRect()
            self.ImageDisplay.Change()
            self.slider.updateHist(self.ImageDisplay.hist)
            QApplication.restoreOverrideCursor()


for addon in addons:
    with open(addon + ".py") as f:
        code = compile(f.read(), addon + ".py", 'exec')
        exec(code)

if __name__ == '__main__':
    app = QApplication(sys.argv)

    if use_filedia is True or filename is None:
        tmp = QFileDialog.getOpenFileName(None, "Choose Image", srcpath)
        srcpath = os.path.split(str(tmp))[0]
        filename = os.path.split(str(tmp))[-1]
        print(srcpath)
        print(filename)
    if outputpath is None:
        outputpath = srcpath

    window = ClickPointsWindow()
    window.show()
    app.exec_()
