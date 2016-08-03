from __future__ import division, print_function
import os
import re
import peewee

from qtpy import QtGui, QtCore, QtWidgets
from qtpy.QtCore import Qt
import qtawesome as qta

import numpy as np
from sortedcontainers import SortedDict

from qimage2ndarray import array2qimage, rgb_view

import uuid

import json
import matplotlib.pyplot as plt
import random
from threading import Thread

from QtShortCuts import AddQSpinBox, AddQLineEdit, AddQLabel, AddQComboBox, AddQColorChoose, GetColorByIndex
from Tools import GraphicsItemEventFilter, disk, PosToArray, BroadCastEvent, HTMLColorToRGB

w = 1.
b = 7
r2 = 10
path1 = QtGui.QPainterPath()
path1.addRect(-r2, -w, b, w * 2)
path1.addRect(r2, -w, -b, w * 2)
path1.addRect(-w, -r2, w * 2, b)
path1.addRect(-w, r2, w * 2, -b)
path1.addEllipse(-r2, -r2, r2 * 2, r2 * 2)
path1.addEllipse(-r2, -r2, r2 * 2, r2 * 2)
w = 2
b = 3
o = 3
path2 = QtGui.QPainterPath()
path2.addRect(-b - o, -w * 0.5, b, w)
path2.addRect(+o, -w * 0.5, b, w)
path2.addRect(-w * 0.5, -b - o, w, b)
path2.addRect(-w * 0.5, +o, w, b)
r3 = 5
path3 = QtGui.QPainterPath()
path3.addEllipse(-0.5 * r3, -0.5 * r3, r3, r3)  # addRect(-0.5,-0.5, 1, 1)
point_display_types = [path1, path2, path3]
point_display_type = 0

path_circle = QtGui.QPainterPath()
# path_circle.arcTo(-5, -5, 10, 10, 0, 130)
path_circle.addEllipse(-5, -5, 10, 10)

path_rect = QtGui.QPainterPath()
path_rect.addRect(-5, -5, 10, 10)

paths = dict(cross=path1, circle=path_circle, rect=path_rect)

TYPE_Normal = 0
TYPE_Rect = 1
TYPE_Line = 2
TYPE_Track = 4


class MarkerFile:
    def __init__(self, datafile):
        self.data_file = datafile

        self.table_markertype = self.data_file.table_markertype
        self.table_marker = self.data_file.table_marker
        self.table_track = self.data_file.table_track
        self.table_line = self.data_file.table_line
        self.table_rectangle = self.data_file.table_rectangle

    def set_track(self, type):
        track = self.table_track(uid=uuid.uuid4().hex, type=type)
        track.save()
        return track

    def set_type(self, id, name, rgb_tuple, mode):
        try:
            type = self.table_markertype.get(self.table_markertype.name == name)
        except peewee.DoesNotExist:
            type = self.table_markertype(name=name, color='#%02x%02x%02x' % tuple(rgb_tuple), mode=mode)
            type.save(force_insert=True)
        return type

    def add_marker(self, **kwargs):
        kwargs.update(dict(image=self.data_file.image))
        return self.table_marker(**kwargs)

    def get_marker_list(self, image_id=None):
        if image_id is None:
            image_id = self.data_file.image.id
        return self.table_marker.select().where(self.table_marker.image == image_id)

    def get_type_list(self):
        return self.table_markertype.select()

    def get_type(self, name):
        return self.table_markertype.get(name=name)

    def get_track_list(self):
        return self.table_track.select()

    def get_track_points(self, track):
        return self.table_marker.select().where(self.table_marker.track == track)

    def get_marker_frames(self):
        return self.table_marker.select().group_by(self.table_marker.image)


def ReadTypeDict(string):
    dictionary = {}
    matches = re.findall(
        r"(\d*):\s*\[\s*\'([^']*?)\',\s*\[\s*([\d.]*)\s*,\s*([\d.]*)\s*,\s*([\d.]*)\s*\]\s*,\s*([\d.]*)\s*\]", string)
    for match in matches:
        dictionary[int(match[0])] = [match[1], map(float, match[2:5]), int(match[5])]
    return dictionary


def GetColorFromMap(identifier, id):
    match = re.match(r"([^\(]*)\((\d*)\)", identifier)
    count = 100
    if match:
        result = match.groups()
        identifier = result[0]
        count = int(result[1])
    cmap = plt.get_cmap(identifier)
    if id is None:
        id = 0
    index = int((id * 255 / count) % 256)
    color = np.array(cmap(index))
    color = color[:3] * 255
    return color


class DeleteType(QtWidgets.QDialog):
    def __init__(self, type, count, types):
        QtWidgets.QDialog.__init__(self)

        # Widget
        self.setMinimumWidth(500)
        self.setMinimumHeight(100)
        self.setWindowTitle("Delete Type - ClickPoints")
        self.setWindowIcon(qta.icon("fa.crosshairs"))
        self.setModal(True)
        main_layout = QtWidgets.QVBoxLayout(self)

        self.label = QtWidgets.QLabel(
            "The type %s has %d marker. Do you want to delete all of them or assign them to another type?" % (
            type.name, count))
        main_layout.addWidget(self.label)

        self.type_ids = {type.name: type.id for type in types}
        self.comboBox = AddQComboBox(main_layout, "New Type:", [type.name for type in types])

        layout2 = QtWidgets.QHBoxLayout()
        main_layout.addLayout(layout2)
        button1 = QtWidgets.QPushButton("Delete")
        button1.clicked.connect(lambda: self.done(-1))
        layout2.addWidget(button1)
        button2 = QtWidgets.QPushButton("Move")
        button2.clicked.connect(lambda: self.done(self.type_ids[self.comboBox.currentText()]))
        layout2.addWidget(button2)
        button3 = QtWidgets.QPushButton("Cancel")
        button3.clicked.connect(lambda: self.done(0))
        layout2.addWidget(button3)


