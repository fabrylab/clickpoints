from qtpy import QtGui, QtWidgets
import os
import colorsys
import numpy as np
from Tools import HTMLColorToRGB

def AddQSpinBox(layout, text, value=0, float=True, strech=False):
    horizontal_layout = QtWidgets.QHBoxLayout()
    layout.addLayout(horizontal_layout)
    text = QtWidgets.QLabel(text)
    if float:
        spinBox = QtWidgets.QDoubleSpinBox()
    else:
        spinBox = QtWidgets.QSpinBox()
    spinBox.setRange(-99999, 99999)
    spinBox.setValue(value)
    spinBox.setHidden_ = spinBox.setHidden
    def setHidden(hidden):
        spinBox.setHidden_(hidden)
        text.setHidden(hidden)
    spinBox.setHidden = setHidden
    horizontal_layout.addWidget(text)
    horizontal_layout.addWidget(spinBox)
    spinBox.managingLayout = horizontal_layout
    if strech:
        horizontal_layout.addStretch()
    return spinBox


def AddQLineEdit(layout, text, value=None, strech=False):
    horizontal_layout = QtWidgets.QHBoxLayout()
    layout.addLayout(horizontal_layout)
    text = QtWidgets.QLabel(text)
    lineEdit = QtWidgets.QLineEdit()
    if value:
        lineEdit.setText(value)
    horizontal_layout.addWidget(text)
    horizontal_layout.addWidget(lineEdit)
    lineEdit.managingLayout = horizontal_layout
    if strech:
        horizontal_layout.addStretch()
    return lineEdit

def AddQSaveFileChoose(layout, text, value=None, dialog_title="Choose File", file_type="All", filename_checker=None, strech=False):
    horizontal_layout = QtWidgets.QHBoxLayout()
    layout.addLayout(horizontal_layout)
    text = QtWidgets.QLabel(text)
    lineEdit = QtWidgets.QLineEdit()
    if value:
        lineEdit.setText(value)
    lineEdit.setEnabled(False)
    def OpenDialog():
        srcpath = str(QtWidgets.QFileDialog.getSaveFileName(None, dialog_title, os.getcwd(), file_type))
        if filename_checker and srcpath:
            srcpath = filename_checker(srcpath)
        if srcpath:
            lineEdit.setText(srcpath)
    button = QtWidgets.QPushButton("Choose File")
    button.pressed.connect(OpenDialog)
    horizontal_layout.addWidget(text)
    horizontal_layout.addWidget(lineEdit)
    horizontal_layout.addWidget(button)
    lineEdit.managingLayout = horizontal_layout
    if strech:
        horizontal_layout.addStretch()
    return lineEdit

def AddQColorChoose(layout, text, value=None, strech=False):
    # add a layout
    horizontal_layout = QtWidgets.QHBoxLayout()
    layout.addLayout(horizontal_layout)
    # add a text
    text = QtWidgets.QLabel(text)
    button = QtWidgets.QPushButton("")

    def OpenDialog():
        # get new color from color picker
        color = QtWidgets.QColorDialog.getColor(QtGui.QColor(*HTMLColorToRGB(button.getColor())))
        # if a color is set, apply it
        if color.isValid():
            color = "#%02x%02x%02x" % color.getRgb()[:3]
            button.setColor(color)

    def setColor(value):
        # display and save the new color
        button.setStyleSheet("background-color: %s;" % value)
        button.color = value

    def getColor():
        # return the color
        return button.color

    # default value for the color
    if value is None:
        value = "#FF0000"
    # add functions to button
    button.pressed.connect(OpenDialog)
    button.setColor = setColor
    button.getColor = getColor
    # set the color
    button.setColor(value)
    # add widgets to the layout
    horizontal_layout.addWidget(text)
    horizontal_layout.addWidget(button)
    # add a strech if requested
    if strech:
        horizontal_layout.addStretch()
    return button


def AddQComboBox(layout, text, values=None, selectedValue=None):
    horizontal_layout = QtWidgets.QHBoxLayout()
    layout.addLayout(horizontal_layout)
    text = QtWidgets.QLabel(text)
    comboBox = QtWidgets.QComboBox()
    for value in values:
        comboBox.addItem(value)
    if selectedValue:
        comboBox.setCurrentIndex(values.index(selectedValue))
    horizontal_layout.addWidget(text)
    horizontal_layout.addWidget(comboBox)
    comboBox.managingLayout = horizontal_layout
    return comboBox


def AddQCheckBox(layout, text, checked=False, strech=False):
    horizontal_layout = QtWidgets.QHBoxLayout()
    layout.addLayout(horizontal_layout)
    text = QtWidgets.QLabel(text)
    checkBox = QtWidgets.QCheckBox()
    checkBox.setChecked(checked)
    horizontal_layout.addWidget(text)
    horizontal_layout.addWidget(checkBox)
    if strech:
        horizontal_layout.addStretch()
    return checkBox


def AddQLabel(layout, text=None):
    text = QtWidgets.QLabel(text)
    if text:
        layout.addWidget(text)
    return text


def AddQHLine(layout):
    line = QtWidgets.QFrame()
    line.setFrameShape(QtWidgets.QFrame.HLine)
    line.setFrameShadow(QtWidgets.QFrame.Sunken)
    layout.addWidget(line)
    return line


def GetColorByIndex(index):
    colors = np.linspace(0, 1, 16, endpoint=False).tolist() * 3  # 16 different hues
    saturations = [1] * 16 + [0.5] * 16 + [1] * 16  # in two different saturations
    value = [1] * 16 + [1] * 16 + [0.5] * 16  # and two different values
    return "#%02x%02x%02x" % tuple((np.array(colorsys.hsv_to_rgb((np.array(colors[index])*3) % 1, saturations[index], value[index])) * 255).astype(int))

# set the standard colors for the color picker dialog
colors = np.linspace(0, 1, 16, endpoint=False).tolist()*3  # 16 different hues
saturations = [1]*16+[0.5]*16+[1]*16  # in two different saturations
value = [1]*16+[1]*16+[0.5]*16  # and two different values
for index, (color, sat, val) in enumerate(zip(colors, saturations, value)):
    # deform the index, as the dialog fills them column wise and we want to fill them rowise
    index = index % 8*6+index//8
    # convert color from hsv to rgb, to an array, to an tuple, to a hex string then to an integer
    color_integer = int("%02x%02x%02x" % tuple((np.array(colorsys.hsv_to_rgb(color, sat, val))*255).astype(int)), 16)
    QtWidgets.QColorDialog.setStandardColor(index, color_integer)
