#!/usr/bin/env python
# -*- coding: utf-8 -*-
# FilelistLoader.py

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

import glob
import os
import sys
import time
from datetime import datetime
from typing import List

import imageio
import qtawesome as qta
from qtpy import QtWidgets

from clickpoints.includes.Database import DataFileExtended
from clickpoints.includes.Tools import BroadCastEvent2

print("Using ImageIO", imageio.__version__)
try:
    from natsort import natsorted
except ImportError:
    natsorted = sorted

try:
    import openslide

    openslide_loaded = True
    print("openslide", openslide.__version__)
except ImportError:
    openslide_loaded = False
    print("use custom openslide variant with tifffile")
    from .slide import myslide


    class lowlevel:
        OpenSlideUnsupportedFormatError = IOError


    class openslide:
        OpenSlide = myslide
        lowlevel = lowlevel


    openslide_loaded = True

# add plugins to imageIO if available
plugin_searchpath = os.path.join(os.path.split(__file__)[0], '..', r'addons/imageio_plugin')
sys.path.append(plugin_searchpath)
if os.path.exists(plugin_searchpath):
    print("Searching ImageIO Plugins ...")
    plugin_list = os.listdir(os.path.abspath(plugin_searchpath))
    for plugin in plugin_list:
        if plugin.startswith('imageio_plugin_') and plugin.endswith('.py'):
            # importlib.import_module(os.path.splitext(plugin)[0])
            print(os.path.sep.join([os.path.abspath(plugin_searchpath), plugin]))
            import importlib.util

            spec = importlib.util.spec_from_file_location(plugin.replace(".py", ""),
                                                          os.path.sep.join([os.path.abspath(plugin_searchpath), plugin])
                                                          )
            imageio_plugin = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(imageio_plugin)
            # importlib.import_module(os.path.sep.join([os.path.abspath(plugin_searchpath), plugin]))
            # print(os.path.abspath(plugin_searchpath))
            print('Adding %s' % plugin)

# check for ffmpeg
try:
    # check if imageio already has an exe file
    imageio.plugins.ffmpeg.get_exe()
    print("ffmpeg found from imageio")
except imageio.core.fetching.NeedDownloadError:
    # try to find an ffmpeg.exe in the ClickPoints folder
    files = glob.glob(os.path.join(os.path.dirname(__file__), "..", "ffmpeg*.exe"))
    files.extend(glob.glob(os.path.join(os.path.dirname(__file__), "..", "external", "ffmpeg*.exe")))
    # if an ffmpeg exe has been found, set the environmental variable accordingly
    if len(files):
        print("ffmpeg found", files[0])
        os.environ['IMAGEIO_FFMPEG_EXE'] = files[0]
    # if not, try to download it
    else:
        print("try to download ffmpeg")
        imageio.plugins.ffmpeg.download()

imgformats = []
for format in imageio.formats:
    if 'i' in format.modes:
        imgformats.extend(format._extensions)
imgformats = [fmt if fmt[0] == "." else "." + fmt for fmt in imgformats]
vidformats = []
for format in imageio.formats:
    if 'I' in format.modes:
        vidformats.extend(format._extensions)
vidformats = [fmt if fmt[0] == "." else "." + fmt for fmt in vidformats]

formats = tuple(imgformats + vidformats)
imgformats = tuple(imgformats)
specialformats = ['.gif'] + [".vms"] + [".tif", ".tiff"]  # potential animated gif = video or gif = image