class MarkerEditor(QtWidgets.QWidget):
    data = None
    prevent_recursion = False

    def __init__(self, marker_handler, marker_file):
        QtWidgets.QWidget.__init__(self)

        # store parameter
        self.marker_handler = marker_handler
        self.data_file = marker_file

        # create window
        self.setMinimumWidth(500)
        self.setMinimumHeight(200)
        self.setWindowTitle("MarkerEditor - ClickPoints")
        self.setWindowIcon(qta.icon("fa.crosshairs"))
        main_layout = QtWidgets.QHBoxLayout(self)

        """ Tree View """
        self.tree = QtWidgets.QTreeView()
        main_layout.addWidget(self.tree)

        # start a list for backwards search (from marker entry back to tree entry)
        self.marker_modelitems = {}
        self.marker_type_modelitems = {}

        # model for tree view
        model = QtGui.QStandardItemModel(0, 0)

        # add all marker types
        marker_types = self.data_file.table_markertype.select()
        row = -1
        for row, marker_type in enumerate(marker_types):
            # add item
            item_type = QtGui.QStandardItem(marker_type.name)
            marker_type.expanded = False
            item_type.entry = marker_type
            item_type.setIcon(qta.icon("fa.crosshairs", color=QtGui.QColor(*HTMLColorToRGB(marker_type.color))))
            item_type.setEditable(False)
            model.setItem(row, 0, item_type)
            self.marker_type_modelitems[marker_type.id] = item_type

            # add dummy child
            child = QtGui.QStandardItem()
            child.setEditable(False)
            item_type.appendRow(child)
            model.setItem(row, 0, item_type)
            """ " ""
            # if type is track type
            if marker_type.mode & TYPE_Track:
                # add all tracks for this type
                tracks = self.data_file.table_track.select().where(self.data_file.table_track.type == marker_type)
                for track in tracks:
                    # get markers for track
                    markers = (self.data_file.table_marker.select()
                               .where(self.data_file.table_marker.track == track)
                               .join(self.data_file.data_file.table_image)
                               .order_by(self.data_file.data_file.table_image.sort_index))

                    # add item
                    item_track = QtGui.QStandardItem("Track #%d (%d)" % (track.id, markers.count()))
                    item_track.entry = track
                    item_track.setEditable(False)
                    item_type.appendRow(item_track)

                    # add all markers for this track
                    for marker in markers:
                        # add item
                        item_marker = QtGui.QStandardItem("Marker #%d (frame %d)" % (marker.id, marker.image.sort_index))
                        item_marker.entry = marker
                        item_marker.setEditable(False)
                        item_track.appendRow(item_marker)
                        self.marker_modelitems[marker.id] = item_marker
            # type not a track type
            else:
                # add marker for the type
                markers = self.data_file.table_marker.select().where(self.data_file.table_marker.type == marker_type)
                for marker in markers:
                    item_marker = QtGui.QStandardItem("Marker #%d (frame %d)" % (marker.id, marker.image.sort_index))
                    item_marker.entry = marker
                    item_marker.setEditable(False)
                    item_type.appendRow(item_marker)
                    self.marker_modelitems[marker.id] = item_marker
            "" " """
        # add entry for new type
        self.new_type = self.data_file.table_markertype()
        self.new_type.color = GetColorByIndex(marker_types.count())
        item_type = QtGui.QStandardItem("add type")
        item_type.entry = self.new_type
        item_type.setIcon(qta.icon("fa.plus"))
        item_type.setEditable(False)
        model.setItem(row + 1, 0, item_type)
        self.marker_type_modelitems[-1] = item_type

        # some settings for the tree
        self.tree.setUniformRowHeights(True)
        self.tree.setHeaderHidden(True)
        self.tree.setAnimated(True)
        self.tree.setModel(model)
        self.tree.expanded.connect(self.TreeExpand)
        self.tree.clicked.connect(self.treeClicked)
        self.tree.selectionModel().selectionChanged.connect(lambda selection, y: self.setMarker(
            selection.indexes()[0].model().itemFromIndex(selection.indexes()[0]).entry))

        self.layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(self.layout)

        self.StackedWidget = QtWidgets.QStackedWidget(self)
        self.layout.addWidget(self.StackedWidget)

        """ Marker Properties """
        self.markerWidget = QtWidgets.QGroupBox()
        self.StackedWidget.addWidget(self.markerWidget)
        layout = QtWidgets.QVBoxLayout(self.markerWidget)
        self.markerWidget.type_indices = {t.id: index for index, t in enumerate(self.data_file.get_type_list())}
        self.markerWidget.type = AddQComboBox(layout, "Type:", [t.name for t in self.data_file.get_type_list()])
        self.markerWidget.x = AddQSpinBox(layout, "X:")
        self.markerWidget.y = AddQSpinBox(layout, "Y:")
        self.markerWidget.x1 = AddQSpinBox(layout, "X1:")
        self.markerWidget.y1 = AddQSpinBox(layout, "Y1:")
        self.markerWidget.x2 = AddQSpinBox(layout, "X2:")
        self.markerWidget.y2 = AddQSpinBox(layout, "Y2:")
        self.markerWidget.width = AddQSpinBox(layout, "Width:")
        self.markerWidget.height = AddQSpinBox(layout, "Height:")
        self.markerWidget.special_widgets = [self.markerWidget.x, self.markerWidget.y, self.markerWidget.x1, self.markerWidget.y1, self.markerWidget.x2, self.markerWidget.y2, self.markerWidget.width, self.markerWidget.height]
        self.markerWidget.widget_types = {TYPE_Normal: [self.markerWidget.x, self.markerWidget.y],
                                          TYPE_Line: [self.markerWidget.x1, self.markerWidget.y1, self.markerWidget.x2, self.markerWidget.y2],
                                          TYPE_Rect: [self.markerWidget.x, self.markerWidget.y, self.markerWidget.width, self.markerWidget.height],
                                          TYPE_Track: [self.markerWidget.x, self.markerWidget.y]}
        self.markerWidget.style = AddQLineEdit(layout, "Style:")
        self.markerWidget.text = AddQLineEdit(layout, "Text:")
        self.markerWidget.label = AddQLabel(layout)
        layout.addStretch()

        """ Type Properties """
        self.typeWidget = QtWidgets.QGroupBox()
        self.StackedWidget.addWidget(self.typeWidget)
        layout = QtWidgets.QVBoxLayout(self.typeWidget)
        self.typeWidget.name = AddQLineEdit(layout, "Name:")
        self.typeWidget.mode_indices = {TYPE_Normal: 0, TYPE_Line: 1, TYPE_Rect: 2, TYPE_Track: 3}
        self.typeWidget.mode_values = {0: TYPE_Normal, 1: TYPE_Line, 2: TYPE_Rect, 3: TYPE_Track}
        self.typeWidget.mode = AddQComboBox(layout, "Mode:", ["TYPE_Normal", "TYPE_Line", "TYPE_Rect", "TYPE_Track"])
        self.typeWidget.style = AddQLineEdit(layout, "Style:")
        self.typeWidget.color = AddQColorChoose(layout, "Color:")
        self.typeWidget.text = AddQLineEdit(layout, "Text:")
        layout.addStretch()

        """ Track Properties """
        self.trackWidget = QtWidgets.QGroupBox()
        self.StackedWidget.addWidget(self.trackWidget)
        layout = QtWidgets.QVBoxLayout(self.trackWidget)
        self.trackWidget.style = AddQLineEdit(layout, "Style:")
        self.trackWidget.text = AddQLineEdit(layout, "Text:")
        layout.addStretch()

        """ Control Buttons """
        horizontal_layout = QtWidgets.QHBoxLayout()
        self.layout.addLayout(horizontal_layout)
        self.pushbutton_Confirm = QtWidgets.QPushButton('S&ave', self)
        self.pushbutton_Confirm.pressed.connect(self.saveMarker)
        horizontal_layout.addWidget(self.pushbutton_Confirm)

        self.pushbutton_Remove = QtWidgets.QPushButton('R&emove', self)
        self.pushbutton_Remove.pressed.connect(self.removeMarker)
        horizontal_layout.addWidget(self.pushbutton_Remove)

        self.pushbutton_Cancel = QtWidgets.QPushButton('&Cancel', self)
        self.pushbutton_Cancel.pressed.connect(self.close)
        horizontal_layout.addWidget(self.pushbutton_Cancel)

    def ExpandType(self, item_type, entry):
        # change icon to hourglass during waiting
        item_type.setIcon(qta.icon("fa.hourglass-o", color=QtGui.QColor(*HTMLColorToRGB(entry.color))))
        # remove the dummy child
        item_type.removeRow(0)

        # if type is track type
        if entry.mode & TYPE_Track:
            # add all tracks for this type
            tracks = self.data_file.table_track.select().where(self.data_file.table_track.type == entry)
            for track in tracks:
                # get markers for track
                markers = (self.data_file.table_marker.select()
                           .where(self.data_file.table_marker.track == track)
                           .join(self.data_file.data_file.table_image)
                           .order_by(self.data_file.data_file.table_image.sort_index))

                # add item
                item_track = QtGui.QStandardItem("Track #%d (%d)" % (track.id, markers.count()))
                track.expanded = False
                item_track.entry = track
                item_track.setEditable(False)
                item_type.appendRow(item_track)
                self.marker_modelitems["T%d" % track.id] = item_track

                # add dummy child
                child = QtGui.QStandardItem()
                child.setEditable(False)
                item_track.appendRow(child)
        elif entry.mode & TYPE_Line:
            # add marker for the type
            lines = self.data_file.table_line.select().where(self.data_file.table_line.type == entry)
            for line in lines:
                item_line = QtGui.QStandardItem("Line #%d (frame %d)" % (line.id, line.image.sort_index))
                item_line.entry = line
                item_line.setEditable(False)
                item_type.appendRow(item_line)
                self.marker_modelitems["L%d" % line.id] = item_line
        elif entry.mode & TYPE_Rect:
            # add marker for the type
            rectangles = self.data_file.table_rectangle.select().where(self.data_file.table_rectangle.type == entry)
            for rect in rectangles:
                item_rect = QtGui.QStandardItem("Rectangle #%d (frame %d)" % (rect.id, rect.image.sort_index))
                item_rect.entry = rect
                item_rect.setEditable(False)
                item_type.appendRow(item_rect)
                self.marker_modelitems["R%d" % rect.id] = item_rect
        else:
            # add marker for the type
            markers = self.data_file.table_marker.select().where(self.data_file.table_marker.type == entry)
            for marker in markers:
                item_marker = QtGui.QStandardItem("Marker #%d (frame %d)" % (marker.id, marker.image.sort_index))
                item_marker.entry = marker
                item_marker.setEditable(False)
                item_type.appendRow(item_marker)
                self.marker_modelitems["M%d" % marker.id] = item_marker

        # mark the entry as expanded and rest the icon
        entry.expanded = True
        item_type.setIcon(qta.icon("fa.crosshairs", color=QtGui.QColor(*HTMLColorToRGB(entry.color))))

    def ExpandTrack(self, item_track, entry):
        # change icon to hourglass during waiting
        item_track.setIcon(qta.icon("fa.hourglass-o"))
        # remove the dummy child
        item_track.removeRow(0)

        # add marker for the type
        # get markers for track
        markers = (self.data_file.table_marker.select()
                   .where(self.data_file.table_marker.track == entry)
                   .join(self.data_file.data_file.table_image)
                   .order_by(self.data_file.data_file.table_image.sort_index))
        for marker in markers:
            item_marker = QtGui.QStandardItem("Marker #%d (frame %d)" % (marker.id, marker.image.sort_index))
            item_marker.entry = marker
            item_marker.setEditable(False)
            item_track.appendRow(item_marker)
            self.marker_modelitems["M%d" % marker.id] = item_marker

        # mark the entry as expanded and rest the icon
        entry.expanded = True
        item_track.setIcon(QtGui.QIcon())

    def TreeExpand(self, index):
        # Get item and entry
        item = index.model().itemFromIndex(index)
        entry = item.entry
        thread = None

        # Expand marker type
        if isinstance(entry, self.data_file.table_markertype) and entry.expanded is False:
            thread = Thread(target=self.ExpandType, args=(item, entry))

        # Expand track
        if isinstance(entry, self.data_file.table_track) and entry.expanded is False:
            thread = Thread(target=self.ExpandTrack, args=(item, entry))

        # Start thread as daemonic
        if thread:
            thread.setDaemon(True)
            thread.start()

    def treeClicked(self, index):
        data = index.model().itemFromIndex(index).entry
        if type(data) == self.data_file.table_marker and self.data == data:
            self.marker_handler.window.JumpToFrame(self.data.image.sort_index)

    def setMarker(self, data, data_type=None):
        if self.prevent_recursion:
            return
        self.data = data

        self.pushbutton_Remove.setHidden(False)

        if type(data) == self.data_file.table_marker or type(data) == self.data_file.table_line or type(data) == self.data_file.table_rectangle:
            self.StackedWidget.setCurrentIndex(0)
            for widget in self.markerWidget.special_widgets:
                widget.setHidden(True)
            for widget in self.markerWidget.widget_types[data.type.mode]:
                widget.setHidden(False)
            self.markerWidget.setTitle("Marker #%d" % data.id)

            self.prevent_recursion = True
            #try:
            #    self.tree.setCurrentIndex(self.marker_modelitems[data.id].index())
            #except KeyError:
            #    if self.data.track is None:
            #        self.ExpandType(self.marker_type_modelitems[self.data.id])
            self.prevent_recursion = False

            data2 = data.partner if data.partner_id is not None else None

            text = ''

            if data.type.mode & TYPE_Line:
                self.markerWidget.x1.setValue(data.x1)
                self.markerWidget.y1.setValue(data.y1)
                self.markerWidget.x2.setValue(data.x2)
                self.markerWidget.y2.setValue(data.y2)
            elif data.type.mode & TYPE_Rect:
                self.markerWidget.x.setValue(data.x)
                self.markerWidget.y.setValue(data.y)
                self.markerWidget.width.setValue(data.width)
                self.markerWidget.height.setValue(data.height)
            else:
                text += ''
                self.markerWidget.x.setValue(data.x)
                self.markerWidget.y.setValue(data.y)

            self.markerWidget.label.setText(text)

            self.markerWidget.type.setCurrentIndex(self.markerWidget.type_indices[data.type.id])
            self.markerWidget.style.setText(data.style if data.style else "")
            self.markerWidget.text.setText(data.text if data.text else "")

        elif type(data) == self.data_file.table_track:
            self.StackedWidget.setCurrentIndex(2)
            self.trackWidget.setTitle("Track #%d" % data.id)
            self.trackWidget.style.setText(data.style if data.style else "")
            self.trackWidget.text.setText(data.text if data.text else "")

        elif type(data) == self.data_file.table_markertype or data_type == "type":
            if data is None:
                data = self.new_type
                self.data = data
            self.StackedWidget.setCurrentIndex(1)
            if data.name is None:
                self.pushbutton_Remove.setHidden(True)
                self.typeWidget.setTitle("add type")
                self.prevent_recursion = True
                self.tree.setCurrentIndex(self.marker_type_modelitems[-1].index())
                self.prevent_recursion = False
            else:
                self.typeWidget.setTitle("Type #%s" % data.name)
                self.prevent_recursion = True
                self.tree.setCurrentIndex(self.marker_type_modelitems[self.data.id].index())
                self.prevent_recursion = False
            self.typeWidget.name.setText(data.name)
            try:
                index = self.typeWidget.mode_indices[data.mode]
                self.prevent_recursion = True
                self.typeWidget.mode.setCurrentIndex(index)
                self.prevent_recursion = False
            except KeyError:
                pass
            self.typeWidget.style.setText(data.style if data.style else "")
            self.typeWidget.color.setColor(data.color)
            self.typeWidget.text.setText(data.text if data.text else "")

    def filterText(self, input):
        # if text field is empty - add Null instead of "" to sql db
        if not input:
            return None
        return input

    def saveMarker(self):
        print("Saving changes...")
        # set parameters
        if type(self.data) == self.data_file.table_marker or type(self.data) == self.data_file.table_line or type(self.data) == self.data_file.table_rectangle:
            if self.data.type.mode & TYPE_Line:
                self.data.x1 = self.markerWidget.x1.value()
                self.data.y1 = self.markerWidget.y1.value()
                self.data.x2 = self.markerWidget.x2.value()
                self.data.y2 = self.markerWidget.y2.value()
            elif self.data.type.mode & TYPE_Rect:
                self.data.x = self.markerWidget.x.value()
                self.data.y = self.markerWidget.y.value()
                self.data.width = self.markerWidget.width.value()
                self.data.height = self.markerWidget.height.value()
            else:
                self.data.x = self.markerWidget.x.value()
                self.data.y = self.markerWidget.y.value()
            self.data.type = self.marker_handler.marker_file.get_type(self.markerWidget.type.currentText())
            self.data.style = self.markerWidget.style.text()
            self.data.text = self.filterText(self.markerWidget.text.text())
            self.data.save()

            # load updated data
            if self.data.type.mode & TYPE_Track:
                track_item = self.marker_handler.GetMarkerItem(self.data.track)
                track_item.update(self.data.image.sort_index, self.data)
            else:
                marker_item = self.marker_handler.GetMarkerItem(self.data)
                if marker_item:
                    marker_item.ReloadData()
        elif type(self.data) == self.data_file.table_track:
            self.data.style = self.trackWidget.style.text()
            self.data.text = self.filterText(self.trackWidget.text.text())
            self.data.save()

            self.marker_handler.ReloadTrack(self.data)
        elif type(self.data) == self.data_file.table_markertype:
            new_type = self.data.id is None
            if new_type:
                self.new_type.color = GetColorByIndex(len(self.marker_type_modelitems))
                self.data = self.data_file.table_markertype()
            self.data.name = self.typeWidget.name.text()
            self.data.mode = self.typeWidget.mode_values[self.typeWidget.mode.currentIndex()]
            self.data.style = self.typeWidget.style.text()
            self.data.color = self.typeWidget.color.getColor()
            self.data.text = self.filterText(self.typeWidget.text.text())
            try:
                self.data.save()
            except peewee.IntegrityError as err:
                if err.message == "UNIQUE constraint failed: markertype.name":
                    QtWidgets.QMessageBox.critical(self, 'Error - ClickPoints',
                                                           'There already exists a markertype with name %s' % self.data.name,
                                                           QtWidgets.QMessageBox.Ok)
                    return
                else:
                    raise err
            self.marker_handler.UpdateCounter()
            if self.data.mode & TYPE_Track:
                self.marker_handler.LoadTracks()
            else:
                self.marker_handler.LoadPoints()

            # get the item from tree or insert a new one
            if new_type:
                item = QtGui.QStandardItem()
                item.setEditable(False)
                item.entry = self.data
                self.marker_type_modelitems[self.data.id] = item
                new_row = self.marker_type_modelitems[-1].row()
                self.tree.model().insertRow(new_row)
                self.tree.model().setItem(new_row, 0, item)
            else:
                item = self.marker_type_modelitems[self.data.id]

            # update item
            item.setIcon(qta.icon("fa.crosshairs", color=QtGui.QColor(*HTMLColorToRGB(self.data.color))))
            item.setText(self.data.name)
            # if a new type was created switch selection to create a new type
            if new_type:
                self.setMarker(self.new_type)

    def removeMarker(self):
        print("Remove ...")
        # currently selected a marker -> remove the marker
        if type(self.data) == self.data_file.table_marker or type(self.data) == self.data_file.table_line or type(self.data) == self.data_file.table_rectangle:
            data_string = {self.data_file.table_marker: "M%d", self.data_file.table_line: "L%d", self.data_file.table_rectangle: "R%d"}
            # get the tree view item (don't delete it right away because this changes the selection)
            index = data_string[type(self.data)] % self.data.id
            item = self.marker_modelitems[index]

            if not (self.data.type.mode & TYPE_Track):
                # find point
                marker_item = self.marker_handler.GetMarkerItem(self.data)
                # delete marker
                if marker_item:
                    marker_item.delete()
                else:
                    self.data.delete_instance()
            else:
                # find corresponding track and remove the point
                track_item = self.marker_handler.GetMarkerItem(self.data.track)
                track_item.RemoveTrackPoint(self.data.image.sort_index)

            # if it is the last item from a track deletet the track item
            if (self.data.type.mode & TYPE_Track) and item.parent().rowCount() == 1:
                item = item.parent()
            # and then delete the tree view item
            item.parent().removeRow(item.row())
            del self.marker_modelitems[index]

        # currently selected a track -> remove the track
        elif type(self.data) == self.data_file.table_track:
            # get the tree view item (don't delete it right away because this changes the selection)
            index = "T%d" % self.data.id
            item = self.marker_modelitems[index]
            # get the track and remove it
            track = self.marker_handler.GetMarkerItem(self.data)
            track.delete()
            # and then delete the tree view item
            item.parent().removeRow(item.row())
            del self.marker_modelitems[index]

        # currently selected a type -> remove the type
        elif type(self.data) == self.data_file.table_markertype:
            # get the tree view item (don't delete it right away because this changes the selection)
            index = self.data.id
            item = self.marker_type_modelitems[index]

            count = self.data.markers.count()
            # if this type doesn't have markers delete it without asking
            if count == 0:
                self.data.delete_instance()
            else:
                # Ask the user if he wants to delete all markers from this type or assign them to a different type
                self.window = DeleteType(self.data, count,
                                         [marker_type for marker_type in self.data_file.get_type_list() if
                                          marker_type != self.data])
                value = self.window.exec_()
                if value == 0:  # canceled
                    return
                if value == -1:  # delete all of them
                    # delete all markers from this type
                    q = self.data_file.table_marker.delete().where(self.data_file.table_marker.type == self.data.id)
                    q.execute()
                    # delete type
                    self.data.delete_instance()
                    # reload marker
                    self.marker_handler.ReloadMarker()
                else:
                    # change the type of all markers which belonged to this type
                    q = self.data_file.table_marker.select().where(self.data_file.table_marker.type == self.data.id)
                    for marker in q:
                        marker.type = value
                        marker.save()
                    # delete type
                    self.data.delete_instance()
                    # reload marker
                    self.marker_handler.ReloadMarker()

            # update the counters
            self.marker_handler.UpdateCounter()

            # delete item from list
            del self.marker_type_modelitems[index]
            self.new_type.color = GetColorByIndex(len(self.marker_type_modelitems)-1)

            # and then delete the tree view item
            self.tree.model().removeRow(item.row())

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.marker_handler.marker_edit_window = None
            self.close()
        if event.key() == QtCore.Qt.Key_Return:
            self.saveMarker()


