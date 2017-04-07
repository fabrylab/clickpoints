#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ClickPoints.py

# Copyright (c) 2015-2016, Richard Gerum, Sebastian Richter
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import division, print_function

import sys
import os
import glob
import natsort

""" some magic to prevent PyQt5 from swallowing exceptions """
# Back up the reference to the exceptionhook
sys._excepthook = sys.excepthook
# Set the exception hook to our wrapping function
sys.excepthook = lambda *args: sys._excepthook(*args)


sys.path.insert(0, os.path.dirname(__file__))

if __name__ == "__main__":
    from ClickPointsBooster import BoosterRunning
    BoosterRunning()
    from SplashScreen import StartSplashScreen, StopSplashScreen
    StartSplashScreen()

icon_path = os.path.join(os.path.dirname(__file__), ".", "icons")
clickpoints_path = os.path.dirname(__file__)
if not os.path.exists(icon_path):  # different position if installed with the installer
    icon_path = os.path.join(os.path.dirname(__file__), "..", "icons")
    clickpoints_path = os.path.join(os.path.dirname(__file__), "..")
if sys.platform[:3] == 'win':
    storage_path = os.path.join(os.getenv('APPDATA'), "..", "Local", "Temp", "ClickPoints")
else:
    storage_path = os.path.expanduser("~/.clickpoints/")
if not os.path.exists(storage_path):
    os.makedirs(storage_path)

print(os.path.join(storage_path, "checked"))
if not os.path.exists(os.path.join(storage_path, "checked")):
    from includes import CheckPackages

    errors = CheckPackages()
    if errors == 0:
        with open(os.path.join(storage_path, "checked"), 'w') as fp:
            fp.write("\n")

import ctypes
import threading
import time

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

from qtpy import QtGui, QtCore, QtWidgets
from qtpy.QtCore import Qt
from qtpy import API_NAME as QT_API_NAME
print("Using %s" % QT_API_NAME)
import qtawesome as qta

from includes import HelpText, BroadCastEvent, SetBroadCastModules, rotate_list
from includes import LoadConfig
from includes import BigImageDisplay
from includes import QExtendedGraphicsView
from includes.FilelistLoader import FolderEditor, addPath, addList, imgformats, vidformats
from includes import DataFile

from modules import MaskHandler
from modules import MarkerHandler
from modules import Timeline
from modules import AnnotationHandler
from modules import GammaCorrection
from modules import ScriptLauncher
from modules import VideoExporter
from modules import InfoHud
from modules import Console
from modules import OptionEditor

class AddVLine():
    def __init__(self, window):
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.VLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        window.layoutButtons.addWidget(line)

class AddStrech():
    def __init__(self, window):
        window.layoutButtons.addStretch()

used_modules = [AddVLine, Timeline, GammaCorrection, VideoExporter, AddVLine, AnnotationHandler, MarkerHandler, MaskHandler, AddVLine, InfoHud, ScriptLauncher, AddStrech, HelpText, OptionEditor, Console]
used_huds = ["", "", "hud_lowerRight", "", "", "", "hud", "hud_upperRight", "", "hud_lowerLeft", "", "", "", "", "", "", ""]


def GetModuleInitArgs(mod):
    import inspect
    return inspect.getargspec(mod.__init__).args


