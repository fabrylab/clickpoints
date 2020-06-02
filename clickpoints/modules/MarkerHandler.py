#!/usr/bin/env python
# -*- coding: utf-8 -*-
# MarkerHandler.py

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
import re
import os
import peewee
import sqlite3

from qtpy import QtGui, QtCore, QtWidgets
from qtpy.QtCore import Qt
import qtawesome as qta

import numpy as np
from sortedcontainers import SortedDict

from qimage2ndarray import array2qimage, rgb_view
import imageio

import uuid

import json
import matplotlib.pyplot as plt
from threading import Thread

from clickpoints.includes.QtShortCuts import AddQSpinBox, AddQLineEdit, AddQLabel, AddQComboBox, AddQColorChoose, GetColorByIndex, AddQCheckBox
from clickpoints.includes.Tools import GraphicsItemEventFilter, disk, PosToArray, BroadCastEvent, HTMLColorToRGB, IconFromFile, MyCommandButton
from clickpoints.includes.slide import myslide

try:
    import openslide
    openslide_loaded = True
    print("openslide", openslide.__version__)
except ImportError:
    openslide_loaded = False

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

path_ring = QtGui.QPainterPath()
# path_circle.arcTo(-5, -5, 10, 10, 0, 130)
path_ring.addEllipse(-5, -5, 10, 10)
path_ring.addEllipse(-4, -4, 8, 8)

path_rect = QtGui.QPainterPath()
path_rect.addRect(-5, -5, 10, 10)

paths = dict(cross=path1, circle=path_circle, ring=path_ring, rect=path_rect)

TYPE_Normal = 0
TYPE_Rect = 1
TYPE_Line = 2
TYPE_Track = 4
TYPE_Ellipse = 8
TYPE_Polygon = 16


def addShapeNone(path, x, y, size):
    pass

def addShapeCircle(path, x, y, size):
    path.addEllipse(x - .5 * size, y - .5 * size, size, size)
    path.moveTo(x, y)

def addShapeRect(path, x, y, size):
    path.addRect(x - .5 * size, y - .5 * size, size, size)
    path.moveTo(x, y)

def connectTrackFirst(path_line, path_gap, x, y):
    path_line.moveTo(x, y)
    path_gap.moveTo(x, y)

def connectTrackLine(path_line, path_gap, x, y):
    path_line.lineTo(x, y)
    path_gap.moveTo(x, y)

def connectTrackGap(path_line, path_gap, x, y):
    path_line.moveTo(x, y)
    path_gap.lineTo(x, y)


def colorToTuple(color):
    return (color.red(), color.green(), color.blue())


def drawLine(image, start, end, color, width, style):

    if not isinstance(color, tuple):
        color = colorToTuple(color)

    pattern = [1]
    if style == "dash":
        pattern = [7, 4]
    elif style == "dot":
        pattern = [1, 3]
    elif style == "dashdot":
        pattern = [7, 4, 2, 4]
    elif style == "dashdotdot":
        pattern = [7, 4, 2, 4, 2, 4]
    pattern = np.array(pattern) * width / 2
    total = sum(pattern)
    repetitions = int(len(pattern) / 2)
    if total == 0:
        return

    # solid line
    if len(pattern) == 1:
        image.line(np.concatenate((start, end)).tolist(), color, width=int(width))
    else:
        difference = end - start
        distance = np.linalg.norm(difference)
        difference = difference / distance

        current_pos = start
        for i in range(int(distance / total)):
            for rep in range(repetitions):
                new_pos = current_pos + difference * pattern[rep * 2]
                image.line(np.concatenate((current_pos, new_pos)).tolist(), color, width=int(width))
                current_pos = new_pos + difference * pattern[rep * 2 + 1]
        image.line(np.concatenate((current_pos, end)).tolist(), color, width=int(width))


def drawMarker(image, point, color, width, shape):
    if not isinstance(color, tuple):
        color = colorToTuple(color)

    if shape == "ring":
        image.arc(np.concatenate((point - .5 * width, point + .5 * width)).tolist(), 0, 360, color)
    elif shape == "circle":
        image.arc(np.concatenate((point - .5 * width, point + .5 * width)).tolist(), 0, 360, color)
    elif shape == "rect":
        image.rectangle(np.concatenate((point - .5 * width, point + .5 * width)).tolist(), color)
    elif shape == "cross":
        w = 1. * width / 10
        b = (10 - 7) * width / 10
        r2 = 10 * width / 10
        x, y = point
        image.rectangle([x - w, y - r2, x + w, y - b], color)
        image.rectangle([x - w, y + b, x + w, y + r2], color)
        image.rectangle([x - r2, y - w, x - b, y + w], color)
        image.rectangle([x + b, y - w, x + r2, y + w], color)


def getMarker(image, color, width, shape):
    name = "%s_%s_%s" % (color.name(), str(width), shape)
    if getattr(image, "marker_dict", None) is None:
        image.marker_dict = {}
    if name in image.marker_dict:
        return image.marker_dict[name]
    if shape == "cross":
        width *= 2
    # create a new marker object
    marker = image.marker(insert=(width, width), size=(width*2, width*2))
    if shape == "ring":
        # red point as marker
        marker.add(image.circle((width, width), r=width / 2, stroke=color.name(), fill="none"))
    elif shape == "circle":
        # red point as marker
        marker.add(image.circle((width, width), r=width / 2, fill=color.name()))
    elif shape == "rect":
        # red point as marker
        marker.add(image.rect((0, 0), (width, width), fill=color.name()))
    elif shape == "cross":
        w = 2. * width / 20.
        b = (10 - 7) * width / 20.
        r2 = 7 * width / 20.
        c = b + r2+width/2

        # red point as marker
        marker.add(image.rect((c + b, c - w / 2), size=(r2, w), fill=color.name()))
        marker.add(image.rect((c - b - r2, c - w / 2), size=(r2, w), fill=color.name()))
        marker.add(image.rect((c - w / 2, c + b), size=(w, r2), fill=color.name()))
        marker.add(image.rect((c - w / 2, c - b - r2), size=(w, r2), fill=color.name()))

    # add marker to defs section of the drawing
    image.defs.add(marker)
    image.marker_dict[name] = marker
    return marker


class TrackMarkerObject:
    save_pos = None

    def __init__(self, pos, data):
        self.pos = pos
        self.data = data
        if self.data["style"]:
            self.style = json.loads(self.data["style"])
            if "color" in self.style:
                self.style["color"] = QtGui.QColor(*HTMLColorToRGB(self.style["color"]))

    def getStyle(self, name, default):
        if self.data["style"] and name in self.style:
            return self.style[name]
        return default

class MarkerFile:
    def __init__(self, datafile):
        self.data_file = datafile

        self.table_markertype = self.data_file.table_markertype
        self.table_marker = self.data_file.table_marker
        self.table_track = self.data_file.table_track
        self.table_line = self.data_file.table_line
        self.table_rectangle = self.data_file.table_rectangle
        self.table_ellipse = self.data_file.table_ellipse
        self.table_polygon = self.data_file.table_polygon
        self.table_polygon_point = self.data_file.table_polygon_point

        self.table_image = self.data_file.table_image
        self.table_offset = self.data_file.table_offset
        self.db = self.data_file.db

    def set_track(self, type):
        track = self.table_track(uid=uuid.uuid4().hex, type=type)
        track.save()
        return track

    def set_type(self, id, name, rgb_tuple, mode, style="", text=""):
        try:
            type = self.table_markertype.get(self.table_markertype.name == name)
        except peewee.DoesNotExist:
            rgb_tuple = [int(i) for i in rgb_tuple]
            type = self.table_markertype(name=name, color='#%02x%02x%02x' % tuple(rgb_tuple), mode=mode, style=style, text=text)
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

    def get_marker_frames1(self):
        # query all sort_indices which have a marker entry
        return (self.data_file.table_image.select(self.data_file.table_image.sort_index)
                                          .join(self.table_marker)
                                          .group_by(self.data_file.table_image.id))

    def get_marker_frames2(self):
        # query all sort_indices which have a rectangle entry
        return (self.data_file.table_image.select(self.data_file.table_image.sort_index)
                                          .join(self.table_rectangle)
                                          .group_by(self.data_file.table_image.id))

    def get_marker_frames3(self):
        # query all sort_indices which have a line entry
        return (self.data_file.table_image.select(self.data_file.table_image.sort_index)
                                          .join(self.table_line)
                                          .group_by(self.data_file.table_image.id))

    def get_marker_frames4(self):
        # query all sort_indices which have a ellipse entry
        return (self.data_file.table_image.select(self.data_file.table_image.sort_index)
                                          .join(self.data_file.table_ellipse)
                                          .group_by(self.data_file.table_image.id))

    def get_marker_frames5(self):
        # query all sort_indices which have a polygon entry
        return (self.data_file.table_image.select(self.data_file.table_image.sort_index)
                                          .join(self.data_file.table_polygon)
                                          .group_by(self.data_file.table_image.id))


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

        self.type_ids = {new_type.name: new_type.id for new_type in types if new_type.mode == type.mode}
        self.type_names = [new_type.name for new_type in types if new_type.mode == type.mode]

        if len(self.type_ids):
            self.label = QtWidgets.QLabel(
                "The type %s has %d marker. Do you want to delete all of them or assign them to another type?" % (
                type.name, count))
        else:
            self.label = QtWidgets.QLabel(
                "The type %s has %d marker. Do you want to delete all of them?" % (
                    type.name, count))
        main_layout.addWidget(self.label)
        if len(self.type_ids):
            self.comboBox = AddQComboBox(main_layout, "New Type:", self.type_names)

        layout2 = QtWidgets.QHBoxLayout()
        main_layout.addLayout(layout2)
        button1 = QtWidgets.QPushButton("Delete")
        button1.clicked.connect(lambda: self.done(-1))
        layout2.addWidget(button1)
        if len(self.type_ids):
            button2 = QtWidgets.QPushButton("Move")
            button2.clicked.connect(lambda: self.done(self.type_ids[self.comboBox.currentText()]))
            layout2.addWidget(button2)
        button3 = QtWidgets.QPushButton("Cancel")
        button3.clicked.connect(lambda: self.done(0))
        layout2.addWidget(button3)

class myTreeWidgetItem(QtGui.QStandardItem):
    def __init__(self, parent=None):
        QtGui.QStandardItem.__init__(self, parent)

    def __lt__(self, otherItem):
        if self.sort is None:
            return 0
        return self.sort < otherItem.sort
        column = self.treeWidget().sortColumn()

        if column == 0 or column == 6 or column == 7 or column == 8:
            return float(self.text(column)) < float(otherItem.text(column))
        else:
            return self.text(column) < otherItem.text(column)


