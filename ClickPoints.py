from __future__ import division, print_function
import sys
import os
import ctypes

try:
    with open("version.txt") as fp:
        version = fp.read().strip()
except IOError:
    try:
        with open("../version.txt") as fp:
            version = fp.read().strip()
    except IOError:
        version = "unknown"

print("ClickPoints", version)

print("Using Python", "%d.%d.%d" % (sys.version_info.major, sys.version_info.minor, sys.version_info.micro), sys.version_info.releaselevel)

import sip
sip.setapi('QVariant', 2)

try:
    from PyQt5 import QtGui, QtCore
    from PyQt5.QtWidgets import QWidget, QApplication, QCursor, QFileDialog, QCursor, QIcon, QMessageBox
    from PyQt5.QtCore import Qt
except ImportError:
    from PyQt4 import QtGui, QtCore
    from PyQt4.QtGui import QWidget, QApplication, QCursor, QFileDialog, QCursor, QIcon, QMessageBox, QGraphicsSceneWheelEvent
    from PyQt4.QtCore import Qt

    from PyQt4.QtCore import QT_VERSION_STR
    from PyQt4.Qt import PYQT_VERSION_STR
    from sip import SIP_VERSION_STR

    print("Using PyQt4 (PyQt %s, SIP %s, Qt %s)" % (PYQT_VERSION_STR, SIP_VERSION_STR, QT_VERSION_STR))

from includes import HelpText, BroadCastEvent, rotate_list
from includes import LoadConfig
from includes import BigImageDisplay
from includes import QExtendedGraphicsView
from includes import MediaHandler
from includes import DataFile

from update import Updater

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

used_modules = [Timeline, MarkerHandler, MaskHandler, AnnotationHandler, GammaCorrection, InfoHud, VideoExporter, ScriptLauncher, HelpText]
used_huds = ["", "hud", "hud_upperRight", "", "hud_lowerRight", "hud_lowerLeft", "", "", ""]

icon_path = os.path.join(os.path.dirname(__file__), ".", "icons")
clickpoints_path = os.path.dirname(__file__)
if not os.path.exists(icon_path):  # different position if installed with the installer
    icon_path = os.path.join(os.path.dirname(__file__), "..", "icons")
    clickpoints_path = os.path.join(os.path.dirname(__file__), "..")

def GetModuleInitArgs(mod):
    import inspect
    return inspect.getargspec(mod.__init__).args

class ClickPointsWindow(QWidget):
    def zoomEvent(self, scale, pos):
        for module in self.modules:
            if "zoomEvent" in dir(module):
                module.zoomEvent(scale, pos)

    def __init__(self, my_config, parent=None):
        global config
        config = my_config
        super(QWidget, self).__init__(parent)
        self.setWindowIcon(QIcon(QIcon(os.path.join(icon_path, "ClickPoints.ico"))))

        self.move(50,50)

        self.updater = Updater(self)

        self.layout = QtGui.QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        QtGui.QFontDatabase.addApplicationFont(os.path.join(clickpoints_path, "icons", "FantasqueSansMono-Regular.ttf"))
        self.mono_font = QtGui.QFont("Fantasque Sans Mono")

        # view/scene setup
        self.view = QExtendedGraphicsView()
        self.view.zoomEvent = self.zoomEvent
        self.local_scene = self.view.scene
        self.origin = self.view.origin
        self.layout.addWidget(self.view)

        self.ImageDisplay = BigImageDisplay(self.origin, self, config)

        exclude_ending = None
        if len(config.draw_types):
            exclude_ending = "_mask.png"#config.maskname_tag
        self.media_handler, select_index = MediaHandler(config.srcpath, config.file_ids, filterparam=config.filterparam, force_recursive=True, dont_process_filelist=config.dont_process_filelist, exclude_ending=exclude_ending, config=config)

        # DataFile
        if config.database_file == "":
            config.database_file = "clickpoints.db"
        self.data_file = DataFile(config.database_file)

        self.modules = []
        arg_dict = {"window": self, "layout": self.layout, "media_handler": self.media_handler, "parent": self.view.origin, "parent_hud": self.view.hud, "view": self.view, "image_display": self.ImageDisplay, "outputpath": config.outputpath, "config": config, "modules": self.modules, "file": __file__, "datafile": self.data_file}
        for mod, hud in zip(used_modules, used_huds):
            allowed = True
            if "can_create_module" in dir(mod):
                allowed = mod.can_create_module(config)
            if allowed:
                # Get a list of the arguments the function takes
                arg_name_list = GetModuleInitArgs(mod)
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

        self.media_handler.set_index(select_index)
        self.media_handler.signals.loaded.connect(self.FrameLoaded)
        self.UpdateImage()
        BroadCastEvent(self.modules, "FrameChangeEvent")

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
        BroadCastEvent(self.modules, "PreLoadImageEvent", filename, frame_number)
        self.setWindowTitle(filename)
        self.LoadImage()
        self.data_file.set_image(self.media_handler.get_file_entry(), self.media_handler.get_file_frame(), self.media_handler.get_timestamp())
        BroadCastEvent(self.modules, "LoadImageEvent", filename, frame_number)

    def LoadImage(self):
        global im
        im = self.media_handler.get_file()
        _, frame = self.media_handler.id_lookup[self.media_handler.get_index()]
        filename = self.media_handler.get_filename()
        offset = self.data_file.get_offset(filename, frame)
        print(offset)
        self.ImageDisplay.SetImage(im, offset)
        self.view.setExtend(*im.shape[:2][::-1])

    def save(self):
        BroadCastEvent(self.modules, "save")
        self.data_file.check_to_save()

    def JumpFrames(self, amount, next_amount=None):
        if next_amount:
            self.JumpToFrame(self.media_handler.get_index() + amount, self.media_handler.get_index() + amount + next_amount)
        else:
            self.JumpToFrame(self.media_handler.get_index() + amount)

    # jump absolute
    def JumpToFrame(self, target_id, next_id=None):
        self.save()
        if config.threaded_image_load:
            self.media_handler.buffer_frame_threaded(target_id)
        else:
            self.media_handler.set_index(target_id)
            self.UpdateImage()
            BroadCastEvent(self.modules, "FrameChangeEvent")
        #self.media_handler.buffer_frame_threaded(target_id)
        #if next_id is not None:
        #    self.media_handler.buffer_frame_threaded(next_id, call=False)

    def FrameLoaded(self, frame_number):
        #if next_id is not None:
        #    self.media_handler.buffer_frame_threaded(next_id)
        self.media_handler.set_index(frame_number)
        self.UpdateImage()
        BroadCastEvent(self.modules, "FrameChangeEvent")

    def closeEvent(self, QCloseEvent):
        self.save()
        self.ImageDisplay.closeEvent(QCloseEvent)
        self.media_handler.closeEvent(QCloseEvent)
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
def main():
    if sys.platform[:3] == 'win':
        myappid = 'fabrybiophysics.clickpoints' # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)

    config = LoadConfig()
    for addon in config.addons:
        with open(addon + ".py") as f:
            code = compile(f.read(), addon + ".py", 'exec')
            exec(code)

    window = ClickPointsWindow(config)
    window.show()
    app.exec_()

if __name__ == '__main__':
    main()
    