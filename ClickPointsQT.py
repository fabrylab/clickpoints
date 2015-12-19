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
    from PyQt4.QtGui import QWidget, QApplication, QCursor, QFileDialog, QCursor, QIcon, QMessageBox, QGraphicsSceneWheelEvent
    from PyQt4.QtCore import Qt

from Tools import HelpText, BroadCastEvent, rotate_list
from ConfigLoad import LoadConfig
from ToolsForClickPoints import BigImageDisplay

from modules import MaskHandler
from modules import MarkerHandler
from modules import Timeline
from modules import AnnotationHandler
from modules import GammaCorrection
from modules import FolderBrowser
from modules import ScriptLauncher
from modules import VideoExporter
from modules import InfoHud
from modules import Overview

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "qextendedgraphicsview"))
from QExtendedGraphicsView import QExtendedGraphicsView

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "mediahandler"))
from mediahandler import MediaHandler

from update import Updater
from Database import DataFile

used_modules = []#[MarkerHandler, MaskHandler, GammaCorrection, InfoHud, Overview, Timeline, FolderBrowser, ScriptLauncher, VideoExporter, HelpText, AnnotationHandler]
used_huds = []#["hud", "hud_upperRight", "hud_lowerRight", "hud_lowerLeft", "hud", "", "", "", "", "hud",""]

used_modules = [Timeline, MarkerHandler, MaskHandler, AnnotationHandler]
used_huds = ["", "hud", "hud_upperRight", ""]#["hud", "hud_upperRight", "hud_lowerRight", "hud_lowerLeft", "hud", "", "", "", "", "hud",""]

icon_path = os.path.join(os.path.dirname(__file__), ".", "icons")
clickpoints_path = os.path.dirname(__file__)

class ClickPointsWindow(QWidget):
    def zoomEvent(self, scale, pos):
        for module in self.modules:
            if "zoomEvent" in dir(module):
                module.zoomEvent(scale, pos)

    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent)
        self.setWindowIcon(QIcon(QIcon(os.path.join(icon_path, "ClickPoints.ico"))))

        self.move(50,50)

        self.updater = Updater(self)

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

        exclude_ending = None
        if len(config.draw_types):
            exclude_ending = config.maskname_tag
        self.media_handler = MediaHandler(config.srcpath, config.file_ids, filterparam=config.filterparam, force_recursive=True, dont_process_filelist=config.dont_process_filelist, exclude_ending=exclude_ending)

        # DataFile
        self.data_file = DataFile()

        self.modules = []
        arg_dict = {"window": self, "layout": self.layout, "media_handler": self.media_handler, "parent": self.view.origin, "parent_hud": self.view.hud, "view": self.view, "image_display": self.ImageDisplay, "outputpath": config.outputpath, "config": config, "modules": self.modules, "file": __file__, "datafile": self.data_file}
        for mod, hud in zip(used_modules, used_huds):
            allowed = True
            if "can_create_module" in dir(mod):
                allowed = mod.can_create_module(config)
            if allowed:
                # Get a list of the arguments the function tages
                arg_name_list = mod.__init__.func_code.co_varnames[:mod.__init__.func_code.co_argcount]
                # Set the proper hud argument
                if "parent_hud" in arg_name_list:
                    arg_dict["parent_hud"] = eval("self.view."+hud)
                # Filter out only the arguments the function wants
                arg_dict2 = {k: v for k, v in arg_dict.items() if k in arg_name_list}
                # Initialize the module
                self.modules.append(mod(**arg_dict2))
        # Find next module, which can be activated
        for module in self.modules:
            if "setActiveModule" in dir(module) and module.setActiveModule(True, True):
                break

        self.media_handler.set_index(0)
        self.UpdateImage()

        if config.rotation != 0:
            self.view.rotate(config.rotation)
            
    def GetModule(self, name):
        module_names = [a.__class__.__name__ for a in self.modules]
        index = module_names.index(name)
        return self.modules[index]

    def UpdateImage(self):
        if not self.media_handler.get_file_entry():
            return
        filename = self.media_handler.get_filename()
        frame_number = self.media_handler.get_index()
        self.setWindowTitle(filename)
        self.LoadImage()
        self.data_file.set_image(self.media_handler.get_file_entry(), self.media_handler.get_file_frame(), self.media_handler.get_timestamp())
        BroadCastEvent(self.modules, "LoadImageEvent", filename, frame_number)

    def LoadImage(self):
        im = self.media_handler.get_file()
        self.ImageDisplay.SetImage(im)
        self.view.setExtend(*im.shape[:2][::-1])

    def save(self):
        BroadCastEvent(self.modules, "save")

    def JumpFrames(self, amount, next_amount=None):
        if next_amount:
            self.JumpToFrame(self.media_handler.get_index() + amount, self.media_handler.get_index() + amount + next_amount)
        else:
            self.JumpToFrame(self.media_handler.get_index() + amount)

    # jump absolute
    def JumpToFrame(self, target_id, next_id=None):
        self.save()
        self.media_handler.set_index(target_id)
        #if next_id is not None:
        #    self.media_handler.buffer_frame_threaded(next_id)
        self.UpdateImage()
        BroadCastEvent(self.modules, "FrameChangeEvent")

    def closeEvent(self, QCloseEvent):
        self.save()
        BroadCastEvent(self.modules, "closeEvent", QCloseEvent)

    def resizeEvent(self, event):
        BroadCastEvent(self.modules, "resizeEvent", event)

    def keyPressEvent(self, event):

        for module in self.modules:
            module.keyPressEvent(event)

        # @key ---- General ----
        if event.key() == QtCore.Qt.Key_F:
            # @key F: fit image to view
            self.view.fitInView()
            
        if event.key() == Qt.Key_F2:
            # @key F2: hide/show interfaces
            BroadCastEvent(self.modules, "ToggleInterfaceEvent")

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
                self.JumpToFrame(self.media_handler.get_frame_count()-1)

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


if __name__ == '__main__':
    if sys.platform[:3] == 'win':
        myappid = 'fabrybiophysics.clickpoints' # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
    QtGui.QFontDatabase.addApplicationFont(os.path.join(clickpoints_path, "FantasqueSansMono-Regular.ttf"))
    app.setFont(QtGui.QFont("FantasqueSansMono"))

    config = LoadConfig()
    for addon in config.addons:
        with open(addon + ".py") as f:
            code = compile(f.read(), addon + ".py", 'exec')
            exec(code)

    window = ClickPointsWindow()
    window.show()
    app.exec_()
