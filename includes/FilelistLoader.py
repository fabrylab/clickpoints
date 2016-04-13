from __future__ import division, print_function, unicode_literals
import os
import glob
import sys
from distutils.version import LooseVersion

from PyQt4 import QtGui, QtCore
import qtawesome as qta

try:
    from natsort import natsorted
except ImportError:
    natsorted = sorted

import imageio
if LooseVersion(imageio.__version__) < LooseVersion('1.3'):
    print("Imageio version %s is too old, trying to update" % imageio.__version__)
    result = os.system("pip install imageio --upgrade")
    if result == 0:
        print("Please restart clickpoints for the update to take effect.")
        sys.exit(-1)
    else:
        print("Update failed, please try to update manually.")
        raise ImportError
print("Using ImageIO", imageio.__version__)

imgformats = []
for format in imageio.formats:
    if 'i' in format.modes:
        imgformats.extend(format._extensions)
imgformats = [fmt if fmt[0] == "." else "."+fmt for fmt in imgformats]
vidformats = []
for format in imageio.formats:
    if 'I' in format.modes:
        vidformats.extend(format._extensions)
vidformats = [fmt if fmt[0] == "." else "."+fmt for fmt in vidformats]


formats = tuple(imgformats+vidformats)
imgformats = tuple(imgformats)


class FolderEditor(QtGui.QWidget):
    def __init__(self, data_file):
        QtGui.QWidget.__init__(self)
        self.data_file = data_file

        # Widget
        self.setMinimumWidth(500)
        self.setMinimumHeight(200)
        self.setWindowTitle("Folder Selector")
        self.layout = QtGui.QVBoxLayout(self)

        self.setWindowIcon(qta.icon("fa.folder-open"))

        """ """
        self.list = QtGui.QListWidget(self)
        for path in self.data_file.table_paths.select():
            QtGui.QListWidgetItem(qta.icon("fa.folder"), "%s  (%d)" % (path.path, path.images.count()), self.list)
        self.layout.addWidget(self.list)

        group_box = QtGui.QGroupBox("Add Folder")
        self.layout.addWidget(group_box)
        layout = QtGui.QVBoxLayout()
        group_box.setLayout(layout)
        """ """

        horizontal_layout = QtGui.QHBoxLayout()
        layout.addLayout(horizontal_layout)

        horizontal_layout.addWidget(QtGui.QLabel("Folder:"))

        self.text_input = QtGui.QLineEdit(self)
        self.text_input.setDisabled(True)
        horizontal_layout.addWidget(self.text_input)

        self.pushbutton_folder = QtGui.QPushButton('Select F&older', self)
        self.pushbutton_folder.pressed.connect(self.select_folder)
        horizontal_layout.addWidget(self.pushbutton_folder)

        self.pushbutton_file = QtGui.QPushButton('Select F&ile', self)
        self.pushbutton_file.pressed.connect(self.select_file)
        horizontal_layout.addWidget(self.pushbutton_file)

        """ """

        horizontal_layout = QtGui.QHBoxLayout()
        layout.addLayout(horizontal_layout)

        horizontal_layout.addWidget(QtGui.QLabel("Filter:"))

        self.text_input_filter = QtGui.QLineEdit(self)
        self.text_input_filter.setToolTip("Use any expression with an wildcard * to filter the files in the selected folder.")
        horizontal_layout.addWidget(self.text_input_filter)

        """ """

        horizontal_layout = QtGui.QHBoxLayout()
        layout.addLayout(horizontal_layout)

        self.checkbox_subfolders = QtGui.QCheckBox("subfolders")
        self.checkbox_subfolders.setToolTip("Add all the subfolders of the selected folder, too.")
        horizontal_layout.addWidget(self.checkbox_subfolders)
        self.checkbox_natsort = QtGui.QCheckBox("natsort")
        self.checkbox_natsort.setToolTip("Use natural sorting of filenames. This will sort numbers correctly (e.g. not 1 10 2 3). Takes more time to load.")
        horizontal_layout.addWidget(self.checkbox_natsort)

        self.pushbutton_folder = QtGui.QPushButton('Load', self)
        self.pushbutton_folder.pressed.connect(self.add_folder)
        horizontal_layout.addWidget(self.pushbutton_folder)

        """ """

        horizontal_layout = QtGui.QHBoxLayout()
        self.layout.addLayout(horizontal_layout)

        horizontal_layout.addStretch()

        self.pushbutton_Confirm = QtGui.QPushButton('O&k', self)
        self.pushbutton_Confirm.pressed.connect(self.close)
        horizontal_layout.addWidget(self.pushbutton_Confirm)

    def select_folder(self):
        # ask for a directory path
        new_path = str(QtGui.QFileDialog.getExistingDirectory(None, "Select Folder", os.getcwd()))
        # if we get one, set it
        if new_path:
            # enable folder settings
            self.checkbox_subfolders.setDisabled(False)
            self.checkbox_natsort.setDisabled(False)
            self.text_input_filter.setDisabled(False)
            # display path
            self.text_input.setText(new_path)

    def select_file(self):
        # ask for a file name
        new_path = str(QtGui.QFileDialog.getOpenFileName(None, "Select File", os.getcwd()))
        # if we got one, set it
        if new_path:
            # disable folder settings
            self.checkbox_subfolders.setDisabled(True)
            self.checkbox_natsort.setDisabled(True)
            self.text_input_filter.setDisabled(True)
            # display path
            self.text_input.setText(new_path)

    def add_folder(self):
        selected_path = str(self.text_input.text())
        # if selected path is a directory, add it with the options
        if os.path.isdir(selected_path):
            addPath(self.data_file, selected_path, str(self.text_input_filter), self.checkbox_subfolders.isChecked(),
                    self.checkbox_natsort.isChecked(), list_gui=self.list)
        # if it is a path, set the filter to the filename to just import this file
        else:
            selected_path, filename = os.path.split(selected_path)
            addPath(self.data_file, selected_path, filename, list_gui=self.list)