def AnimationChangeScale(target, start=0, end=1, duration=200, fps=36, endcall=None):
    timer = QtCore.QTimer()
    timer.animation_counter = 0
    duration /= 1e3
    def timerEvent():
        timer.animation_time += 1./(fps*duration)
        timer.animation_counter += 1
        if timer.animation_time >= 1:
            target.setScale(end)
            timer.stop()
            if endcall:
                endcall()
        x = timer.animation_time
        k = 3
        y = 0.5 * (x * 2) ** k * (x < 0.5) + (1 - 0.5 * ((1 - x) * 2) ** k) * (x >= 0.5)
        target.setScale(y*(end-start)+start)
    timer.timeout.connect(timerEvent)
    timer.animation_time = 0
    target.setScale(start)
    target.animation_timer = timer
    timer.start(1e3/fps)


class MyGrabberItem(QtWidgets.QGraphicsPathItem):
    scale_value = 1
    use_crosshair = False

    def __init__(self, parent, color, x, y, shape="rect", use_crosshair=False):
        # init and store parent
        QtWidgets.QGraphicsPathItem.__init__(self, parent)
        self.use_crosshair = use_crosshair

        # set path
        self.setPath(paths[shape])

        # set brush and pen
        self.setBrush(QtGui.QBrush(color))
        self.setPen(QtGui.QPen(0))

        # accept hover events and set position
        self.setAcceptHoverEvents(True)
        self.setPos(x, y)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations)

        if parent.is_new:
            AnimationChangeScale(self)

    def setShape(self, shape):
        self.setPath(paths[shape])

    def hoverEnterEvent(self, event):
        # a bit bigger during hover
        super(QtWidgets.QGraphicsPathItem, self).setScale(1.2 * self.scale_value)

    def hoverLeaveEvent(self, event):
        # switch back to normal size
        super(QtWidgets.QGraphicsPathItem, self).setScale(1 * self.scale_value)

    def mousePressEvent(self, event):
        # store start position of move
        if event.button() == QtCore.Qt.LeftButton:
            # left click + control -> remove
            if event.modifiers() == QtCore.Qt.ControlModifier:
                self.parentItem().graberDelete(self)
            # normal left click -> move
            else:
                if self.use_crosshair:
                    # display crosshair
                    self.setCursor(QtGui.QCursor(QtCore.Qt.BlankCursor))
                    self.parentItem().marker_handler.Crosshair.Show(self)
                    self.parentItem().marker_handler.Crosshair.MoveCrosshair(self.pos().x(), self.pos().y())
        if event.button() == QtCore.Qt.RightButton:
            # right button -> open menu
            # open marker edit menu
            mh = self.parentItem().marker_handler
            if not mh.marker_edit_window or not mh.marker_edit_window.isVisible():
                mh.marker_edit_window = MarkerEditor(mh, mh.marker_file)
                mh.marker_edit_window.show()
            mh.marker_edit_window.setMarker(self.parentItem().data)

    def mouseMoveEvent(self, event):
        # move crosshair
        if self.use_crosshair:
            self.parentItem().marker_handler.Crosshair.MoveCrosshair(self.pos().x(), self.pos().y())
        # notify parent
        pos = self.parentItem().mapFromScene(event.scenePos())
        self.parentItem().graberMoved(self, pos)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            # hide crosshair
            if self.use_crosshair:
                self.setCursor(QtGui.QCursor(QtCore.Qt.OpenHandCursor))
                self.parentItem().marker_handler.Crosshair.Hide()

    def setScale(self, scale=None):
        # store scale
        if scale is not None:
            self.scale_value = scale
        # adjust scale
        super(QtWidgets.QGraphicsPathItem, self).setScale(self.scale_value)

    def delete(self):
        self.setAcceptedMouseButtons(Qt.MouseButtons(0))
        self.setAcceptHoverEvents(False)
        self.setParentItem(self.parentItem().parentItem())
        AnimationChangeScale(self, start=1, end=0, endcall=lambda: self.scene().removeItem(self))