class MyTreeView(QtWidgets.QTreeView):
    item_selected = lambda x: 0
    item_clicked = lambda x: 0
    item_activated = lambda x: 0
    item_hoverEnter = lambda x: 0
    item_hoverLeave = lambda x: 0

    last_selection = None
    last_hover = None

    def __init__(self, parent, layout):
        super(QtWidgets.QTreeView, self).__init__()

        self.data_file = parent.data_file

        layout.addWidget(self)

        # start a list for backwards search (from marker entry back to tree entry)
        self.marker_modelitems = {}
        self.marker_type_modelitems = {}

        # model for tree view
        self.model = QtGui.QStandardItemModel(0, 0)

        # some settings for the tree
        self.setUniformRowHeights(True)
        self.setHeaderHidden(True)
        self.setAnimated(True)
        self.setModel(self.model)
        self.expanded.connect(self.TreeExpand)
        self.clicked.connect(self.treeClicked)
        self.activated.connect(self.treeActivated)
        self.selectionModel().selectionChanged.connect(self.selectionChanged)

        # add context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)

        # add hover highlight
        self.viewport().setMouseTracking(True)
        self.viewport().installEventFilter(self)

        self.item_lookup = {}

        self.expand(None)

    def selectionChanged(self, selection, y):
        try:
            entry = selection.indexes()[0].model().itemFromIndex(selection.indexes()[0]).entry
        except IndexError:
            entry = None
        if self.last_selection != entry:
            self.last_selection = entry
            self.item_selected(entry)

    def setCurrentIndex(self, entry):
        item = self.getItemFromEntry(entry)
        if item is not None:
            super(QtWidgets.QTreeView, self).setCurrentIndex(item.index())

    def treeClicked(self, index):
        # upon selecting one of the tree elements
        data = index.model().itemFromIndex(index).entry
        return self.item_clicked(data)

    def treeActivated(self, index):
        # upon selecting one of the tree elements
        data = index.model().itemFromIndex(index).entry
        return self.item_activated(data)

    def eventFilter(self, object, event):
        """ event filter for tree view port to handle mouse over events and marker highlighting"""
        if event.type() == QtCore.QEvent.HoverMove:
            index = self.indexAt(event.pos())
            try:
                item = index.model().itemFromIndex(index)
                entry = item.entry
            except:
                item = None
                entry = None

            # check for new item
            if entry != self.last_hover:

                # deactivate last hover item
                if self.last_hover is not None:
                    self.item_hoverLeave(self.last_hover)

                # activate current hover item
                if entry is not None:
                    self.item_hoverEnter(entry)

                self.last_hover = entry
                return True

        return False

    def queryToExpandEntry(self, entry):
        if entry is None:
            return self.data_file.table_markertype.select()
        if isinstance(entry, self.data_file.table_markertype):
            if entry.mode == TYPE_Normal:
                return self.data_file.table_marker.select().where(self.data_file.table_marker.type == entry)\
                .join(self.data_file.table_image).order_by(self.data_file.table_image.sort_index)
            elif entry.mode == TYPE_Line:
                return self.data_file.table_line.select().where(self.data_file.table_line.type == entry)\
                .join(self.data_file.table_image).order_by(self.data_file.table_image.sort_index)
            elif entry.mode == TYPE_Rect:
                return self.data_file.table_rectangle.select().where(self.data_file.table_rectangle.type == entry)\
                .join(self.data_file.table_image).order_by(self.data_file.table_image.sort_index)
            elif entry.mode == TYPE_Track:
                return self.data_file.table_track.select().where(self.data_file.table_track.type == entry)
            elif entry.mode == TYPE_Ellipse:
                return self.data_file.table_ellipse.select().where(self.data_file.table_ellipse.type == entry)
            elif entry.mode == TYPE_Polygon:
                return self.data_file.table_polygon.select().where(self.data_file.table_polygon.type == entry)
        if isinstance(entry, self.data_file.table_track):
            return self.data_file.table_marker.select().where(self.data_file.table_marker.track == entry)\
                .join(self.data_file.table_image).order_by(self.data_file.table_image.sort_index)

    def getParentEntry(self, entry):
        if isinstance(entry, self.data_file.table_markertype):
            return None
        if isinstance(entry, self.data_file.table_marker):
            if entry.track:
                return entry.track
        return entry.type

    def getNameOfEntry(self, entry):
        if isinstance(entry, self.data_file.table_markertype):
            return entry.name
        if isinstance(entry, self.data_file.table_marker):
            return "Marker #%d (frame %d)" % (entry.id, entry.image.sort_index)
        if isinstance(entry, self.data_file.table_line):
            return "Line #%d (frame %d)" % (entry.id, entry.image.sort_index)
        if isinstance(entry, self.data_file.table_rectangle):
            return "Rectangle #%d (frame %d)" % (entry.id, entry.image.sort_index)
        if isinstance(entry, self.data_file.table_ellipse):
            return "Ellipse #%d (frame %d)" % (entry.id, entry.image.sort_index)
        if isinstance(entry, self.data_file.table_polygon):
            return "Polygon #%d (frame %d)" % (entry.id, entry.image.sort_index)
        if isinstance(entry, self.data_file.table_track):
            count = entry.track_markers.count()
            if count == 0:
                self.deleteEntry(entry)
                return None
            return "Track #%d (count %d)" % (entry.id, count)
        return "nix"

    def getIconOfEntry(self, entry):
        if isinstance(entry, self.data_file.table_markertype):
            if entry.mode == TYPE_Normal:
                return qta.icon("fa.crosshairs", color=QtGui.QColor(*HTMLColorToRGB(entry.color)))
            if entry.mode == TYPE_Line:
                return IconFromFile("Line.png", color=QtGui.QColor(*HTMLColorToRGB(entry.color)))
            if entry.mode == TYPE_Rect:
                return IconFromFile("Rectangle.png", color=QtGui.QColor(*HTMLColorToRGB(entry.color)))
            if entry.mode == TYPE_Track:
                return IconFromFile("Track.png", color=QtGui.QColor(*HTMLColorToRGB(entry.color)))
            if entry.mode == TYPE_Ellipse:
                return IconFromFile("Ellipse.png", color=QtGui.QColor(*HTMLColorToRGB(entry.color)))
            if entry.mode == TYPE_Polygon:
                return IconFromFile("Polygon.png", color=QtGui.QColor(*HTMLColorToRGB(entry.color)))
        return QtGui.QIcon()

    def getEntrySortRole(self, entry):
        if isinstance(entry, self.data_file.table_marker):
            return entry.image.sort_index
        return None

    def getKey(self, entry):
        return type(entry).__name__ + str(entry.id)

    def getItemFromEntry(self, entry):
        if entry is None:
            return None
        key = self.getKey(entry)
        try:
            return self.item_lookup[key]
        except KeyError:
            return None

    def setItemForEntry(self, entry, item):
        key = self.getKey(entry)
        self.item_lookup[key] = item

    def expand(self, entry, force_reload=True):
        query = self.queryToExpandEntry(entry)
        parent_item = self.getItemFromEntry(entry)

        if parent_item:
            if parent_item.expanded is False:
                # remove the dummy child
                parent_item.removeRow(0)
                parent_item.expanded = True
            # force_reload: delete all child entries and re query content from DB
            elif force_reload:
                # delete child entries
                parent_item.removeRows(0, parent_item.rowCount())
            else:
                return

        # add all marker types
        row = -1
        for row, entry in enumerate(query):
            self.addChild(parent_item, entry)

        if parent_item is None:
            # add entry for new type
            self.new_type = self.data_file.table_markertype()
            self.new_type.color = GetColorByIndex(self.data_file.table_markertype.select().count()-1)
            item_type = myTreeWidgetItem("add type")
            item_type.entry = self.new_type
            item_type.setIcon(qta.icon("fa.plus"))
            item_type.setEditable(False)
            self.model.setItem(row + 1, 0, item_type)
            self.setItemForEntry(self.new_type, item_type)
            #self.marker_type_modelitems[-1] = item_type


    def addChild(self, parent_item, entry, row=None):
        if parent_item is None:
            parent_item = self.model

        # add item
        item = myTreeWidgetItem(self.getNameOfEntry(entry))
        item.expanded = False
        item.entry = entry

        item.setIcon(self.getIconOfEntry(entry))
        item.setEditable(False)
        item.sort = self.getEntrySortRole(entry)

        if parent_item is None:
            if row is None:
                row = self.model.rowCount()
            self.model.insertRow(row)
            self.model.setItem(row, 0, item)
        else:
            if row is None:
                parent_item.appendRow(item)
            else:
                parent_item.insertRow(row, item)
        self.setItemForEntry(entry, item)

        # add dummy child
        if self.queryToExpandEntry(entry) is not None:
            child = QtGui.QStandardItem("loading")
            child.entry = None
            child.setEditable(False)
            child.setIcon(qta.icon("fa.hourglass-half"))
            item.appendRow(child)
            item.expanded = False
        return item

    def TreeExpand(self, index):
        # Get item and entry
        item = index.model().itemFromIndex(index)
        entry = item.entry
        thread = None

        # Expand
        if item.expanded is False:
            thread = Thread(target=self.expand, args=(entry,))

        # Start thread as daemonic
        if thread:
            thread.setDaemon(True)
            thread.start()

    def updateEntry(self, entry, update_children=False, insert_before=None, insert_after=None):
        # get the tree view item for the database entry
        item = self.getItemFromEntry(entry)
        # if we haven't one yet, we have to create it
        if item is None:
            # get the parent entry
            parent_entry = self.getParentEntry(entry)
            parent_item = None
            # if we have a parent and are not at the top level try to get the corresponding item
            if parent_entry:
                parent_item = self.getItemFromEntry(parent_entry)
                # parent item not in list or not expanded, than we don't need to update it because it is not shown
                if parent_item is None or parent_item.expanded is False:
                    if parent_item:
                        parent_item.setText(self.getNameOfEntry(parent_entry))
                    return

            # define the row where the new item should be
            row = None
            if insert_before:
                row = self.getItemFromEntry(insert_before).row()
            if insert_after:
                row = self.getItemFromEntry(insert_after).row() + 1

            # add the item as a child of its parent
            self.addChild(parent_item, entry, row)
            if parent_item:
                if row is None:
                    parent_item.sortChildren(0)
                if parent_entry:
                    parent_item.setText(self.getNameOfEntry(parent_entry))
        else:
            # check if we have to change the parent
            parent_entry = self.getParentEntry(entry)
            parent_item = self.getItemFromEntry(parent_entry)
            if parent_item != item.parent():
                # remove the item from the old position
                if item.parent() is None:
                    self.model.takeRow(item.row())
                else:
                    item.parent().takeRow(item.row())

                # determine a potential new position
                row = None
                if insert_before:
                    row = self.getItemFromEntry(insert_before).row()
                if insert_after:
                    row = self.getItemFromEntry(insert_after).row() + 1

                # move the item to the new position
                if parent_item is None:
                    if row is None:
                        row = self.model.rowCount()
                    self.model.insertRow(row)
                    self.model.setItem(row, 0, item)
                else:
                    if row is None:
                        parent_item.appendRow(item)
                    else:
                        parent_item.insertRow(row, item)

            # update the items name, icon and children
            item.setIcon(self.getIconOfEntry(entry))
            item.setText(self.getNameOfEntry(entry))
            if update_children:
                self.expand(entry, force_reload=True)

    def deleteEntry(self, entry):
        item = self.getItemFromEntry(entry)
        if item is None:
            return

        parent_item = item.parent()
        if parent_item:
            parent_entry = parent_item.entry

        key = self.getKey(entry)
        del self.item_lookup[key]

        if parent_item is None:
            self.model.removeRow(item.row())
        else:
            item.parent().removeRow(item.row())

        if parent_item:
            name = self.getNameOfEntry(parent_entry)
            if name is not None:
                parent_item.setText(name)


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

        # create tree view
        self.tree = MyTreeView(self, main_layout)

        # connect tree view callbacks
        self.tree.item_selected = self.setMarker
        self.tree.item_clicked = self.treeClicked
        self.tree.item_activated = self.treeClicked
        self.tree.item_hoverEnter = self.hoverEnter
        self.tree.item_hoverLeave = self.hoverLeave

        # add context menu
        self.tree.customContextMenuRequested.connect(self.openContextMenu)

        self.layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(self.layout)

        self.StackedWidget = QtWidgets.QStackedWidget(self)
        self.layout.addWidget(self.StackedWidget)

        """ Context Menue Actions """
        self.act_delete = QtWidgets.QAction(qta.icon("fa.trash"),self.tr("Delete"),self)
        self.act_delete.triggered.connect(self.removeMarker)

        self.act_delete_after = QtWidgets.QAction(qta.icon("fa.trash-o"),self.tr("Delete after this marker"),self)
        self.act_delete_after.triggered.connect(self.removeMarkersAfter)

        self.act_split = QtWidgets.QAction(qta.icon("fa.scissors"),self.tr("Split"),self)
        self.act_split.triggered.connect(self.splitTrack)

        self.act_merge = QtWidgets.QAction(qta.icon("fa.compress"),self.tr("Merge ..."),self)
        self.act_merge.triggered.connect(self.mergeTrack)

        self.act_changeType = QtWidgets.QAction(qta.icon("fa.arrow-right"),self.tr("Change Type ..."),self)
        self.act_changeType.triggered.connect(self.changeType)

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
                                          TYPE_Track: [self.markerWidget.x, self.markerWidget.y],
                                          TYPE_Ellipse: [self.markerWidget.x, self.markerWidget.y, self.markerWidget.width, self.markerWidget.height],
                                          TYPE_Polygon: [],
                                          }
        self.markerWidget.style = AddQLineEdit(layout, "Style:")
        self.markerWidget.text = AddQLineEdit(layout, "Text:")
        self.markerWidget.label = AddQLabel(layout)

        self.addValueChangedSignals(self.markerWidget)

        layout.addStretch()

        """ Type Properties """
        self.typeWidget = QtWidgets.QGroupBox()
        self.StackedWidget.addWidget(self.typeWidget)
        layout = QtWidgets.QVBoxLayout(self.typeWidget)
        self.typeWidget.name = AddQLineEdit(layout, "Name:")
        self.typeWidget.mode_indices = {TYPE_Normal: 0, TYPE_Line: 1, TYPE_Rect: 2, TYPE_Track: 3, TYPE_Ellipse: 4, TYPE_Polygon: 5}
        self.typeWidget.mode_values = {0: TYPE_Normal, 1: TYPE_Line, 2: TYPE_Rect, 3: TYPE_Track, 4: TYPE_Ellipse, 5: TYPE_Polygon}
        self.typeWidget.mode = AddQComboBox(layout, "Mode:", ["TYPE_Normal", "TYPE_Line", "TYPE_Rect", "TYPE_Track", "TYPE_Ellipse", "TYPE_Polygon"])
        self.typeWidget.style = AddQLineEdit(layout, "Style:")
        self.typeWidget.color = AddQColorChoose(layout, "Color:")
        self.typeWidget.text = AddQLineEdit(layout, "Text:")
        self.typeWidget.hidden = AddQCheckBox(layout, "Hidden:")

        self.addValueChangedSignals(self.typeWidget)

        layout.addStretch()

        """ Track Properties """
        self.trackWidget = QtWidgets.QGroupBox()
        self.StackedWidget.addWidget(self.trackWidget)
        layout = QtWidgets.QVBoxLayout(self.trackWidget)
        self.trackWidget.style = AddQLineEdit(layout, "Style:")
        self.trackWidget.text = AddQLineEdit(layout, "Text:")
        self.trackWidget.hidden = AddQCheckBox(layout, "Hidden:")

        self.addValueChangedSignals(self.trackWidget)

        layout.addStretch()

        """ empty """
        self.emptyWidget = QtWidgets.QGroupBox()
        self.StackedWidget.addWidget(self.emptyWidget)

        """ Control Buttons """
        horizontal_layout = QtWidgets.QHBoxLayout()
        self.layout.addLayout(horizontal_layout)
        self.pushbutton_Ok = QtWidgets.QPushButton('&Ok', self)
        def ok():
            self.saveMarker()
            self.close()
        self.pushbutton_Ok.pressed.connect(ok)
        horizontal_layout.addWidget(self.pushbutton_Ok)

        self.pushbutton_Exit = QtWidgets.QPushButton('&Cancel', self)
        self.pushbutton_Exit.pressed.connect(self.close)
        horizontal_layout.addWidget(self.pushbutton_Exit)

        self.pushbutton_Confirm = QtWidgets.QPushButton('&Apply', self)
        self.pushbutton_Confirm.pressed.connect(self.saveMarker)
        horizontal_layout.addWidget(self.pushbutton_Confirm)

        #self.pushbutton_Remove = QtWidgets.QPushButton('R&emove', self)
        #self.pushbutton_Remove.pressed.connect(self.removeMarker)
        #horizontal_layout.addWidget(self.pushbutton_Remove)

    def addValueChangedSignals(self, parent):
        for key in dir(parent):
            obj = getattr(parent, key)
            if isinstance(obj, QtWidgets.QWidget):
                for signal in ["valueChanged", "currentIndexChanged", "textChanged", "stateChanged"]:
                    try:
                        getattr(obj, signal).connect(self.valueChanged)
                        break
                    except AttributeError:
                        continue

    def valueChanged(self):
        self.pushbutton_Confirm.setDisabled(False)

    def hoverLeave(self, entry):
        if type(entry) in [self.data_file.table_marker, self.data_file.table_line,
                                                self.data_file.table_rectangle, self.data_file.table_track, self.data_file.table_ellipse, self.data_file.table_polygon]:
            if isinstance(entry, self.data_file.table_marker) and entry.track_id:
                track_item = self.marker_handler.GetMarkerItem(entry.track)
                if track_item:
                    track_item.hoverTrackMarkerLeave(entry)
            marker_item = self.marker_handler.GetMarkerItem(entry)
            # TODO how to handle markers in tracks?
            try:
                marker_item.hoverLeave()
            except:
                pass

    def hoverEnter(self, entry):
        if type(entry) in [self.data_file.table_marker, self.data_file.table_line, self.data_file.table_rectangle,
                                self.data_file.table_track, self.data_file.table_ellipse, self.data_file.table_polygon]:
            if isinstance(entry, self.data_file.table_marker) and entry.track_id:
                track_item = self.marker_handler.GetMarkerItem(entry.track)
                if track_item:
                    track_item.hoverTrackMarkerEnter(entry)
            marker_item = self.marker_handler.GetMarkerItem(entry)
            # TODO how to handle markers in tracks?
            try:
                marker_item.hoverEnter()
            except:
                pass

    def openContextMenu(self, position):
        # retrieve selected item and hierarchie level
        indexes = self.tree.selectedIndexes()
        if len(indexes) > 0:
            level = 0
            index = indexes[0]
            while index.parent().isValid():
                index = index.parent()
                level += 1

        index = indexes[0]  # to get the item
        item = index.model().itemFromIndex(index)  # contains the query object as entry
        entry = item.entry  # query object of various db table types
        if level > 0:
            parent = item.parent().entry
        else:
            parent = None

        self.index = index
        self.parent = parent

        """ DEBUG"""
        # print("item", item)
        # print("entry", entry)
        # print("level", level)
        # print("parent",parent)

        # context menu
        menu = QtWidgets.QMenu()
        if entry is not self.tree.new_type:
            menu.addAction(self.act_delete)

        if not type(entry) == self.data_file.table_markertype:
            menu.addAction(self.act_changeType)

        # add remove after action ONLY for track points
        if type(entry) == self.data_file.table_marker and type(parent) == self.data_file.table_track:
            menu.addAction(self.act_delete_after)
            menu.addAction(self.act_split)
            menu.addAction(self.act_merge)
            # remove default action for track markers
            menu.removeAction(self.act_changeType)

        if type(entry) == self.data_file.table_track:
            menu.addAction(self.act_merge)

        # open menu at mouse click position
        if menu:
            menu.exec_(self.tree.viewport().mapToGlobal(position))

    def treeClicked(self, data):
        # upon selecting one of the tree elements
        if (type(data)in [self.data_file.table_marker, self.data_file.table_line, self.data_file.table_rectangle, self.data_file.table_ellipse, self.data_file.table_polygon]) and self.data == data:
            # got to the frame of the selected object
            self.marker_handler.window.JumpToFrame(self.data.image.sort_index)
        if (type(data)in [self.data_file.table_marker]) and self.data == data:
            # center view on marker
            self.marker_handler.window.CenterOn(self.data.x, self.data.y)
        if (type(data)in [self.data_file.table_track]) and self.data == data:
            # center view on first track marker
            self.marker_handler.window.JumpToFrame(self.data.markers[0].image.sort_index)
            self.marker_handler.window.CenterOn(self.data.markers[0].x, self.data.markers[0].y)

    def setMarkerData(self, data):
        # None should select the "new type" button
        if data is None:
            data = self.tree.new_type
        # try to select the item, will automatically call self.setMarker
        self.tree.setCurrentIndex(data)
        # if the data hasn't been selected at least display it in the right menu part
        if self.data != data:
            self.setMarker(data)

    def setMarker(self, data):
        self.data = data

        #self.pushbutton_Remove.setHidden(False)

        if type(data) == self.data_file.table_marker or type(data) == self.data_file.table_line or type(data) == self.data_file.table_rectangle\
                or type(data) == self.data_file.table_ellipse or type(data) == self.data_file.table_polygon:
            self.StackedWidget.setCurrentIndex(0)
            for widget in self.markerWidget.special_widgets:
                widget.setHidden(True)
            marker_type = data.type if data.type is not None else data.track.type
            for widget in self.markerWidget.widget_types[marker_type.mode]:
                widget.setHidden(False)
            self.markerWidget.setTitle("Marker #%d" % data.id)

            text = ''

            if marker_type.mode & TYPE_Line:
                self.markerWidget.x1.setValue(data.x1)
                self.markerWidget.y1.setValue(data.y1)
                self.markerWidget.x2.setValue(data.x2)
                self.markerWidget.y2.setValue(data.y2)
            elif marker_type.mode & TYPE_Polygon:
                pass
            elif marker_type.mode & TYPE_Rect or marker_type.mode & TYPE_Ellipse:
                self.markerWidget.x.setValue(data.x)
                self.markerWidget.y.setValue(data.y)
                self.markerWidget.width.setValue(data.width)
                self.markerWidget.height.setValue(data.height)
            else:
                text += ''
                self.markerWidget.x.setValue(data.x)
                self.markerWidget.y.setValue(data.y)

            #if marker_type.mode & TYPE_Track and data.track_id:
            #    self.markerWidget.type.setHidden(True)

            self.markerWidget.label.setText(text)

            self.markerWidget.type.setCurrentIndex(self.markerWidget.type_indices[marker_type.id])
            self.markerWidget.style.setText(data.style if data.style else "")
            self.markerWidget.text.setText(data.text if data.text else "")

        elif type(data) == self.data_file.table_track:
            self.StackedWidget.setCurrentIndex(2)
            self.trackWidget.setTitle("Track #%d" % data.id)
            self.trackWidget.style.setText(data.style if data.style else "")
            self.trackWidget.text.setText(data.text if data.text else "")
            self.trackWidget.hidden.setChecked(data.hidden)

        elif type(data) == self.data_file.table_markertype:
            if data is None:
                data = self.tree.new_type
                self.data = data
            if self.data.id is not None:
                self.marker_handler.SetActiveMarkerType(new_type=self.data)
            self.StackedWidget.setCurrentIndex(1)
            if data.name is None:
                #self.pushbutton_Remove.setHidden(True)
                self.typeWidget.setTitle("add type")
            else:
                self.typeWidget.setTitle("Type #%s" % data.name)
            self.typeWidget.name.setText(data.name)
            try:
                index = self.typeWidget.mode_indices[data.mode]
                self.typeWidget.mode.setCurrentIndex(index)
            except KeyError:
                pass
            self.typeWidget.style.setText(data.style if data.style else "")
            self.typeWidget.color.setColor(data.color)
            self.typeWidget.text.setText(data.text if data.text else "")
            self.typeWidget.hidden.setChecked(data.hidden)
        else:
            self.StackedWidget.setCurrentIndex(3)
        self.pushbutton_Confirm.setDisabled(True)

    def filterText(self, input):
        # if text field is empty - add Null instead of "" to sql db
        if not input:
            return None
        return input

    def saveMarker(self):
        print("Saving changes...")
        # set parameters
        if type(self.data) == self.data_file.table_marker or type(self.data) == self.data_file.table_line or \
            type(self.data) == self.data_file.table_rectangle or type(self.data) == self.data_file.table_ellipse or \
            type(self.data) == self.data_file.table_polygon:
            marker_type = self.data.type if self.data.type else self.data.track.type
            if marker_type.mode & TYPE_Line:
                self.data.x1 = self.markerWidget.x1.value()
                self.data.y1 = self.markerWidget.y1.value()
                self.data.x2 = self.markerWidget.x2.value()
                self.data.y2 = self.markerWidget.y2.value()
            elif marker_type.mode & TYPE_Rect:
                self.data.x = self.markerWidget.x.value()
                self.data.y = self.markerWidget.y.value()
                self.data.width = self.markerWidget.width.value()
                self.data.height = self.markerWidget.height.value()
            else:
                self.data.x = self.markerWidget.x.value()
                self.data.y = self.markerWidget.y.value()
            self.data.type = self.marker_handler.marker_file.get_type(self.markerWidget.type.currentText())
            self.data.style = self.markerWidget.style.text().strip()
            self.data.text = self.filterText(self.markerWidget.text.text())
            self.data.save()

            # load updated data
            if marker_type.mode & TYPE_Track:
                track_item = self.marker_handler.GetMarkerItem(self.data.track)
                track_item.update(self.data.image.sort_index, self.data)
            else:
                marker_item = self.marker_handler.GetMarkerItem(self.data)
                if marker_item:
                    marker_item.ReloadData()
        elif type(self.data) == self.data_file.table_track:
            self.data.style = self.trackWidget.style.text().strip()
            self.data.text = self.filterText(self.trackWidget.text.text())
            self.data.hidden = self.trackWidget.hidden.isChecked()
            self.data.save()

            self.marker_handler.ReloadTrack(self.data)
        elif type(self.data) == self.data_file.table_markertype:
            new_type = self.data.id is None
            if new_type:
                self.tree.new_type.color = GetColorByIndex(self.data_file.table_markertype.select().count())
                self.data = self.data_file.table_markertype()
            self.data.name = self.typeWidget.name.text()
            new_mode = self.typeWidget.mode_values[self.typeWidget.mode.currentIndex()]
            if new_mode != self.data.mode:
                if not new_type:
                    count = self.data.markers.count() + self.data.lines.count() + self.data.rectangles.count() + self.data.ellipses.count() + self.data.polygons.count()
                    if count:
                        reply = QtWidgets.QMessageBox.question(self, 'Warning',
                                                               'Changing the mode of this markertype will delete all %d previous markers of this type.\nDo you want to proceed?' % count,
                                                               QtWidgets.QMessageBox.Yes,
                                                               QtWidgets.QMessageBox.No)
                        if reply == QtWidgets.QMessageBox.No:
                            return
                        self.marker_handler.save()
                        if self.data.mode == TYPE_Normal:
                            self.data_file.table_marker.delete().where(self.data_file.table_marker.type == self.data).execute()
                            self.marker_handler.LoadPoints()
                        elif self.data.mode & TYPE_Line:
                            self.data_file.table_line.delete().where(self.data_file.table_line.type == self.data).execute()
                            self.marker_handler.LoadLines()
                        elif self.data.mode & TYPE_Rect:
                            self.data_file.table_rectangle.delete().where(self.data_file.table_rectangle.type == self.data).execute()
                            self.marker_handler.LoadRectangles()
                        elif self.data.mode & TYPE_Track:
                            self.data_file.table_track.delete().where(self.data_file.table_track.type == self.data).execute()
                            self.marker_handler.LoadTracks()
                        elif self.data.mode & TYPE_Ellipse:
                            self.data_file.table_ellipse.delete().where(self.data_file.table_ellipse.type == self.data).execute()
                            self.marker_handler.LoadEllipses()
                        elif self.data.mode & TYPE_Polygon:
                            self.data_file.table_polygon.delete().where(self.data_file.table_polygon.type == self.data).execute()
                            self.marker_handler.LoadPolygons()
                        self.tree.updateEntry(self.data, update_children=True)
                self.data.mode = new_mode
            self.data.style = self.typeWidget.style.text()
            self.data.color = self.typeWidget.color.getColor()
            self.data.text = self.filterText(self.typeWidget.text.text())
            self.data.hidden = self.typeWidget.hidden.isChecked()
            try:
                self.data.save()
            except peewee.IntegrityError as err:
                if str(err) == "UNIQUE constraint failed: markertype.name":
                    QtWidgets.QMessageBox.critical(self, 'Error - ClickPoints',
                                                           'There already exists a markertype with name %s' % self.data.name,
                                                           QtWidgets.QMessageBox.Ok)
                    return
                else:
                    raise err
            if new_type:
                self.marker_handler.addCounter(self.data)
            else:
                self.marker_handler.GetCounter(self.data).Update(self.data)
            self.marker_handler.save()
            if self.data.mode & TYPE_Track:
                self.marker_handler.ReloadTrackType(self.data)
            elif self.data.mode & TYPE_Line:
                self.marker_handler.LoadLines()
            elif self.data.mode & TYPE_Rect:
                self.marker_handler.LoadRectangles()
            elif self.data.mode & TYPE_Ellipse:
                self.marker_handler.LoadEllipses()
            elif self.data.mode & TYPE_Polygon:
                self.marker_handler.LoadPolygons()
            else:
                self.marker_handler.LoadPoints()
            if self.marker_handler.active_type is not None and self.marker_handler.active_type.id == self.data.id:
                self.marker_handler.active_type = self.data

            self.tree.updateEntry(self.data, insert_before=self.tree.new_type)
            self.tree.setCurrentIndex(self.data)

            # update the drop-down menus for the types
            self.markerWidget.type_indices = {t.id: index for index, t in enumerate(self.data_file.get_type_list())}
            self.markerWidget.type.setValues([t.name for t in self.data_file.get_type_list()])

        self.data_file.data_file.setChangesMade()

    def changeType(self):
        print("Change Type ...")

        # ie for marker, track, line, rect
        own_type = self.data.type

        # check for own type and select matching types
        q_types = self.data_file.table_markertype.select().where(self.data_file.table_markertype.mode == own_type.mode)
        all_types = ["%s" % t.name for t in q_types]

        # remove own type from list
        all_types.remove("%s" % own_type.name)

        old_type = own_type

        type_target, ok = QtWidgets.QInputDialog.getItem(self, "Select new Type:", "", all_types, 1, True)

        if ok:
            type_target = self.data_file.table_markertype.get(name=type_target)
            print("type:", type(self.data))
            self.data.changeType(type_target)

            # refresh display
            try:
                if not type(self.data) in [self.data_file.table_track]:
                    self.marker_handler.ReloadMarker(self.data.image.sort_index)
                else:
                    self.marker_handler.ReloadTrack(self.data)
            finally:
                self.tree.updateEntry(self.data)

    def mergeTrack(self):
        print("Merge ...")

        if type(self.data) in [self.data_file.table_marker, self.data_file.table_track]:
            if type(self.data) == self.data_file.table_marker:
                own_track_id = self.data.track.id
                track = self.data.track
            elif type(self.data) == self.data_file.table_track:
                own_track_id = self.data.id
                track = self.data

            q_tracks = self.data_file.table_track.select()
            all_tracks = ["%d" % t.id for t in q_tracks]
            all_tracks.remove("%d" % own_track_id)

            merge_target, ok = QtWidgets.QInputDialog.getItem(self, "Merge with TrackID:", "", all_tracks, 1, True)
            if merge_target:
                try:
                    merge_target = np.uint(merge_target)
                    merge_target = self.data_file.table_track.get(id=merge_target)
                except peewee.DoesNotExist as err:
                    QtWidgets.QMessageBox.critical(self, 'Error - ClickPoints', "Track #%d does not exist." % merge_target, QtWidgets.QMessageBox.Ok)
                    return

            if ok:
                try:
                    track.merge(merge_target)
                except ValueError as err:
                    QtWidgets.QMessageBox.critical(self, 'Error - ClickPoints', str(err), QtWidgets.QMessageBox.Ok)
                    return

                # refresh display
                try:
                    self.marker_handler.ReloadTrack(track)
                finally:
                    # refresh marker editor display
                    self.tree.deleteEntry(merge_target)
                    self.tree.updateEntry(track, update_children=True)

    def splitTrack(self):
        print("Split ...")

        if type(self.data) == self.data_file.table_marker:

            first_track = self.data.track

            # remove points from Track in DB
            second_track = first_track.split(self.data)

            # refresh display
            try:
                self.marker_handler.ReloadTrack(first_track)
            finally:
                # refresh marker editor display
                self.tree.updateEntry(first_track, update_children=True)
                self.tree.updateEntry(second_track, insert_after=first_track)
                self.tree.setCurrentIndex(second_track)


    def removeMarkersAfter(self):
        """ remove markers from track that appear after this marker """
        print("Remove after ...")

        if type(self.data) == self.data_file.table_marker:

            track = self.data.track

            # remove points from Track in DB
            track.removeAfter(self.data)

            # refresh display
            try:
                self.marker_handler.ReloadTrack(self.data.track)
            finally:
                self.tree.updateEntry(track, update_children=True)

    def removeMarker(self):
        reply = QtWidgets.QMessageBox.question(self, 'Delete %s - ClickPoints' % type(self.data).__name__,
                                              'Do you really want to delete %s #%d?' % (type(self.data).__name__, self.data.id),
                                              QtWidgets.QMessageBox.Yes,
                                              QtWidgets.QMessageBox.No)

        if reply != QtWidgets.QMessageBox.Yes:
            return
        print("Remove ...")
        data = self.data
        # currently selected a marker -> remove the marker
        if type(data) == self.data_file.table_marker or type(data) == self.data_file.table_line or type(data) == self.data_file.table_rectangle or \
                type(data) == self.data_file.table_ellipse or type(data) == self.data_file.table_polygon:
            marker_type = data.type
            if marker_type is None:
                marker_type = data.track.type

            if not (marker_type.mode & TYPE_Track):
                # find point
                marker_item = self.marker_handler.GetMarkerItem(data)
                # delete marker
                if marker_item:
                    marker_item.delete()
                else:
                    data.delete_instance()
                self.tree.deleteEntry(data)
            else:

                # find corresponding track and remove the point
                track_item = self.marker_handler.GetMarkerItem(data.track)
                # if we have a track display item, tell it to remove a point (removes the point from the database, too)
                if track_item:
                    if track_item.removeTrackPoint(data.image.sort_index):
                        self.tree.deleteEntry(data.track)
                # if not, we have to delete it from the database
                else:
                    data.delete_instance()
                self.tree.deleteEntry(data)

        # currently selected a track -> remove the track
        elif type(data) == self.data_file.table_track:
            # get the track and remove it
            track = self.marker_handler.GetMarkerItem(data)
            if track:
                track.delete()
            data.delete_instance()
            # and then delete the tree view item
            self.tree.deleteEntry(data)

        # currently selected a type -> remove the type
        elif type(data) == self.data_file.table_markertype:
            count = data.markers.count()+data.lines.count()+data.rectangles.count()+data.ellipses.count()+data.polygons.count()
            # if this type doesn't have markers delete it without asking
            if count == 0:
                data.delete_instance()
            else:
                # Ask the user if he wants to delete all markers from this type or assign them to a different type
                self.window = DeleteType(data, count,
                                         [marker_type for marker_type in self.data_file.get_type_list() if
                                          marker_type != data])
                value = self.window.exec_()
                if value == 0:  # canceled
                    return
                self.marker_handler.save()
                if value == -1:  # delete all of them
                    # delete all markers from this type
                    self.data_file.table_marker.delete().where(self.data_file.table_marker.type == data.id).execute()
                    self.data_file.table_line.delete().where(self.data_file.table_line.type == data.id).execute()
                    self.data_file.table_rectangle.delete().where(self.data_file.table_rectangle.type == data.id).execute()
                    self.data_file.table_ellipse.delete().where(self.data_file.table_ellipse.type == data.id).execute()
                    self.data_file.table_polygon.delete().where(self.data_file.table_polygon.type == data.id).execute()
                    self.data_file.table_track.delete().where(self.data_file.table_track.type == data.id).execute()
                else:
                    # change the type of all markers which belonged to this type
                    self.data_file.table_marker.update(type=value).where(self.data_file.table_marker.type == data.id).execute()
                    self.data_file.table_line.update(type=value).where(self.data_file.table_line.type == data.id).execute()
                    self.data_file.table_rectangle.update(type=value).where(self.data_file.table_rectangle.type == data.id).execute()
                    self.data_file.table_ellipse.update(type=value).where(self.data_file.table_ellipse.type == data.id).execute()
                    self.data_file.table_polygon.update(type=value).where(self.data_file.table_polygon.type == data.id).execute()
                    self.data_file.table_track.update(type=value).where(self.data_file.table_track.type == data.id).execute()
                    new_entry = self.data_file.table_markertype.get(id=value)
                    self.tree.updateEntry(new_entry, update_children=True)
                # delete type
                if self.marker_handler.active_type is not None and self.marker_handler.active_type.id == data.id:
                    self.marker_handler.active_type = None
                data.delete_instance()
                # reload marker
                if data.mode == TYPE_Normal:
                    self.marker_handler.LoadPoints()
                elif data.mode & TYPE_Line:
                    self.marker_handler.LoadLines()
                elif data.mode & TYPE_Rect:
                    self.marker_handler.LoadRectangles()
                elif data.mode & TYPE_Track:
                    self.marker_handler.DeleteTrackType(data)
                elif data.mode & TYPE_Ellipse:
                    self.marker_handler.LoadEllipses()
                elif data.mode & TYPE_Polygon:
                    self.marker_handler.LoadPolygons()

            # update the counters
            self.marker_handler.removeCounter(data)

            # delete item from list
            # TODO
            #self.new_type.color = GetColorByIndex(len(self.marker_type_modelitems)-1)

            # and then delete the tree view item
            self.tree.deleteEntry(self.data)

            # update the drop-down menus for the types
            self.markerWidget.type_indices = {t.id: index for index, t in enumerate(self.data_file.get_type_list())}
            self.markerWidget.type.setValues([t.name for t in self.data_file.get_type_list()])

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.marker_handler.marker_edit_window = None
            self.close()
        if event.key() == QtCore.Qt.Key_Return:
            self.saveMarker()
        if event.key() == QtCore.Qt.Key_Delete:
            self.removeMarker()

