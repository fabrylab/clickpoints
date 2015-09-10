from __future__ import division, print_function
import sys
import os
import ctypes

try:
    from PyQt5 import QtGui, QtCore
    from PyQt5.QtWidgets import QWidget, QApplication, QCursor, QFileDialog, QCursor, QIcon, QMessageBox
    from PyQt5.QtCore import Qt
except ImportError:
    from PyQt4 import QtGui, QtCore
    from PyQt4.QtGui import QWidget, QApplication, QCursor, QFileDialog, QCursor, QIcon, QMessageBox
    from PyQt4.QtCore import Qt

from MaskHandler import MaskHandler
from MarkerHandler import MarkerHandler
from Timeline import Timeline
from annotationhandler import AnnotationHandler

from Tools import HelpText, BroadCastEvent, rotate_list
from ConfigLoad import LoadConfig
from ToolsForClickPoints import BigImageDisplay
from GammaCorrection import GammaCorrection
from FolderBrowser import FolderBrowser
from ScriptLauncher import ScriptLauncher

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "qextendedgraphicsview"))
from QExtendedGraphicsView import QExtendedGraphicsView

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "mediahandler"))
from mediahandler import MediaHandler

config = LoadConfig()

used_modules = [MarkerHandler, MaskHandler, GammaCorrection, Timeline, AnnotationHandler, FolderBrowser, ScriptLauncher, HelpText]
used_huds = ["hud", "hud_upperRight", "hud_lowerRight", "hud", "hud", "hud", "hud", "hud"]

icon_path = os.path.join(os.path.dirname(__file__), ".", "icons")

class ClickPointsWindow(QWidget):
    def zoomEvent(self, scale, pos):
        for module in self.modules:
            if "zoomEvent" in dir(module):
                module.zoomEvent(scale, pos)

    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent)
        self.setWindowTitle('Select Window')
        self.setWindowIcon(QIcon(QIcon(os.path.join(icon_path, "ClickPoints.ico"))))

        self.layout = QtGui.QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        # view/scene setup
        self.view = QExtendedGraphicsView()
        self.view.zoomEvent = self.zoomEvent
        self.local_scene = self.view.scene
        self.origin = self.view.origin
        self.layout.addWidget(self.view)

        self.ImageDisplay = BigImageDisplay(self.origin, self, config)

        self.media_handler = MediaHandler(config.srcpath, filterparam=config.filterparam)

        self.modules = []
        arg_dict = {"window": self, "layout": self.layout, "media_handler": self.media_handler, "parent": self.view.origin, "parent_hud": self.view.hud, "view": self.view, "image_display": self.ImageDisplay, "outputpath": config.outputpath, "config": config, "modules": self.modules, "file": __file__}
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
            if "setActiveModule" in dir(module) and module.setActiveModule(True, True):
                break

        self.UpdateImage()

        if config.rotation != 0:
            self.view.rotate(config.rotation)

    def UpdateImage(self):
        filename = self.media_handler.getCurrentFilename()[1]
        frame_number = self.media_handler.getCurrentPos()

        self.setWindowTitle(filename)

        self.LoadImage()
        BroadCastEvent(self.modules, "LoadImageEvent", filename, frame_number)

    def LoadImage(self):
        self.ImageDisplay.SetImage(self.media_handler.getCurrentImg())

    def save(self):
        BroadCastEvent(self.modules, "save")

    def JumpFrames(self, amount):
        self.JumpToFrame(self.media_handler.getCurrentPos() + amount)

    # jump absolute
    def JumpToFrame(self, targetid):
        #QApplication.setOverrideCursor(QCursor(QtCore.Qt.WaitCursor))

        self.save()
        if self.media_handler.setCurrentPos(targetid):
            self.UpdateImage()
        for module in self.modules:
            if "FrameChangeEvent" in dir(module):
                module.FrameChangeEvent()
        #QApplication.restoreOverrideCursor()

    def closeEvent(self, QCloseEvent):
        BroadCastEvent(self.modules, "closeEvent", QCloseEvent)

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

        if event.key() == QtCore.Qt.Key_Escape:
            # @key Escape: close window
            self.close()

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
                    BroadCastEvent(self.modules, "loadLast")

        if event.key() == QtCore.Qt.Key_Delete:
            # @key Delete: close window
            path, name = self.media_handler.getCurrentFilename()
            path = os.path.join(path, name)
            if os.path.isfile(path):
                reply = QMessageBox.question(None, 'Warning', 'Do you really want to delete %s from your hard drive?' % path, QMessageBox.Yes,
                                             QMessageBox.No)
                if reply == QMessageBox.Yes:
                    print('Deleting file %s' % path)
                    os.remove(path)

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
                self.modules[index].setActiveModule(False)
            else:
                index = 0
            # Find next module, which can be activated
            for cur_index in rotate_list(range(len(self.modules)), index+1):
                if "setActiveModule" in dir(self.modules[cur_index]) and self.modules[cur_index].setActiveModule(True):
                    break

        # @key ---- Frame jumps ----
        if self.view.painted is True:
            if event.key() == QtCore.Qt.Key_Left and not event.modifiers() & Qt.ControlModifier:
                # @key Left: previous image
                self.JumpFrames(-1)
            if event.key() == QtCore.Qt.Key_Right and not event.modifiers() & Qt.ControlModifier:
                # @key Right: next image
                self.JumpFrames(+1)

            if event.key() == QtCore.Qt.Key_Home:
                # @key Home: jump to beginning
                self.JumpToFrame(0)
            if event.key() == QtCore.Qt.Key_End:
                # @key End: jump to end
                self.JumpToFrame(self.media_handler.totalNr-1)

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

for addon in config.addons:
    with open(addon + ".py") as f:
        code = compile(f.read(), addon + ".py", 'exec')
        exec(code)

if __name__ == '__main__':
    if sys.platform[:3] == 'win':
        myappid = 'fabrybiophysics.clickpoints' # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)

    if config.srcpath is "":
        config.srcpath = str(QFileDialog.getOpenFileName(None, "Choose Image", os.getcwd()))
        print(config.srcpath)
    if config.outputpath is "":
        config.relative_outputpath = True
        config.outputpath = os.path.dirname(config.srcpath)
    else:
        config.relative_outputpath = False

    window = ClickPointsWindow()
    window.show()
    app.exec_()