class MyDisplayItem:
    style = {}
    track_style = {}
    scale_value = 1

    font = None
    text = None

    text_parent = None

    is_new = None

    default_shape = "cross"

    def __init__(self, marker_handler, data=None, event=None, type=None):
        # store marker handler
        self.marker_handler = marker_handler
        # store data or create new instance
        if data is not None:
            self.data = data
            self.is_new = False
        else:
            self.data = self.newData(event, type)
            self.data.save()
            self.is_new = True
        # extract the style information
        self.GetStyle()
        # call the init function of the main class
        self.init2()

        # tell the counter that we ware here
        self.marker_handler.GetCounter(self.data.type).AddCount(1)

        # update the displayed text
        self.setText(self.GetText())

        # apply the style
        self.ApplyStyle()

        # adjust the size
        pen = self.pen()
        pen.setCosmetic(True)
        self.setPen(pen)
        self.setScale(1 / self.marker_handler.scale)

    def ReloadData(self):
        # reload data from database
        self.data = self.data.get(id=self.data.id)
        # update marker display
        self.GetStyle()
        self.ApplyStyle()
        self.setText(self.GetText())

    def GetStyle(self):
        self.style = {}
        entries = [self.data.type, self.data]

        for entry in entries:
            if entry and entry.style:
                style_text = entry.style
                try:
                    type_style = json.loads(style_text)
                except ValueError:
                    type_style = {}
                    print("WARNING: %d style could not be read: %s" % (entry.id, style_text))
                self.style.update(type_style)

        # get color from old color field
        if "color" not in self.style and self.data.type:
            self.style["color"] = self.data.type.color

        # change color text to rgb by interpreting it as html text or a color map
        if self.style["color"][0] != "#":
            self.style["color"] = GetColorFromMap(self.style["color"], self.data.id)
        else:
            self.style["color"] = HTMLColorToRGB(self.style["color"])

        # store color
        self.color = QtGui.QColor(*self.style["color"])

    def ApplyStyle(self):
        if self.text:
            self.text.setBrush(QtGui.QBrush(self.color))
        self.setScale(None)
        line_styles = dict(solid=Qt.SolidLine, dash=Qt.DashLine, dot=Qt.DotLine, dashdot=Qt.DashDotLine,
                           dashdotdot=Qt.DashDotDotLine)
        pen = self.pen()
        pen.setColor(self.color)
        pen.setWidthF(self.style.get("line-width", 2))
        pen.setStyle(line_styles[self.style.get("line-style", "solid")])
        self.setPen(pen)
        i = 1
        while True:
            grabber = getattr(self, "g%d" % i, None)
            if grabber is None:
                break
            grabber.setShape(self.style.get("shape", self.default_shape))
            grabber.setScale(self.style.get("scale", 1))
            i += 1

    # update text with priorities: marker, track, label
    def GetText(self):
        # check for marker text entry
        if self.data.text is not None:
            return self.data.text

        # check for track text entry
        if isinstance(self.data,
                      self.marker_handler.data_file.table_marker) and self.data.track is not None and self.data.track.text is not None:
            return self.data.track.text

        # check for type text entry
        if self.data.type and self.data.type.text is not None:
            return self.data.type.text

        # check for type text entry
        if isinstance(self.data,
                      self.marker_handler.data_file.table_marker) and self.data.track and self.data.track.type.text is not None:
            return self.data.track.type.text

        # if there are no text entries return an empty string
        return ""

    def setText(self, text):
        if self.text is None:
            self.font = QtGui.QFont()
            self.font.setPointSize(10)
            self.text_parent = QtWidgets.QGraphicsPathItem(self if self.text_parent is None else self.text_parent)
            self.text_parent.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations)
            self.text = QtWidgets.QGraphicsSimpleTextItem(self.text_parent)
            self.text.setFont(self.font)
            self.text.setPos(5, 5)
            self.text.setZValue(10)
            self.text.setBrush(QtGui.QBrush(self.color))

        # augment text
        if '$track_id' in text:
            data = self.data if type(self.data) is self.marker_handler.data_file.table_track else None
            if data and data.id:
                text = text.replace('$track_id', '%d' % data.id)
            else:
                text = text.replace('$track_id', '??')
        if '$marker_id' in text:
            data = self.data if type(self.data) is not self.marker_handler.data_file.table_track else self.marker
            if data and data.id:
                text = text.replace('$marker_id', '%d' % data.id)
            else:
                text = text.replace('$marker_id', '??')
        if '$x_pos' in text:
            text = text.replace('$x_pos', '%.2f' % self.data.x)
        if '$y_pos' in text:
            text = text.replace('$y_pos', '%.2f' % self.data.y)
        if '$length' in text:
            if type(self.data) is self.marker_handler.data_file.table_line:
                if self.data.length() is not None:
                    text = text.replace('$length', '%.2f' % self.data.length())
                else:
                    text = text.replace('$length', '')
            else:
                text = text.replace('$length', '??')
        if '$area' in text:
            if type(self.data) is self.marker_handler.data_file.table_rectangle:
                if self.data.area() is not None:
                    text = text.replace('$area', '%.2f' % self.data.area())
                else:
                    text = text.replace('$area', '')
            else:
                text = text.replace('$area', '??')
        if '\\n' in text:
            text = text.replace('\\n', '\n')

        self.text.setText(text)

    def setScale(self, scale=None):
        if scale is not None:
            self.scale_value = scale

    def draw(self, image, start_x, start_y, scale=1, image_scale=1):
        pass

    def graberDelete(self, grabber):
        self.delete()

    def save(self):
        # only if there are fields which are changed
        if len(self.data.dirty_fields):
            self.data.processed = 0
            self.data.save(only=self.data.dirty_fields)

    def delete(self, just_display=False):
        # delete the database entry
        if not just_display:
            self.data.delete_instance()

        # delete from marker handler list
        self.marker_handler.RemoveFromList(self)

        # delete from scene
        self.scene().removeItem(self)

        # delete from counter
        self.marker_handler.GetCounter(self.data.type).AddCount(-1)


