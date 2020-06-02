#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ScriptLauncher.py

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

import os
import socket
import sys
import traceback
from typing import Any, Callable, List, Union

import qtawesome as qta
from qtpy import QtCore, QtGui, QtWidgets

from clickpoints.includes.ConfigLoad import dotdict
from clickpoints.includes.Database import DataFileExtended

try:
    import SocketServer  # python 2

    socketobject = socket._socketobject
except ImportError:
    import socketserver as SocketServer  # python 3

    socketobject = socket.socket

import time
import glob

try:
    import ConfigParser
except ImportError:
    import configparser as ConfigParser
from importlib import import_module
import pip

if int(pip.__version__.split('.')[0]) > 9:
    from pip._internal import main
else:
    from pip import main


def install(package_name):
    main(['install', package_name])


try:
    # python 3
    from importlib import reload

    py2 = False
except ImportError:
    # python 2
    reload
    py2 = True


def check_packages_installed(package_name: str) -> bool:
    """ check if a package is installed"""

    # some packages have other names when they are imported compared to the install name
    translation_names = {"pillow": "PIL", "scikit-image": "skimage", "opencv-python": "cv2", "opencv": "cv2"}

    # translate the package name if it is in the list
    if package_name in translation_names:
        package_name = translation_names[package_name]

    # use importlib for python3
    try:
        # python 3
        import importlib.util
    except ImportError:
        # python 2
        import pip
        # or pip for python 2
        installed_packages = pip.get_installed_distributions()
        return package_name in [p.project_name for p in installed_packages]

    # try to find the package and return True if it was found
    spec = importlib.util.find_spec(package_name)
    if spec is None:
        return False
    return True


def get_clickpoints_addons() -> List[str]:
    import sys
    addons = []
    for p in sys.path:
        try:
            for path in os.listdir(p):
                path = os.path.join(p, path)
                if os.path.isdir(path):
                    addon_file = os.path.join(path, "__clickpoints_addon__.txt")
                    if os.path.exists(addon_file):
                        with open(addon_file) as fp:
                            for line in fp:
                                line = line.strip()
                                if line == "":
                                    continue
                                # if the path is not an absolute path, define it relative to the path of the .txt file
                                if not os.path.isabs(line):
                                    line = os.path.join(path, line)
                                addons.append(line)
        except (FileNotFoundError, NotADirectoryError):
            pass
    return addons


# implement the fallback keyword for the ConfigParser in Python 2.7
def wrap_get(function: Callable) -> Callable:
    def wrapper(section, name, raw=True, fallback=None):
        try:
            return function(section, name, raw=raw)
        except ConfigParser.NoOptionError:
            return fallback

    return wrapper


