from __future__ import division, print_function

if __name__ == "__main__":
    import sys, os
    import sip
    sip.setapi('QVariant', 2)
    from PyQt4 import QtGui, QtCore
    # start the Qt application
    app = QtGui.QApplication(sys.argv)

    # Create and display the splash screen
    splash_pix = QtGui.QPixmap(os.path.join(os.path.dirname(__file__), 'icons', 'Splash.png'))
    splash = QtGui.QSplashScreen(splash_pix, QtCore.Qt.WindowStaysOnTopHint)
    splash.setMask(splash_pix.mask())
    splash.show()
    app.processEvents()

import sys
import os
import ctypes

try:
    with open(os.path.join(os.path.dirname(__file__), "version.txt")) as fp:
        version = fp.read().strip()
except IOError:
    try:
        with open(os.path.join(os.path.dirname(__file__), "..", "version.txt")) as fp:
            version = fp.read().strip()
    except IOError:
        version = "unknown"

print("ClickPoints", version)

print("Using Python", "%d.%d.%d" % (sys.version_info.major, sys.version_info.minor, sys.version_info.micro), sys.version_info.releaselevel, "64bit" if sys.maxsize > 2**32 else "32bit")

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
from includes.FilelistLoader import ListFiles
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

    def __init__(self, my_config, parent=None):
        global config
        config = my_config
        super(QWidget, self).__init__(parent)
        self.setWindowIcon(QIcon(QIcon(os.path.join(icon_path, "ClickPoints.ico"))))

        self.setMinimumWidth(650)
        self.setMinimumHeight(400)

        # init updater
        self.updater = Updater(self)

        # add layout
        self.layout = QtGui.QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        # setup mono space font
        QtGui.QFontDatabase.addApplicationFont(os.path.join(clickpoints_path, "icons", "FantasqueSansMono-Regular.ttf"))
        self.mono_font = QtGui.QFont("Fantasque Sans Mono")

        # view/scene setup
        self.view = QExtendedGraphicsView()
        self.view.zoomEvent = self.zoomEvent
        self.local_scene = self.view.scene
        self.origin = self.view.origin
        self.layout.addWidget(self.view)

        # init image display
        self.ImageDisplay = BigImageDisplay(self.origin, self, config)

        # init DataFile for storage
        load_list = True
        if os.path.splitext(config.srcpath)[1] == ".db":
            config.database_file = config.srcpath
            load_list = False
        self.data_file = DataFile(config.database_file)

        # init media handler
        exclude_ending = None
        if len(config.draw_types):
            exclude_ending = "_mask.png"#config.maskname_tag
        if load_list:
            ListFiles(self.data_file, config.srcpath, config.file_ids, filterparam=config.filterparam, force_recursive=True, dont_process_filelist=config.dont_process_filelist, exclude_ending=exclude_ending, config=config)

        # init the modules
        self.modules = []
        arg_dict = {"window": self, "layout": self.layout, "data_file": self.data_file, "parent": self.view.origin, "parent_hud": self.view.hud, "view": self.view, "image_display": self.ImageDisplay, "outputpath": config.outputpath, "config": config, "modules": self.modules, "file": __file__, "datafile": self.data_file}
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

        # find next module, which can be activated
        for module in self.modules:
            if "setActiveModule" in dir(module) and module.setActiveModule(True, True):
                break

        # initialize some variables
        self.new_filename = None
        self.new_frame_number = None
        self.im = None

        # select the first frame
        self.target_frame = 0
        self.data_file.signals.loaded.connect(self.FrameLoaded)
        if self.data_file.get_image_count():
            self.JumpToFrame(0)

        # apply image rotation from config
        if config.rotation != 0:
            self.view.rotate(config.rotation)
            
    def GetModule(self, name):
        module_names = [a.__class__.__name__ for a in self.modules]
        index = module_names.index(name)
        return self.modules[index]

    def Save(self):
        BroadCastEvent(self.modules, "save")
        #self.data_file.check_to_save()

    """ jumping frames and displaying images """

    def JumpFrames(self, amount):
        # redirect to an absolute jump
        self.JumpToFrame(self.target_frame + amount)

    # jump absolute
    def JumpToFrame(self, target_id, no_threaded_load=False):
        # if no frame is loaded yet, do nothing
        if self.data_file.get_image_count() == 0:
            return

        # save the data on frame change
        self.Save()

        # Test if the new frame is valid
        if target_id >= self.data_file.get_image_count():
            if self.target_frame == self.data_file.get_image_count()-1:
                target_id = 0
            else:
                target_id = self.data_file.get_image_count()-1
        if target_id < 0:
            if self.target_frame == 0:
                target_id = self.data_file.get_image_count()-1
            else:
                target_id = 0

        self.target_frame = target_id

        # load the next frame (threaded or not)
        # this will call FrameLoaded afterwards
        if config.threaded_image_load and not no_threaded_load:
            self.data_file.load_frame(target_id, threaded=1)
        else:
            self.data_file.load_frame(target_id, threaded=0)

    def FrameLoaded(self, frame_number, no_threaded_load=False):
        # set the index of the current frame
        self.data_file.set_image(frame_number)

        # get filename and frame number
        self.new_filename = self.data_file.image.filename
        self.new_frame_number = self.target_frame

        # Notify that the frame will be loaded TODO are all these events necessary?
        BroadCastEvent(self.modules, "FrameChangeEvent")
        BroadCastEvent(self.modules, "PreLoadImageEvent", self.new_filename, self.new_frame_number)
        self.setWindowTitle(self.new_filename)

        # get image
        self.im = self.data_file.get_image_data()

        # get offsets
        offset = self.data_file.get_offset()

        # display the image
        self.ImageDisplay.SetImage(self.im, offset, no_threaded_load)  # calls DisplayedImage

    def DisplayedImage(self):
        # tell the QExtendedGraphicsView the shape of the new image
        self.view.setExtend(*self.im.shape[:2][::-1])

        # notify all modules that a new frame is loaded
        BroadCastEvent(self.modules, "LoadImageEvent", self.new_filename, self.new_frame_number)

    """ some Qt events which should be passed around """

    def closeEvent(self, QCloseEvent):
        # save the data
        self.Save()
        # broadcast event the image display and the mediahandler (so that they can terminate their threads)
        self.ImageDisplay.closeEvent(QCloseEvent)
        self.data_file.closeEvent(QCloseEvent)
        # broadcast event to the modules
        BroadCastEvent(self.modules, "closeEvent", QCloseEvent)

    def resizeEvent(self, event):
        # broadcast event to the modules
        BroadCastEvent(self.modules, "resizeEvent", event)

    def zoomEvent(self, scale, pos):
        # broadcast event to the modules
        BroadCastEvent(self.modules, "zoomEvent", scale, pos)

    def keyPressEvent(self, event):
        # broadcast event to the modules
        BroadCastEvent(self.modules, "keyPressEvent", event)

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
            self.data_file.save_database()
            self.Save()

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
            self.JumpToFrame(self.data_file.get_image_count()-1)

        # JUMP keys
        # @key Numpad 2,3: Jump -/+ 1 frame
        # @key Numpad 5,6: Jump -/+ 10 frames
        # @key Numpad 8,9: Jump -/+ 100 frames
        # @key Numpad /,*: Jump -/+ 100 frames
        keys = [Qt.Key_2, Qt.Key_3, Qt.Key_5, Qt.Key_6, Qt.Key_8, Qt.Key_9, Qt.Key_Slash, Qt.Key_Asterisk]
        for key, jump in zip(keys, config.jumps):
            if event.key() == key and event.modifiers() == Qt.KeypadModifier:
                self.JumpFrames(jump)


def main():
    global app, splash
    # set an application id, so that windows properly stacks them in the task bar
    if sys.platform[:3] == 'win':
        myappid = 'fabrybiophysics.clickpoints'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    # load config and exec addon code
    config = LoadConfig()
    for addon in config.addons:
        with open(addon + ".py") as f:
            code = compile(f.read(), addon + ".py", 'exec')
            exec(code)

    # init and open the ClickPoints window
    window = ClickPointsWindow(config)
    window.app = app
    window.show()
    splash.finish(window)
    app.exec_()

# start the main function as entry point
if __name__ == '__main__':
    main()
