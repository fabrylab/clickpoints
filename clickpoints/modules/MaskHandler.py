#!/usr/bin/env python
# -*- coding: utf-8 -*-
# MaskHandler.py

# Copyright (c) 2015-2016, Richard Gerum, Sebastian Richter
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ClickPoints. If not, see <http://www.gnu.org/licenses/>

from __future__ import division, print_function
import os
import sys
import peewee

from qtpy import QtGui, QtCore, QtWidgets
from qtpy.QtCore import Qt
import qtawesome as qta

import numpy as np

from PIL import Image, ImageDraw
import includes.ImageQt_Stride as ImageQt
from qimage2ndarray import array2qimage
from skimage import measure
import imageio

from includes.Tools import GraphicsItemEventFilter, disk, PosToArray, BroadCastEvent, HTMLColorToRGB, MyCommandButton, IconFromFile
from includes.QtShortCuts import AddQSpinBox, AddQLineEdit, AddQLabel, AddQComboBox, AddQColorChoose, GetColorByIndex


class MaskFile:
    def __init__(self, datafile):
        self.data_file = datafile

        self.table_masktype = self.data_file.table_masktype
        self.table_mask = self.data_file.table_mask

        self.mask_path = None

    def set_type(self, id, name, rgb_tuple, index):
        try:
            type = self.table_masktype.get(self.table_masktype.id == id)
        except peewee.DoesNotExist:
            type = self.table_masktype(id=id, name=name, color='#%02x%02x%02x' % tuple(rgb_tuple), index=index)
            type.save(force_insert=True)
        return type

    def get_mask_type_list(self):
        return self.table_masktype.select()

    def add_mask(self, **kwargs):
        kwargs.update(dict(image=self.data_file.image))
        return self.table_mask(**kwargs)

    def get_mask(self):
        try:
            image_id = self.data_file.get_image(index=self.data_file.current_image_index, layer=0).id
            return self.table_mask.get(self.table_mask.image == image_id)
        except peewee.DoesNotExist:
            return None

    def get_mask_frames(self):
        # query all sort_indices which have a mask
        return (self.data_file.table_image.select(self.data_file.table_image.sort_index)
                .join(self.table_mask)
                .group_by(self.data_file.table_image.id))

    def get_mask_path(self):
        if self.mask_path:
            return self.mask_path
        try:
            outputpath_mask = self.data_file.table_meta.get(key="mask_path").value
        except peewee.DoesNotExist:
            outputpath_mask = self.data_file.database_filename+"_mask.png"
            self.data_file.table_meta(key="mask_path", value=outputpath_mask).save()
        self.mask_path = os.path.join(os.path.dirname(self.data_file.database_filename), outputpath_mask)
        return self.mask_path