def AnimationChangeScale(target, start=0, end=1, duration=200, fps=36, endcall=None):
    timer = QtCore.QTimer()
    timer.animation_counter = 0
    duration /= 1e3
    def timerEvent():
        timer.animation_time += 1./(fps*duration)
        timer.animation_counter += 1
        if timer.animation_time >= 1:
            target.setScale(animation_scale=end)
            timer.stop()
            if endcall:
                endcall()
            return
        x = timer.animation_time
        k = 3
        y = 0.5 * (x * 2) ** k * (x < 0.5) + (1 - 0.5 * ((1 - x) * 2) ** k) * (x >= 0.5)
        target.setScale(animation_scale=y*(end-start)+start)
    timer.timeout.connect(timerEvent)
    timer.animation_time = 0
    target.setScale(animation_scale=start)
    target.animation_timer = timer
    timer.start(1e3/fps)


class MyGrabberItem(QtWidgets.QGraphicsPathItem):
    scale_value = 1
    scale_animation = 1
    scale_hover = 1
    use_crosshair = False
    grabbed = True
    outline = False

    def __init__(self, parent, color, x, y, shape="rect", use_crosshair=False):
        # init and store parent
        QtWidgets.QGraphicsPathItem.__init__(self, parent)
        self.use_crosshair = use_crosshair
        self.parent = parent

        # set path
        self.color = color
        #self.setPath(paths[shape])
        self.setShape(shape)

        # accept hover events and set position
        self.setAcceptHoverEvents(True)
        self.setPos(x, y)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations)

        if parent.is_new:
            AnimationChangeScale(self)

    def setShape(self, shape):
        if shape.endswith("-o"):
            self.outline = True
            self.setBrush(QtGui.QBrush(0))
            self.setPath(paths[shape[:-2]])
        else:
            self.outline = False
            self.setPen(QtGui.QPen(0))
            self.setPath(paths[shape])
        self.setColor(self.color)

    def setColor(self, color):
        self.color = color
        if not self.outline:
            self.setBrush(QtGui.QBrush(color))
        else:
            self.setBrush(QtGui.QBrush(0))
            self.setPen(QtGui.QPen(color))
            pen = self.pen()
            pen.setColor(color)
            pen.setCosmetic(True)
            self.setPen(pen)

    def shape(self):
        if self.outline:
            return QtWidgets.QGraphicsPathItem.shape(self)
        path = QtGui.QPainterPath()
        path.addEllipse(self.boundingRect())
        return path

    def hoverEnterEvent(self, event):
        # a bit bigger during hover
        self.setScale(hover_scale=1.2)
        self.parentItem().graberHoverEnter(self, event)

    def hoverLeaveEvent(self, event):
        # switch back to normal size
        self.setScale(hover_scale=1)
        self.parentItem().graberHoverLeave(self, event)

    def mousePressEvent(self, event):
        self.grabbed = False
        # store start position of move
        if event.button() == QtCore.Qt.LeftButton:
            # left click + control -> remove
            if self.parent.marker_handler.tool_index == 1 or event.modifiers() == QtCore.Qt.ControlModifier:
                self.parentItem().graberDelete(self)
            elif self.parent.marker_handler.tool_index == 2:
                self.parentItem().changeTypeEvent()
            # normal left click -> move
            else:
                if self.use_crosshair:
                    # display crosshair
                    self.setCursor(QtGui.QCursor(QtCore.Qt.BlankCursor))
                    self.parentItem().marker_handler.Crosshair.Show(self)
                    self.parentItem().marker_handler.Crosshair.MoveCrosshair(self.pos().x(), self.pos().y())
                self.grabbed = True
                self.mouseMoveEvent(event)
        if event.button() == QtCore.Qt.RightButton:
            # right button -> open menu
            self.parentItem().rightClick(self)

    def mouseMoveEvent(self, event):
        if self.grabbed:
            # move crosshair
            if self.use_crosshair:
                self.parentItem().marker_handler.Crosshair.MoveCrosshair(self.pos().x(), self.pos().y())
            # notify parent
            pos = self.parentItem().mapFromScene(event.scenePos())
            self.parentItem().graberMoved(self, pos, event)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.grabbed = False
            # hide crosshair
            if self.use_crosshair:
                self.setCursor(QtGui.QCursor(QtCore.Qt.OpenHandCursor))
                self.parentItem().marker_handler.Crosshair.Hide()
            self.parentItem().graberReleased(self, event)

    def setScale(self, scale=None, animation_scale=None, hover_scale=None):
        # store scale
        if scale is not None:
            self.scale_value = scale
        if animation_scale is not None:
            self.scale_animation = animation_scale
        if hover_scale is not None:
            self.scale_hover = hover_scale
        # adjust scale
        if self.outline:
            super(QtWidgets.QGraphicsPathItem, self).setScale(self.scale_value)
            pen = self.pen()
            pen.setWidthF(5*self.scale_animation*self.scale_hover)
            self.setPen(pen)
        else:
            super(QtWidgets.QGraphicsPathItem, self).setScale(self.scale_value*self.scale_animation*self.scale_hover)

    def delete(self):
        self.setAcceptedMouseButtons(Qt.MouseButtons(0))
        self.setAcceptHoverEvents(False)
        self.setParentItem(self.parentItem().parentItem())
        AnimationChangeScale(self, start=1, end=0, endcall=lambda: self.scene().removeItem(self))