class FolderEditor(QtWidgets.QWidget):
    def __init__(self, window: "ClickPointsWindow", data_file: DataFileExtended) -> None:
        QtWidgets.QWidget.__init__(self)
        self.window = window
        self.data_file = data_file

        # Widget
        self.setMinimumWidth(500)
        self.setMinimumHeight(200)
        self.setWindowTitle("Folder Selector - ClickPoints")
        self.layout = QtWidgets.QVBoxLayout(self)

        self.setWindowIcon(qta.icon("fa.folder-open"))

        """ """
        self.list = QtWidgets.QListWidget(self)
        self.layout.addWidget(self.list)
        self.list.itemSelectionChanged.connect(self.list_selected)

        group_box = QtWidgets.QGroupBox("Add Folder")
        self.group_box = group_box
        self.layout.addWidget(group_box)
        layout = QtWidgets.QVBoxLayout()
        group_box.setLayout(layout)
        """ """

        horizontal_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(horizontal_layout)

        horizontal_layout.addWidget(QtWidgets.QLabel("Folder:"))

        self.text_input = QtWidgets.QLineEdit(self)
        self.text_input.setDisabled(True)
        horizontal_layout.addWidget(self.text_input)

        self.pushbutton_folder = QtWidgets.QPushButton('Select F&older', self)
        self.pushbutton_folder.pressed.connect(self.select_folder)
        horizontal_layout.addWidget(self.pushbutton_folder)

        self.pushbutton_file = QtWidgets.QPushButton('Select F&ile', self)
        self.pushbutton_file.pressed.connect(self.select_file)
        horizontal_layout.addWidget(self.pushbutton_file)

        """ """

        horizontal_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(horizontal_layout)

        horizontal_layout.addWidget(QtWidgets.QLabel("Filter:"))

        self.text_input_filter = QtWidgets.QLineEdit(self)
        self.text_input_filter.setToolTip(
            "Use any expression with an wildcard * to filter the files in the selected folder.")
        horizontal_layout.addWidget(self.text_input_filter)

        """ """

        horizontal_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(horizontal_layout)

        self.checkbox_subfolders = QtWidgets.QCheckBox("subfolders")
        self.checkbox_subfolders.setToolTip("Add all the subfolders of the selected folder, too.")
        horizontal_layout.addWidget(self.checkbox_subfolders)
        self.checkbox_natsort = QtWidgets.QCheckBox("natsort")
        self.checkbox_natsort.setToolTip(
            "Use natural sorting of filenames. This will sort numbers correctly (e.g. not 1 10 2 3). Takes more time to load.")
        horizontal_layout.addWidget(self.checkbox_natsort)

        self.pushbutton_load = QtWidgets.QPushButton('Load', self)
        self.pushbutton_load.pressed.connect(self.add_folder)
        horizontal_layout.addWidget(self.pushbutton_load)

        self.pushbutton_delete = QtWidgets.QPushButton('Remove', self)
        self.pushbutton_delete.pressed.connect(self.remove_folder)
        horizontal_layout.addWidget(self.pushbutton_delete)

        """ """

        horizontal_layout = QtWidgets.QHBoxLayout()
        self.layout.addLayout(horizontal_layout)

        horizontal_layout.addStretch()

        self.pushbutton_Confirm = QtWidgets.QPushButton('O&k', self)
        self.pushbutton_Confirm.pressed.connect(self.close)
        horizontal_layout.addWidget(self.pushbutton_Confirm)

        self.update_folder_list()
        self.list.setCurrentRow(self.list.count() - 1)

    def list_selected(self) -> None:
        selections = self.list.selectedItems()
        if len(selections) == 0 or self.list.currentRow() == self.list.count() - 1:
            self.text_input.setText("")
            self.group_box.setTitle("Add Folder")
            self.pushbutton_folder.setHidden(False)
            self.pushbutton_file.setHidden(False)
            self.pushbutton_load.setText("Load")
            self.pushbutton_delete.setHidden(True)
        else:
            self.text_input.setText(selections[0].text().rsplit("  ", 1)[0])
            self.group_box.setTitle("Update Folder")
            self.pushbutton_folder.setHidden(True)
            self.pushbutton_file.setHidden(True)
            self.pushbutton_load.setText("Reload")
            self.pushbutton_delete.setHidden(False)

    def update_folder_list(self) -> None:
        self.list.clear()
        for path in self.data_file.table_path.select():
            item = QtWidgets.QListWidgetItem(qta.icon("fa.folder"), "%s  (%d)" % (path.path, path.images.count()),
                                             self.list)
            item.path_entry = path
        QtWidgets.QListWidgetItem(qta.icon("fa.plus"), "add folder", self.list)

    def select_folder(self) -> None:
        # ask for a directory path
        new_path = QtWidgets.QFileDialog.getExistingDirectory(None, "Select Folder", os.getcwd())
        # if we get one, set it
        if new_path:
            if isinstance(new_path, tuple):
                new_path = new_path[0]
            else:
                new_path = str(new_path)
            # enable folder settings
            self.checkbox_subfolders.setDisabled(False)
            self.checkbox_natsort.setDisabled(False)
            self.text_input_filter.setDisabled(False)
            # display path
            self.text_input.setText(new_path)

    def select_file(self) -> None:
        # ask for a file name
        new_path = QtWidgets.QFileDialog.getOpenFileName(None, "Select File", os.getcwd())
        # if we got one, set it
        if new_path:
            if isinstance(new_path, tuple):
                new_path = new_path[0]
            else:
                new_path = str(new_path)
            # disable folder settings
            self.checkbox_subfolders.setDisabled(True)
            self.checkbox_natsort.setDisabled(True)
            self.text_input_filter.setDisabled(True)
            # display path
            self.text_input.setText(new_path)

    def add_folder(self) -> None:
        self.data_file.resortSortIndex()
        selected_path = str(self.text_input.text())
        if selected_path == "":
            return
        # get a layer for the paths
        layer_entry = self.data_file.getLayer("default", create=True)
        # if selected path is a directory, add it with the options
        if os.path.isdir(selected_path):
            addPath(self.data_file, selected_path, str(self.text_input_filter.text()), layer_entry,
                    self.checkbox_subfolders.isChecked(),
                    self.checkbox_natsort.isChecked())
        # if it is a path, set the filter to the filename to just import this file
        else:
            selected_path, filename = os.path.split(selected_path)
            addPath(self.data_file, selected_path, filename, layer_entry)
        self.update_folder_list()
        self.window.GetModule("Timeline").ImagesAdded()
        self.window.ImagesAdded()
        self.window.GetModule("Timeline").LoadingFinishedEvent()

    def remove_folder(self) -> None:
        path = self.list.selectedItems()[0].path_entry
        query = self.data_file.table_image.select().where(self.data_file.table_image.path == path)
        if query.count() == 0:
            path.delete_instance()
        else:
            reply = QtWidgets.QMessageBox.question(self, 'Delete Folder',
                                                   "Do you really want to remove folder %s with %d images?" % (
                                                   path.path, query.count()), QtWidgets.QMessageBox.Yes,
                                                   QtWidgets.QMessageBox.Cancel)
            if reply == QtWidgets.QMessageBox.Yes:
                self.data_file.table_image.delete().where(self.data_file.table_image.path == path).execute()
                path.delete_instance()
            else:
                return
        # update sort index
        self.data_file.resortSortIndex()
        self.data_file.reset_buffer()
        # update list of folders and notify all modules
        self.update_folder_list()
        BroadCastEvent2("ImagesAdded")
        self.window.ImagesAdded()


