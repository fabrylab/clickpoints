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
from PyViewer import Viewer

from Tools import *
from ConfigLoad import LoadConfig
from ToolsForClickPoints import SliderBox, BigImageDisplay

config = LoadConfig()

used_modules = [MarkerHandler, MaskHandler, SliderBox, Viewer, HelpText]
used_huds = ["hud", "hud_upperRight", "hud_lowerRight", "hud", "hud"]

class ClickPointsWindow(QWidget):
    def zoomEvent(self, scale, pos):
        for module in self.modules:
            if "zoomEvent" in dir(module):
                module.zoomEvent(scale, pos)

    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent)
        self.setWindowTitle('Select Window')

        self.layout = QtGui.QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        ## view/scene setup
        self.view = QExtendedGraphicsView()
        self.view.zoomEvent = self.zoomEvent
        self.local_scene = self.view.scene
        self.origin = self.view.origin
        self.layout.addWidget(self.view)

        self.ImageDisplay = BigImageDisplay(self.origin, self, config)

        self.MediaHandler = MediaHandler(join(config.srcpath, config.filename), filterparam=config.filterparam)

        self.modules = []
        arg_dict = {"window": self, "layout": self.layout, "MediaHandler": self.MediaHandler, "parent": self.view.origin, "parent_hud": self.view.hud, "view": self.view, "image_display": self.ImageDisplay, "outputpath": config.outputpath, "config": config, "modules": self.modules, "file": __file__}
        for mod, hud in zip(used_modules, used_huds):
            allowed = True
            if "can_create_module" in dir(mod):
                allowed = mod.can_create_module(config)
            if allowed:
                # Get a list of the arguments the function tages
                arg_name_list = mod.__init__.func_code.co_varnames[:mod.__init__.func_code.co_argcount]
                # Set the proper hud argument
                arg_dict["parent_hud"] = eval("self.view."+hud)
                # Filter out only the arguments the function wants
                arg_dict2 = {k: v for k, v in arg_dict.items() if k in arg_name_list}
                # Initialize the module
                self.modules.append(mod(**arg_dict2))
        # Find next module, which can be activated
        for module in self.modules:
            if "setActive" in dir(module) and module.setActive(True, True):
                break

        self.UpdateImage()

        if config.rotation != 0:
            self.view.rotate(config.rotation)

    def UpdateImage(self):
        filename = self.MediaHandler.getCurrentFilename()[1]
        frame_number = self.MediaHandler.getCurrentPos()

        self.setWindowTitle(filename)

        self.LoadImage()
        for module in self.modules:
            if "LoadImageEvent" in dir(module):
                module.LoadImageEvent(filename, frame_number)

    def LoadImage(self):
        self.ImageDisplay.SetImage(self.MediaHandler.getCurrentImg())

    def save(self):
        for module in self.modules:
            if "save" in dir(module):
                module.save()

    def JumpFrames(self, amount):
        self.JumpToFrame(self.MediaHandler.getCurrentPos() + amount)

    # jump absolute
    def JumpToFrame(self, targetid):
        QApplication.setOverrideCursor(QCursor(QtCore.Qt.WaitCursor))
        self.save()
        if self.MediaHandler.setCurrentPos(targetid):
            self.UpdateImage()
        for module in self.modules:
            if "FrameChangeEvent" in dir(module):
                module.FrameChangeEvent()
        QApplication.restoreOverrideCursor()

    def keyPressEvent(self, event):

        for module in self.modules:
            module.keyPressEvent(event)

        # @key ---- General ----
        if event.key() == QtCore.Qt.Key_F:
            # @key F: fit image to view
            self.view.fitInView()

        # @key W: fullscreen toggle
        if event.key() == QtCore.Qt.Key_W:
            if self.isFullScreen():
                self.setWindowState(Qt.WindowMaximized)
            else:
                self.setWindowState(Qt.WindowFullScreen)

        # @key R: rotate the image
        if event.key() == QtCore.Qt.Key_R:
            self.view.rotate(config.rotation_steps)

        if event.key() == QtCore.Qt.Key_S:
            # @key S: save marker and mask
            self.save()

        if event.key() == QtCore.Qt.Key_L:
            # @key L: load marker and mask from last image
            last_available = False
            for module in self.modules:
                if "canLoadLast" in dir(module) and module.canLoadLast():
                    last_available = True
                    break
            if last_available:
                # saveguard/confirmation with MessageBox
                reply = QMessageBox.question(None, 'Warning', 'Load data of last Image?', QMessageBox.Yes,
                                             QMessageBox.No)
                if reply == QMessageBox.Yes:
                    print('Loading data of last image ...')
                    for module in self.modules:
                        if "loadLast" in dir(module):
                            module.loadLast()

        # @key ---- Modules ----
        if event.key() == QtCore.Qt.Key_P:
            # @key P: change active module
            # Find active module
            index = -1
            for cur_index, module in enumerate(self.modules):
                if "active" in dir(module) and module.active:
                    index = cur_index
            # Deactivate current module
            if index != -1:
                self.modules[index].setActive(False)
            else:
                index = 0
            # Find next module, which can be activated
            for cur_index in rotate_list(range(len(self.modules)), index+1):
                if "setActive" in dir(self.modules[cur_index]) and self.modules[cur_index].setActive(True):
                    break

        # @key ---- Frame jumps ----
        if event.key() == QtCore.Qt.Key_Left:
            # @key Left: previous image
            self.JumpFrames(-1)
        if event.key() == QtCore.Qt.Key_Right:
            # @key Right: next image
            self.JumpFrames(+1)

        # JUMP keys
        # @key Numpad 2,3: Jump -/+ 1 frame
        # @key Numpad 5,6: Jump -/+ 10 frames
        # @key Numpad 8,9: Jump -/+ 100 frames
        # @key Numpad /,*: Jump -/+ 100 frames
        keys = [Qt.Key_2, Qt.Key_3, Qt.Key_5, Qt.Key_6, Qt.Key_8, Qt.Key_9, Qt.Key_Slash, Qt.Key_Asterisk]
        for key, jump in zip(keys, config.jumps):
            if event.key() == key and event.modifiers() == Qt.KeypadModifier:
                self.JumpFrames(jump)
                print(jump)
print "config", config
for addon in config.addons:
    with open(addon + ".py") as f:
        code = compile(f.read(), addon + ".py", 'exec')
        exec(code)

print "config", config

if __name__ == '__main__':
    app = QApplication(sys.argv)

    if config.use_filedia is True or config.filename is None:
        tmp = QFileDialog.getOpenFileName(None, "Choose Image", config.srcpath)
        config.srcpath = os.path.split(str(tmp))[0]
        config.filename = os.path.split(str(tmp))[-1]
        print(config.srcpath)
        print(config.filename)
    if config.outputpath is None:
        config.outputpath = config.srcpath

    window = ClickPointsWindow()
    window.show()
    app.exec_()