def addPath(data_file, path, file_filter="", subdirectories=False, use_natsort=False, list_gui=None):
    # if we should add subdirectories, add them or create a list with only one path
    if subdirectories:
        path_list = GetSubdirectories(path)
    else:
        path_list = [path]

    # iterate over all folders
    for path in path_list:
        # use glob if a filter is active or just get all the files
        if file_filter != "":
            file_list = glob.glob(os.path.join(path, file_filter))
        else:
            file_list = GetFilesInDirectory(path)
        # if no files are left skip this folder
        if len(path_list) == 0:
            continue
        # add the folder to the database
        path_entry = data_file.add_path(path)
        # if a gui window is open add the path to the display list
        if list_gui:
            QtGui.QListWidgetItem(qta.icon("fa.folder"), "%s  (%d)" % (path, len(path_list)), list_gui)
        # maybe sort the files
        if use_natsort:
            file_list = natsorted(file_list)
        # iterate over all files
        for filename in file_list:
            # extract the extension and frame number
            extension = os.path.splitext(filename)[1]
            frames = getFrameNumber(filename, extension)
            # add the file to the database
            data_file.add_image(filename, extension, None, frames, path=path_entry)


def GetSubdirectories(directory):
    # return all subdirectories
    return [x[0] for x in os.walk(directory)]


def GetFilesInDirectory(root):
    # return all file names which have and known file extension
    return [filename for filename in os.listdir(root) if filename.lower().endswith(formats)]


def getFrameNumber(file, extension):
    # for image we are already done, they only contain one frame
    if extension.lower() in imgformats:
        frames = 1
    else:
        # for videos, we have to open them and get the length
        try:
            reader = imageio.get_reader(file)
        except IOError:
            print("ERROR: can't read file", file)
            return 0
        frames = reader.get_length()
    # return the number of frames
    return frames