class MyNonGrabberItem(QtWidgets.QGraphicsPathItem):
    scale_value = 1
    scale_animation = 1
    scale_hover = 1

    def __init__(self, parent, color, x, y, shape="rect", scale=1):
        # init and store parent
        QtWidgets.QGraphicsPathItem.__init__(self, parent)

        # set path
        self.setPath(paths[shape])

        # set brush and pen
        self.setBrush(QtGui.QBrush(color))
        self.setPen(QtGui.QPen(0))

        # accept hover events and set position
        self.setPos(x, y)
        self.setScale(scale)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations)

        if parent.is_new:
            AnimationChangeScale(self)

    def setShape(self, shape):
        self.setPath(paths[shape])

    def hoverEnterEventCustom(self, event):
        # a bit bigger during hover
        self.setScale(hover_scale=1.2)
        #self.parentItem().graberHoverEnter(self, event)

    def hoverLeaveEventCustom(self, event):
        # switch back to normal size
        self.setScale(hover_scale=1)
        #self.parentItem().graberHoverLeave(self, event)

    def setScale(self, scale=None, animation_scale=None, hover_scale=None):
        # store scale
        if scale is not None:
            self.scale_value = scale
        if animation_scale is not None:
            self.scale_animation = animation_scale
        if hover_scale is not None:
            self.scale_hover = hover_scale
        # adjust scale
        super(QtWidgets.QGraphicsPathItem, self).setScale(self.scale_value*self.scale_animation*self.scale_hover)

    def delete(self, just_remove=False):
        if just_remove:
            self.scene().removeItem(self)
        else:
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
            BroadCastEvent(self.marker_handler.modules, "markerAddEvent", self.data)
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
            if grabber is None or grabber == self:
                break
            grabber.setShape(self.style.get("shape", self.default_shape))
            grabber.setColor(self.color)
            if self.style.get("transform", "screen") == "screen":
                grabber.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations, True)
                grabber.setScale(self.style.get("scale", 1))
            else:
                grabber.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations, False)
                grabber.setScale(self.style.get("scale", 1)*0.1)
            i += 1

    # update text with priorities: marker, track, label
    def GetText(self):
        # check for track marker text entry (only applicable for tracks)
        if isinstance(self.data, self.marker_handler.data_file.table_track) and \
                        self.marker is not None and self.marker.data["text"] is not None:
            return self.marker.data["text"]

        # check for self text entry (this should be a single marker or the track)
        if self.data.text is not None:
            return self.data.text

        # check for type text entry
        if self.data.type and self.data.type.text is not None:
            return self.data.type.text

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
            id = None
            data = self.data if type(self.data) is not self.marker_handler.data_file.table_track else self.marker.data if self.marker else None
            if data:
                try:
                    id = data.id
                except AttributeError:
                    id = data["id"]
            if id:
                text = text.replace('$marker_id', '%d' % id)
            else:
                text = text.replace('$marker_id', '??')
        if '$x' in text:
            if type(self.data) is self.marker_handler.data_file.table_line:
                text = text.replace('$x', '%.2f' % self.data.x1)
            else:
                try:
                    text = text.replace('$x', '%.2f' % self.data.x)
                except TypeError:
                    text = text.replace('$x', '%.2f' % self.marker.x)
        if '$y' in text:
            if type(self.data) is self.marker_handler.data_file.table_line:
                text = text.replace('$y', '%.2f' % self.data.y1)
            else:
                try:
                    text = text.replace('$y', '%.2f' % self.data.y)
                except TypeError:
                    text = text.replace('$y', '%.2f' % self.marker.y)
        if '$length' in text:
            if type(self.data) is self.marker_handler.data_file.table_line:
                if self.data.length() is not None:
                    text = text.replace('$length', '%.2f' % self.data.length())
                else:
                    text = text.replace('$length', '')
            else:
                text = text.replace('$length', '??')
        if '$area' in text:
            if type(self.data) is self.marker_handler.data_file.table_rectangle or\
                    type(self.data) is self.marker_handler.data_file.table_ellipse or \
                    type(self.data) is self.marker_handler.data_file.table_polygon:
                try:
                    area = self.data.area()
                except TypeError:
                    area = self.data.area
                if area is not None:
                    text = text.replace('$area', '%.2f' % area)
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

    def draw(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        pass

    def draw2(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        pass

    def drawMarker(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        marker_scale = scale * self.style.get("scale", 1)
        marker_shape = self.style.get("shape", "cross")
        x, y = self.g1.pos().x() - start_x, self.g1.pos().y() - start_y
        x *= image_scale
        y *= image_scale
        drawMarker(image, np.array([x, y]), self.color, marker_scale*10, marker_shape)

    def drawMarkerSvg(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        marker_scale = scale * self.style.get("scale", 1)
        marker_shape = self.style.get("shape", "cross")
        x, y = self.g1.pos().x() - start_x, self.g1.pos().y() - start_y
        x *= image_scale
        y *= image_scale
        marker = getMarker(image, self.color, marker_scale*10, marker_shape)
        print(marker_shape, marker)
        line = image.add(image.polyline([(x, y)]))
        line['marker-end'] = marker.get_funciri()

    def drawText(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        # only if there is a text
        if self.text is None:
            return
        x, y = self.text_parent.parentItem().pos().x() - start_x, self.text_parent.parentItem().pos().y() - start_y
        x *= image_scale
        y *= image_scale
        # transform coordinates, because we are printing on the rotated image
        if rotation == 90:
            x, y = (image.pil_image.size[0]-y, x)
        if rotation == 180:
            x, y = (image.pil_image.size[0] - x, image.pil_image.size[1]-y)
        if rotation == 270:
            x, y = (y, image.pil_image.size[1]-x)
        # draw the text
        from PIL import ImageFont
        try:
            font = ImageFont.truetype("arial.ttf", int(12*scale))
        except IOError:
            font = ImageFont.truetype(os.path.join(os.environ["CLICKPOINTS_ICON"], "FantasqueSansMono-Regular.ttf"), int(12*scale))
        text = self.text.text()
        #alignment = image.textsize(text, font=font)
        offsetx, offsety = (6*scale, 6*scale)
        image.text((x+offsetx, y+offsety), text, colorToTuple(self.color), font=font)

    def drawTextSvg(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        # only if there is a text
        if self.text is None:
            return
        x, y = self.text_parent.parentItem().pos().x() - start_x, self.text_parent.parentItem().pos().y() - start_y
        x *= image_scale
        y *= image_scale
        # transform coordinates, because we are printing on the rotated image
        if rotation == 90:
            x, y = (image.pil_image.size[0]-y, x)
        if rotation == 180:
            x, y = (image.pil_image.size[0] - x, image.pil_image.size[1]-y)
        if rotation == 270:
            x, y = (y, image.pil_image.size[1]-x)
        # draw the text
        text = self.text.text()
        #alignment = image.textsize(text, font=font)
        offsetx, offsety = (6*scale, 3*6*scale)
        image.add(image.text(text, insert=(x+offsetx, y+offsety), fill=self.color.name()))

    def graberDelete(self, grabber):
        self.delete()

    def changeTypeEvent(self):
        if self.marker_handler.active_type.mode == self.data.type.mode:
            self.changeType(self.marker_handler.active_type)
            BroadCastEvent(self.marker_handler.modules, "markerAddEvent", self.data)

    def changeType(self, type):
        self.data.changeType(type)
        self.ReloadData()
        #self.GetStyle()
        #self.ApplyStyle()
        #self.setText(self.GetText())

    def graberReleased(self, grabber, event):
        pass

    def graberHoverEnter(self, grabber, event):
        pass

    def graberHoverLeave(self, grabber, event):
        pass

    def rightClick(self, grabber):
        # open marker edit menu
        mh = self.marker_handler
        if not mh.marker_edit_window or not mh.marker_edit_window.isVisible():
            mh.marker_edit_window = MarkerEditor(mh, mh.marker_file)
            mh.marker_edit_window.show()
        else:
            mh.marker_edit_window.raise_()
        mh.marker_edit_window.setMarkerData(self.data)

    def save(self):
        # only if there are fields which are changed
        if self.data.is_dirty():
            self.data.processed = 0
            self.data.save(only=self.data.dirty_fields)

    def delete(self, just_display=False):
        # delete the database entry
        if not just_display:
            self.data.delete_instance()
            BroadCastEvent(self.marker_handler.modules, "markerRemoveEvent", self.data)

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
        return self.marker_handler.data_file.table_marker(image=self.marker_handler.reference_image,
                                                          x=event.pos().x(), y=event.pos().y(), type=type)

    def ReloadData(self):
        MyDisplayItem.ReloadData(self)
        self.updateDisplay()

    def updateDisplay(self):
        # update marker display
        self.g1.setPos(self.data.x, self.data.y)
        self.setText(self.GetText())

    def graberMoved(self, grabber, pos, event):
        self.data.x = pos.x()
        self.data.y = pos.y()
        self.updateDisplay()
        BroadCastEvent(self.marker_handler.modules, "markerMoveEvent", self.data)

    def graberReleased(self, grabber, event):
        BroadCastEvent(self.marker_handler.modules, "markerMoveFinishedEvent", self.data)

    def draw(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        super(MyMarkerItem, self).drawMarker(image, start_x, start_y, scale=scale, image_scale=image_scale, rotation=rotation)

    def draw2(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        super(MyMarkerItem, self).drawText(image, start_x, start_y, scale=scale, image_scale=image_scale, rotation=rotation)

    def drawSvg(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        super(MyMarkerItem, self).drawMarkerSvg(image, start_x, start_y, scale=scale, image_scale=image_scale, rotation=rotation)

    def draw2Svg(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        super(MyMarkerItem, self).drawTextSvg(image, start_x, start_y, scale=scale, image_scale=image_scale, rotation=rotation)

    def hoverEnter(self):
        self.g1.hoverEnterEvent(None)

    def hoverLeave(self):
        self.g1.hoverLeaveEvent(None)

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
        return self.marker_handler.data_file.table_line(image=self.marker_handler.reference_image,
                                                        x1=x, y1=y, x2=x, y2=y, type=type)

    def ReloadData(self):
        MyDisplayItem.ReloadData(self)
        # update line display
        self.setLine(*self.data.getPos())
        self.g1.setPos(*self.data.getPos1())
        self.g2.setPos(*self.data.getPos2())

    def graberMoved(self, grabber, pos, event):
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
        BroadCastEvent(self.marker_handler.modules, "markerMoveEvent", self.data)

    def graberReleased(self, grabber, event):
        BroadCastEvent(self.marker_handler.modules, "markerMoveFinishedEvent", self.data)

    def drag(self, event):
        self.graberMoved(self.g2, event.pos(), event)

    def draw(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        x1, y1 = self.data.getPos1()[0] - start_x, self.data.getPos1()[1] - start_y
        x2, y2 = self.data.getPos2()[0] - start_x, self.data.getPos2()[1] - start_y
        x1, y1, x2, y2 = np.array([x1, y1, x2, y2])*image_scale
        color = (self.color.red(), self.color.green(), self.color.blue())
        image.line([x1, y1, x2, y2], color, width=int(3 * scale * self.style.get("scale", 1)))

    def draw2(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        super(MyLineItem, self).drawText(image, start_x, start_y, scale=scale, image_scale=image_scale, rotation=rotation)

    def drawSvg(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        x1, y1 = self.data.getPos1()[0] - start_x, self.data.getPos1()[1] - start_y
        x2, y2 = self.data.getPos2()[0] - start_x, self.data.getPos2()[1] - start_y
        x1, y1, x2, y2 = np.array([x1, y1, x2, y2])*image_scale
        color = (self.color.red(), self.color.green(), self.color.blue())
        image.add(image.polyline([(x1, y1), (x2, y2)], stroke=self.color.name(), stroke_width=3 * scale * self.style.get("scale", 1)))

    def draw2Svg(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        super(MyLineItem, self).drawTextSvg(image, start_x, start_y, scale=scale, image_scale=image_scale, rotation=rotation)

    def hoverEnter(self):
        self.g1.hoverEnterEvent(None)
        self.g2.hoverEnterEvent(None)

    def hoverLeave(self):
        self.g1.hoverLeaveEvent(None)
        self.g2.hoverLeaveEvent(None)

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
        self.start_grabber = self.g3
        self.text_parent = self.g3
        pen = self.pen()
        pen.setWidth(2)
        self.setPen(pen)

    def newData(self, event, type):
        x, y = event.pos().x(), event.pos().y()
        return self.marker_handler.data_file.table_rectangle(image=self.marker_handler.reference_image,
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

    def graberMoved(self, grabber, pos, event):
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
        BroadCastEvent(self.marker_handler.modules, "markerMoveEvent", self.data)

    def graberReleased(self, grabber, event):
        BroadCastEvent(self.marker_handler.modules, "markerMoveFinishedEvent", self.data)

    def drag(self, event):
        self.graberMoved(self.start_grabber, event.pos(), event)

    def draw(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        x1, y1 = self.data.getPos1()[0] - start_x, self.data.getPos1()[1] - start_y
        x2, y2 = self.data.getPos3()[0] - start_x, self.data.getPos3()[1] - start_y
        x1, y1, x2, y2 = np.array([x1, y1, x2, y2]) * image_scale
        color = (self.color.red(), self.color.green(), self.color.blue())
        image.line([x1, y1, x2, y1], color, width=int(3 * scale * self.style.get("scale", 1)))
        image.line([x2, y1, x2, y2], color, width=int(3 * scale * self.style.get("scale", 1)))
        image.line([x2, y2, x1, y2], color, width=int(3 * scale * self.style.get("scale", 1)))
        image.line([x1, y2, x1, y1], color, width=int(3 * scale * self.style.get("scale", 1)))

    def draw2(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        super(MyRectangleItem, self).drawText(image, start_x, start_y, scale=scale, image_scale=image_scale, rotation=rotation)

    def drawSvg(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        x1, y1 = self.data.getPos1()[0] - start_x, self.data.getPos1()[1] - start_y
        x2, y2 = self.data.getPos3()[0] - start_x, self.data.getPos3()[1] - start_y
        x1, y1, x2, y2 = np.array([x1, y1, x2, y2]) * image_scale
        image.add(image.polyline([(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)], stroke=self.color.name(), stroke_width=3 * scale * self.style.get("scale", 1), fill="none"))

    def draw2Svg(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        super(MyRectangleItem, self).drawTextSvg(image, start_x, start_y, scale=scale, image_scale=image_scale, rotation=rotation)

    def hoverEnter(self):
        self.g1.hoverEnterEvent(None)
        self.g2.hoverEnterEvent(None)
        self.g3.hoverEnterEvent(None)
        self.g4.hoverEnterEvent(None)

    def hoverLeave(self):
        self.g1.hoverLeaveEvent(None)
        self.g2.hoverLeaveEvent(None)
        self.g3.hoverLeaveEvent(None)
        self.g4.hoverLeaveEvent(None)

    def delete(self, just_display=False):
        if not just_display:
            self.g1.delete()
            self.g2.delete()
            self.g3.delete()
            self.g4.delete()
        MyDisplayItem.delete(self, just_display)


class MyEllipseItem(MyDisplayItem, QtWidgets.QGraphicsEllipseItem):
    default_shape = "rect"

    def __init__(self, marker_handler, parent, data=None, event=None, type=None):
        QtWidgets.QGraphicsLineItem.__init__(self, parent)
        MyDisplayItem.__init__(self, marker_handler, data, event, type)

    def getRect(self):
        return [self.data.x - self.data.width / 2, self.data.y - self.data.height / 2, self.data.width, self.data.height]

    def getPos1(self):
        return [self.data.x + self.data.width / 2, self.data.y]

    def getPos2(self):
        return [self.data.x - self.data.width / 2, self.data.y]

    def getPos3(self):
        return [self.data.x, self.data.y + self.data.height / 2]

    def getPos4(self):
        return [self.data.x, self.data.y - self.data.height / 2]

    def getPos5(self):
        return [self.data.x, self.data.y]

    def getPos6(self):
        return [self.data.x + self.data.width / 2, self.data.y + self.data.height / 2]

    def init2(self):
        self.setRect(*self.getRect())
        self.g5 = MyGrabberItem(self, self.color, *self.getPos5())
        self.g6 = MyGrabberItem(self, self.color, *self.getPos6())
        self.g1 = MyGrabberItem(self, self.color, *self.getPos1())
        self.g2 = MyGrabberItem(self, self.color, *self.getPos2())
        self.g3 = MyGrabberItem(self, self.color, *self.getPos3())
        self.g4 = MyGrabberItem(self, self.color, *self.getPos4())
        self.setTransformOriginPoint(self.data.x, self.data.y)
        self.setRotation(self.data.angle)
        self.start_grabber = self.g6
        self.text_parent = self.g5
        pen = self.pen()
        pen.setWidth(2)
        self.setPen(pen)

    def newData(self, event, type):
        x, y = event.pos().x(), event.pos().y()
        return self.marker_handler.data_file.table_ellipse(image=self.marker_handler.reference_image,
                                                        x=x, y=y, width=10, height=10, angle=0, type=type)

    def ReloadData(self):
        MyDisplayItem.ReloadData(self)
        self.updateDisplay()

    def updateDisplay(self):
        # update line display
        self.setRect(*self.getRect())
        self.g1.setPos(*self.getPos1())
        self.g2.setPos(*self.getPos2())
        self.g3.setPos(*self.getPos3())
        self.g4.setPos(*self.getPos4())
        self.g5.setPos(*self.getPos5())
        self.g6.setPos(*self.getPos6())
        self.setTransformOriginPoint(self.data.x, self.data.y)
        self.setRotation(self.data.angle)
        self.setText(self.GetText())

    def CheckPositiveWidthHeight(self):
        if self.data.width < 0:
            self.data.width = -self.data.width
            #self.g1, self.g2 = self.g2, self.g1
        if self.data.height < 0:
            self.data.height = -self.data.height
            #self.g3, self.g4 = self.g4, self.g3

    def graberMoved(self, grabber, pos, event):
        def process(p1, p2, c, a):
            sin, cos = np.sin(a * np.pi / 180), np.cos(a * np.pi / 180)
            rotation = np.array([[cos, -sin], [sin, cos]])

            p1 = rotation @ (p1 - c) + c
            p2 = rotation @ (p2 - c) + c

            delta = p1 - p2
            center = (p1 + p2) / 2
            angle = np.arctan2(delta[1], delta[0]) * 180 / np.pi
            dist = np.linalg.norm(delta)
            return dist, center, angle

        if grabber == self.g5:
            a = self.rotation() * np.pi / 180
            sin, cos = np.sin(a), np.cos(a)
            rotation = np.array([[cos, -sin], [sin, cos]])
            self.data.x, self.data.y = rotation @ np.array([pos.x() - self.data.x, pos.y() - self.data.y]) + np.array([self.data.x, self.data.y])

            self.CheckPositiveWidthHeight()
            self.updateDisplay()
        if grabber == self.g1:
            dist, center, angle = process(np.array([pos.x(), pos.y()]), np.array([self.g2.x(), self.g2.y()]), self.data.center, self.data.angle)
            self.data.angle = angle
            self.data.width = dist
            self.data.x, self.data.y = center

            self.CheckPositiveWidthHeight()
            self.updateDisplay()
        if grabber == self.g2:
            dist, center, angle = process(np.array([pos.x(), pos.y()]), np.array([self.g1.x(), self.g1.y()]),
                                          self.data.center, self.data.angle)
            self.data.angle = angle + 180
            self.data.width = dist
            self.data.x, self.data.y = center

            self.CheckPositiveWidthHeight()
            self.updateDisplay()
        if grabber == self.g3:
            dist, center, angle = process(np.array([pos.x(), pos.y()]), np.array([self.g4.x(), self.g4.y()]),
                                          self.data.center, self.data.angle)
            self.data.angle = angle - 90
            self.data.height = dist
            self.data.x, self.data.y = center

            self.CheckPositiveWidthHeight()
            self.updateDisplay()
        if grabber == self.g4:
            dist, center, angle = process(np.array([pos.x(), pos.y()]), np.array([self.g3.x(), self.g3.y()]),
                                          self.data.center, self.data.angle)
            self.data.angle = angle + 90
            self.data.height = dist
            self.data.x, self.data.y = center

            self.CheckPositiveWidthHeight()
            self.updateDisplay()
        if grabber == self.g6:
            self.data.width = (pos.x() - self.data.x)*2
            self.data.height = (pos.y() - self.data.y)*2
            self.CheckPositiveWidthHeight()
            self.updateDisplay()
        BroadCastEvent(self.marker_handler.modules, "markerMoveEvent", self.data)

    def graberReleased(self, grabber, event):
        BroadCastEvent(self.marker_handler.modules, "markerMoveFinishedEvent", self.data)

    def drag(self, event):
        self.graberMoved(self.start_grabber, event.pos(), event)

    def draw(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        x1, y1 = self.data.x - start_x, self.data.y - start_y
        x1, y1, w, h = np.array([x1, y1, self.data.width, self.data.height]) * image_scale
        color = (self.color.red(), self.color.green(), self.color.blue())

        from PIL import Image, ImageDraw
        w, h = int(np.ceil(w)), int(np.ceil(h))
        s = np.max([w, h])+4
        overlay = Image.new('RGBA', (s, s))
        draw = ImageDraw.Draw(overlay)
        xo = (s-w)/2
        yo = (s-h)/2
        draw.ellipse((xo, yo, xo+w, yo+h), outline=color)

        rotated = overlay.rotate(-self.data.angle, expand=False)
        image.pil_image.paste(rotated, (int(x1-rotated.size[0]/2), int(y1-rotated.size[1]/2)), rotated)

    def draw2(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        super(MyEllipseItem, self).drawText(image, start_x, start_y, scale=scale, image_scale=image_scale, rotation=rotation)

    def drawSvg(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        x1, y1 = self.data.x - start_x, self.data.y - start_y
        x1, y1, w, h = np.array([x1, y1, self.data.width, self.data.height]) * image_scale
        image.add(image.ellipse((0, 0), r=(w/2, h/2), stroke=self.color.name(), stroke_width=3 * scale * self.style.get("scale", 1), fill="none", transform="translate(%f, %f) rotate(%d)" % (x1, y1, self.data.angle)))

    def draw2Svg(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        super(MyEllipseItem, self).drawTextSvg(image, start_x, start_y, scale=scale, image_scale=image_scale, rotation=rotation)

    def hoverEnter(self):
        self.g1.hoverEnterEvent(None)
        self.g2.hoverEnterEvent(None)
        self.g3.hoverEnterEvent(None)
        self.g4.hoverEnterEvent(None)
        self.g5.hoverEnterEvent(None)

    def hoverLeave(self):
        self.g1.hoverLeaveEvent(None)
        self.g2.hoverLeaveEvent(None)
        self.g3.hoverLeaveEvent(None)
        self.g4.hoverLeaveEvent(None)
        self.g5.hoverLeaveEvent(None)

    def delete(self, just_display=False):
        if not just_display:
            self.g1.delete()
            self.g2.delete()
            self.g3.delete()
            self.g4.delete()
            self.g5.delete()
            self.g6.delete()
        MyDisplayItem.delete(self, just_display)


class MyPolygonItem(MyDisplayItem, QtWidgets.QGraphicsPathItem):
    default_shape = "rect"
    points = None
    grabbers = None
    adding_grabbers = False
    preview_point = None

    def __init__(self, marker_handler, parent, data=None, event=None, type=None):
        QtWidgets.QGraphicsLineItem.__init__(self, parent)
        self.points = []
        self.grabbers = []
        if data is None:
            self.adding_grabbers = True
        else:
            self.points = list(data.points)
        MyDisplayItem.__init__(self, marker_handler, data, event, type)

    def init2(self):
        self.start_grabber = None
        self.text_parent = None
        pen = self.pen()
        pen.setWidth(2)
        self.setPen(pen)

        self.updateDisplay()

    def newData(self, event, type):
        x, y = event.pos().x(), event.pos().y()
        self.points = [np.array([x, y])]
        return self.marker_handler.data_file.table_polygon(image=self.marker_handler.reference_image, type=type)

    def ReloadData(self):
        MyDisplayItem.ReloadData(self)
        self.updateDisplay()

    def storePoints(self):
        self.data.points = self.points

    def updateDisplay(self):
        path = QtGui.QPainterPath()
        if len(self.points):
            path.moveTo(*self.points[0])
        for point in self.points[1:]:
            path.lineTo(*point)
        if self.data.closed and len(self.points):
            path.lineTo(*self.points[0])
        if self.preview_point is not None:
            path.lineTo(*self.preview_point)
        self.setPath(path)

        grabber_count = len(self.points)*2-1+self.data.closed
        # only use a center if we have points
        if len(self.points):
            grabber_count += 1
        if len(self.grabbers) < grabber_count:
            for i in range(len(self.grabbers), grabber_count):
                self.grabbers.append(MyGrabberItem(self, self.color, 0, 0))
        if grabber_count < len(self.grabbers):
            for i in range(grabber_count, len(self.grabbers)):
                self.grabbers[-1].pop().delete()
        self.text_parent = self.grabbers[-1]
        for i in range(len(self.grabbers)):
            setattr(self, "g%d" % (i + 1), self.grabbers[i])
            if i == len(self.grabbers)-1:
                self.grabbers[i].grabber_index = -1
                self.grabbers[i].setPos(*np.mean(np.array(self.points), axis=0))
                self.grabbers[i].setShape("ring")
                self.grabbers[i].setZValue(3)
                continue
            j = i // 2
            if i % 2 == 0:
                self.grabbers[i].setPos(*self.points[i//2])
                self.grabbers[i].setShape("rect")
                self.grabbers[i].setZValue(10)
            else:
                if j == len(self.points)-1:
                    j = -1
                self.grabbers[i].setPos(*(self.points[j] + self.points[j + 1])/2)
                self.grabbers[i].setShape("circle")
                self.grabbers[i].setZValue(5)
            self.grabbers[i].grabber_index = i

        self.setText(self.GetText())

    def drag_click(self, event):
        if self.adding_grabbers:
            self.points.append(np.array([event.pos().x(), event.pos().y()]))
            self.grabbers.insert(len(self.grabbers)-1, MyGrabberItem(self, self.color, 0, 0))
            self.grabbers.insert(len(self.grabbers)-1, MyGrabberItem(self, self.color, 0, 0))
            self.storePoints()
            self.updateDisplay()
            return True
        else:
            return False

    def hover_drag(self, event):
        self.preview_point = (event.pos().x(), event.pos().y())
        self.updateDisplay()

    def graberMoved(self, grabber, pos, event):
        if grabber is None:
            return
        if self.adding_grabbers:
            if grabber.grabber_index == 0:
                self.data.closed = True
                self.grabbers.insert(len(self.grabbers) - 1, MyGrabberItem(self, self.color, 0, 0))
            self.preview_point = None
            self.adding_grabbers = False
            self.marker_handler.active_drag = None
            self.updateDisplay()
            return

        if grabber is not None:
            i = grabber.grabber_index
            # center marker
            if i == -1:
                center = np.mean(np.array(self.points), axis=0)
                offset = np.array([pos.x(), pos.y()])-center
                for point in self.points:
                    point += offset
                self.storePoints()
            else:
                j = grabber.grabber_index//2
                if grabber.grabber_index % 2 == 0:
                    self.points[grabber.grabber_index//2][:] = [pos.x(), pos.y()]
                    self.storePoints()
                else:
                    if j == len(self.points)-1:
                        self.points.append((self.points[-1] + self.points[0]) / 2)
                        self.grabbers.insert(i, MyGrabberItem(self, self.color, 0, 0))
                        self.grabbers.insert(i + 2, MyGrabberItem(self, self.color, 0, 0))
                    else:
                        self.points.insert(j+1, (self.points[j] + self.points[j+1])/2)
                        self.grabbers.insert(i, MyGrabberItem(self, self.color, 0, 0))
                        self.grabbers.insert(i+2, MyGrabberItem(self, self.color, 0, 0))
                    self.storePoints()
            self.updateDisplay()
        BroadCastEvent(self.marker_handler.modules, "markerMoveEvent", self.data)

    def graberReleased(self, grabber, event):
        BroadCastEvent(self.marker_handler.modules, "markerMoveFinishedEvent", self.data)

    def drag(self, event):
        self.graberMoved(self.start_grabber, event.pos(), event)

    def draw(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        pass  # TODO implement

    def draw2(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        super(MyEllipseItem, self).drawText(image, start_x, start_y, scale=scale, image_scale=image_scale, rotation=rotation)

    def drawSvg(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        pass  # TODO implement

    def draw2Svg(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        super(MyEllipseItem, self).drawTextSvg(image, start_x, start_y, scale=scale, image_scale=image_scale, rotation=rotation)

    def hoverEnter(self):
        for grabber in self.grabbers:
            grabber.hoverEnterEvent(None)

    def hoverLeave(self):
        for grabber in self.grabbers:
            grabber.hoverLeaveEvent(None)

    def graberDelete(self, grabber):
        if len(self.points) == 1 or grabber.grabber_index == -1:
            return self.delete()
        i = grabber.grabber_index
        j = grabber.grabber_index // 2
        if i % 2 == 0:
            self.points.pop(j)
            if i+1 == len(self.grabbers):
                self.grabbers.pop(i).delete()
                self.grabbers.pop(i-1).delete()
            elif i == 0:
                self.grabbers.pop(i+1).delete()
                self.grabbers.pop(i).delete()
            else:
                self.grabbers.pop(i+1).delete()
                self.grabbers.pop(i-1).delete()
        self.storePoints()
        self.updateDisplay()

    def delete(self, just_display=False):
        if not just_display:
            for grabber in self.grabbers:
                grabber.delete()
        MyDisplayItem.delete(self, just_display)


class MyTrackItem(MyDisplayItem, QtWidgets.QGraphicsPathItem):
    marker = None
    active = False
    hidden = False

    cur_off = (0, 0)
    g1 = None
    path2 = None

    markers = None
    marker_draw_items = None

    def __init__(self, marker_handler, parent, data=None, event=None, type=None, frame=None, markers=None):
        self.current_frame = frame
        self.markers = markers
        # initialize QGraphicsPathItem
        QtWidgets.QGraphicsPathItem.__init__(self, parent)
        # initialize MyDisplayItem
        MyDisplayItem.__init__(self, marker_handler, data, event, type)

    def newData(self, event, type):
        # create track database entry
        self.data = self.marker_handler.data_file.table_track(uid=uuid.uuid1(), type=type)
        self.data.save()
        # create marker list
        self.markers = SortedDict()
        # add the first point
        self.addPoint(event.pos())
        # return database entry
        return self.data

    def init2(self):
        self.g1 = MyGrabberItem(self, self.color, 0, 0, shape="cross")
        self.text_parent = self.g1
        self.marker_draw_items = {}

        self.path2 = QtWidgets.QGraphicsPathItem(self)  # second path for the lines to cover gaps
        pen = self.path2.pen()
        pen.setCosmetic(True)
        self.path2.setPen(pen)

    def setCurrentFrame(self, framenumber, cur_off):
        self.current_frame = framenumber
        self.cur_off = cur_off
        self.updateDisplay()

    def update(self, frame, marker_new):
        marker_new = dict(x=marker_new.x, y=marker_new.y, id=marker_new.id, type=marker_new.type, style=marker_new.style, text=marker_new.text)
        self.markers[frame] = TrackMarkerObject((marker_new["x"] + self.cur_off[0], marker_new["y"] + self.cur_off[1]), marker_new)

        self.marker_draw_items[frame].delete(just_remove=True)
        del self.marker_draw_items[frame]

        self.ApplyStyle()
        self.updateDisplay()

    def updateDisplay(self):
        framenumber = self.current_frame
        markers = self.markers
        cur_off = self.cur_off

        # start with empty paths
        path_line = QtGui.QPainterPath()
        path_gap = QtGui.QPainterPath()

        # get shape of track markers
        circle_width = self.style.get("track-point-scale", 1)
        shape = self.style.get("track-point-shape", "ring")
        if shape not in paths:
            shape = None

        for frame in self.marker_draw_items:
            self.marker_draw_items[frame].to_remove = True

        # set first connect (moveTo for path_line and path_gap)
        connect_function = connectTrackFirst
        # iterate over range
        last_frame = None
        for frame in markers:
            marker = markers[frame]
            # with the track doesn't have marker at this frame, ignore the frame
            if last_frame is not None and frame-1 != last_frame:
                # next connect is a gap connect (moveTo for path_line and lineTo for path_gap)
                connect_function = connectTrackGap
            # get the next point
            x, y = (marker.pos[0]-cur_off[0], marker.pos[1]-cur_off[1])
            # connect path_line and path_gap according to the current function
            connect_function(path_line, path_gap, x, y)
            # next connect is a gap connect (lineTo for path_line and moveTo for path_gap)
            connect_function = connectTrackLine
            last_frame = frame
            # add or move a point marker to this position
            if shape:
                if frame not in self.marker_draw_items:
                    self.marker_draw_items[frame] = MyNonGrabberItem(self, marker.getStyle("color", self.color), x, y, shape=marker.getStyle("shape", shape), scale=marker.getStyle("scale", circle_width))
                else:
                    self.marker_draw_items[frame].setPos(x, y)
                self.marker_draw_items[frame].to_remove = False
        frames = [k for k in self.marker_draw_items.keys()]
        for frame in frames:
            if self.marker_draw_items[frame].to_remove:
                self.marker_draw_items[frame].delete(just_remove=True)
                del self.marker_draw_items[frame]

        # set the line and gap path
        self.path2.setPath(path_gap)
        self.setPath(path_line)
        # move the grabber
        if framenumber in markers:
            self.g1.setPos(markers[framenumber].pos[0]-cur_off[0], markers[framenumber].pos[1]-cur_off[1])
            self.marker = markers[framenumber]
            self.setTrackActive(True)
        else:
            self.marker = None
            self.setTrackActive(False)

        # update text
        self.setText(self.GetText())

    def hoverTrackMarkerEnter(self, marker):
        frame = marker.image.sort_index
        if frame in self.marker_draw_items:
            self.marker_draw_items[frame].hoverEnterEventCustom(None)

    def hoverTrackMarkerLeave(self, marker):
        frame = marker.image.sort_index
        if frame in self.marker_draw_items:
            self.marker_draw_items[frame].hoverLeaveEventCustom(None)

    def ApplyStyle(self):
        MyDisplayItem.ApplyStyle(self)
        line_styles = dict(solid=Qt.SolidLine, dash=Qt.DashLine, dot=Qt.DotLine, dashdot=Qt.DashDotLine,
                           dashdotdot=Qt.DashDotDotLine)

        # the line between points
        pen = self.pen()
        pen.setWidthF(self.style.get("track-line-width", 2))
        pen.setStyle(line_styles[self.style.get("track-line-style", "solid")])
        self.setPen(pen)

        # the line between gaps
        pen = self.path2.pen()
        pen.setWidthF(self.style.get("track-gap-line-width", self.style.get("track-line-width", 2)))
        pen.setStyle(line_styles[self.style.get("track-gap-line-style", "dash")])
        pen.setColor(self.color)
        self.path2.setPen(pen)

        self.g1.setShape(self.style.get("shape", "cross"))
        if self.style.get("transform", "screen") == "screen":
            self.g1.setScale(self.style.get("scale", 1))
        else:
            self.g1.setScale(self.style.get("scale", 1)*0.1)

    def addPoint(self, pos):
        if self.marker is None:
            image = self.marker_handler.reference_image
            marker = self.marker_handler.marker_file.table_marker(image=image,
                                                                       x=pos.x(), y=pos.y(),
                                                                     type=self.data.type,
                                                                     track=self.data, text=None)
            marker.save()
            BroadCastEvent(self.marker_handler.modules, "markerAddEvent", marker)
            self.marker = TrackMarkerObject([0, 0], dict(id=marker.id, type=marker.type, track=marker.track, image=image, text=None, style={}))
            self.markers[self.current_frame] = self.marker
            self.setTrackActive(True)
        self.markers[self.current_frame].pos = (pos.x()+self.cur_off[0], pos.y()+self.cur_off[1])
        self.markers[self.current_frame].save_pos = (pos.x(), pos.y())
        if self.marker_draw_items and self.current_frame in self.marker_draw_items:
            self.marker_draw_items[self.current_frame].setPos(*self.markers[self.current_frame].pos)

    def graberMoved(self, grabber, pos, event):
        self.addPoint(pos)
        self.updateDisplay()
        BroadCastEvent(self.marker_handler.modules, "markerMoveEvent", self.data)

    def graberReleased(self, grabber, event):
        if self.marker_handler.data_file.getOption("tracking_connect_nearest") and event.modifiers() & Qt.ShiftModifier:
            step = self.marker_handler.config.skip
            self.marker_handler.window.JumpFrames(step)

    def graberDelete(self, grabber):
        self.removeTrackPoint()

    def rightClick(self, grabber):
        MyDisplayItem.rightClick(self, grabber)
        if self.marker is not None:
            entry = self.marker_handler.marker_file.table_marker.get(id=self.marker.data["id"])
            self.marker_handler.marker_edit_window.setMarkerData(entry)

    def removeTrackPoint(self, frame=None):
        # use the current frame if no frame is supplied
        if frame is None:
            frame = self.current_frame
        # delete the frame from points
        try:
            # delete entry from list
            data = self.markers.pop(frame)
            entry = self.marker_handler.marker_file.table_marker(id=data.data["id"])
            # delete entry from database
            self.marker_handler.marker_file.table_marker.delete().where(self.marker_handler.marker_file.table_marker.id == data.data["id"]).execute()
            # notify marker_handler
            BroadCastEvent(self.marker_handler.modules, "markerRemoveEvent", entry)
            # if it is the current frame, delete reference to marker
            if frame == self.current_frame:
                self.marker = None
        except KeyError:
            pass
        # if it was the last one delete the track, too
        if len(self.markers) == 0:
            self.delete()
            BroadCastEvent(self.marker_handler.modules, "markerRemoveEvent", self.data)
            return True  # True indicates that we remove the track too
        # set the track to inactive if the current marker was removed
        if frame == self.current_frame:
            self.setTrackActive(False)
        # redraw the track history
        self.updateDisplay()

    def setTrackActive(self, active):
        if active is False:
            self.active = False
            self.setOpacity(0.25)
            if self.marker_handler.data_file.getOption("tracking_connect_nearest"):
                self.setAcceptedMouseButtons(Qt.MouseButtons(0))
        else:
            self.active = True
            self.setOpacity(1)
            if self.marker_handler.data_file.getOption("tracking_connect_nearest"):
                self.setAcceptedMouseButtons(Qt.MouseButtons(3))

    def graberHoverEnter(self, grabber, event):
        self.setAdditionalLineWidthScale(1.5)

    def graberHoverLeave(self, grabber, event):
        self.setAdditionalLineWidthScale(1)

    def setAdditionalLineWidthScale(self, scale):
        pen = self.pen()
        pen.setWidthF(self.style.get("track-line-width", 2)*scale)
        self.setPen(pen)

        # the line between gaps
        pen = self.path2.pen()
        pen.setWidthF(self.style.get("track-gap-line-width", self.style.get("track-line-width", 2))*scale)
        self.path2.setPen(pen)

    def draw(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        if self.data.hidden or self.data.type.hidden:
            return
        if self.active:
            super(MyTrackItem, self).drawMarker(image, start_x, start_y, scale, image_scale, rotation)

        color = (self.color.red(), self.color.green(), self.color.blue())
        circle_width = scale * self.style.get("track-point-scale", 1)
        shape = self.style.get("track-point-shape", "ring")
        line_style = self.style.get("track-line-style", "solid")
        line_width = scale * self.style.get("track-line-width", 2)
        gap_line_style = self.style.get("track-gap-line-style", "dash")
        gap_line_width = scale * self.style.get("track-gap-line-width", self.style.get("track-line-width", 2))
        last_frame = None
        last_point = np.array([0, 0])
        offset = np.array([start_x, start_y])
        for frame in self.markers:
            marker = self.markers[frame]
            x, y = marker.pos
            point = np.array([x - start_x - self.cur_off[0], y - start_y - self.cur_off[1]])# + offset
            point *= image_scale

            if last_frame == frame - 1:
                drawLine(image, last_point, point, color, line_width, line_style)
            elif last_frame:
                drawLine(image, last_point, point, color, gap_line_width, gap_line_style)
            marker_shape = marker.getStyle("shape", shape)
            marker_width = marker.getStyle("scale", circle_width)*10
            drawMarker(image, point, marker.getStyle("color", self.color), marker_width, marker_shape)
            last_point = point
            last_frame = frame

    def drawSvg(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        if self.data.hidden or self.data.type.hidden:
            return
        if self.active:
            super(MyTrackItem, self).drawMarkerSvg(image, start_x, start_y, scale, image_scale, rotation)
        scale *= self.style.get("scale", 1)

        color = (self.color.red(), self.color.green(), self.color.blue())
        circle_width = scale * self.style.get("track-point-scale", 1)
        shape = self.style.get("track-point-shape", "ring")
        line_style = self.style.get("track-line-style", "solid")
        line_width = scale * self.style.get("track-line-width", 2)
        gap_line_style = self.style.get("track-gap-line-style", "dash")
        gap_line_width = scale * self.style.get("track-gap-line-width", self.style.get("track-line-width", 2))
        last_frame = None
        last_point = np.array([0, 0])
        offset = np.array([start_x, start_y])
        line = []
        line_skip = []
        for frame in self.markers:
            marker = self.markers[frame]
            x, y = marker.pos
            point = np.array([x - start_x - self.cur_off[0], y - start_y - self.cur_off[1]])# + offset
            point *= image_scale

            if last_frame == frame - 1:
                line.append(point)
                #drawLine(image, last_point, point, color, line_width, line_style)
            elif last_frame:
                line.append(point)
                pass
                #drawLine(image, last_point, point, color, gap_line_width, gap_line_style)
            marker_shape = marker.getStyle("shape", shape)
            marker_width = marker.getStyle("scale", circle_width)*10
            #drawMarker(image, point, marker.getStyle("color", self.color), marker_width, marker_shape)
            last_point = point
            last_frame = frame
        print(line)
        if len(line):
            marker = getMarker(image, marker.getStyle("color", self.color), marker.getStyle("scale", circle_width)*5, marker.getStyle("shape", shape))
            line = image.add(image.polyline(line, stroke=self.color.name(), fill='none', stroke_width=line_width))
            line['marker-mid'] = marker.get_funciri()
            line['marker-start'] = marker.get_funciri()
            line['marker-end'] = marker.get_funciri()

    def draw2(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        if self.active:
            super(MyTrackItem, self).drawText(image, start_x, start_y, scale=scale, image_scale=image_scale, rotation=rotation)

    def draw2Svg(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        if self.active:
            super(MyTrackItem, self).drawTextSvg(image, start_x, start_y, scale=scale, image_scale=image_scale, rotation=rotation)

    def hoverEnter(self):
        self.g1.hoverEnterEvent(None)
        self.graberHoverEnter(None,None)

    def hoverLeave(self):
        self.g1.hoverLeaveEvent(None)
        self.graberHoverLeave(None,None)


    def delete(self, just_display=False):
        # as the track entry removes itself, we always just want do delete the display
        MyDisplayItem.delete(self, just_display=True)

    def save(self):
        pass
        # if there is a marker at the current frame and it has a new position, save it
        if self.current_frame in self.markers and self.markers[self.current_frame].save_pos is not None:
            # get new position
            pos = self.markers[self.current_frame].save_pos
            # store it in the database
            self.marker_handler.marker_file.table_marker.update(x=pos[0], y=pos[1], processed=0).where(self.marker_handler.marker_file.table_marker.id == self.marker.data["id"]).execute()
            # set the save position to None
            self.markers[self.current_frame].save_pos = None


class Crosshair(QtWidgets.QGraphicsPathItem):
    def __init__(self, parent, view, image):
        QtWidgets.QGraphicsPathItem.__init__(self, parent)
        self.parent = parent
        self.view = view
        self.image = image
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
        if openslide_loaded and isinstance(self.image.image, openslide.OpenSlide):
            return
        if isinstance(self.image.image, myslide):
            src, srcpos = self.image.image.read_region_uncropped((x,y), 0, (2*self.radius-1, 2*self.radius-1))
            self.CrosshairQImageView[:, :, :] = self.SaveSlideSlice(src,
                                                           [[y - self.radius, y + self.radius + 1],
                                                            [x - self.radius, x + self.radius + 1], [0, 3]],
                                                                    srcpos+(0,))
            self.Crosshair.setPixmap(QtGui.QPixmap(self.CrosshairQImage))
            return
        self.CrosshairQImageView[:, :, :] = self.SaveSlice(self.image.image,
                                                           [[y - self.radius, y + self.radius + 1],
                                                            [x - self.radius, x + self.radius + 1], [0, 3]])
        self.Crosshair.setPixmap(QtGui.QPixmap(self.CrosshairQImage))

    @staticmethod
    def SaveSlideSlice(source, slices, sourceposition):
        shape = []
        slices1 = []
        slices2 = []
        empty = False
        for length, slice_border, slice_offset in zip(source.shape, slices, sourceposition):
            slice_border = [int(b) for b in slice_border]
            shape.append(slice_border[1] - slice_border[0])
            if slice_border[1] < 0:
                empty = True
            slices1.append(slice(max(slice_border[0]-slice_offset, 0), min(slice_border[1]-slice_offset, length)))
            slices2.append(slice(-min(slice_border[0]-slice_offset, 0),
                                 min(length - (slice_border[1]-slice_offset), 0) if min(length - (slice_border[1]-slice_offset), 0) != 0 else shape[
                                     -1]))
        new_slice = np.zeros(shape)
        if empty:
            return new_slice
        new_slice[slices2[0], slices2[1], :] = source[slices1[0], slices1[1], :3]
        return new_slice

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
    def __init__(self, parent, marker_handler, type, index, scale=1):
        QtWidgets.QGraphicsRectItem.__init__(self, parent)
        self.parent = parent
        self.marker_handler = marker_handler
        self.type = type
        self.count = 0
        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.scale_factor = scale

        self.setAcceptHoverEvents(True)
        self.active = False

        self.font = self.marker_handler.window.mono_font
        self.font.setPointSize(14)

        self.text = QtWidgets.QGraphicsSimpleTextItem(self)
        self.text.setFont(self.font)
        self.text.setZValue(10)
        self.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 128)))

        self.setZValue(9)

        self.setIndex(index)
        self.Update(self.type)
        self.AddCount(0)

    def setIndex(self, index):
        self.index = index
        self.setPos(10*self.scale_factor, (10 + 25 * self.index + 25)*self.scale_factor)
        self.AddCount(0)

    def Update(self, type):
        self.type = type
        if self.type is not None:
            self.color = QtGui.QColor(*HTMLColorToRGB(self.type.color))
        else:
            self.color = QtGui.QColor("white")
        self.text.setBrush(QtGui.QBrush(self.color))
        self.AddCount(0)

    def AddCount(self, new_count):
        self.count += new_count
        if self.type:
            self.text.setText(
                str(self.index + 1) + ": " + self.type.name + " %d" % self.count)
        else:
            self.text.setText("+ add type")
        rect = self.text.boundingRect()
        rect.setX(-5*self.scale_factor)
        rect.setWidth(rect.width() + 5*self.scale_factor)
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
            else:
                self.marker_handler.marker_edit_window.raise_()
            self.marker_handler.marker_edit_window.setMarkerData(self.type)
        elif event.button() == QtCore.Qt.LeftButton:
            if not self.marker_handler.active:
                BroadCastEvent([module for module in self.marker_handler.modules if module != self.marker_handler],
                               "setActiveModule", False)
                self.marker_handler.setActiveModule(True)
            self.marker_handler.SetActiveMarkerType(self.index)
            if self.marker_handler.marker_edit_window:
                self.marker_handler.marker_edit_window.setMarkerData(self.type)

    def delete(self):
        # delete from scene
        self.scene().removeItem(self)


class IterableDict:
    def __init__(self, dict):
        self.dict = dict

    def __iter__(self):
        return iter([self.dict[key] for key in self.dict])

    def __len__(self):
        return len(self.dict)

    def remove(self, item):
        if item in self.dict.values():
            for key in [key for key in self.dict]:
                if self.dict[key] == item:
                    del self.dict[key]
        else:
            raise ValueError


class MarkerHandler:
    points = None
    tracks = None
    tracks_loaded = False
    lines = None
    rectangles = None
    ellipses = None
    polygons = None
    display_lists = None
    display_dicts = None
    counter = None
    scale = 1

    marker_edit_window = None

    active = False
    frame_number = None
    hidden = False

    active_type_index = None
    active_type = None

    active_drag = None

    data_file = None
    config = None
    marker_file = None

    def __init__(self, window, parent, parent_hud, view, image_display, modules):
        self.window = window
        self.view = view
        self.parent_hud = parent_hud
        self.modules = modules
        self.parent = parent

        self.button = QtWidgets.QPushButton()
        self.button.setCheckable(True)
        self.button.setIcon(qta.icon("fa.crosshairs"))
        self.button.setToolTip("add/edit marker for current frame")
        self.button.clicked.connect(self.ToggleInterfaceEvent)
        self.window.layoutButtons.addWidget(self.button)

        self.MarkerParent = QtWidgets.QGraphicsPixmapItem(QtGui.QPixmap(array2qimage(np.zeros([1, 1, 4]))), self.parent)
        self.MarkerParent.setZValue(20)

        self.TrackParent = QtWidgets.QGraphicsPixmapItem(QtGui.QPixmap(array2qimage(np.zeros([1, 1, 4]))), self.parent)
        self.TrackParent.setZValue(20)

        self.scene_event_filter = GraphicsItemEventFilter(parent, self)
        image_display.AddEventFilter(self.scene_event_filter)

        self.Crosshair = Crosshair(parent, view, image_display)

        self.points = []
        self.tracks = {}
        self.marker_lists = {}
        self.cached_images = set()
        self.lines = []
        self.rectangles = []
        self.ellipses = []
        self.polygons = []
        self.counter = []
        self.display_lists = [self.points, IterableDict(self.tracks), self.lines, self.rectangles, self.ellipses, self.polygons]

        self.closeDataFile()

        self.button1 = MyCommandButton(self.parent_hud, self, qta.icon("fa.plus"), (10 + (26+5)*0, 10), scale=self.window.scale_factor)
        self.button2 = MyCommandButton(self.parent_hud, self, qta.icon("fa.trash"), (10 + (26+5)*1, 10), scale=self.window.scale_factor)
        self.button3 = MyCommandButton(self.parent_hud, self, qta.icon("fa.tint"), (10 + (26+5)*2, 10), scale=self.window.scale_factor)
        self.button1.setToolTip("add or move marker <b>M</b>")
        self.button2.setToolTip("delete marker<br/>(<b>D</b> or hold <b>ctrl</b>)")
        self.button3.setToolTip("change marker type <b>C</b>")
        self.tool_buttons = [self.button1, self.button2, self.button3]
        self.tool_index = -1
        self.tool_index_clicked = -1
        self.button1.clicked = lambda: self.selectTool(0)
        self.button2.clicked = lambda: self.selectTool(1)
        self.button3.clicked = lambda: self.selectTool(2)

    def selectTool(self, index, temporary=False):
        self.tool_index = index
        if not temporary:
            self.tool_index_clicked = index
        for button in self.tool_buttons:
            button.SetToInactiveColor()
        if index >= 0:
            self.tool_buttons[index].SetToActiveColor()
            BroadCastEvent(self.modules, "eventToolSelected", "Marker", self.tool_index)
            if not self.active:
                self.setActiveModule(True)
            if self.active_type_index is None:
                self.SetActiveMarkerType(0)
            self.counter[self.active_type_index].SetToActiveColor()
        else:
            for index in self.counter:
                self.counter[index].SetToInactiveColor()

        # set the cursor according to the tool
        cursor_name = ["fa.plus", "fa.trash", "fa.tint", None][self.tool_index]
        self.setCursor(cursor_name)

    def setCursor(self, cursor_name):
        # if no cursor is given, hide the cursor
        if cursor_name is None:
            self.window.ImageDisplay.unsetCursor()
        else:
            # get the cursor from file or name
            if cursor_name.startswith("fa."):
                icon = qta.icon(cursor_name, color=QtGui.QColor(*HTMLColorToRGB(self.active_type.color)[::-1]))
            else:
                icon = IconFromFile(cursor_name, color=QtGui.QColor(*HTMLColorToRGB(self.active_type.color)))
            # convert icon to numpy array
            buffer = icon.pixmap(16, 16).toImage().constBits()
            cursor2 = np.ndarray(shape=(16, 16, 4), buffer=buffer.asarray(size=16 * 16 * 4), dtype=np.uint8)
            # load the cursor image
            cursor = imageio.imread(os.path.join(os.environ["CLICKPOINTS_ICON"], "Cursor.png"))
            # compose them
            cursor3 = np.zeros([cursor.shape[0] + cursor2.shape[0], cursor.shape[1] + cursor2.shape[1], 4],
                               cursor.dtype)
            cursor3[:cursor.shape[0], :cursor.shape[1], :] = cursor
            y, x = (cursor.shape[0] - 6, cursor.shape[1] - 4)
            cursor3[y:y + cursor2.shape[0], x:x + cursor2.shape[1], :] = cursor2
            # create a cursor
            cursor = QtGui.QCursor(QtGui.QPixmap(array2qimage(cursor3)), 0, 0)

            # and the the cursor as the active one
            self.window.ImageDisplay.setCursor(cursor)

    def eventToolSelected(self, module, tool):
        if module == "Marker":
            return
        # if another module has selected a tool, we deselect our tool
        self.selectTool(-1)

    def closeDataFile(self):
        self.data_file = None
        self.config = None
        self.marker_file = None

        # remove all markers
        for list in self.display_lists:
            while len(list):
                list[0].delete(just_display=True)

        # remove all counters
        for counter in self.counter:
            self.view.scene.removeItem(self.counter[counter])
        self.counter = []

        if self.marker_edit_window:
            self.marker_edit_window.close()

    def updateDataFile(self, data_file, new_database):
        self.data_file = data_file
        self.config = data_file.getOptionAccess()

        self.marker_file = MarkerFile(data_file)
        self.tracks_loaded = False

        # if a new database is created fill it with markers from the config
        if new_database:
            for type_id, type_def in self.config.types.items():
                self.marker_file.set_type(type_id, *type_def)

        self.UpdateCounter()

        # get config options
        self.ToggleInterfaceEvent(hidden=self.config.marker_interface_hidden)
        if self.config.selected_marker_type >= 0:
            self.SetActiveMarkerType(self.config.selected_marker_type)

        #return
        # place tick marks for already present markers
        # frames from markers
        try:
            frames1 = np.array(self.marker_file.get_marker_frames1().tuples())[:, 0]
        except IndexError:
            frames1 = []
        # frames for rectangles
        try:
            frames2 = np.array(self.marker_file.get_marker_frames2().tuples())[:, 0]
        except IndexError:
            frames2 = []
            pass
        # frames for lines
        try:
            frames3 = np.array(self.marker_file.get_marker_frames3().tuples())[:, 0]
        except IndexError:
            frames3 = []
            pass
        # frames for ellipses
        try:
            frames4 = np.array(self.marker_file.get_marker_frames4().tuples())[:, 0]
        except IndexError:
            frames4 = []
            pass
        # frames for polygons
        try:
            frames5 = np.array(self.marker_file.get_marker_frames5().tuples())[:, 0]
        except IndexError:
            frames5 = []
            pass
        # join sets
        frames = set(frames1) | set(frames2) | set(frames3) | set(frames4) | set(frames5)
        # if we have marker, set ticks accordingly
        if len(frames):
            BroadCastEvent(self.modules, "MarkerPointsAddedList", frames)

    def drawToImage(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        for list in self.display_lists:
            for point in list:
                point.draw(image, start_x, start_y, scale, image_scale, rotation)

    def drawToImage2(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        for list in self.display_lists:
            for point in list:
                point.draw2(image, start_x, start_y, scale, image_scale, rotation)

    def drawToImageSvg(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        for list in self.display_lists:
            for point in list:
                point.drawSvg(image, start_x, start_y, scale, image_scale, rotation)

    def drawToImage2Svg(self, image, start_x, start_y, scale=1, image_scale=1, rotation=0):
        for list in self.display_lists:
            for point in list:
                point.draw2Svg(image, start_x, start_y, scale, image_scale, rotation)

    def UpdateCounter(self):
        for counter in self.counter:
            self.view.scene.removeItem(self.counter[counter])

        type_list = self.marker_file.get_type_list()
        self.counter = {index: MyCounter(self.parent_hud, self, type, index, scale=self.window.scale_factor) for index, type in enumerate(type_list)}
        self.counter[-1] = MyCounter(self.parent_hud, self, None, len(self.counter), scale=self.window.scale_factor)
        if len(list(self.counter.keys())):
            self.active_type = self.counter[list(self.counter.keys())[0]].type
        else:
            self.active_type = None

        for key in self.counter:
            self.counter[key].setVisible(not self.hidden)

    def removeCounter(self, type):
        # find the index to the type
        for index in self.counter:
            if self.counter[index].type == type:
                # delete the counter
                self.counter[index].delete()
                del self.counter[index]
                # if it was active set active to None
                if index == self.active_type_index:
                    self.active_type_index = None
                break
        # store the "add type" button
        add_type_button = self.counter[-1]
        # resort the buttons
        self.counter = {new_index: self.counter[old_index] for new_index, old_index in enumerate(sorted(self.counter.keys())[1:])}
        self.counter[-1] = add_type_button
        # update the buttons with their new index
        for index in self.counter:
            if index != -1:
                self.counter[index].setIndex(index)
        self.counter[-1].setIndex(max(self.counter.keys()) + 1)

    def addCounter(self, type):
        new_index = max(self.counter.keys())+1
        self.counter[new_index] = MyCounter(self.parent_hud, self, type, new_index)
        self.counter[-1].setIndex(new_index + 1)

    def GetCounter(self, type):
        for index in self.counter:
            if self.counter[index].type == type:
                return self.counter[index]
        raise NameError("A non existing type was referenced")

    def ReloadMarker(self, frame=None, layer=None):
        # called via SendCommand from external scripts or add-ons
        # get the frame
        if frame is None:
            frame = self.data_file.get_current_image()
        # delete the current frame from cache to be able to reload it
        self.cached_images = self.cached_images - set([frame])
        # Points
        if frame == self.frame_number:
            self.LoadPoints()
            self.LoadTracks()
            self.LoadLines()
            self.LoadRectangles()
            self.LoadEllipses()
            self.LoadPolygons()

    def imageLoadedEvent(self, filename, framenumber):
        self.frame_number = framenumber
        # get the image of the given frame, but in layer 1.
        # this will be the image that all new markers will be attached to
        self.reference_image = self.data_file.current_reference_image
        self.LoadPoints()
        self.LoadTracks()
        self.LoadLines()
        self.LoadRectangles()
        self.LoadEllipses()
        self.LoadPolygons()

    def LoadTracks(self, new_tracks=None):
        # get the current offset
        image = self.data_file.image
        offset = image.offset
        if offset:
            cur_off = (offset.x, offset.y)
        else:
            cur_off = (0, 0)

        # get the start frame
        if self.data_file.getOption("tracking_show_trailing") == -1:
            start = 0
        else:
            start = max([0, self.frame_number - self.data_file.getOption("tracking_show_trailing")])
        # get the end frame
        if self.data_file.getOption("tracking_show_leading") == -1:
            end = self.data_file.get_image_count()
        else:
            end = min([self.data_file.get_image_count(),
                       self.frame_number + self.data_file.getOption("tracking_show_leading")])

        if new_tracks is None:
            new_tracks = []
        loaded_images = []
        # get the database connection and set query results to sqlite3.Row
        conn = self.data_file.db.connection()
        conn.row_factory = sqlite3.Row
        try:
            # iterate over the frame range
            for frame in range(start, end + 1):
                # add to loaded images
                loaded_images.append(frame)
                # only load if it is not marked as cached
                if frame not in self.cached_images:
                    # query markers for the given sort_index
                    # the x, y coordinates are corrected by the offset
                    query = conn.execute('SELECT m.id, m.image_id, m.x+IFNULL(o.x, 0) AS x, m.y+IFNULL(o.y, 0) AS y, type_id, processed, track_id, style, text FROM marker m JOIN image i ON m.image_id = i.id LEFT JOIN offset o ON i.id = o.image_id where sort_index IS ? AND track_id', (frame,))
                    for marker in query:
                        # get track id
                        track_id = marker["track_id"]
                        # add to marker_list
                        if track_id not in self.marker_lists:
                            self.marker_lists[track_id] = SortedDict()
                        self.marker_lists[track_id][frame] = TrackMarkerObject((marker["x"], marker["y"]), marker)
                        # if the track doesn't have a display item we will query it later
                        if track_id not in self.tracks and track_id not in new_tracks:
                            new_tracks.append(track_id)
        finally:
            # set query result type back to default
            conn.row_factory = None

        # query track entries for new tracks found in the images which were loaded
        if len(new_tracks):
            # query tracks
            new_track_query = []
            if self.data_file._SQLITE_MAX_VARIABLE_NUMBER is None:
                self.data_file._SQLITE_MAX_VARIABLE_NUMBER = self.data_file.max_sql_variables()
            chunk_size = (self.data_file._SQLITE_MAX_VARIABLE_NUMBER - 1) // 2
            with self.data_file.db.atomic():
                for idx in range(0, len(new_tracks), chunk_size):
                    new_track_query.extend(self.marker_file.table_track.select().where(
                        self.marker_file.table_track.id << new_tracks[idx:idx + chunk_size]))

            # and crate track display items from it
            for track in new_track_query:
                try:
                    self.tracks[track.id]
                except KeyError:
                    pass
                else:
                    print("Error", track.id)
                self.tracks[track.id] = MyTrackItem(self, self.TrackParent, data=track,
                                                     markers=self.marker_lists[track.id])

        # find out which images should be removed from the cache
        loaded_images = set(loaded_images)
        cached_images_to_delete = self.cached_images - loaded_images
        self.cached_images = loaded_images

        # iterate over current track ids
        track_ids = [key for key in self.marker_lists.keys()]
        active_track_count = 0
        for track_id in track_ids:
            # delete old image frames from cache
            for image in cached_images_to_delete:
                try:
                    del self.marker_lists[track_id][image]
                except KeyError:
                    pass
            # if the marker_list doesn't have any items left, delete it with its track
            if len(self.marker_lists[track_id]) == 0:
                del self.marker_lists[track_id]
                if track_id in self.tracks:
                    self.tracks[track_id].delete(just_display=True)
                continue
            # only for tracks that are present
            if track_id not in self.tracks:
                continue
            # find out if the track has to be displayed
            active = False
            # is the track present in the current frame?
            if self.frame_number in self.marker_lists[track_id]:
                active = True
            # or is it at least visible in the range?
            elif min(self.marker_lists[track_id]) - self.data_file.getOption("tracking_show_trailing")\
                    <= self.frame_number <= \
                 max(self.marker_lists[track_id]) + self.data_file.getOption("tracking_hide_leading"):
                    active = True
            # display the track with the current markers
            if active and not self.tracks[track_id].data.hidden and not self.tracks[track_id].data.type.hidden:
                self.tracks[track_id].setVisible(True)
                self.tracks[track_id].setCurrentFrame(self.frame_number, cur_off)
                active_track_count += 1
            # or hide the track
            else:
                self.tracks[track_id].setVisible(False)

    def ReloadTrack(self, track):
        track_item = self.GetMarkerItem(track)
        if track_item is not None:
            track_item.delete(just_display=True)
        if not track.hidden:
            self.LoadTracks([track.id])

    def ReloadTrackType(self, track_type):
        new_tracks = []
        track_ids = [id for id in self.tracks]
        for track_id in track_ids:
            track = self.tracks[track_id]
            if track.data.type.id == track_type.id:
                new_tracks.append(track_id)
                track.delete()
        self.LoadTracks(new_tracks)

    def DeleteTrackType(self, track_type):
        track_ids = [id for id in self.tracks]
        for track_id in track_ids:
            track = self.tracks[track_id]
            if track.data.type.id == track_type.id:
                track.delete()
        self.LoadTracks()

    def LoadPoints(self):
        while len(self.points):
            self.points[0].delete(just_display=True)
        frame = self.data_file.get_current_image()
        image_id = self.data_file.current_reference_image.id
        marker_list = (
            self.marker_file.table_marker.select(self.marker_file.table_marker, self.marker_file.table_markertype)
                .join(self.marker_file.table_markertype)
                .where(self.marker_file.table_marker.image == image_id)
                .where(self.marker_file.table_markertype.hidden == False)
        )
        for marker in marker_list:
            if not marker.track:
                self.points.append(MyMarkerItem(self, self.MarkerParent, marker))
                self.points[-1].setScale(1 / self.scale)

    def LoadLines(self):
        while len(self.lines):
            self.lines[0].delete(just_display=True)
        frame = self.data_file.get_current_image()
        image_id = self.data_file.current_reference_image.id
        line_list = (
            self.marker_file.table_line.select(self.marker_file.table_line, self.marker_file.table_markertype)
                .join(self.marker_file.table_markertype)
                .where(self.marker_file.table_line.image == image_id)
                .where(self.marker_file.table_markertype.hidden == False)
        )
        for line in line_list:
            self.lines.append(MyLineItem(self, self.MarkerParent, data=line))

    def LoadRectangles(self):
        while len(self.rectangles):
            self.rectangles[0].delete(just_display=True)
        frame = self.data_file.get_current_image()
        image_id = self.data_file.current_reference_image.id
        rect_list = (
            self.marker_file.table_rectangle.select(self.marker_file.table_rectangle, self.marker_file.table_markertype)
                .join(self.marker_file.table_markertype)
                .where(self.marker_file.table_rectangle.image == image_id)
                .where(self.marker_file.table_markertype.hidden == False)
        )
        for rect in rect_list:
            self.rectangles.append(MyRectangleItem(self, self.MarkerParent, data=rect))

    def LoadEllipses(self):
        while len(self.ellipses):
            self.ellipses[0].delete(just_display=True)
        frame = self.data_file.get_current_image()
        image_id = self.data_file.current_reference_image.id
        ellipse_list = (
            self.marker_file.table_ellipse.select(self.marker_file.table_ellipse, self.marker_file.table_markertype)
                .join(self.marker_file.table_markertype)
                .where(self.marker_file.table_ellipse.image == image_id)
                .where(self.marker_file.table_markertype.hidden == False)
        )
        for ellipse in ellipse_list:
            self.ellipses.append(MyEllipseItem(self, self.MarkerParent, data=ellipse))

    def LoadPolygons(self):
        while len(self.polygons):
            self.polygons[0].delete(just_display=True)
        frame = self.data_file.get_current_image()
        image_id = self.data_file.current_reference_image.id
        polygon_list = (
            self.marker_file.table_polygon.select(self.marker_file.table_polygon, self.marker_file.table_markertype)
                .join(self.marker_file.table_markertype)
                .where(self.marker_file.table_polygon.image == image_id)
                .where(self.marker_file.table_markertype.hidden == False)
        )
        for polygon in polygon_list:
            self.polygons.append(MyPolygonItem(self, self.MarkerParent, data=polygon))

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

    def SetActiveMarkerType(self, new_index=None, new_type=None):
        if new_type is not None:
            for index in self.counter:
                if self.counter[index].type == new_type:
                    new_index = index
                    break
        if new_index >= len(self.counter) - 1:
            return
        if self.active_type_index is not None:
            self.counter[self.active_type_index].SetToInactiveColor()
        self.active_type = self.counter[new_index].type
        self.active_type_index = new_index
        if self.tool_index != 0 and self.tool_index != 2:
            self.selectTool(0)
        self.config.selected_marker_type = new_index
        self.counter[self.active_type_index].SetToActiveColor()

        # reset the cursor to adjust the color to the new markertype
        cursor_name = ["fa.plus", "fa.trash", "fa.tint", None][self.tool_index]
        self.setCursor(cursor_name)

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
                self.config.selected_marker_type = self.active_type_index
        else:
            if self.active_type_index is not None:
                self.counter[self.active_type_index].SetToInactiveColor()
            self.config.selected_marker_type = -1
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
        if self.hidden or self.data_file.image is None or self.tool_index == -1:
            return False
        if event.type() == QtCore.QEvent.GraphicsSceneMousePress and event.button() == QtCore.Qt.LeftButton and \
                not event.modifiers() & Qt.ControlModifier and self.active_type is not None and self.tool_index == 0:
            if getattr(self.active_drag, "drag_click", None) is not None:
                if getattr(self.active_drag, "drag_click", None)(event):
                    return True
            self.active_drag = None
            if len(self.points) >= 0:
                BroadCastEvent(self.modules, "MarkerPointsAdded")
            tracks = [track for track in self.tracks.values() if track.data.type.id == self.active_type.id]
            if self.active_type.mode & TYPE_Track and self.data_file.getOption("tracking_connect_nearest") and \
                    len(tracks) and not event.modifiers() & Qt.AltModifier:
                distances = [np.linalg.norm(PosToArray(point.g1.pos() - event.pos())) for point in tracks]
                index = np.argmin(distances)
                tracks[index].graberMoved(None, event.pos(), event)
                tracks[index].graberReleased(None, event)
            elif self.active_type.mode & TYPE_Track:
                track = MyTrackItem(self, self.TrackParent, event=event, type=self.active_type, frame=self.frame_number)
                track.updateDisplay()
                self.tracks[track.data.id] = track
                self.marker_lists[track.data.id] = track.markers
            elif self.active_type.mode & TYPE_Line:
                self.lines.append(MyLineItem(self, self.TrackParent, event=event, type=self.active_type))
                self.active_drag = self.lines[-1]
            elif self.active_type.mode & TYPE_Rect:
                self.rectangles.append(MyRectangleItem(self, self.TrackParent, event=event, type=self.active_type))
                self.active_drag = self.rectangles[-1]
            elif self.active_type.mode & TYPE_Ellipse:
                self.ellipses.append(MyEllipseItem(self, self.TrackParent, event=event, type=self.active_type))
                self.active_drag = self.ellipses[-1]
            elif self.active_type.mode & TYPE_Polygon:
                self.polygons.append(MyPolygonItem(self, self.TrackParent, event=event, type=self.active_type))
                self.active_drag = self.polygons[-1]
            else:
                self.points.append(MyMarkerItem(self, self.MarkerParent, event=event, type=self.active_type))
            self.data_file.setChangesMade()
            return True
        elif event.type() == QtCore.QEvent.GraphicsSceneMouseMove and self.active_drag:
            self.active_drag.drag(event)
            return True
        elif event.type() == QtCore.QEvent.GraphicsSceneHoverMove and self.active_drag and getattr(self.active_drag, "hover_drag", None) is not None:
            getattr(self.active_drag, "hover_drag", None)(event)
            return True
        return False

    def markerAddEvent(self, entry):
        if self.marker_edit_window:
            self.marker_edit_window.tree.updateEntry(entry)

    def markerRemoveEvent(self, entry):
        if self.marker_edit_window:
            self.marker_edit_window.tree.deleteEntry(entry)

    def optionsImported(self):
        for type_id, type_def in self.config.types.items():
            self.marker_file.set_type(type_id, *type_def)
        self.UpdateCounter()

    def keyPressEvent(self, event):

        numberkey = event.key() - 49

        # @key ---- Marker ----
        if self.tool_index >= 0 and 0 <= numberkey < 9 and event.modifiers() != Qt.KeypadModifier:
            # @key 0-9: change marker type
            self.SetActiveMarkerType(numberkey)

            # add mouse functions
            # @key MB1: set marker
            # @key ctrl + MB1: delete marker
            # @key MB2: open marker editor

        if not self.hidden:
            if event.key() == QtCore.Qt.Key_M:
                # @key M: add/move marker
                self.selectTool(0)

            if event.key() == QtCore.Qt.Key_D:
                # @key D: delete marker
                self.selectTool(1)

            if event.key() == QtCore.Qt.Key_C:
                # @key C: change marker type
                self.selectTool(2)

            if self.tool_index != -1:
                # show the erase tool highlighted when Control is pressed
                if event.key() == Qt.Key_Control and self.tool_index != 1:
                    self.selectTool(1, temporary=True)

    def keyReleaseEvent(self, event):
        if self.tool_index != -1:
            # show the erase tool highlighted when Control is pressed
            if event.key() == Qt.Key_Control:
                self.selectTool(self.tool_index_clicked)

    def ToggleInterfaceEvent(self, event=None, hidden=None):
        if hidden is None:
            self.hidden = not self.hidden
        else:
            self.hidden = hidden
        # reset the tool
        if self.hidden:
            self.selectTool(-1)
        # store in options
        if self.config is not None:
            self.config.marker_interface_hidden = self.hidden
        for key in self.counter:
            self.counter[key].setVisible(not self.hidden)
        for button in self.tool_buttons:
            button.setVisible(not self.hidden)
        for point in self.points:
            point.setActive(not self.hidden)
        for key in self.tracks:
            self.tracks[key].setActive(not self.hidden)
        self.button.setChecked(not self.hidden)

    def closeEvent(self, event):
        if self.marker_edit_window:
            self.marker_edit_window.close()

    @staticmethod
    def file():
        return __file__