class BigPaintableImageDisplay:
    def __init__(self, origin, max_image_size=2**12):
        self.number_of_imagesX = 0
        self.number_of_imagesY = 0
        self.pixMapItems = []
        self.origin = origin
        self.full_image = None
        self.images = []
        self.DrawImages = []
        self.qimages = []
        self.max_image_size = max_image_size

        self.opacity = 0
        self.colormap = [QtGui.QColor(255, 0, 255).rgba() for i in range(256)]

    def UpdateColormap(self, types):
        self.colormap = [QtGui.QColor(255, 0, 255, 0).rgba() for i in range(256)]
        for drawtype in types:
            self.colormap[drawtype.index] = QtGui.QColor(*HTMLColorToRGB(drawtype.color)).rgb()
        self.colormap[0] = QtGui.QColor(0, 0, 0, 0).rgba()
        self.UpdateImage()

    def UpdatePixmapCount(self):
        # Create new subimages if needed
        for i in range(len(self.pixMapItems), self.number_of_imagesX * self.number_of_imagesY):
            self.images.append(None)
            self.DrawImages.append(None)
            self.qimages.append(None)
            if i == 0:
                new_pixmap = QtWidgets.QGraphicsPixmapItem(self.origin)
            else:
                new_pixmap = QtWidgets.QGraphicsPixmapItem(self.origin)
            self.pixMapItems.append(new_pixmap)
            new_pixmap.setOpacity(self.opacity)
        # Hide images which are not needed
        for i in range(self.number_of_imagesX * self.number_of_imagesY, len(self.pixMapItems)):
            im = np.zeros((1, 1, 1))
            self.pixMapItems[i].setPixmap(QtGui.QPixmap(array2qimage(im)))
            self.pixMapItems[i].setOffset(0, 0)

    def SetImage(self, image):
        self.number_of_imagesX = int(np.ceil(image.size[0] / self.max_image_size))
        self.number_of_imagesY = int(np.ceil(image.size[1] / self.max_image_size))
        self.UpdatePixmapCount()
        self.full_image = image

        for y in range(self.number_of_imagesY):
            for x in range(self.number_of_imagesX):
                i = y * self.number_of_imagesX + x
                start_x = x * self.max_image_size
                start_y = y * self.max_image_size
                end_x = min([(x + 1) * self.max_image_size, image.size[0]])
                end_y = min([(y + 1) * self.max_image_size, image.size[1]])

                self.images[i] = image.crop((start_x, start_y, end_x, end_y))
                self.DrawImages[i] = ImageDraw.Draw(self.images[i])
                self.pixMapItems[i].setOffset(start_x, start_y)
        self.UpdateImage()

    def UpdateImage(self):
        for i in range(self.number_of_imagesY * self.number_of_imagesX):
            self.qimages[i] = ImageQt.ImageQt(self.images[i])
            qimage = QtGui.QImage(self.qimages[i])
            qimage.setColorTable(self.colormap)
            pixmap = QtGui.QPixmap(qimage)
            self.pixMapItems[i].setPixmap(pixmap)

    def DrawLine(self, x1, x2, y1, y2, size, line_type):
        if line_type == 0:
            color = 0
        else:
            color = line_type.index
        for y in range(self.number_of_imagesY):
            for x in range(self.number_of_imagesX):
                i = y * self.number_of_imagesX + x
                if x * self.max_image_size < x1 < (x + 1) * self.max_image_size or x * self.max_image_size < x2 < (
                            x + 1) * self.max_image_size:
                    if y * self.max_image_size < y1 < (y + 1) * self.max_image_size or y * self.max_image_size < y2 < (
                                y + 1) * self.max_image_size:
                        draw = self.DrawImages[i]
                        draw.line((x1 - x * self.max_image_size, y1 - y * self.max_image_size, x2 - x * self.max_image_size,
                                   y2 - y * self.max_image_size), fill=color, width=size + 1)
                        draw.ellipse((x1 - x * self.max_image_size - size // 2, y1 - y * self.max_image_size - size // 2,
                                      x1 - x * self.max_image_size + size // 2, y1 - y * self.max_image_size + size // 2),
                                     fill=color)
        draw = ImageDraw.Draw(self.full_image)
        draw.line((x1, y1, x2, y2), fill=color, width=size + 1)
        draw.ellipse((x1 - size // 2, y1 - size // 2, x1 + size // 2, y1 + size // 2), fill=color)

    def Fill(self, x, y, line_type):
        if line_type == 0:
            color = 0
        else:
            color = line_type.index
        pix = np.asarray(self.full_image)
        pix.setflags(write=True)
        label = measure.label(pix, background=-1)
        pix[label == label[int(y), int(x)]] = color
        self.SetImage(Image.fromarray(pix))

    def GetColor(self, x1, y1):
        if 0 < x1 < self.full_image.size[0] and 0 < y1 < self.full_image.size[1]:
            return self.full_image.getpixel((x1, y1))
        return None

    def setOpacity(self, opacity):
        self.opacity = opacity
        for pixmap in self.pixMapItems:
            pixmap.setOpacity(opacity)

    def setVisible(self, visible):
        for pixmap in self.pixMapItems:
            pixmap.setVisible(visible)

    def save(self, filename):
        lut = np.zeros(3 * 256, np.uint8)
        for draw_type in self.config.draw_types:
            index = draw_type[0]
            lut[index * 3:(index + 1) * 3] = draw_type[1]
        self.full_image.putpalette(lut)

        fpath,fname = os.path.split(filename)
        if not os.path.exists(fpath):
            os.mkdir(fpath)

        self.full_image.save(filename)


class MaskEditor(QtWidgets.QWidget):
    data = None
    prevent_recursion = False

    def __init__(self, mask_handler, data_file):
        QtWidgets.QWidget.__init__(self)

        # store handle to database
        self.mask_handler = mask_handler
        self.mask_file = mask_handler.mask_file
        self.data_file = data_file

        # initialize window
        self.setMinimumWidth(500)
        self.setMinimumHeight(200)
        self.setWindowTitle("MaskEditor - ClickPoints")
        self.setWindowIcon(qta.icon("fa.paint-brush"))
        main_layout = QtWidgets.QHBoxLayout(self)

        # initialize tree view
        self.tree = QtWidgets.QTreeView()
        main_layout.addWidget(self.tree)

        # populate model with mask types
        model = QtGui.QStandardItemModel(0, 0)
        mask_types = self.mask_file.table_masktype.select()
        self.mask_type_modelitems = {}
        row = -1
        for row, mask_type in enumerate(mask_types):
            item = QtGui.QStandardItem(mask_type.name)
            item.setIcon(qta.icon("fa.paint-brush", color=QtGui.QColor(*HTMLColorToRGB(mask_type.color))))
            item.setEditable(False)
            item.entry = mask_type
            self.mask_type_modelitems[mask_type.id] = item
            model.setItem(row, 0, item)

        # add an "add type" row
        item = QtGui.QStandardItem("add type")
        item.setIcon(qta.icon("fa.plus"))
        item.setEditable(False)
        self.new_type = self.mask_file.table_masktype()
        self.new_type.color = GetColorByIndex(mask_types.count() + 16)
        item.entry = self.new_type
        self.mask_type_modelitems[-1] = item
        model.setItem(row+1, 0, item)

        # some settings for the tree view
        self.tree.setUniformRowHeights(True)
        self.tree.setHeaderHidden(True)
        self.tree.setAnimated(True)
        self.tree.setModel(model)
        self.tree.selectionModel().selectionChanged.connect(lambda selection, y: self.setMaskType(
            selection.indexes()[0].model().itemFromIndex(selection.indexes()[0]).entry))

        # create editor layout
        edit_layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(edit_layout)

        # edit fields for the mask type properties
        self.typeWidget = QtWidgets.QGroupBox()
        edit_layout.addWidget(self.typeWidget)
        layout = QtWidgets.QVBoxLayout(self.typeWidget)
        self.typeWidget.name = AddQLineEdit(layout, "Name:")
        self.typeWidget.color = AddQColorChoose(layout, "Color:")
        layout.addStretch()

        # control buttons
        horizontal_layout = QtWidgets.QHBoxLayout()
        edit_layout.addLayout(horizontal_layout)
        self.pushbutton_Confirm = QtWidgets.QPushButton('S&ave', self)
        self.pushbutton_Confirm.pressed.connect(self.saveMaskType)
        horizontal_layout.addWidget(self.pushbutton_Confirm)

        self.pushbutton_Remove = QtWidgets.QPushButton('R&emove', self)
        self.pushbutton_Remove.pressed.connect(self.removeMarker)
        horizontal_layout.addWidget(self.pushbutton_Remove)

        self.pushbutton_Exit = QtWidgets.QPushButton('&Exit', self)
        self.pushbutton_Exit.pressed.connect(self.close)
        horizontal_layout.addWidget(self.pushbutton_Exit)

    def setMaskType(self, data):
        # check flag to prevent recursion
        if self.prevent_recursion:
            return
        # store the data
        self.data = data if data is not None else self.new_type

        if data is None or data.name is None or data.id is None:
            # select type in tree
            self.prevent_recursion = True
            self.tree.setCurrentIndex(self.mask_type_modelitems[-1].index())
            self.prevent_recursion = False
            # hide remove button and set title
            self.pushbutton_Remove.setHidden(True)
            self.typeWidget.setTitle("Add Type")
        else:
            # select "add type" in tree
            self.prevent_recursion = True
            self.tree.setCurrentIndex(self.mask_type_modelitems[data.id].index())
            self.prevent_recursion = False
            # add remove button and set title
            self.pushbutton_Remove.setHidden(False)
            self.typeWidget.setTitle("Type #%s" % self.data.name)
        # set text and color
        self.typeWidget.name.setText(self.data.name)
        self.typeWidget.color.setColor(self.data.color)

    def saveMaskType(self):
        # if a new type should be added create it
        new_type = self.data.index is None
        if new_type:
            self.new_type.color = GetColorByIndex(len(self.mask_type_modelitems) + 16)
            self.data = self.mask_file.table_masktype()
            # find a new index
            new_index = 1
            while True:
                try:
                    self.data_file.table_masktype.get(index=new_index)
                except peewee.DoesNotExist:
                    break
                new_index += 1
            self.data.index = new_index
        # get data from fields
        self.data.name = self.typeWidget.name.text()
        self.data.color = self.typeWidget.color.getColor()
        # save and update
        self.data.save()
        self.mask_handler.UpdateButtons()

        # get the item from tree or insert a new one
        if new_type:
            item = QtGui.QStandardItem()
            item.setEditable(False)
            item.entry = self.data
            self.mask_type_modelitems[self.data.id] = item
            new_row = self.mask_type_modelitems[-1].row()
            self.tree.model().insertRow(new_row)
            self.tree.model().setItem(new_row, 0, item)
        else:
            item = self.mask_type_modelitems[self.data.id]

        # update item
        item.setIcon(qta.icon("fa.paint-brush", color=QtGui.QColor(*HTMLColorToRGB(self.data.color))))
        item.setText(self.data.name)
        # if a new type was created switch selection to create a new type
        if new_type:
            self.setMaskType(None)
        # set the database changed flag
        self.data_file.data_file.setChangesMade()

    def removeMarker(self):
        # get the tree view item (don't delete it right away because this changes the selection)
        index = self.data.id
        item = self.mask_type_modelitems[index]

        # delete the database entry
        self.data.delete_instance()

        # remove from list
        del self.mask_type_modelitems[index]
        self.new_type.color = GetColorByIndex(len(self.mask_type_modelitems) + 16 - 1)

        # and then delete the tree view item
        self.tree.model().removeRow(item.row())

        # update display
        self.mask_handler.UpdateButtons()

    def keyPressEvent(self, event):
        # close the window with esc
        if event.key() == QtCore.Qt.Key_Escape:
            self.mask_handler.marker_edit_window = None
            self.close()
        # save marker with return
        if event.key() == QtCore.Qt.Key_Return:
            self.saveMaskType()


class MaskTypeButton(QtWidgets.QGraphicsRectItem):
    def __init__(self, parent, mask_handler, point_type, index):
        QtWidgets.QGraphicsRectItem.__init__(self, parent)

        # store mask handler, type and index
        self.mask_handler = mask_handler
        self.type = point_type
        self.index = index

        # get hover events and set to inactive
        self.setAcceptHoverEvents(True)
        self.active = False

        # define the font
        self.font = self.mask_handler.window.mono_font
        self.font.setPointSize(14)

        # initialize the tex
        self.text = QtWidgets.QGraphicsSimpleTextItem(self)
        self.text.setFont(self.font)
        self.text.setZValue(10)
        self.updateText()

        # set the brush for the background color
        self.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 128)))
        self.setZValue(9)

    def updateText(self):
        # get text and color from type
        if self.type is None:
            self.text.setText("+ add type")
            color = QtGui.QColor("white")
        else:
            self.text.setText("%d: %s" % (self.index + 1, self.type.name))
            color = QtGui.QColor(*HTMLColorToRGB(self.type.color))
        # apply color
        self.text.setBrush(QtGui.QBrush(color))
        # update rect to fit text
        rect = self.text.boundingRect()
        rect.setX(-5)
        rect.setWidth(rect.width() + 5)
        self.setRect(rect)
        self.setPos(-rect.width() - 5, 10 + 25 * self.index + 25)

    def SetToActiveColor(self):
        # change background color
        self.active = True
        self.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255, 128)))

    def SetToInactiveColor(self):
        # change background color
        self.active = False
        self.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 128)))

    def hoverEnterEvent(self, event):
        # if not active highlight on mouse over
        if self.active is False:
            self.setBrush(QtGui.QBrush(QtGui.QColor(128, 128, 128, 128)))

    def hoverLeaveEvent(self, event):
        # ... or switch back to standard color
        if self.active is False:
            self.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 128)))

    def mousePressEvent(self, event):
        # right mouse button opens the mask menu
        if event.button() == QtCore.Qt.RightButton or self.type is None:
            # open the menu if it is not open already
            if not self.mask_handler.mask_edit_window or not self.mask_handler.mask_edit_window.isVisible():
                self.mask_handler.mask_edit_window = MaskEditor(self.mask_handler, self.mask_handler.mask_file)
                self.mask_handler.mask_edit_window.show()
            else:
                self.mask_handler.mask_edit_window.raise_()
            # select this mask type in the menu
            self.mask_handler.mask_edit_window.setMaskType(self.type if self.index != 0 else None)
        # a left click selects this type
        elif event.button() == QtCore.Qt.LeftButton:
            # select this mask type
            self.mask_handler.selectType(self.index)

    def delete(self):
        # delete from scene
        self.scene().removeItem(self)