class MyMarkerItem(MyDisplayItem, QtWidgets.QGraphicsPathItem):
    drag_start_pos = None

    def __init__(self, marker_handler, parent, data=None, event=None, type=None):
        QtWidgets.QGraphicsPathItem.__init__(self, parent)
        MyDisplayItem.__init__(self, marker_handler, data, event, type)

    def init2(self):
        self.g1 = MyGrabberItem(self, self.color, self.data.x, self.data.y, shape="cross", use_crosshair=True)
        self.text_parent = self.g1

    def newData(self, event, type):
        return self.marker_handler.data_file.table_marker(image=self.marker_handler.data_file.image,
                                                          x=event.pos().x(), y=event.pos().y(), type=type)

    def ReloadData(self):
        MyDisplayItem.ReloadData(self)
        self.updateDisplay()

    def updateDisplay(self):
        # update marker display
        self.g1.setPos(self.data.x, self.data.y)

    def graberMoved(self, grabber, pos):
        self.data.x = pos.x()
        self.data.y = pos.y()
        self.updateDisplay()

    def draw(self, image, start_x, start_y, scale=1, image_scale=1):
        w = 1. * scale
        b = (10 - 7) * scale
        r2 = 10 * scale
        x, y = self.pos().x() - start_x, self.pos().y() - start_y
        x *= image_scale
        y *= image_scale
        color = (self.color.red(), self.color.green(), self.color.blue())
        image.rectangle([x - w, y - r2, x + w, y - b], color)
        image.rectangle([x - w, y + b, x + w, y + r2], color)
        image.rectangle([x - r2, y - w, x - b, y + w], color)
        image.rectangle([x + b, y - w, x + r2, y + w], color)

    def delete(self, just_display=False):
        if not just_display:
            self.g1.delete()
        MyDisplayItem.delete(self, just_display)


class MyLineItem(MyDisplayItem, QtWidgets.QGraphicsLineItem):
    default_shape = "rect"

    def __init__(self, marker_handler, parent, data=None, event=None, type=None):
        QtWidgets.QGraphicsLineItem.__init__(self, parent)
        MyDisplayItem.__init__(self, marker_handler, data, event, type)

    def init2(self):
        self.setLine(*self.data.getPos())
        self.g1 = MyGrabberItem(self, self.color, *self.data.getPos1())
        self.g2 = MyGrabberItem(self, self.color, *self.data.getPos2())
        self.text_parent = self.g1
        pen = self.pen()
        pen.setWidth(2)
        self.setPen(pen)

    def newData(self, event, type):
        x, y = event.pos().x(), event.pos().y()
        return self.marker_handler.data_file.table_line(image=self.marker_handler.data_file.image,
                                                        x1=x, y1=y, x2=x, y2=y, type=type)

    def ReloadData(self):
        MyDisplayItem.ReloadData(self)
        # update line display
        self.setLine(*self.data.getPos())
        self.g1.setPos(*self.data.getPos1())
        self.g2.setPos(*self.data.getPos2())

    def graberMoved(self, grabber, pos):
        if grabber == self.g1:
            self.data.setPos1(pos.x(), pos.y())
            self.setLine(*self.data.getPos())
            self.g1.setPos(*self.data.getPos1())
            self.setText(self.GetText())
        if grabber == self.g2:
            self.data.setPos2(pos.x(), pos.y())
            self.setLine(*self.data.getPos())
            self.g2.setPos(*self.data.getPos2())
            self.setText(self.GetText())

    def drag(self, event):
        self.graberMoved(self.g2, event.pos())

    def draw(self, image, start_x, start_y, scale=1, image_scale=1):
        x1, y1 = self.data.getPos1()[0] - start_x, self.data.getPos1()[1] - start_y
        x2, y2 = self.data.getPos2()[0] - start_x, self.data.getPos2()[1] - start_y
        x1, y1, x2, y2 = np.array([x1, y1, x2, y2])*image_scale
        color = (self.color.red(), self.color.green(), self.color.blue())
        image.line([x1, y1, x2, y2], color, width=int(3 * scale * self.style.get("scale", 1)))

    def delete(self, just_display=False):
        if not just_display:
            self.g1.delete()
            self.g2.delete()
        MyDisplayItem.delete(self, just_display)


class MyRectangleItem(MyDisplayItem, QtWidgets.QGraphicsRectItem):
    default_shape = "rect"

    def __init__(self, marker_handler, parent, data=None, event=None, type=None):
        QtWidgets.QGraphicsLineItem.__init__(self, parent)
        MyDisplayItem.__init__(self, marker_handler, data, event, type)

    def init2(self):
        self.setRect(*self.data.getRect())
        self.g1 = MyGrabberItem(self, self.color, *self.data.getPos1())
        self.g2 = MyGrabberItem(self, self.color, *self.data.getPos2())
        self.g3 = MyGrabberItem(self, self.color, *self.data.getPos3())
        self.g4 = MyGrabberItem(self, self.color, *self.data.getPos4())
        self.text_parent = self.g3
        pen = self.pen()
        pen.setWidth(2)
        self.setPen(pen)

    def newData(self, event, type):
        x, y = event.pos().x(), event.pos().y()
        return self.marker_handler.data_file.table_rectangle(image=self.marker_handler.data_file.image,
                                                        x=x, y=y, width=0, height=0, type=type)

    def ReloadData(self):
        MyDisplayItem.ReloadData(self)
        self.updateDisplay()

    def updateDisplay(self):
        # update line display
        self.setRect(*self.data.getRect())
        self.g1.setPos(*self.data.getPos1())
        self.g2.setPos(*self.data.getPos2())
        self.g3.setPos(*self.data.getPos3())
        self.g4.setPos(*self.data.getPos4())
        self.setText(self.GetText())

    def CheckPositiveWidthHeight(self):
        if self.data.width < 0:
            self.data.x += self.data.width
            self.data.width = -self.data.width
            self.g1, self.g2, self.g3, self.g4 = self.g2, self.g1, self.g4, self.g3
            if self.text:
                self.text.setParentItem(self.g3)
        if self.data.height < 0:
            self.data.y += self.data.height
            self.data.height = -self.data.height
            self.g1, self.g2, self.g3, self.g4 = self.g4, self.g3, self.g2, self.g1
            if self.text:
                self.text.setParentItem(self.g3)

    def graberMoved(self, grabber, pos):
        if grabber == self.g1:
            self.data.width = self.data.x + self.data.width - pos.x()
            self.data.height = self.data.y + self.data.height - pos.y()
            self.data.x = pos.x()
            self.data.y = pos.y()
            self.CheckPositiveWidthHeight()
            self.updateDisplay()
        if grabber == self.g2:
            self.data.width = pos.x() - self.data.x
            self.data.height = self.data.y + self.data.height - pos.y()
            self.data.y = pos.y()
            self.CheckPositiveWidthHeight()
            self.updateDisplay()
        if grabber == self.g3:
            self.data.width = pos.x() - self.data.x
            self.data.height = pos.y() - self.data.y
            self.CheckPositiveWidthHeight()
            self.updateDisplay()
        if grabber == self.g4:
            self.data.width = self.data.x + self.data.width - pos.x()
            self.data.height = pos.y() - self.data.y
            self.data.x = pos.x()
            self.CheckPositiveWidthHeight()
            self.updateDisplay()

    def drag(self, event):
        self.graberMoved(self.g3, event.pos())

    def draw(self, image, start_x, start_y, scale=1, image_scale=1):
        x1, y1 = self.data.getPos1()[0] - start_x, self.data.getPos1()[1] - start_y
        x2, y2 = self.data.getPos3()[0] - start_x, self.data.getPos3()[1] - start_y
        x1, y1, x2, y2 = np.array([x1, y1, x2, y2]) * image_scale
        color = (self.color.red(), self.color.green(), self.color.blue())
        image.line([x1, y1, x2, y1], color, width=int(3 * scale * self.style.get("scale", 1)))
        image.line([x2, y1, x2, y2], color, width=int(3 * scale * self.style.get("scale", 1)))
        image.line([x2, y2, x1, y2], color, width=int(3 * scale * self.style.get("scale", 1)))
        image.line([x1, y2, x1, y1], color, width=int(3 * scale * self.style.get("scale", 1)))

    def delete(self, just_display=False):
        if not just_display:
            self.g1.delete()
            self.g2.delete()
            self.g3.delete()
            self.g4.delete()
        MyDisplayItem.delete(self, just_display)


