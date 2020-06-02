#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Core.py

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

from __future__ import division, print_function

import sys
import os
import glob
import natsort

import threading
import time
import numpy as np
import asyncio

from qtpy import QtGui, QtCore, QtWidgets
from qtpy.QtCore import Qt
import qtawesome as qta

from .includes import HelpText, BroadCastEvent, SetBroadCastModules, rotate_list
from .includes import BigImageDisplay
from .includes import QExtendedGraphicsView
from .includes.FilelistLoader import FolderEditor, addPath, addList, imgformats, vidformats
from .includes import Database

from .modules.ChangeTracker import ChangeTracker
from .modules.MaskHandler import MaskHandler
from .modules.MarkerHandler import MarkerHandler
from .modules.Timeline import Timeline
from .modules.AnnotationHandler import AnnotationHandler
from .modules.GammaCorrection import GammaCorrection
from .modules.ScriptLauncher import ScriptLauncher
from .modules.VideoExporter import VideoExporter
from .modules.InfoHud import InfoHud
from .modules.Console import Console
from .modules.OptionEditor import OptionEditor

from PyQt5.QtCore import QPoint, QPointF
from PyQt5.QtGui import QCloseEvent, QKeyEvent, QResizeEvent
from PyQt5.QtWidgets import QApplication
from clickpoints.includes.ConfigLoad import dotdict
from clickpoints.modules.ChangeTracker import ChangeTracker
from clickpoints.modules.MarkerHandler import MarkerHandler
from clickpoints.modules.Timeline import Timeline
from typing import Any, List, Union
class AddVLine():
    def __init__(self, window: "ClickPointsWindow") -> None:
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.VLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        window.layoutButtons.addWidget(line)

class AddStrech():
    def __init__(self, window: "ClickPointsWindow") -> None:
        window.layoutButtons.addStretch()

used_modules = [ChangeTracker, AddVLine, Timeline, GammaCorrection, VideoExporter, AddVLine, AnnotationHandler, MarkerHandler, MaskHandler, AddVLine, InfoHud, ScriptLauncher, AddStrech, HelpText, OptionEditor, Console]
used_huds = ["", "", "", "hud_lowerRight", "", "", "", "hud", "hud_upperRight", "", "hud_lowerLeft", "", "", "", "", "", "", ""]


def GetModuleInitArgs(mod: Any) -> List[str]:
    import inspect
    return inspect.getfullargspec(mod.__init__).args