def addPath(data_file: DataFileExtended, path: str, file_filter: str = "", layer_entry: "Layer" = None,
            subdirectories: bool = False, use_natsort: bool = False, select_file: str = None,
            window: "ClickPointsWindow" = None):
    # if we should add subdirectories, add them or create a list with only one path
    if subdirectories:
        path_list = iter(sorted(GetSubdirectories(path)))
    else:
        path_list = iter([path])

    if layer_entry is None:
        # get a layer for the paths
        layer_entry = data_file.getLayer("default", create=True)

    # with data_file.db.atomic():
    data = []
    while True:
        # iterate over all folders
        for path in path_list:
            # use glob if a filter is active or just get all the files
            if file_filter != "":
                file_list = glob.glob(os.path.join(path, file_filter))
                file_list = [os.path.split(filename)[1] for filename in file_list]
            else:
                file_list = GetFilesInDirectory(path)
            # if no files are left skip this folder
            if len(file_list) == 0:
                print("WARNING: folder %s doesn't contain any files ClickPoints can read." % path)
                continue
            # add the folder to the database
            path_entry = data_file.add_path(path)
            # maybe sort the files
            if use_natsort:
                file_list = iter(natsorted(file_list))
            else:
                file_list = iter(sorted(file_list))
            # iterate over all files
            while True:
                for filename in file_list:
                    # extract the extension and frame number
                    extension = os.path.splitext(filename)[1]
                    frames = getFrameNumber(os.path.join(path, filename), extension)
                    # if the file is not properly readable, skip it
                    if frames == 0:
                        continue
                    # add the file to the database
                    try:
                        data.extend(
                            data_file.add_image(filename, extension, None, frames, path=path_entry, layer=layer_entry,
                                                full_path=os.path.join(path, filename), commit=False))
                    except OSError as err:
                        print("ERROR:", err)
                    if len(data) > 100 or filename == select_file:
                        # split the data array in slices of 100
                        for i in range(int(len(data) / 100) + 1):
                            data_file.add_bulk(data[i * 100:i * 100 + 100])
                        data = []
                        # if the file is the file which should be selected jump to that frame
                        if filename == select_file:
                            file = data_file.table_image.get(filename=select_file)
                            window.first_frame = file.sort_index
                            select_file = None
                        break
                else:
                    break
            if len(data) > 100:
                data_file.add_bulk(data)
                data = []
        else:
            data_file.add_bulk(data)
            break
    # data_file.start_adding_timestamps()
    BroadCastEvent2("ImagesAdded")