class MyTrackItem(MyDisplayItem, QtWidgets.QGraphicsPathItem):
    marker = None
    active = False
    hidden = False

    points_data = []
    min_frame = 0
    max_frame = 0
    g1 = None

    def __init__(self, marker_handler, parent, data=None, event=None, type=None, frame=None):
        self.current_frame = frame
        QtWidgets.QGraphicsPathItem.__init__(self, parent)
        MyDisplayItem.__init__(self, marker_handler, data, event, type)

    def newData(self, event, type):
        self.data = self.marker_handler.data_file.table_track(uid=uuid.uuid1(), type=type)
        self.data.save()
        self.marker = self.marker_handler.data_file.table_marker(image=self.marker_handler.data_file.image,
                                                          x=event.pos().x(), y=event.pos().y(), type=type, track=self.data)
        self.marker.save()
        return self.data

    def init2(self):
        self.points_data = SortedDict()
        for point in self.data.markers:
            self.points_data[point.image.sort_index] = point
        self.min_frame = min(self.points_data.keys())
        self.max_frame = max(self.points_data.keys())
        self.g1 = MyGrabberItem(self, self.color, 0, 0, shape="cross")
        self.text_parent = self.g1
        if self.marker is None:
            try:
                self.marker = self.points_data[self.current_frame]
            except KeyError:
                self.marker = None
                self.g1.setPos(*point.pos())
        self.updateDisplay()

    def ApplyStyle(self):
        MyDisplayItem.ApplyStyle(self)
        line_styles = dict(solid=Qt.SolidLine, dash=Qt.DashLine, dot=Qt.DotLine, dashdot=Qt.DashDotLine,
                           dashdotdot=Qt.DashDotDotLine)

        pen = self.pen()
        pen.setWidthF(self.style.get("track-line-width", 2))
        pen.setStyle(line_styles[self.style.get("track-line-style", "solid")])
        self.setPen(pen)
        self.g1.setShape(self.style.get("shape", "cross"))
        self.g1.setScale(self.style.get("scale", 1))

    def graberMoved(self, grabber, pos):
        if self.marker is None:
            self.marker = self.marker_handler.marker_file.table_marker(image=self.marker_handler.marker_file.data_file.image,
                                                                       x=pos.x(), y=pos.y(),
                                                                     type=self.data.type,
                                                                     track=self.data, text=None)
            self.marker.save()
            self.points_data[self.current_frame] = self.marker
            self.SetTrackActive(True)
        else:
            self.marker.x = pos.x()
            self.marker.y = pos.y()
        self.updateDisplay()

    def graberDelete(self, grabber):
        self.RemoveTrackPoint()

    def updateDisplay(self):
        path = QtGui.QPainterPath()
        circle_width = self.scale_value * 10 * self.style.get("track-point-scale", 1)
        last_frame = None
        shape = self.style.get("track-point-shape", "circle")
        for frame in self.points_data:
            if self.marker_handler.config.tracking_show_trailing != -1 and frame < self.current_frame - self.marker_handler.config.tracking_show_trailing:
                continue
            if self.marker_handler.config.tracking_show_leading != -1 and frame > self.current_frame + self.marker_handler.config.tracking_show_leading:
                break
            point = self.points_data[frame]
            if last_frame == frame - 1:
                path.lineTo(point.x, point.y)
            else:
                path.moveTo(point.x, point.y)
            last_frame = frame
            if shape == "circle":
                path.addEllipse(point.x - .5 * circle_width, point.y - .5 * circle_width, circle_width,
                                circle_width)
            if shape == "rect":
                path.addRect(point.x - .5 * circle_width, point.y - .5 * circle_width, circle_width, circle_width)
            path.moveTo(point.x, point.y)
        self.setPath(path)
        if self.marker is not None:
            self.g1.setPos(*self.marker.pos())

    def FrameChanged(self, frame):

        self.current_frame = frame
        hide = not self.CheckToDisplay()
        if hide != self.hidden:
            self.hidden = hide
            self.setVisible(not self.hidden)
            self.g1.setVisible(not self.hidden)

        if frame in self.points_data:
            self.marker = self.points_data[frame]
            self.updateDisplay()
            self.SetTrackActive(True)
            #self.GetStyle()
            self.setText(self.GetText())
            return

        if not self.hidden:
            self.updateDisplay()
        self.SetTrackActive(False)
        self.marker = None

    def update(self, frame, point=None):
        if point is not None:
            self.AddTrackPoint(frame, point)
            if frame == self.current_frame:
                self.marker = self.marker.get(id=self.marker.id)
                self.GetStyle()
        else:
            self.RemoveTrackPoint(frame)
        self.updateDisplay()

    def AddTrackPoint(self, frame=None, point=None):
        if frame is None:
            frame = self.current_frame
        if point is None:
            point = self.data
        self.points_data[frame] = point
        self.min_frame = min(self.points_data.keys())
        self.max_frame = max(self.points_data.keys())
        if frame == self.current_frame:
            self.SetTrackActive(True)
        BroadCastEvent(self.marker_handler.modules, "MarkerPointsAdded")

    def RemoveTrackPoint(self, frame=None):
        # use the current frame if no frame is supplied
        if frame is None:
            frame = self.current_frame
        # delete the frame from points
        try:
            data = self.points_data.pop(frame)
            data.delete_instance()
            if frame == self.current_frame:
                self.marker = None
        except KeyError:
            pass
        # if it was the last one delete the track, too
        if len(self.points_data) == 0:
            self.delete()
            return
        # adjust the frame range
        self.min_frame = min(self.points_data.keys())
        self.max_frame = max(self.points_data.keys())
        # set the track to inactive if the current marker was removed
        if frame == self.current_frame:
            self.SetTrackActive(False)
        # redraw the track history
        self.updateDisplay()

    def SetTrackActive(self, active):
        if active is False:
            self.active = False
            self.setOpacity(0.25)
            #self.g1.setOpacity(0.5)
            if self.marker_handler.config.tracking_connect_nearest:
                self.setAcceptedMouseButtons(Qt.MouseButtons(0))
        else:
            self.active = True
            self.setOpacity(1)
            #self.g1.setOpacity(2)
            if self.marker_handler.config.tracking_connect_nearest:
                self.setAcceptedMouseButtons(Qt.MouseButtons(3))

    def CheckToDisplay(self):
        if self.min_frame - 2 <= self.current_frame <= self.max_frame + 100:
            return True
        return False

    def draw(self, image, start_x, start_y, scale=1, image_scale=1):
        if not self.CheckToDisplay():
            return
        color = (self.color.red(), self.color.green(), self.color.blue())
        circle_width = 10 * scale
        last_frame = None
        last_point = np.array([0, 0])
        offset = np.array([start_x, start_y])
        for frame in self.points_data:
            if self.marker_handler.config.tracking_show_trailing != -1 and frame < self.current_frame - self.marker_handler.config.tracking_show_trailing:
                continue
            if self.marker_handler.config.tracking_show_leading != -1 and frame > self.current_frame + self.marker_handler.config.tracking_show_leading:
                break
            point = self.points_data[frame]
            point = np.array([point.x, point.y]) - offset
            point *= image_scale

            if last_frame == frame - 1:
                image.line(np.concatenate((last_point, point)).tolist(), color, width=int(2 * scale))
            image.arc(np.concatenate((point - .5 * circle_width, point + .5 * circle_width)).tolist(), 0, 360, color)
            last_point = point
            last_frame = frame
        #if self.active:
        #    MyMarkerItem.draw(self, image, start_x, start_y, scale, image_scale)

    def setScale(self, scale):
        MyDisplayItem.setScale(self, scale)
        self.updateDisplay()

    def save(self):
        if self.active:
            if len(self.marker.dirty_fields):
                self.marker.processed = 0
                self.marker.save(only=self.marker.dirty_fields)
            MyDisplayItem.save(self)


