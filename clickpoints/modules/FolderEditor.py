#!/usr/bin/env python
# -*- coding: utf-8 -*-
# FolderEditor.py

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
from typing import List

from pathlib import Path
import qtawesome as qta
from qtpy import QtWidgets, QtCore, QtGui

from clickpoints.includes.Tools import BroadCastEvent2


class FolderEditor(QtWidgets.QWidget):
    def __init__(self, window: "ClickPointsWindow", modules: List[QtCore.QObject], config: None = None) -> None:
        QtWidgets.QWidget.__init__(self)
        # default settings and parameters
        self.window = window
        self.data_file = window.data_file
        self.modules = modules
        self.ExporterWindow = None

        # add button to the icon toolbar
        self.button = QtWidgets.QPushButton()
        self.button.setIcon(qta.icon('fa.folder-open'))
        self.button.setToolTip("add/remove folder from the current project")
        self.button.clicked.connect(self.showDialog)
        window.layoutButtons.addWidget(self.button)

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

    def showDialog(self):
        self.update_folder_list()
        self.show()

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
        if self.data_file is None:
            return
        for path in self.data_file.table_path.select():
            item = QtWidgets.QListWidgetItem(qta.icon("fa.folder"), "%s  (%d)" % (path.path, path.images.count()),
                                             self.list)
            item.path_entry = path
        QtWidgets.QListWidgetItem(qta.icon("fa.plus"), "add folder", self.list)

    def closeDataFile(self):
        self.data_file = None

    def updateDataFile(self, data_file, new_database):
        self.data_file = data_file

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
            self.window.loadUrl(Path(selected_path) / str(self.text_input_filter.text()), self.checkbox_natsort.isChecked())
        # if it is a path, set the filter to the filename to just import this file
        else:
            self.window.loadUrl(Path(selected_path), self.checkbox_natsort.isChecked())

        #self.window.GetModule("Timeline").ImagesAdded()
        #self.window.ImagesAdded()
        #self.window.GetModule("Timeline").LoadingFinishedEvent()

    def LoadingFinishedEvent(self):
        print("LoadingFinishedEvent", self)
        self.update_folder_list()

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

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.close()