class Script(QtCore.QObject):
    active = False
    loaded = False

    addon_class_instance = None

    script_launcher = None
    button = None

    def __init__(self, filename: str) -> None:
        QtCore.QObject.__init__(self)
        self.filename = filename
        parser = ConfigParser.ConfigParser()
        # for python 2 compatibility implement the fallback parameter, which is already there for python 3
        parser.get = wrap_get(parser.get)
        parser.read(filename)
        self.name = parser.get("addon", "name", fallback=os.path.split(os.path.dirname(filename))[1])
        try:
            self.description = parser.get("addon", "description", fallback="")
        except ConfigParser.NoOptionError:
            self.description = ""
        if self.description is "":
            path = os.path.join(os.path.dirname(filename), "Desc.html")
            try:
                with open(path) as fp:
                    self.description = fp.read()
            except IOError:
                self.description = "<i>no description available</i>"
        self.icon = parser.get("addon", "icon", fallback="fa.code")
        self.icon_name = self.icon
        self.script = parser.get("addon", "file", fallback="Script.py")
        self.script = os.path.join(os.path.dirname(filename), self.script)
        self.requirements = parser.get("addon", "requirements", fallback="")
        self.requirements = [s.strip() for s in self.requirements.split(",") if s.strip() is not ""]
        self.image = parser.get("addon", "image", fallback="")
        if self.image:
            self.image = os.path.join(os.path.dirname(filename), self.image)

        try:
            self.icon = qta.icon(self.icon)
        except Exception as err:
            try:
                self.icon = QtGui.QIcon(self.icon)
            except Exception as err:
                print("ERROR: the icon %s is neither a valid qtawsome icon nor a valid filename." % self.icon_name)
                self.icon_name = "fa.code"
                self.icon = qta.icon(self.icon_name)

        self.hourglassAnimationTimer = QtCore.QTimer()
        self.hourglassAnimationTimer.timeout.connect(self.displayHourglassAnimation)

    def activate(self, script_launcher: "ScriptLauncher", silent: bool = False) -> bool:
        self.script_launcher = script_launcher
        path = os.path.abspath(self.script)
        name = os.path.splitext(os.path.basename(path))[0]
        # check requirements
        needed_packages = []
        for package_name in self.requirements:
            if not check_packages_installed(package_name):
                needed_packages.append(package_name)
        print("needed_packages", needed_packages, len(needed_packages))
        if len(needed_packages):
            reply = QtWidgets.QMessageBox.question(self.script_launcher.scriptSelector, 'Warning - ClickPoints',
                                                   'The add-on requires the following packages: %s\nDo you want to install them?' % (
                                                       ", ".join(needed_packages)),
                                                   QtWidgets.QMessageBox.Yes,
                                                   QtWidgets.QMessageBox.No)
            if reply == QtWidgets.QMessageBox.No:
                return
            for package_name in needed_packages:
                install(package_name)
        folder, filename = os.path.split(path)
        path, folder = os.path.split(folder)
        basefilename, ext = os.path.splitext(filename)
        print("import add-on path", path)
        if py2:
            sys.path.insert(0, os.path.join(path, folder))
        else:
            sys.path.insert(0, path)
        try:
            if not self.loaded:
                try:
                    print("import", folder + "." + basefilename)
                    if py2:
                        self.addon_module = import_module(basefilename)
                    else:
                        self.addon_module = import_module(folder + "." + basefilename)
                except Exception as err:
                    QtWidgets.QMessageBox.critical(self.script_launcher.scriptSelector, 'Error - ClickPoints',
                                                   'An exception occurred when trying to import add-on %s:\n%s' % (
                                                   name, err),
                                                   QtWidgets.QMessageBox.Ok)
                    raise err
                self.loaded = True
            else:
                self.addon_module = reload(self.addon_module)
        finally:
            sys.path.pop(0)
        if "Addon" not in dir(self.addon_module):
            raise NameError("No addon module found in " + path)
        try:
            self.addon_class_instance = self.addon_module.Addon(script_launcher.data_file, script_launcher, self.name,
                                                                icon=self.icon)
        except Exception as err:
            traceback.print_exc()
            return False

        self.active = True
        if not silent:
            QtWidgets.QMessageBox.information(self.script_launcher.scriptSelector, 'Add-on - ClickPoints',
                                              'The add-on %s has been activated.' % name, QtWidgets.QMessageBox.Ok)
        return True

    def deactivate(self):
        try:
            self.addon_class_instance.delete()
            self.addon_class_instance.close()
        except Exception as err:
            print(err)
        self.active = False
        self.button = None

    def displayHourglassAnimation(self) -> None:
        spin_icon = qta.icon(self.icon_name,
                             'fa.hourglass-%d' % (int(self.hourglassAnimationTimer.duration() * 2) % 3 + 1),
                             options=[{},
                                      {'scale_factor': 0.9, 'offset': (0.3, 0.2), 'color': QtGui.QColor(128, 0, 0)}])
        self.button.setIcon(spin_icon)
        self.button.setChecked(True)

    def setStatus(self, status: int) -> None:
        if self.button is None:
            return

        # STATUS_Running
        if status == 2:
            self.hourglassAnimationTimer.start_time = time.time()
            self.hourglassAnimationTimer.duration = lambda: time.time() - self.hourglassAnimationTimer.start_time
            self.hourglassAnimationTimer.start()
        # STATUS_Active
        elif status == 1:
            self.button.setIcon(self.icon)
            self.button.setChecked(True)
            self.hourglassAnimationTimer.stop()
        # STATUS_Idle
        else:
            self.button.setIcon(self.icon)
            self.button.setChecked(False)
            self.hourglassAnimationTimer.stop()

    def run(self) -> None:
        self.addon_class_instance.buttonPressedEvent()

    def reload(self):
        button = self.button
        self.deactivate()
        self.activate(self.script_launcher)
        self.button = button