class Crosshair(QtWidgets.QGraphicsPathItem):
    def __init__(self, parent, view, image, config):
        QtWidgets.QGraphicsPathItem.__init__(self, parent)
        self.parent = parent
        self.view = view
        self.image = image
        self.config = config
        self.radius = 50
        self.not_scaled = True
        self.scale = 1

        self.RGB = np.zeros((self.radius * 2 + 1, self.radius * 2 + 1, 3))
        self.Alpha = disk(self.radius) * 255
        self.Image = np.concatenate((self.RGB, self.Alpha[:, :, None]), axis=2)
        self.CrosshairQImage = array2qimage(self.Image)
        self.CrosshairQImageView = rgb_view(self.CrosshairQImage)

        self.Crosshair = QtWidgets.QGraphicsPixmapItem(QtGui.QPixmap(self.CrosshairQImage), self)
        self.Crosshair.setOffset(-self.radius, -self.radius)
        self.setPos(self.radius * 3, self.radius * 3)
        self.Crosshair.setZValue(-5)
        self.setZValue(30)
        self.setVisible(False)

        self.pathCrosshair = QtGui.QPainterPath()
        self.pathCrosshair.addEllipse(-self.radius, -self.radius, self.radius * 2, self.radius * 2)

        w = 0.333 * 0.5
        b = 40
        r2 = 50
        self.pathCrosshair2 = QtGui.QPainterPath()
        self.pathCrosshair2.addRect(-r2, -w, b, w * 2)
        self.pathCrosshair2.addRect(r2, -w, -b, w * 2)
        self.pathCrosshair2.addRect(-w, -r2, w * 2, b)
        self.pathCrosshair2.addRect(-w, r2, w * 2, -b)

        self.CrosshairPathItem = QtWidgets.QGraphicsPathItem(self.pathCrosshair, self)
        # self.setPath(self.pathCrosshair)
        self.CrosshairPathItem2 = QtWidgets.QGraphicsPathItem(self.pathCrosshair2, self)

    def setScale(self, value):
        QtWidgets.QGraphicsPathItem.setScale(self, value)
        self.scale = value
        if not self.SetZoom(value):
            QtWidgets.QGraphicsPathItem.setScale(self, 0)
        return True

    def SetZoom(self, new_radius=None):
        if new_radius is not None:
            self.radius = int(new_radius * 50 / 3)
        if not self.isVisible():
            self.not_scaled = True
            return False
        self.not_scaled = False
        if self.radius <= 10:
            return False
        self.RGB = np.zeros((self.radius * 2 + 1, self.radius * 2 + 1, 3))
        self.Alpha = disk(self.radius) * 255
        self.Image = np.concatenate((self.RGB, self.Alpha[:, :, None]), axis=2)
        self.CrosshairQImage = array2qimage(self.Image)
        self.CrosshairQImageView = rgb_view(self.CrosshairQImage)
        self.Crosshair.setPixmap(QtGui.QPixmap(self.CrosshairQImage))
        self.Crosshair.setScale(1 / self.radius * 50)
        self.Crosshair.setOffset(-self.radius - 0.5, -self.radius - 0.5)
        self.MoveCrosshair(self.pos().x(), self.pos().y())
        return True

    def MoveCrosshair(self, x, y):
        y = int(y)
        x = int(x)
        self.setPos(x, y)
        if not self.isVisible() or self.radius <= 10:
            return
        self.CrosshairQImageView[:, :, :] = self.SaveSlice(self.image.image,
                                                           [[y - self.radius, y + self.radius + 1],
                                                            [x - self.radius, x + self.radius + 1], [0, 3]])
        self.Crosshair.setPixmap(QtGui.QPixmap(self.CrosshairQImage))

    @staticmethod
    def SaveSlice(source, slices):
        shape = []
        slices1 = []
        slices2 = []
        empty = False
        for length, slice_border in zip(source.shape, slices):
            slice_border = [int(b) for b in slice_border]
            shape.append(slice_border[1] - slice_border[0])
            if slice_border[1] < 0:
                empty = True
            slices1.append(slice(max(slice_border[0], 0), min(slice_border[1], length)))
            slices2.append(slice(-min(slice_border[0], 0),
                                 min(length - slice_border[1], 0) if min(length - slice_border[1], 0) != 0 else shape[
                                     -1]))
        new_slice = np.zeros(shape)
        if empty:
            return new_slice
        new_slice[slices2[0], slices2[1], :] = source[slices1[0], slices1[1], :3]
        return new_slice

    def Hide(self):
        self.setVisible(False)

    def Show(self, point):
        self.setVisible(True)
        if self.not_scaled:
            if self.SetZoom():
                self.setScale(self.scale)
            else:
                self.setScale(0)
        self.CrosshairPathItem2.setPen(QtGui.QPen(point.brush().color(), 1))
        self.CrosshairPathItem.setPen(QtGui.QPen(point.brush().color(), 2))


class MyCounter(QtWidgets.QGraphicsRectItem):
    def __init__(self, parent, marker_handler, type, index):
        QtWidgets.QGraphicsRectItem.__init__(self, parent)
        self.parent = parent
        self.marker_handler = marker_handler
        self.type = type
        self.index = index
        self.count = 0
        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))

        self.setAcceptHoverEvents(True)
        self.active = False

        self.font = self.marker_handler.window.mono_font
        self.font.setPointSize(14)

        self.text = QtWidgets.QGraphicsSimpleTextItem(self)
        self.text.setFont(self.font)
        if self.type is not None:
            self.color = QtGui.QColor(*HTMLColorToRGB(self.type.color))
        else:
            self.color = QtGui.QColor("white")
        self.text.setBrush(QtGui.QBrush(self.color))
        self.text.setZValue(10)

        self.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 128)))
        self.setPos(10, 10 + 25 * self.index)
        self.setZValue(9)

        count = 0
        if self.type:
            for point in self.marker_handler.points:
                if point.data.type == self.type:
                    count += 1
        self.AddCount(count)

    def AddCount(self, new_count):
        self.count += new_count
        if self.type:
            self.text.setText(
                str(self.index + 1) + ": " + self.type.name + " %d" % self.count)
        else:
            self.text.setText("+ add type")
        rect = self.text.boundingRect()
        rect.setX(-5)
        rect.setWidth(rect.width() + 5)
        self.setRect(rect)

    def SetToActiveColor(self):
        self.active = True
        self.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255, 128)))

    def SetToInactiveColor(self):
        self.active = False
        self.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 128)))

    def hoverEnterEvent(self, event):
        if self.active is False:
            self.setBrush(QtGui.QBrush(QtGui.QColor(128, 128, 128, 128)))

    def hoverLeaveEvent(self, event):
        if self.active is False:
            self.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 128)))

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.RightButton or self.type is None:
            if not self.marker_handler.marker_edit_window or not self.marker_handler.marker_edit_window.isVisible():
                self.marker_handler.marker_edit_window = MarkerEditor(self.marker_handler,
                                                                      self.marker_handler.marker_file)
                self.marker_handler.marker_edit_window.show()
            self.marker_handler.marker_edit_window.setMarker(self.type, data_type="type")
        elif event.button() == QtCore.Qt.LeftButton:
            if not self.marker_handler.active:
                BroadCastEvent([module for module in self.marker_handler.modules if module != self.marker_handler],
                               "setActiveModule", False)
                self.marker_handler.setActiveModule(True)
            self.marker_handler.SetActiveMarkerType(self.index)
            if self.marker_handler.marker_edit_window:
                self.marker_handler.marker_edit_window.setMarker(self.type, data_type="type")