class MaskHandler:
    mask_edit_window = None

    DrawCursorSize = 10

    mask_opacity = 0
    color_under_cursor = None
    last_x = None
    last_y = None

    MaskChanged = False  # if the mask has been changed and display has not been updated yet
    MaskUnsaved = False  # if the mask was changed and has to be saved
    MaskEmpty = False  # if no mask has been loaded/created
    hidden = False

    buttons = None

    active_draw_type_index = None
    active_draw_type = None

    data_file = None
    config = None
    mask_file = None

    def __init__(self, window, parent, parent_hud, image_display, modules):
        # store some references
        self.window = window
        self.parent_hud = parent_hud
        self.ImageDisplay = image_display
        self.modules = modules

        # create mask display
        self.MaskDisplay = BigPaintableImageDisplay(parent)
        self.drawPathItem = QtWidgets.QGraphicsPathItem(parent)
        self.drawPathItem.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255)))

        # event filter to grab mouse click and move events
        self.scene_event_filter = GraphicsItemEventFilter(parent, self)
        image_display.AddEventFilter(self.scene_event_filter)

        # draw path to display last drawn stroke (only used in auto_update=False mode)
        self.drawPath = self.drawPathItem.path()
        self.drawPathItem.setPath(self.drawPath)
        self.drawPathItem.setZValue(10)

        # a cursor to display the currently used brush color and size
        self.DrawCursor = QtWidgets.QGraphicsPathItem(parent)
        self.DrawCursor.setPos(10, 10)
        self.DrawCursor.setZValue(10)
        self.DrawCursor.setVisible(False)
        self.UpdateDrawCursorDisplay()

        # a button to display/hide the mask interface
        self.buttonMask = QtWidgets.QPushButton()
        self.buttonMask.setCheckable(True)
        self.buttonMask.setIcon(qta.icon("fa.paint-brush"))
        self.buttonMask.setToolTip("add/edit mask for current frame")
        self.buttonMask.clicked.connect(self.ToggleInterfaceEvent)
        self.window.layoutButtons.addWidget(self.buttonMask)

        # set the mask opacity to 0.5
        self.changeOpacity(0.5)

        self.closeDataFile()

        self.button1 = MyCommandButton(self.parent_hud, self, qta.icon("fa.paint-brush"), (-30 - (26 + 5) * 0, 10))
        self.button2 = MyCommandButton(self.parent_hud, self, qta.icon("fa.eraser"), (-30 - (26 + 5) * 1, 10))
        self.button3 = MyCommandButton(self.parent_hud, self, qta.icon("fa.eyedropper"), (-30 - (26 + 5) * 2, 10))
        self.button4 = MyCommandButton(self.parent_hud, self, IconFromFile("Bucket.png"), (-30 - (26 + 5) * 3, 10))
        self.button1.setToolTip("paint mask color <b>P</b>")
        self.button2.setToolTip("erase mask<br/>(<b>E</b> or hold <b>ctrl</b>)")
        self.button3.setToolTip("pick mask color<br/>(<b>K</b> or hold <b>alt</b>)")
        self.button4.setToolTip("fill with mask color<br/>(<b>B</b> or hold <b>shift</b>)")
        self.tool_buttons = [self.button1, self.button2, self.button3, self.button4]
        self.tool_index = -1
        self.tool_index_clicked = -1
        self.button1.clicked = lambda: self.selectTool(0)
        self.button2.clicked = lambda: self.selectTool(1)
        self.button3.clicked = lambda: self.selectTool(2)
        self.button4.clicked = lambda: self.selectTool(3)

    def selectTool(self, index, temporary=False):
        # set the tool
        self.tool_index = index
        # and if not temporary the "clicked" tool
        # (this is for temporary changing the tool with Ctrl or Alt)
        if not temporary:
            self.tool_index_clicked = index

        # set all mask type buttons to inactive
        for button_index in self.buttons:
            self.buttons[button_index].SetToInactiveColor()
        # set all tool buttons to inactive
        for button in self.tool_buttons:
            button.SetToInactiveColor()

        # if a tool is selected
        if index >= 0:
            # set the current mask type button to active
            self.tool_buttons[index].SetToActiveColor()
            # and the tool button to active
            self.buttons[self.active_draw_type_index].SetToActiveColor()
            # and notify the other modules
            BroadCastEvent(self.modules, "eventToolSelected", "Mask", self.tool_index)
            # activate the scene event filter (to receive mouse events)
            self.scene_event_filter.active = True
        else:
            # activate the scene event filter (to receive mouse events)
            self.scene_event_filter.active = False

        # set the cursor according to the tool
        cursor_name = ["fa.paint-brush", "fa.eraser", "fa.eyedropper", "Bucket.png", None][self.tool_index]
        self.setCursor(cursor_name)

        # and show the brush circle if necessary
        if index == 0 or index == 1:
            self.DrawCursor.setVisible(True)
        else:
            self.DrawCursor.setVisible(False)

    def setCursor(self, cursor_name):
        # if no cursor is given, hide the cursor
        if cursor_name is None:
            for pixmap in self.ImageDisplay.pixMapItems:
                pixmap.unsetCursor()
        else:
            # get the cursor from file or name
            if cursor_name.startswith("fa."):
                icon = qta.icon(cursor_name, color=QtGui.QColor(255, 255, 255))
            else:
                icon = IconFromFile(cursor_name, color=QtGui.QColor(255, 255, 255))
            # convert icon to numpy array
            buffer = icon.pixmap(16, 16).toImage().constBits()
            cursor2 = np.ndarray(shape=(16, 16, 4), buffer=buffer.asarray(size=16 * 16 * 4), dtype=np.uint8)
            # load the cursor image
            cursor = imageio.imread(os.path.join(os.environ["CLICKPOINTS_ICON"], "Cursor.png"))
            # compose them
            cursor3 = np.zeros([cursor.shape[0]+cursor2.shape[0], cursor.shape[1]+cursor2.shape[1], 4], cursor.dtype)
            cursor3[:cursor.shape[0], :cursor.shape[1], :] = cursor
            y, x = (cursor.shape[0]-6, cursor.shape[1]-4)
            cursor3[y:y+cursor2.shape[0], x:x+cursor2.shape[1], :] = cursor2
            # create a cursor
            cursor = QtGui.QCursor(QtGui.QPixmap(array2qimage(cursor3)), 0, 0)

            # and the the cursor as the active one
            for pixmap in self.ImageDisplay.pixMapItems:
                pixmap.setCursor(cursor)

    def eventToolSelected(self, module, tool):
        if module == "Mask":
            return
        # if another module has selected a tool, we deselect our tool
        self.selectTool(-1)

    def closeDataFile(self):
        self.data_file = None
        self.config = None
        self.mask_file = None

        # remove mask
        self.LoadMask(None)

        # remove all counters
        if self.buttons is not None:
            for button in self.buttons:
                self.buttons[button].delete()
        self.buttons = []

        if self.mask_edit_window:
            self.mask_edit_window.close()

    def updateDataFile(self, data_file, new_database):
        self.data_file = data_file
        self.config = data_file.getOptionAccess()

        self.mask_file = MaskFile(data_file)

        # if a new database is created take mask types from config
        if new_database:
            for type_id, type_def in enumerate(self.config.draw_types):
                if len(type_def) >= 3:
                    name = type_def[2]
                else:
                    name = "Color%d" % type_id
                self.mask_file.set_type(type_id, name, type_def[1], type_def[0])

        # update mask interface buttons
        self.UpdateButtons()

        # get config options
        self.changeOpacity(self.config.mask_opacity - self.mask_opacity)
        self.changeCursorSize(self.config.mask_brush_size - self.DrawCursorSize)
        self.ToggleInterfaceEvent(hidden=self.config.mask_interface_hidden)
        if self.config.selected_draw_type >= 0:
            self.SetActiveDrawType(self.config.selected_draw_type)

        # place tick marks for already present masks
        # but lets take care that there are masks ...
        try:
            frames = np.array(self.mask_file.get_mask_frames().tuples())[:, 0]
            BroadCastEvent(self.modules, "MarkerPointsAddedList", frames)
        except IndexError:
            pass

    def UpdateButtons(self):
        # remove all counter
        for button in self.buttons:
            self.buttons[button].delete()

        # create new ones
        type_list = self.mask_file.get_mask_type_list()
        # create buttons for types
        self.buttons = {index: MaskTypeButton(self.parent_hud, self, type, index) for index, type in enumerate(type_list)}
        # create button for "add_type"
        self.buttons[-1] = MaskTypeButton(self.parent_hud, self, None, len(self.buttons))
        ## create button for background "delete"
        #self.buttons[0] = MaskTypeButton(self.parent_hud, self, self.mask_file.table_mask(name="delete", color="#B0B0B0", index=0), 0)

        # set "delete" the active draw type
        self.active_draw_type = self.buttons[-1].type
        self.active_draw_type_index = -1

        # update the colormap of the displayed mask
        self.MaskDisplay.UpdateColormap(type_list)

        # buttons are visible according to self.hidden flag
        for key in self.buttons:
            self.buttons[key].setVisible(not self.hidden)

    def LoadImageEvent(self, filename, framenumber):
        # Broadcast from ClickPoints Main

        # load mask from mask database entry
        self.LoadMask(self.mask_file.get_mask())

    def ReloadMask(self):
        # load mask from mask database entry
        self.LoadMask(self.mask_file.get_mask())

    def LoadMask(self, mask_entry):
        # Load mask data or set to None if no
        if mask_entry is not None:
            self.MaskDisplay.SetImage(Image.fromarray(mask_entry.data))
            self.MaskDisplay.setVisible(True)
            self.MaskEmpty = False
        else:
            self.MaskDisplay.setVisible(False)
            self.MaskEmpty = True
        # Reset mask saved status
        self.MaskUnsaved = False
        # reset mask display
        self.drawPath = QtGui.QPainterPath()
        self.drawPathItem.setPath(self.drawPath)
        self.MaskChanged = False

    def AddEmptyMask(self):
        # create a new empty mask display
        self.MaskDisplay.SetImage(Image.new('L', (self.ImageDisplay.image.shape[1], self.ImageDisplay.image.shape[0])))
        self.MaskDisplay.setVisible(True)

    def save(self):
        # only save if the mask has been changed
        if self.MaskUnsaved:
            # get the current mask entry
            mask_entry = self.mask_file.get_mask()
            # if non exit yet, create a new one
            if mask_entry is None:
                mask_entry = self.mask_file.add_mask()
            # assign the current mask data and save it
            mask_entry.data = np.asarray(self.MaskDisplay.full_image)
            mask_entry.save()
            # reset the saved flag
            self.MaskUnsaved = False

    def RedrawMask(self):
        # redraw the mask image
        self.MaskDisplay.UpdateImage()
        # delete the stroke display
        self.drawPath = QtGui.QPainterPath()
        self.drawPathItem.setPath(self.drawPath)
        # reset the mask changed flag
        self.MaskChanged = False

    def setActiveModule(self, active, first_time=False):
        return

    def changeOpacity(self, value):
        # alter the opacity by value
        self.mask_opacity += value
        # the opacity has to be maximally 1
        if self.mask_opacity >= 1:
            self.mask_opacity = 1
        # and minimally 0
        if self.mask_opacity < 0:
            self.mask_opacity = 0
        # store in options
        if self.config is not None:
            self.config.mask_opacity = self.mask_opacity
        # set the opacity
        self.MaskDisplay.setOpacity(self.mask_opacity)

    def selectType(self, index):
        self.SetActiveDrawType(index)
        if self.tool_index != 0 and self.tool_index != 3:
            self.selectTool(0)

    def SetActiveDrawType(self, new_index):
        # only allow valid types
        if new_index >= len(self.buttons)-1:
            return
        # set the old button to inactive
        if self.active_draw_type_index is not None:
            self.buttons[self.active_draw_type_index].SetToInactiveColor()
        # store the new type
        self.active_draw_type = self.buttons[new_index].type
        self.active_draw_type_index = new_index
        self.config.selected_draw_type = new_index
        # set the new button to active
        self.buttons[self.active_draw_type_index].SetToActiveColor()
        # update mask and draw cursor
        self.RedrawMask()
        self.UpdateDrawCursorDisplay()

    def PickColor(self):
        # find the type which corresponds to the color_under_cursor
        for index, draw_type in enumerate(self.mask_file.get_mask_type_list()):
            if draw_type.index == self.color_under_cursor:
                self.SetActiveDrawType(index)
                return
        # if no color has been found, take background color
        self.SetActiveDrawType(0)

    def FillColor(self, x, y):
        self.MaskDisplay.Fill(x, y, self.active_draw_type)

    def changeCursorSize(self, value):
        # increase/decrease the brush size by value
        self.DrawCursorSize += value
        # size has to be at least 1
        if self.DrawCursorSize < 1:
            self.DrawCursorSize = 1
        # store in options
        if self.config is not None:
            self.config.mask_brush_size = self.DrawCursorSize
        # update displayed brush cursor size
        self.UpdateDrawCursorDisplay()
        if self.MaskChanged:
            self.RedrawMask()

    def UpdateDrawCursorDisplay(self):
        # if no type is selected do nothing
        if self.active_draw_type is None:
            return

        # get the color from the current type
        color = QtGui.QColor(*HTMLColorToRGB(self.active_draw_type.color))

        # create a pen with this color and apply it ti the drawPathItem
        pen = QtGui.QPen(color, self.DrawCursorSize)
        pen.setCapStyle(Qt.RoundCap)
        self.drawPathItem.setPen(pen)

        # update color and size of brush cursor
        draw_cursor_path = QtGui.QPainterPath()
        draw_cursor_path.addEllipse(-self.DrawCursorSize * 0.5, -self.DrawCursorSize * 0.5, self.DrawCursorSize,
                                    self.DrawCursorSize)
        self.DrawCursor.setPen(QtGui.QPen(color))
        self.DrawCursor.setPath(draw_cursor_path)

    def DrawLine(self, start_x, end_x, start_y, end_y):
        # draw the line on the mask
        if self.tool_index == 0:
            self.MaskDisplay.DrawLine(start_x, end_x, start_y, end_y, self.DrawCursorSize, self.active_draw_type)
        else:
            self.MaskDisplay.DrawLine(start_x, end_x, start_y, end_y, self.DrawCursorSize, 0)
        self.MaskChanged = True
        self.MaskUnsaved = True

        # directly update the mask or display last stroke as drawPath
        if self.config.auto_mask_update:
            self.RedrawMask()
        else:
            self.drawPath.moveTo(start_x, start_y)
            self.drawPath.lineTo(end_x, end_y)
            self.drawPathItem.setPath(self.drawPath)

        # if the mask was empty notify modules that a new mask was created
        if self.MaskEmpty:
            self.MaskEmpty = False
            BroadCastEvent(self.modules, "MaskAdded")

    def sceneEventFilter(self, event):
        # only draw if an image is currently displayed
        if self.data_file.image is None:
            return False
        # Mouse press starts drawing
        if event.type() == QtCore.QEvent.GraphicsSceneMousePress and event.button() == QtCore.Qt.LeftButton:
            if self.tool_index == 0 or self.tool_index == 1:
                # if no mask has been created, create one for painting
                if self.MaskEmpty is True:
                    self.AddEmptyMask()
                # store the coordinates
                self.last_x = event.pos().x()
                self.last_y = event.pos().y()
                # add a first circle (so that even if the mouse isn't moved something is drawn)
                self.DrawLine(self.last_x, self.last_x + 0.00001, self.last_y, self.last_y)
                # set the changed flag for the database
                self.data_file.setChangesMade()
            elif self.tool_index == 2:
                self.PickColor()
            elif self.tool_index == 3:
                self.FillColor(event.pos().x(), event.pos().y())
            # accept the event
            return True
        # Mouse move event to draw the stroke
        if event.type() == QtCore.QEvent.GraphicsSceneMouseMove and (self.tool_index == 0 or self.tool_index == 1):
            # get the new position
            self.DrawCursor.setPos(event.pos())
            pos_x = event.pos().x()
            pos_y = event.pos().y()
            # draw a line and store the position
            self.DrawLine(pos_x, self.last_x, pos_y, self.last_y)
            self.last_x = pos_x
            self.last_y = pos_y
            # accept the event
            return True
        # Mouse hover updates the color_under_cursor and displays the brush cursor
        if event.type() == QtCore.QEvent.GraphicsSceneHoverMove:
            # move brush cursor
            self.DrawCursor.setPos(event.pos())
            # get color at this position
            if self.MaskEmpty is True:
                self.color_under_cursor = 0
            else:
                color = self.MaskDisplay.GetColor(event.pos().x(), event.pos().y())
                if color is not None:
                    self.color_under_cursor = color
        # don't accept the event, so that others can accept it
        return False

    def optionsChanged(self):
        for type_id, type_def in enumerate(self.config.draw_types):
            if len(type_def) >= 3:
                name = type_def[2]
            else:
                name = "Color%d" % type_id
            self.mask_file.set_type(type_id, name, type_def[1], type_def[0])
        self.UpdateButtons()

    def keyPressEvent(self, event):
        numberkey = event.key() - 49
        # @key ---- Painting ----
        if self.tool_index >= 0 and 0 <= numberkey < self.mask_file.get_mask_type_list().count()+1 and event.modifiers() != Qt.KeypadModifier:
            # @key 0-9: change brush type
            self.selectType(numberkey)

        if event.key() == QtCore.Qt.Key_K:
            # @key K: pick color of brush
            self.selectTool(2)

        if event.key() == QtCore.Qt.Key_P:
            # @key P: paint brush
            self.selectTool(0)

        if event.key() == QtCore.Qt.Key_E:
            # @key E: eraser
            self.selectTool(1)

        if event.key() == QtCore.Qt.Key_B:
            # @key E: fill bucket
            self.selectTool(3)

        if event.key() == QtCore.Qt.Key_Plus:
            # @key +: increase brush radius
            self.changeCursorSize(+1)
        if event.key() == QtCore.Qt.Key_Minus:
            # @key -: decrease brush radius
            self.changeCursorSize(-1)
        if event.key() == QtCore.Qt.Key_O:
            # @key O: increase mask transparency
            self.changeOpacity(+0.1)

        if event.key() == QtCore.Qt.Key_I:
            # @key I: decrease mask transparency
            self.changeOpacity(-0.1)

        #if event.key() == QtCore.Qt.Key_M:
        #    # @ key M: redraw the mask
        #    self.RedrawMask()

        # show the erase tool highlighted when Control is pressed
        if self.tool_index != -1:
            if event.key() == Qt.Key_Control and self.tool_index != 1:
                self.selectTool(1, temporary=True)
            if event.key() == Qt.Key_Alt and self.tool_index != 2:
                self.selectTool(2, temporary=True)
            if event.key() == Qt.Key_Shift and self.tool_index != 3:
                self.selectTool(3, temporary=True)

    def keyReleaseEvent(self, event):
        if self.tool_index != -1:
            # show the erase tool highlighted when Control is pressed
            if event.key() == Qt.Key_Control:
                self.selectTool(self.tool_index_clicked)
            if event.key() == Qt.Key_Alt:
                self.selectTool(self.tool_index_clicked)
            if event.key() == Qt.Key_Shift:
                self.selectTool(self.tool_index_clicked)
            
    def ToggleInterfaceEvent(self, event=None, hidden=None):
        if hidden is None:
            # invert hidden status
            self.hidden = not self.hidden
        else:
            self.hidden = hidden
        # store in options
        if self.config is not None:
            self.config.mask_interface_hidden = self.hidden
        # update visibility status of the buttons
        for button in self.buttons:
            self.buttons[button].setVisible(not self.hidden)
        for button in self.tool_buttons:
            button.setVisible(not self.hidden)
        # set the mask button to checked/unchecked
        self.buttonMask.setChecked(not self.hidden)

    def closeEvent(self, event):
        # close the mask editor window when ClickPoints is closed
        if self.mask_edit_window:
            self.mask_edit_window.close()

    @staticmethod
    def file():
        # return the file (needed for the key help display)
        return __file__
