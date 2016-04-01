from PyQt4 import QtGui
import os

def AddQSpinBox(layout, text, value=0, float=True, strech=False):
    horizontal_layout = QtGui.QHBoxLayout()
    layout.addLayout(horizontal_layout)
    text = QtGui.QLabel(text)
    if float:
        spinBox = QtGui.QDoubleSpinBox()
    else:
        spinBox = QtGui.QSpinBox()
    spinBox.setRange(-99999, 99999)
    spinBox.setValue(value)
    horizontal_layout.addWidget(text)
    horizontal_layout.addWidget(spinBox)
    spinBox.managingLayout = horizontal_layout
    if strech:
        horizontal_layout.addStretch()
    return spinBox


def AddQLineEdit(layout, text, value=None, strech=False):
    horizontal_layout = QtGui.QHBoxLayout()
    layout.addLayout(horizontal_layout)
    text = QtGui.QLabel(text)
    lineEdit = QtGui.QLineEdit()
    if value:
        lineEdit.setText(value)
    horizontal_layout.addWidget(text)
    horizontal_layout.addWidget(lineEdit)
    lineEdit.managingLayout = horizontal_layout
    if strech:
        horizontal_layout.addStretch()
    return lineEdit

def AddQSaveFileChoose(layout, text, value=None, dialog_title="Choose File", file_type="All", filename_checker=None, strech=False):
    horizontal_layout = QtGui.QHBoxLayout()
    layout.addLayout(horizontal_layout)
    text = QtGui.QLabel(text)
    lineEdit = QtGui.QLineEdit()
    if value:
        lineEdit.setText(value)
    lineEdit.setEnabled(False)
    def OpenDialog():
        srcpath = str(QtGui.QFileDialog.getSaveFileName(None, dialog_title, os.getcwd(), file_type))
        if filename_checker and srcpath:
            srcpath = filename_checker(srcpath)
        if srcpath:
            lineEdit.setText(srcpath)
    button = QtGui.QPushButton("Choose File")
    button.pressed.connect(OpenDialog)
    horizontal_layout.addWidget(text)
    horizontal_layout.addWidget(lineEdit)
    horizontal_layout.addWidget(button)
    lineEdit.managingLayout = horizontal_layout
    if strech:
        horizontal_layout.addStretch()
    return lineEdit


def AddQComboBox(layout, text, values=None, selectedValue=None):
    horizontal_layout = QtGui.QHBoxLayout()
    layout.addLayout(horizontal_layout)
    text = QtGui.QLabel(text)
    comboBox = QtGui.QComboBox()
    for value in values:
        comboBox.addItem(value)
    if selectedValue:
        comboBox.setCurrentIndex(values.index(selectedValue))
    horizontal_layout.addWidget(text)
    horizontal_layout.addWidget(comboBox)
    comboBox.managingLayout = horizontal_layout
    return comboBox


def AddQCheckBox(layout, text, checked=False, strech=False):
    horizontal_layout = QtGui.QHBoxLayout()
    layout.addLayout(horizontal_layout)
    text = QtGui.QLabel(text)
    checkBox = QtGui.QCheckBox()
    checkBox.setChecked(checked)
    horizontal_layout.addWidget(text)
    horizontal_layout.addWidget(checkBox)
    if strech:
        horizontal_layout.addStretch()
    return checkBox


def AddQLabel(layout, text=None):
    text = QtGui.QLabel(text)
    if text:
        layout.addWidget(text)
    return text


def AddQHLine(layout):
    line = QtGui.QFrame()
    line.setFrameShape(QtGui.QFrame.HLine)
    line.setFrameShadow(QtGui.QFrame.Sunken)
    layout.addWidget(line)
    return line