def addList(data_file: DataFileExtended, path: str, list_filename: list) -> None:
    with open(os.path.join(path, list_filename)) as fp:
        paths = {}
        data = []
        while True:
            start_time = time.time()
            for line in fp:  # continue with the iteration over the file iterator where we stopped last time
                timestamp = None
                external_id = None
                annotation_id = None
                try:
                    line, timestamp, external_id, annotation_id = line.strip().split()
                except:
                    line = line.strip().split()[0]

                file_path, file_name = os.path.split(line)
                if file_path not in paths.keys():
                    paths[file_path] = data_file.table_path(path=file_path)
                    paths[file_path].save()

                if timestamp:
                    timestamp = datetime.strptime(timestamp, '%Y%m%d-%H%M%S')
                    # TODO implement getting time stamps from file for file lists
                else:
                    data_file.getTimeStamp(file_name)

                # extract the extension and frame number
                extension = os.path.splitext(file_name)[1]
                frames = getFrameNumber(line, extension)
                # add the file to the database
                data_new = data_file.add_image(file_name, extension, external_id, frames, path=paths[file_path],
                                               full_path=os.path.join(file_path, file_name), timestamp=timestamp,
                                               commit=False)
                data.extend(data_new)

                if time.time() - start_time > 0.1:
                    break
            else:  # break if we have reached the end of the file
                break
            data_file.add_bulk(data)
            data = []
        data_file.add_bulk(data)

    BroadCastEvent2("ImagesAdded")


def GetSubdirectories(directory: str) -> List[str]:
    if directory == "":
        directory = "."
    # return all subdirectories
    return [x[0] for x in os.walk(directory)]


def GetFilesInDirectory(root: str) -> List[str]:
    # return all file names which have and known file extension
    if root == "":
        root = "."
    return [filename for filename in next(os.walk(root))[2] if filename.lower().endswith(formats)]


def getFrameNumber(file: str, extension: str) -> int:
    # for image we are already done, they only contain one frame
    if extension.lower() in imgformats and extension.lower() not in specialformats:
        frames = 1
    else:
        # for other formats let imagio choose a reader
        try:
            reader = openslide.OpenSlide(file)
            reader.close()
            return 1
        except IOError:
            pass
        try:
            reader = imageio.get_reader(file)
        except (IOError, ValueError):
            print("ERROR: can't read file", file)
            return 0
        frames = reader.get_length()
        # for imagio ffmpeg > 2.5.0, check if frames might be inf
        if not isinstance(frames, int):
            frames = reader.count_frames()
        reader.close()
    # return the number of frames
    return frames