class ClickPointsWindow(QtWidgets.QWidget):
    folderEditor = None
    optionEditor = None
    first_frame = 0

    load_thread = None
    data_file = None

    def __init__(self, my_config, app, parent=None):
        global config
        config = my_config
        self.app = app
        super(QtWidgets.QWidget, self).__init__(parent)
        self.setWindowIcon(QtGui.QIcon(QtGui.QIcon(os.path.join(icon_path, "ClickPoints.ico"))))

        self.setMinimumWidth(650)
        self.setMinimumHeight(400)
        self.setWindowTitle("ClickPoints")

        self.setAcceptDrops(True)

        # center window
        screen_geometry = QtWidgets.QApplication.desktop().screenGeometry()
        x = (screen_geometry.width()-self.width()) / 2
        y = (screen_geometry.height()-self.height()) / 2
        self.move(x, y*0.5)

        # add layout
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)

        # setup mono space font
        QtGui.QFontDatabase.addApplicationFont(os.path.join(clickpoints_path, "icons", "FantasqueSansMono-Regular.ttf"))
        self.mono_font = QtGui.QFont("Fantasque Sans Mono")

        self.icon_path = icon_path
        self.storage_path = storage_path
        self.layoutButtons = QtWidgets.QHBoxLayout()
        self.layoutButtons.setSpacing(5)
        self.layoutButtons.setContentsMargins(0, 0, 0, 5)
        self.button_play = QtWidgets.QPushButton()
        self.button_play.clicked.connect(lambda x: self.SaveDatabase())
        self.button_play.setIcon(qta.icon("fa.save"))
        self.button_play.setToolTip("save current project")
        self.layoutButtons.addWidget(self.button_play)

        self.button_play = QtWidgets.QPushButton()
        self.button_play.clicked.connect(self.Folder)
        self.button_play.setIcon(qta.icon("fa.folder-open"))
        self.button_play.setToolTip("add/remove folder from the current project")
        self.layoutButtons.addWidget(self.button_play)

        self.layout.addLayout(self.layoutButtons)

        # view/scene setup
        self.view = QExtendedGraphicsView(dropTarget=self)
        self.layout.addWidget(self.view)
        self.view.zoomEvent = self.zoomEvent
        self.local_scene = self.view.scene
        self.origin = self.view.origin

        # init image display
        self.ImageDisplay = BigImageDisplay(self.origin, self)

        # init media handler
        self.load_thread = None
        self.load_timer = QtCore.QTimer()
        self.load_timer.setInterval(0.1)
        self.load_timer.timeout.connect(self.LoadTimer)
        self.loading_time = time.time()

        # init the modules
        self.modules = [self.ImageDisplay]
        arg_dict = {"window": self, "layout": self.layout, "parent": self.view.origin, "parent_hud": self.view.hud, "view": self.view, "image_display": self.ImageDisplay,  "modules": self.modules, "file": __file__}
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

        SetBroadCastModules(self.modules)

        #self.layoutButtons.addStretch()

        # find next module, which can be activated
        for module in self.modules:
            if "setActiveModule" in dir(module) and module.setActiveModule(True, True):
                break

        # initialize some variables
        self.new_filename = None
        self.new_frame_number = None
        self.loading_image = -1
        self.im = None
        self.layer = 0

        # select the first frame
        self.target_frame = 0

        # set focus policy for buttons
        for i in range(self.layoutButtons.count()):
            if self.layoutButtons.itemAt(i).widget():
                self.layoutButtons.itemAt(i).widget().setFocusPolicy(Qt.NoFocus)

        self.setFocus()

        self.start_timer = QtCore.QTimer.singleShot(1, lambda: self.loadUrl(config.srcpath))

        self.log("ClickPoints", version)
        self.log("Using Python", "%d.%d.%d" % (sys.version_info.major, sys.version_info.minor, sys.version_info.micro),
              sys.version_info.releaselevel, "64bit" if sys.maxsize > 2 ** 32 else "32bit")
        self.log("Using %s" % QT_API_NAME)

        self.app.processEvents()

    def dragEnterEvent(self, event):
        # accept url lists (files by drag and drop)
        if event.mimeData().hasFormat("text/uri-list"):
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        if self.load_thread is not None:
            self.load_thread.join()
        for url in event.mimeData().urls():
            url = str(url.toString()).strip()
            if url.startswith("file:///"):
                url = url[len("file:///"):]
            if url.startswith("file:"):
                url = url[len("file:"):]
            self.loadUrl(url, reset=True)

    def loadUrl(self, url, reset=False):
        print("Loading url", url)
        if url == "":
            if self.data_file is None or reset:
                self.reset()
            self.GetModule("Timeline").ImagesAdded()
            BroadCastEvent(self.modules, "LoadingFinishedEvent")
            return

        # glob support
        if '*' in url:
            print("Glob string detected - building list")
            if self.data_file is None or reset:
                self.reset()
            # obj can be directory or files
            obj_list = natsort.natsorted(glob.glob(url))
            for obj in obj_list:
                print("Loading GLOB URL", os.path.abspath(obj))
                self.loadObject(os.path.abspath(obj))
            self.JumpToFrame(0)
            self.view.fitInView()
            self.GetModule("Timeline").ImagesAdded()
            BroadCastEvent(self.modules, "LoadingFinishedEvent")
            return

        # open an existing database
        if url.endswith(".cdb"):
            self.reset(url)
            self.JumpToFrame(0)
            self.view.fitInView()
            self.GetModule("Timeline").ImagesAdded()
            BroadCastEvent(self.modules, "LoadingFinishedEvent")
        else:
            if self.data_file is None or reset:
                self.reset()
            # if it is a directory add it
            if os.path.isdir(url):
                self.load_thread = threading.Thread(target=addPath, args=(self.data_file, url),
                                                    kwargs=dict(subdirectories=True, use_natsort=config.use_natsort))
                # addPath(self.data_file, config.srcpath, subdirectories=True, use_natsort=config.use_natsort)
            # if not check what type of file it is
            else:
                directory, filename = os.path.split(url)
                ext = os.path.splitext(filename)[1]
                # for images load the folder
                if ext.lower() in imgformats:
                    self.load_thread = threading.Thread(target=addPath, args=(self.data_file, directory),
                                                        kwargs=dict(use_natsort=config.use_natsort, window=self,
                                                                    select_file=filename))
                    self.first_frame = None
                    # addPath(self.data_file, directory, use_natsort=config.use_natsort)
                # for videos just load the file
                elif ext.lower() in vidformats:
                    self.load_thread = threading.Thread(target=addPath, args=(self.data_file, directory),
                                                        kwargs=dict(file_filter=os.path.split(filename)[1]))
                    # addPath(self.data_file, directory, file_filter=os.path.split(filename)[1])
                elif ext.lower() == ".txt":
                    self.load_thread = threading.Thread(target=addList, args=(self.data_file, directory, filename))
                    # addList(self.data_file, directory, filename)
                # if the extension is not known, raise an exception
                else:
                    raise Exception("unknown file extension " + ext, filename)

            if self.load_thread is not None:
                self.load_thread.daemon = True
                self.load_thread.start()
                self.load_timer.start()

    def loadObject(self,url):
        #TODO: rebuild threaded version for glob, replace duplicated code above with this function
        """
        Loads objects of type directory, img or video file
        HACKED the non thread version as i couldnt get threaded to work ...

        :param url (string): path to object
        :return:
        """
        if os.path.isdir(url):
            # self.load_thread = threading.Thread(target=addPath, args=(self.data_file, url),
            #                                     kwargs=dict(subdirectories=True, use_natsort=config.use_natsort))
            addPath(self.data_file, url, subdirectories=True, use_natsort=config.use_natsort)
        # if not check what type of file it is
        else:
            directory, filename = os.path.split(url)
            ext = os.path.splitext(filename)[1]
            # for images load the folder
            if ext.lower() in imgformats:
                # self.load_thread = threading.Thread(target=addPath, args=(self.data_file, directory),
                #                                     kwargs=dict(use_natsort=config.use_natsort, window=self,
                #                                                 select_file=filename))
                self.first_frame = None
                addPath(self.data_file, directory, use_natsort=config.use_natsort)
            # for videos just load the file
            elif ext.lower() in vidformats:
                # self.load_thread = threading.Thread(target=addPath, args=(self.data_file, directory),
                #                                     kwargs=dict(file_filter=os.path.split(filename)[1]))
                addPath(self.data_file, directory, file_filter=os.path.split(filename)[1])
            elif ext.lower() == ".txt":
                # self.load_thread = threading.Thread(target=addList, args=(self.data_file, directory, filename))
                addList(self.data_file, directory, filename)
            # if the extension is not known, raise an exception
            else:
                raise Exception("unknown file extension " + ext, filename)

        # if self.load_thread is not None:
        #     self.load_thread.daemon = True
        #     self.load_thread.start()
        #     self.load_timer.start()


    def reset(self, filename=""):
        if self.data_file is not None:
            # ask to save current data
            self.testForUnsaved()
            # close database
            self.data_file.closeEvent(None)
            BroadCastEvent(self.modules, "closeDataFile")
        # open new database
        self.data_file = DataFile(filename, config, storage_path=storage_path)
        self.data_file.signals.loaded.connect(self.FrameLoaded)
        # apply image rotation from config
        if self.data_file.getOption("rotation") != 0:
            self.view.rotate(self.data_file.getOption("rotation"))
        BroadCastEvent(self.modules, "updateDataFile", self.data_file, filename == "")
        self.GetModule("Timeline").ImagesAdded()

    def LoadTimer(self):
        if self.data_file.image is None and self.data_file.get_image_count() and self.first_frame is not None:
            self.JumpToFrame(self.first_frame)
            self.view.fitInView()
            self.GetModule("Timeline").ImagesAdded()
        else:
            self.GetModule("Timeline").ImagesAdded()
        if not self.load_thread.is_alive() and (self.data_file.image is not None or self.data_file.get_image_count() == 0):
            self.load_timer.stop()
            BroadCastEvent(self.modules, "LoadingFinishedEvent")
            print("Loading finished in %.2fs " % (time.time()-self.loading_time))

    def Folder(self):
        if not self.data_file:
            return
        self.folderEditor = FolderEditor(self, self.data_file)
        self.folderEditor.show()

    def ImagesAdded(self):
        if self.data_file.image is None and self.data_file.get_image_count():
            self.JumpToFrame(0)
            self.view.fitInView()

    def GetModule(self, name):
        module_names = [a.__class__.__name__ for a in self.modules]
        index = module_names.index(name)
        return self.modules[index]

    def Save(self):
        BroadCastEvent(self.modules, "save")
        #self.data_file.check_to_save()

    def SaveDatabase(self, srcpath=None):
        if not self.data_file:
            return
        if srcpath is None:
            srcpath = QtWidgets.QFileDialog.getSaveFileName(None, "Save project - ClickPoints", os.getcwd(), "ClickPoints Database *.cdb")
        if isinstance(srcpath, tuple):
            srcpath = srcpath[0]
        else:
            srcpath = str(srcpath)
        if srcpath:
            self.data_file.save_database(file=srcpath)
            BroadCastEvent(self.modules, "DatabaseSaved")
            self.JumpFrames(0)

    def log(self, *args, **kwargs):
        self.GetModule("Console").log(*args, **kwargs)

    """ jumping frames and displaying images """

    def JumpFrames(self, amount):
        # redirect to an absolute jump
        self.JumpToFrame(self.target_frame + amount)

    # jump absolute
    def JumpToFrame(self, target_id, threaded=True):
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
        if self.loading_image == -1:
            self.loading_image = 1
        else:
            self.loading_image += 1

        if self.data_file.getOption("threaded_image_load") and threaded:
            self.data_file.load_frame(target_id, layer=self.layer, threaded=1)
        else:
            self.data_file.load_frame(target_id, layer=self.layer, threaded=0)

    def FrameLoaded(self, frame_number, threaded=True):
        # set the index of the current frame
        self.data_file.set_image(frame_number)

        # get filename and frame number
        self.new_filename = self.data_file.image.filename
        self.new_frame_number = self.target_frame

        # Notify that the frame will be loaded TODO are all these events necessary?
        BroadCastEvent(self.modules, "FrameChangeEvent")
        BroadCastEvent(self.modules, "PreLoadImageEvent", self.new_filename, self.new_frame_number)
        self.setWindowTitle("%s - %s - ClickPoints - Layer %s" % (self.new_filename, self.data_file.getFilename(), self.layer))

        # get image
        self.im = self.data_file.get_image_data()

        # get offsets
        offset = self.data_file.get_offset()

        # display the image
        self.ImageDisplay.SetImage(self.im, offset, threaded)  # calls DisplayedImage

    def DisplayedImage(self):
        # tell the QExtendedGraphicsView the shape of the new image
        self.view.setExtend(*self.im.shape[:2][::-1])

        # notify all modules that a new frame is loaded
        BroadCastEvent(self.modules, "LoadImageEvent", self.new_filename, self.new_frame_number)

        self.loading_image -= 1

    """ some Qt events which should be passed around """

    def testForUnsaved(self):
        if self.data_file is not None and not self.data_file.exists and self.data_file.made_changes:
            reply = QtWidgets.QMessageBox.question(self, 'Warning', 'This ClickPoints project has not been saved. '
                                                                    'All data will be lost.\nDo you want to save it?',
                                                   QtWidgets.QMessageBox.Yes,
                                                   QtWidgets.QMessageBox.No)

            if reply == QtWidgets.QMessageBox.Yes:
                self.SaveDatabase()

    def closeEvent(self, QCloseEvent):
        self.testForUnsaved()
        # close the folder editor
        if self.folderEditor is not None:
            self.folderEditor.close()
        # save the data
        self.Save()
        # broadcast event
        if self.data_file is not None:
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

        if event.key() == QtCore.Qt.Key_T:
            # @key T: set pixel scale to 1
            self.view.scaleOrigin(1./self.view.getOriginScale(), QtCore.QPoint(0, 0))
            
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
            step = self.data_file.getOption("rotation_steps")
            self.data_file.setOption("rotation", (self.data_file.getOption("rotation")+step) % 360)
            self.view.rotate(step)

        if event.key() == QtCore.Qt.Key_S:
            # @key S: save marker and mask
            self.data_file.save_database()
            self.Save()

        if event.key() == QtCore.Qt.Key_PageUp:
            # @key PageUp: show next upper layer
            self.layer += 1
            self.JumpFrames(0)


        if event.key() == QtCore.Qt.Key_PageDown:
            # @key PageDown: show next lower layer
            self.layer -= 1
            self.JumpFrames(0)

        if event.key() == QtCore.Qt.Key_Escape:
            # @key Escape: close window
            self.close()


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
            for cur_index in rotate_list(list(range(len(self.modules))), index+1):
                if "setActiveModule" in dir(self.modules[cur_index]) and self.modules[cur_index].setActiveModule(True):
                    break

        if self.data_file is None:
            return

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
        for key, jump in zip(keys, self.data_file.getOption("jumps")):
            if event.key() == key and event.modifiers() == Qt.KeypadModifier:
                self.JumpFrames(jump)


def main():
    from ClickPointsBooster import BoosterRunning
    BoosterRunning()
    app, splash = StartSplashScreen()

    # set an application id, so that windows properly stacks them in the task bar
    if sys.platform[:3] == 'win':
        myappid = 'fabrybiophysics.clickpoints'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    # load config and exec addon code
    config = LoadConfig()

    # init and open the ClickPoints window
    window = ClickPointsWindow(config, app)
    window.show()
    StopSplashScreen(window)
    app.exec_()

# start the main function as entry point
if __name__ == '__main__':
    main()