class ClickPointsWindow(QtWidgets.QWidget):
    folderEditor = None
    optionEditor = None
    first_frame = 0

    load_thread = None
    data_file = None

    signal_jump = QtCore.Signal(int)
    signal_jumpTo = QtCore.Signal(int)
    signal_broadcast = QtCore.Signal(str, tuple)

    def __init__(self, my_config: dotdict, app: QApplication, parent: QtWidgets.QWidget = None) -> None:
        global config, storage_path
        config = my_config

        self.app = app
        super(QtWidgets.QWidget, self).__init__(parent)
        self.setWindowIcon(QtGui.QIcon(QtGui.QIcon(os.path.join(os.environ["CLICKPOINTS_ICON"], "ClickPoints.ico"))))

        self.setMinimumWidth(650)
        self.setMinimumHeight(400)
        self.setWindowTitle("ClickPoints")

        self.scale_factor = app.desktop().logicalDpiX()/96

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
        QtGui.QFontDatabase.addApplicationFont(os.path.join(os.environ["CLICKPOINTS_ICON"], "FantasqueSansMono-Regular.ttf"))
        self.mono_font = QtGui.QFont("Fantasque Sans Mono")

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
        self.view.panEvent = self.panEvent
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

        self.changeTracker = self.GetModule("ChangeTracker")

        #self.layoutButtons.addStretch()

        # find next module, which can be activated
        for module in self.modules:
            if "setActiveModule" in dir(module) and module.setActiveModule(True, True):
                break

        # initialize some variables
        self.im = None
        self.layer_index = 1
        self.current_layer = None

        # select the first frame
        self.target_frame = 0

        # set focus policy for buttons
        for i in range(self.layoutButtons.count()):
            if self.layoutButtons.itemAt(i).widget():
                self.layoutButtons.itemAt(i).widget().setFocusPolicy(Qt.NoFocus)

        self.signal_jump.connect(self.JumpFrames)
        self.signal_jumpTo.connect(self.JumpToFrame)
        self.signal_broadcast.connect(lambda s, a: BroadCastEvent(self.modules, s, *a))

        self.setFocus()

        self.start_timer = QtCore.QTimer.singleShot(1, lambda: self.loadUrl(config.srcpath))

        self.app.processEvents()

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
        # accept url lists (files by drag and drop)
        if event.mimeData().hasFormat("text/uri-list"):
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QtGui.QDragMoveEvent):
        event.acceptProposedAction()

    def dropEvent(self, event: QtCore.QEvent):
        if self.load_thread is not None:
            self.load_thread.join()
        for url in event.mimeData().urls():
            url = str(url.toString()).strip()
            if url.startswith("file:///"):
                url = url[len("file:///"):]
            if url.startswith("file:"):
                url = url[len("file:"):]
            self.loadUrl(url, reset=True)

    def loadUrl(self, url: str, reset: bool = False) -> None:
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
                elif ext.lower() in vidformats or ext.lower() == ".vms":
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

    def loadObject(self, url: str) -> None:
        #TODO: rebuild threaded version for glob, replace duplicated code above with this function
        """
        Loads objects of type directory, img or video file
        HACKED the non thread version as i couldnt get threaded to work ...

        :param url: path to object
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


    def reset(self, filename: str = "") -> None:
        if self.data_file is not None:
            # ask to save current data
            self.testForUnsaved()
            # close database
            self.data_file.closeEvent(None)
            BroadCastEvent(self.modules, "closeDataFile")
        # open new database
        self.data_file = Database.DataFileExtended(filename, config, storage_path=os.environ["CLICKPOINTS_TMP"])
        #self.data_file.signals.loaded.connect(self.FrameLoaded)
        # apply image rotation from config
        if self.data_file.getOption("rotation") != 0:
            self.view.rotate(self.data_file.getOption("rotation"))
        BroadCastEvent(self.modules, "updateDataFile", self.data_file, filename == "")
        self.GetModule("Timeline").ImagesAdded()

    def LoadTimer(self) -> None:
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

    def Folder(self) -> None:
        if not self.data_file:
            return
        self.folderEditor = FolderEditor(self, self.data_file)
        self.folderEditor.show()

    def ImagesAdded(self) -> None:
        if self.data_file.image is None and self.data_file.get_image_count():
            self.JumpToFrame(0)
            self.view.fitInView()

    def GetModule(self, name: str) -> QtCore.QObject:
        module_names = [a.__class__.__name__ for a in self.modules]
        index = module_names.index(name)
        return self.modules[index]

    def Save(self) -> None:
        BroadCastEvent(self.modules, "save")
        #self.data_file.check_to_save()

    def SaveDatabase(self, srcpath=None) -> None:
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

    def log(self, *args, **kwargs) -> None:
        self.GetModule("Console").log(*args, **kwargs)

    """ jumping frames and displaying images """

    def reloadImage(self, target_id: int = None, layer_id: int = None) -> None:
        print("reloadImage")
        if target_id is None:
            target_id = self.target_frame
        if layer_id is None:
            layer_id = self.current_layer
        self.data_file.buffer.remove_frame(target_id, layer_id)
        self.JumpFrames(0)

    def JumpFrames(self, amount: int) -> None:
        # redirect to an absolute jump
        self.JumpToFrame(self.target_frame + amount)

    # jump absolute
    def JumpToFrame(self, target_id: int, threaded: bool = True) -> None:
        asyncio.ensure_future(self.load_frame(target_id), loop=self.app.loop)

    async def load_frame(self, target_id: int, layer_id: None = None) -> None:
        # if no frame is loaded yet, do nothing
        if self.data_file.get_image_count() == 0:
            return

        # save the data on frame change
        self.Save()

        # Test if the new frame is valid
        if target_id >= self.data_file.get_image_count():
            if self.target_frame == self.data_file.get_image_count() - 1:
                target_id = 0
            else:
                target_id = self.data_file.get_image_count() - 1

        if target_id < 0:
            if self.target_frame == 0:
                target_id = self.data_file.get_image_count() - 1
            else:
                target_id = 0

        # ensure that we have a layer
        if self.current_layer is None:
            self.current_layer = self.data_file.table_layer.select().paginate(self.layer_index, 1)[0]
            BroadCastEvent(self.modules, "LayerChangedEvent", self.current_layer.id)
        layer_id = self.current_layer

        # get the database entry of the image
        image_object = self.data_file.table_image.get(sort_index=target_id, layer_id=layer_id.id)

        # load the image from disk
        image = await self.data_file.load_frame_async(image_object, target_id, layer=layer_id)

        # set the index of the current frame
        self.data_file.set_image(target_id, layer_id)

        # Notify that the frame will be loaded
        BroadCastEvent(self.modules, "frameChangedEvent")
        self.setWindowTitle("%s - %s - ClickPoints - Layer %s" % (image_object.filename, self.data_file.getFilename(), self.current_layer.name))

        # display the image
        await self.ImageDisplay.SetImage_async(image, self.data_file.get_offset())

        # tell the QExtendedGraphicsView the shape of the new image
        self.view.setExtend(*image.shape[:2][::-1])

        # notify all modules that a new frame is loaded
        BroadCastEvent(self.modules, "imageLoadedEvent", image_object.filename, target_id)

        self.target_frame = target_id

    def CenterOn(self, x: float, y: float) -> None:
        print("Center on: %d %d" % (x,y))
        self.view.centerOn(float(x),float(y))

    """ some Qt events which should be passed around """

    def testForUnsaved(self) -> bool:
        if self.data_file is not None and not self.data_file.exists and self.data_file.made_changes:
            reply = QtWidgets.QMessageBox.question(self, 'Warning', 'This ClickPoints project has not been saved. '
                                                                    'All data will be lost.\nDo you want to save it?',
                                                   QtWidgets.QMessageBox.Cancel | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Yes,
                                                   QtWidgets.QMessageBox.Yes)

            if reply == QtWidgets.QMessageBox.Cancel:
                return -1
            if reply == QtWidgets.QMessageBox.Yes:
                self.SaveDatabase()
        return True

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.testForUnsaved() == -1:
            return event.ignore()
        # close the folder editor
        if self.folderEditor is not None:
            self.folderEditor.close()
        # save the data
        self.Save()
        # broadcast event
        if self.data_file is not None:
            self.data_file.closeEvent(event)
        # broadcast event to the modules
        BroadCastEvent(self.modules, "closeEvent", event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        # broadcast event to the modules
        BroadCastEvent(self.modules, "resizeEvent", event)

    def zoomEvent(self, scale: float, pos: Union[QPoint, QPointF]) -> None:
        # broadcast event to the modules
        BroadCastEvent(self.modules, "zoomEvent", scale, pos)

    def panEvent(self, xoff: float, yoff: float) -> None:
        # broadcast event to the modules
        BroadCastEvent(self.modules, "panEvent", xoff, yoff)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        # broadcast event to the modules
        BroadCastEvent(self.modules, "keyReleaseEvent", event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
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

        if event.key() == Qt.Key_G:
            self.ImageDisplay.updateSlideView()

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
            try:
                self.current_layer = self.data_file.table_layer.select().paginate(self.layer_index + 1, 1)[0]
            except IndexError:
                pass
            else:
                self.layer_index += 1
                self.JumpFrames(0)
                BroadCastEvent(self.modules, "LayerChangedEvent", self.current_layer.id)

        if event.key() == QtCore.Qt.Key_PageDown:
            # @key PageDown: show next lower layer
            if self.layer_index > 1:
                self.current_layer = self.data_file.table_layer.select().paginate(self.layer_index - 1, 1)[0]
                self.layer_index -= 1
                BroadCastEvent(self.modules, "LayerChangedEvent", self.current_layer.id)
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

        # @key ---- Zoom ----
        if event.key() == QtCore.Qt.Key_Plus and event.modifiers() & Qt.ControlModifier:
            # @key Cntrl+'+' or MouseWheel: zoom in
            self.view.scaleOrigin(1.1, QtCore.QPoint(self.view.width()/2, self.view.height()/2))
        if event.key() == QtCore.Qt.Key_Minus and event.modifiers() & Qt.ControlModifier:
            # @key Ctrl+'-' or MouseWheel: zoom out
            self.view.scaleOrigin(0.9, QtCore.QPoint(self.view.width()/2, self.view.height()/2))

        # @key ---- Frame jumps ----
        if event.key() == QtCore.Qt.Key_Left and not event.modifiers() & Qt.ControlModifier:
            # @key Left: previous image
            self.JumpFrames(-1)
        if event.key() == QtCore.Qt.Key_Right and not event.modifiers() & Qt.ControlModifier:
            # @key Right: next image
            self.JumpFrames(+1)

        if event.key() == QtCore.Qt.Key_Home and not event.modifiers() & Qt.ControlModifier:
            # @key Home: jump to beginning
            self.JumpToFrame(0)
        if event.key() == QtCore.Qt.Key_End and not event.modifiers() & Qt.ControlModifier:
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