class MarkerHandler:
    points = []
    tracks = []
    lines = []
    rectangles = []
    display_lists = [points, tracks, lines, rectangles]
    counter = []
    scale = 1

    marker_edit_window = None

    active = False
    frame_number = None
    hidden = False

    active_type_index = None
    active_type = None

    active_drag = None

    def __init__(self, window, data_file, parent, parent_hud, view, image_display, config, modules, datafile, new_database):
        self.window = window
        self.data_file = data_file
        self.view = view
        self.parent_hud = parent_hud
        self.modules = modules
        self.config = config
        self.data_file = datafile
        self.parent = parent

        self.button = QtWidgets.QPushButton()
        self.button.setCheckable(True)
        self.button.setIcon(qta.icon("fa.crosshairs"))
        self.button.setToolTip("add/edit marker for current frame")
        self.button.clicked.connect(self.ToggleInterfaceEvent)
        self.window.layoutButtons.addWidget(self.button)

        self.marker_file = MarkerFile(datafile)

        if self.config.hide_interfaces:
            self.hidden = True

        self.MarkerParent = QtWidgets.QGraphicsPixmapItem(QtGui.QPixmap(array2qimage(np.zeros([1, 1, 4]))), self.parent)
        self.MarkerParent.setZValue(10)

        self.TrackParent = QtWidgets.QGraphicsPixmapItem(QtGui.QPixmap(array2qimage(np.zeros([1, 1, 4]))), self.parent)
        self.TrackParent.setZValue(10)

        self.scene_event_filter = GraphicsItemEventFilter(parent, self)
        image_display.AddEventFilter(self.scene_event_filter)

        self.Crosshair = Crosshair(parent, view, image_display, config)

        # if a new database is created fill it with markers from the config
        if new_database:
            for type_id, type_def in self.config.types.items():
                self.marker_file.set_type(type_id, type_def[0], type_def[1], type_def[2])

        self.UpdateCounter()

        # place tick marks for already present markers
        for item in self.marker_file.get_marker_frames():
            BroadCastEvent(self.modules, "MarkerPointsAdded", item.image.sort_index)

    def drawToImage(self, image, start_x, start_y, scale=1, image_scale=1):
        for list in self.display_lists:
            for point in list:
                point.draw(image, start_x, start_y, scale, image_scale)

    def UpdateCounter(self):
        for counter in self.counter:
            self.view.scene.removeItem(self.counter[counter])

        type_list = self.marker_file.get_type_list()
        self.counter = {index: MyCounter(self.parent_hud, self, type, index) for index, type in enumerate(type_list)}
        self.counter[-1] = MyCounter(self.parent_hud, self, None, len(self.counter))
        if len(list(self.counter.keys())):
            self.active_type = self.counter[list(self.counter.keys())[0]].type
        else:
            self.active_type = None

        for key in self.counter:
            self.counter[key].setVisible(not self.hidden)

    def GetCounter(self, type):
        for index in self.counter:
            if self.counter[index].type == type:
                return self.counter[index]
        raise NameError("A non existing type was referenced")

    def ReloadMarker(self, frame=None):
        # called via SendCommand from external scripts or add-ons
        # get the frame
        if frame is None:
            frame = self.data_file.get_current_image()
            image_id = self.data_file.image.id
        else:
            image_id = self.data_file.get_image(frame).id
        # Tracks
        marker_list = self.data_file.table_marker.select().where(self.data_file.table_marker.image == image_id)
        marker_list = {marker.track_id: marker for marker in marker_list}
        for track in self.tracks:
            if track.data.id in marker_list:
                track.update(frame, marker_list[track.data.id])
                marker_list.pop(track.data.id)
            else:
                track.update(frame, None)
        # Points
        if frame == self.frame_number:
            self.LoadPoints()
            self.LoadLines()
            self.LoadRectangles()

    def LoadImageEvent(self, filename, framenumber):
        self.frame_number = framenumber
        image = self.data_file.image

        if len(self.tracks) == 0:
            self.LoadTracks()
        else:
            for track in self.tracks:
                track.FrameChanged(framenumber)
        self.LoadPoints()
        self.LoadLines()
        self.LoadRectangles()

    def LoadTracks(self):
        while len(self.tracks):
            self.tracks[0].delete(just_display=True)
        track_list = self.marker_file.table_track.select()
        for track in track_list:
            data = track.markers
            if data.count():
                self.tracks.append(MyTrackItem(self, self.TrackParent, data=track, frame=self.frame_number))

    def ReloadTrack(self, track):
        track_item = self.GetMarkerItem(track)
        track_item.delete(just_display=True)
        self.tracks.append(MyTrackItem(self, self.TrackParent, data=track, frame=self.frame_number))

    def LoadPoints(self):
        while len(self.points):
            self.points[0].delete(just_display=True)
        marker_list = (
        self.marker_file.table_marker.select(self.marker_file.table_marker, self.marker_file.table_markertype)
        .join(self.marker_file.table_markertype)
        .where(self.marker_file.table_marker.image == self.data_file.image.id)
        )
        for marker in marker_list:
            if not marker.track:
                self.points.append(MyMarkerItem(self, self.MarkerParent, marker))
                self.points[-1].setScale(1 / self.scale)

    def LoadLines(self):
        while len(self.lines):
            self.lines[0].delete(just_display=True)
        line_list = (
            self.marker_file.table_line.select(self.marker_file.table_line, self.marker_file.table_markertype)
                .join(self.marker_file.table_markertype)
                .where(self.marker_file.table_line.image == self.data_file.image.id)
        )
        for line in line_list:
            self.lines.append(MyLineItem(self, self.MarkerParent, data=line))

    def LoadRectangles(self):
        while len(self.rectangles):
            self.rectangles[0].delete(just_display=True)
        rect_list = (
            self.marker_file.table_rectangle.select(self.marker_file.table_rectangle, self.marker_file.table_markertype)
                .join(self.marker_file.table_markertype)
                .where(self.marker_file.table_rectangle.image == self.data_file.image.id)
        )
        for rect in rect_list:
            self.rectangles.append(MyRectangleItem(self, self.MarkerParent, data=rect))

    def ClearPoints(self):
        self.points = []
        self.view.scene.removeItem(self.MarkerParent)
        self.MarkerParent = QtWidgets.QGraphicsPixmapItem(QtGui.QPixmap(array2qimage(np.zeros([1, 1, 4]))), self.parent)
        self.MarkerParent.setZValue(10)

    def RemoveFromList(self, point):
        for list in self.display_lists:
            try:
                list.remove(point)
                break
            except ValueError:
                continue

    def GetMarkerItem(self, data):
        for list in self.display_lists:
            for point in list:
                if type(point.data) != type(data):
                    break
                if point.data.id == data.id:
                    return point

    def GetTrackItem(self, data):
        for track in self.tracks:
            if track.data.id == data.id:
                return track

    def save(self):
        for list in self.display_lists:
            for point in list:
                point.save()

    def SetActiveMarkerType(self, new_index):
        if new_index >= len(self.counter) - 1:
            return
        if self.active_type_index is not None:
            self.counter[self.active_type_index].SetToInactiveColor()
        self.active_type = self.counter[new_index].type
        self.active_type_index = new_index
        self.counter[self.active_type_index].SetToActiveColor()

    def zoomEvent(self, scale, pos):
        self.scale = scale
        for list in self.display_lists:
            for point in list:
                point.setScale(1 / scale)
        self.Crosshair.setScale(1 / scale)

    def setActiveModule(self, active, first_time=False):
        self.scene_event_filter.active = active
        self.active = active
        for point in self.points:
            point.setActive(active)
        if active:
            self.view.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
            if self.active_type_index is not None:
                self.counter[self.active_type_index].SetToActiveColor()
        else:
            if self.active_type_index is not None:
                self.counter[self.active_type_index].SetToInactiveColor()
        return True

    def toggleMarkerShape(self):
        global point_display_type
        point_display_type += 1
        if point_display_type >= len(point_display_types):
            point_display_type = 0
        for point in self.points:
            point.UpdatePath()
        for track in self.tracks:
            track.UpdatePath()

    def sceneEventFilter(self, event):
        if self.hidden or self.data_file.image is None:
            return False
        if event.type() == QtCore.QEvent.GraphicsSceneMousePress and event.button() == QtCore.Qt.LeftButton and not event.modifiers() & Qt.ControlModifier:  # QtCore.QEvent.MouseButtonPress:
            self.active_drag = None
            if len(self.points) >= 0:
                BroadCastEvent(self.modules, "MarkerPointsAdded")
            tracks = [track for track in self.tracks if track.data.type.id == self.active_type.id]
            if self.active_type.mode & TYPE_Track and self.config.tracking_connect_nearest and \
                    len(tracks) and not event.modifiers() & Qt.AltModifier:
                distances = [np.linalg.norm(PosToArray(point.g1.pos() - event.pos())) for point in tracks]
                index = np.argmin(distances)
                tracks[index].graberMoved(None, event.pos())
                if event.modifiers() & Qt.ShiftModifier:
                    self.window.JumpFrames(1)
            elif self.active_type.mode & TYPE_Track:
                self.tracks.append(
                    MyTrackItem(self, self.TrackParent, event=event, type=self.active_type, frame=self.frame_number))
            elif self.active_type.mode & TYPE_Line:
                self.lines.append(MyLineItem(self, self.TrackParent, event=event, type=self.active_type))
                self.active_drag = self.lines[-1]
            elif self.active_type.mode & TYPE_Rect:
                self.rectangles.append(MyRectangleItem(self, self.TrackParent, event=event, type=self.active_type))
                self.active_drag = self.rectangles[-1]
            else:
                self.points.append(MyMarkerItem(self, self.MarkerParent, event=event, type=self.active_type))
            return True
        elif event.type() == QtCore.QEvent.GraphicsSceneMouseMove and self.active_drag:
            self.active_drag.drag(event)
            return True
        return False

    def keyPressEvent(self, event):

        numberkey = event.key() - 49

        # @key ---- Marker ----
        if self.active and 0 <= numberkey < 9 and event.modifiers() != Qt.KeypadModifier:
            # @key 0-9: change marker type
            self.SetActiveMarkerType(numberkey)

        if event.key() == QtCore.Qt.Key_T:
            # @key T: toggle marker shape
            self.toggleMarkerShape()

    def ToggleInterfaceEvent(self):
        self.hidden = not self.hidden
        for key in self.counter:
            self.counter[key].setVisible(not self.hidden)
        for point in self.points:
            point.setActive(not self.hidden)
        for track in self.tracks:
            track.setActive(not self.hidden)
        self.button.setChecked(not self.hidden)

    def closeEvent(self, event):
        if self.marker_edit_window:
            self.marker_edit_window.close()

    @staticmethod
    def file():
        return __file__

    @staticmethod
    def can_create_module(config):
        return len(config.types) > 0