class ScriptChooser(QtWidgets.QWidget):
    def __init__(self, script_launcher: "ScriptLauncher") -> None:
        QtWidgets.QWidget.__init__(self)
        self.script_launcher = script_launcher

        # Widget
        self.setMinimumWidth(700)
        self.setMinimumHeight(400)
        self.setWindowTitle("Add-on Browser - ClickPoints")
        self.layout_main = QtWidgets.QHBoxLayout(self)
        self.layout = QtWidgets.QVBoxLayout()
        self.layout_main.addLayout(self.layout)
        self.layout2 = QtWidgets.QVBoxLayout()
        self.layout_main.addLayout(self.layout2)

        self.setWindowIcon(qta.icon("fa.code"))

        self.list2 = QtWidgets.QListWidget(self)
        self.layout.addWidget(self.list2)
        self.list2.itemSelectionChanged.connect(self.list_selected2)

        layout = QtWidgets.QHBoxLayout()
        self.layout.addLayout(layout)
        self.button_import = QtWidgets.QPushButton("Import")
        self.button_import.clicked.connect(self.importScript)
        layout.addWidget(self.button_import)
        layout.addStretch()

        layout2b = QtWidgets.QVBoxLayout()
        self.layout2.addLayout(layout2b)
        # self.nameDisplay = QtWidgets.QLabel(self)
        self.nameDisplay = QtWidgets.QTextEdit(self)
        self.nameDisplay.setReadOnly(True)
        self.nameDisplay.setMaximumHeight(37)
        self.nameDisplay.setStyleSheet(
            "border-width: 1px; border-bottom-width: 0px; border-color: darkgray; border-style: solid; /* just a single line */; border-top-right-radius: 0px; /* same radius as the QComboBox */;")
        layout2b.setSpacing(0)
        layout2b.addWidget(self.nameDisplay)

        self.imageDisplay = QtWidgets.QLabel(self)
        # self.layout2.addWidget(self.imageDisplay)

        self.textDisplay = QtWidgets.QTextEdit(self)
        self.textDisplay.setReadOnly(True)
        self.textDisplay.setStyleSheet(
            "border-width: 1px; border-top-width: 0px; border-color: darkgray; border-style: solid; /* just a single line */; border-top-right-radius: 0px; /* same radius as the QComboBox */;")
        layout2b.addWidget(self.textDisplay)

        self.layout_buttons = QtWidgets.QHBoxLayout()
        self.layout2.addLayout(self.layout_buttons)
        self.layout_buttons.addStretch()

        self.button_removeAdd = QtWidgets.QPushButton("Remove")
        self.button_removeAdd.clicked.connect(self.add_script)
        self.layout_buttons.addWidget(self.button_removeAdd)

        self.selected_script = None

        self.update_folder_list2()

    def importScript(self):
        srcpath = QtWidgets.QFileDialog.getOpenFileName(None, "Import Add-on - ClickPoints", os.getcwd(),
                                                        "ClickPoints Scripts *.txt")
        if isinstance(srcpath, tuple):
            srcpath = srcpath[0]
        else:
            srcpath = str(srcpath)
        if srcpath:
            try:
                script = Script(srcpath)
            except ConfigParser.NoSectionError:
                reply = QtWidgets.QMessageBox.critical(self, 'Error',
                                                       "Can not import selected file:\n%s\nThe selected file is no valid ClickPoints add-on file." % srcpath,
                                                       QtWidgets.QMessageBox.Ok)
            else:
                self.script_launcher.scripts.append(script)
                self.update_folder_list2()

    def list_selected2(self) -> None:
        selections = self.list2.selectedItems()
        if len(selections) == 0:
            self.button_removeAdd.setDisabled(True)
            self.selected_script = None
            return
        script = selections[0].entry
        self.selected_script = script
        self.nameDisplay.setText("<h1>" + script.name + "</h1>")

        if script.image:
            with open(script.image, "rb") as fp:
                import base64
                image = bytes(base64.b64encode(fp.read())).decode()
            html = '<img src="data:image/png;base64,{}" style="border: 10px solid black;">'.format(image)
            self.textDisplay.setHtml(html + script.description)
        else:
            self.textDisplay.setHtml(script.description)
        if script.active:
            self.button_removeAdd.setText("Deactivate")
            self.button_removeAdd.setDisabled(False)
        else:
            self.button_removeAdd.setText("Activate")
            self.button_removeAdd.setDisabled(False)
        return

    def update_folder_list2(self) -> None:
        self.list2.clear()
        for index, script in enumerate(self.script_launcher.scripts):
            text = script.name
            if script.active:
                text += " (active)"
            item = QtWidgets.QListWidgetItem(script.icon, text, self.list2)
            item.entry = script

    def add_script(self) -> None:
        if self.selected_script.active:
            self.script_launcher.deactivateScript(self.selected_script)
        else:
            self.script_launcher.activateScript(self.selected_script)
        self.update_folder_list2()
        self.script_launcher.updateScripts()

    def keyPressEvent(self, event):
        # close the window with esc
        if event.key() == QtCore.Qt.Key_Escape:
            self.close()


class ScriptLauncher(QtCore.QObject):
    signal = QtCore.Signal(str, socketobject, tuple)

    scriptSelector = None

    data_file = None
    config = None

    scripts = None
    active_scripts = None

    def __init__(self, window: "ClickPointsWindow", modules: List[Any]) -> None:
        QtCore.QObject.__init__(self)
        self.window = window
        self.modules = modules

        self.button = QtWidgets.QPushButton()
        self.button.setIcon(qta.icon("fa.external-link"))
        self.button.clicked.connect(self.showScriptSelector)
        self.button.setToolTip("load/remove add-ons")
        self.window.layoutButtons.addWidget(self.button)

        self.button_group_layout = QtWidgets.QHBoxLayout()
        self.button_group_layout.setContentsMargins(0, 0, 0, 0)  # setStyleSheet("margin: 0px; padding: 0px;")
        self.script_buttons = []
        self.window.layoutButtons.addLayout(self.button_group_layout)

        self.script_path = os.path.normpath(os.environ["CLICKPOINTS_ADDON"])

        self.closeDataFile()

    def loadScripts(self) -> List[Script]:
        scripts = glob.glob(os.path.join(os.environ["CLICKPOINTS_ADDON"], "*", '*.txt'))
        scripts.extend(get_clickpoints_addons())
        loaded_scripts = []
        for filename in scripts:
            try:
                loaded_scripts.append(Script(filename))
            except:
                print("ERROR: Loading add-on %s failed" % filename)
                pass
        return loaded_scripts

    def closeDataFile(self) -> None:
        self.data_file = None
        self.config = None
        self.scripts = self.loadScripts()
        self.active_scripts = []
        self.updateScripts()
        if self.scriptSelector:
            self.scriptSelector.close()

    def updateDataFile(self, data_file: DataFileExtended, new_database: bool) -> None:
        self.data_file = data_file
        self.config = data_file.getOptionAccess()
        self.scripts = self.loadScripts()

        for script in self.data_file.getOption("scripts"):
            self.activateScript(script, silent=True)

        self.updateScripts()

    def activateScript(self, script_name: Union[Script, str], silent: bool = False) -> None:
        script = self.getScriptByFilename(script_name)
        if script is not None:
            if script.activate(self, silent=silent):
                self.active_scripts.append(script)
            else:
                print("Add-on %s could not be activated" % script.name, file=sys.stderr)
        else:
            print("Add-on %s could not be loaded" % script_name, file=sys.stderr)

    def deactivateScript(self, script: Script) -> None:
        script = self.getScriptByFilename(script)
        if script is not None:
            self.active_scripts.remove(script)
            script.deactivate()

    def getScriptByFilename(self, filename: Union[Script, str]) -> Script:
        if isinstance(filename, Script):
            return filename
        filename = os.path.normpath(filename)
        if self.scripts:
            filenames = [os.path.normpath(s.filename) for s in self.scripts]
            if filename in filenames:
                return self.scripts[filenames.index(filename)]
        try:
            script = Script(filename)
            self.scripts.append(script)
            return script
        except (FileNotFoundError, ConfigParser.NoSectionError):
            return None

    def updateScripts(self) -> None:
        if self.data_file is not None:
            self.data_file.setOption("scripts", [os.path.normpath(s.filename) for s in self.active_scripts])
        for button in self.script_buttons:
            self.button_group_layout.removeWidget(button)
            button.setParent(None)
            del button
        self.script_buttons = []
        for index, script in enumerate(self.active_scripts):
            button = QtWidgets.QPushButton()
            button.setCheckable(True)
            button.setIcon(script.icon)
            button.setToolTip(script.name)
            button.clicked.connect(lambda x, i=index: self.launch(i))
            self.button_group_layout.addWidget(button)
            self.script_buttons.append(button)
            script.button = button

    def receiveBroadCastEvent(self, function: str, *args, **kwargs) -> None:
        for script in self.scripts:
            if function in dir(script.addon_class_instance):
                try:
                    getattr(script.addon_class_instance, function)(*args, **kwargs)
                except:
                    print("Calling", script.addon_class_instance, function, args, kwargs, file=sys.stderr)
                    traceback.print_exc()

    def showScriptSelector(self) -> None:
        self.scriptSelector = ScriptChooser(self)
        self.scriptSelector.show()

    def launch(self, index: int) -> None:
        self.window.Save()
        script = self.active_scripts[index]
        script.run()
        print("Launch", index)

    def reload(self, index: int) -> None:
        script = self.active_scripts[index]
        script.reload()
        print("Reload", index)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        keys = [QtCore.Qt.Key_F12, QtCore.Qt.Key_F11, QtCore.Qt.Key_F10, QtCore.Qt.Key_F9, QtCore.Qt.Key_F8,
                QtCore.Qt.Key_F7, QtCore.Qt.Key_F6, QtCore.Qt.Key_F5]
        for index, key in enumerate(keys):
            # @key F12: Launch
            if event.key() == key:
                if event.modifiers() & QtCore.Qt.ControlModifier:
                    self.reload(index)
                else:
                    self.launch(index)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self.scriptSelector:
            self.scriptSelector.close()
        for script in self.active_scripts:
            script.addon_class_instance.close()

    def setStatus(self, name: str, status: int) -> None:
        for script in self.active_scripts:
            if script.name == name:
                script.setStatus(status)

    @staticmethod
    def file() -> str:
        return __file__

    @staticmethod
    def can_create_module(config: dotdict) -> int:
        return 1
