#!/usr/bin/env python
# -*- coding: utf-8 -*-
# MaskHandler.py

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
from typing import Any, List, Optional

import imageio
import numpy as np
import peewee
import qtawesome as qta
from PIL import Image, ImageDraw
from numpy import ndarray
from peewee import ModelSelect
from qtpy import QtGui, QtCore, QtWidgets
from skimage import measure

import clickpoints.includes.ImageQt_Stride as ImageQt
from clickpoints.includes import QtShortCuts
from clickpoints.includes.BigImageDisplay import BigImageDisplay
from clickpoints.includes.Database import DataFileExtended
from clickpoints.includes.QtShortCuts import GetColorByIndex
from clickpoints.includes.Tools import GraphicsItemEventFilter, BroadCastEvent, HTMLColorToRGB, IconFromFile, \
    MyTextButtonGroup, \
    MyToolGroup, array2qimage


class MaskFile:
    def __init__(self, datafile: DataFileExtended) -> None:
        self.data_file = datafile

        self.table_masktype = self.data_file.table_masktype
        self.table_mask = self.data_file.table_mask

        self.mask_path = None

    def set_type(self, id: id, name: str, rgb_tuple: tuple, index: int) -> "MarkerType":
        try:
            type = self.table_masktype.get(self.table_masktype.id == id)
        except peewee.DoesNotExist:
            type = self.table_masktype(id=id, name=name, color='#%02x%02x%02x' % tuple(rgb_tuple), index=index)
            type.save(force_insert=True)
        return type

    def get_mask_type_list(self) -> ModelSelect:
        return self.table_masktype.select()

    def add_mask(self, **kwargs):
        kwargs.update(dict(image=self.data_file.current_reference_image))
        return self.table_mask(**kwargs)

    def get_mask(self) -> None:
        try:
            return self.table_mask.get(self.table_mask.image == self.data_file.current_reference_image)
        except peewee.DoesNotExist:
            return None

    def get_mask_frames(self) -> ModelSelect:
        # query all sort_indices which have a mask
        return (self.data_file.table_image.select(self.data_file.table_image.sort_index)
                .join(self.table_mask)
                .group_by(self.data_file.table_image.id))


class BigPaintableImageDisplay:
    def __init__(self, origin: QtWidgets.QGraphicsPixmapItem, max_image_size: int = 2 ** 12) -> None:
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

    def UpdateColormap(self, types: ModelSelect) -> None:
        self.colormap = [QtGui.QColor(255, 0, 255, 0).rgba() for i in range(256)]
        for drawtype in types:
            self.colormap[drawtype.index] = QtGui.QColor(*HTMLColorToRGB(drawtype.color)).rgb()
        self.colormap[0] = QtGui.QColor(0, 0, 0, 0).rgba()
        self.UpdateImage()

    def UpdatePixmapCount(self) -> None:
        # Create new subimages if needed
        for i in range(len(self.pixMapItems), self.number_of_imagesX * self.number_of_imagesY):
            self.images.append(None)
            self.DrawImages.append(None)
            self.qimages.append(None)
            if i == 0:
                new_pixmap = QtWidgets.QGraphicsPixmapItem(self.origin)
            else:
                new_pixmap = QtWidgets.QGraphicsPixmapItem(self.origin)
            new_pixmap.setZValue(20)
            self.pixMapItems.append(new_pixmap)
            new_pixmap.setOpacity(self.opacity)
        # Hide images which are not needed
        for i in range(self.number_of_imagesX * self.number_of_imagesY, len(self.pixMapItems)):
            im = np.zeros((1, 1, 1))
            self.pixMapItems[i].setPixmap(QtGui.QPixmap(array2qimage(im)))
            self.pixMapItems[i].setOffset(0, 0)

    def SetImage(self, image: Image) -> None:
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

    def UpdateImage(self) -> None:
        for i in range(self.number_of_imagesY * self.number_of_imagesX):
            self.qimages[i] = ImageQt.ImageQt(self.images[i])
            qimage = QtGui.QImage(self.qimages[i])
            qimage.setColorTable(self.colormap)
            pixmap = QtGui.QPixmap(qimage)
            self.pixMapItems[i].setPixmap(pixmap)

    def DrawLine(self, x1: float, x2: float, y1: float, y2: float, size: int, line_type: int) -> None:
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
                        draw.line(
                            (x1 - x * self.max_image_size, y1 - y * self.max_image_size, x2 - x * self.max_image_size,
                             y2 - y * self.max_image_size), fill=color, width=size + 1)
                        draw.ellipse(
                            (x1 - x * self.max_image_size - size // 2, y1 - y * self.max_image_size - size // 2,
                             x1 - x * self.max_image_size + size // 2, y1 - y * self.max_image_size + size // 2),
                            fill=color)
        draw = ImageDraw.Draw(self.full_image)
        draw.line((x1, y1, x2, y2), fill=color, width=size + 1)
        draw.ellipse((x1 - size // 2, y1 - size // 2, x1 + size // 2, y1 + size // 2), fill=color)

    def Fill(self, x: float, y: float, line_type: int) -> bool:
        if line_type == 0:
            color = 0
        else:
            color = line_type.index
        if self.GetColor(x, y) == color:
            return False
        pix = np.asarray(self.full_image)
        try:
            pix.setflags(write=True)
        except ValueError:
            print("Could not set writeable Flag. Copying array.")
            pix = np.array(self.full_image)
            pix.setflags(write=True)
        label = measure.label(pix, background=-1)
        pix[label == label[int(y), int(x)]] = color
        self.SetImage(Image.fromarray(pix))
        return True

    def GetColor(self, x1: float, y1: float) -> int:
        if 0 < x1 < self.full_image.size[0] and 0 < y1 < self.full_image.size[1]:
            return self.full_image.getpixel((x1, y1))
        return None

    def setOpacity(self, opacity: float) -> None:
        self.opacity = opacity
        for pixmap in self.pixMapItems:
            pixmap.setOpacity(opacity)

    def setVisible(self, visible: bool) -> None:
        for pixmap in self.pixMapItems:
            pixmap.setVisible(visible)

    def save(self, filename: str) -> None:
        lut = np.zeros(3 * 256, np.uint8)
        for draw_type in self.config.draw_types:
            index = draw_type[0]
            lut[index * 3:(index + 1) * 3] = draw_type[1]
        self.full_image.putpalette(lut)

        fpath, fname = os.path.split(filename)
        if not os.path.exists(fpath):
            os.mkdir(fpath)

        self.full_image.save(filename)


class MaskEditor(QtWidgets.QWidget):
    data = None
    prevent_recursion = False

    def __init__(self, mask_handler: "MaskHandler", data_file: MaskFile) -> None:
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
        model.setItem(row + 1, 0, item)

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
        self.typeWidget.name = QtShortCuts.QInputString(layout, "Name:")
        self.typeWidget.color = QtShortCuts.QInputColor(layout, "Color:")
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

    def setMaskType(self, data: "MarkerType") -> None:
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
        self.typeWidget.name.setValue(self.data.name)
        self.typeWidget.color.setValue(self.data.color)

    def saveMaskType(self) -> None:
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
        self.data.name = self.typeWidget.name.value()
        self.data.color = self.typeWidget.color.value()
        # save and update
        try:
            self.data.save()
        except peewee.IntegrityError as err:
            if str(err) == "UNIQUE constraint failed: masktype.name":
                QtWidgets.QMessageBox.critical(self, 'Error - ClickPoints',
                                               'There already exists a masktype with name %s' % self.data.name,
                                               QtWidgets.QMessageBox.Ok)
                self.data.index = None
                return
            else:
                raise err
        self.mask_handler.maskTypeChooser.updateButtons(self.mask_handler.mask_file)

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

    def removeMarker(self) -> None:
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
        self.mask_handler.maskTypeChooser.updateButtons(self.mask_handler.mask_file)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        # close the window with esc
        if event.key() == QtCore.Qt.Key_Escape:
            self.mask_handler.marker_edit_window = None
            self.close()
        # save marker with return
        if event.key() == QtCore.Qt.Key_Return:
            self.saveMaskType()


class MaskTypeChooser(MyTextButtonGroup):
    tool = None
    active_draw_type = None

    def __init__(self, mask_handler: "MaskHandler", parent_hud: QtWidgets.QGraphicsPathItem) -> None:
        MyTextButtonGroup.__init__(self, parent_hud, mask_handler.window.mono_font, mask_handler.window.scale_factor)
        # store the mask handler
        self.mask_handler = mask_handler

    def getAlign(self) -> QtCore.Qt.AlignmentFlag:
        return QtCore.Qt.AlignRight

    def toolSelected(self, tool: Optional["MaskTool"]) -> None:
        # store the tool
        self.tool = tool
        # set to active if the present tool draws colors
        if tool is not None and tool.isColorTool():
            self.setActive()
        else:
            self.setInatice()

    def updateButtons(self, mask_file: MaskFile) -> None:
        # get all mask types
        self.types = mask_file.get_mask_type_list()
        # gather the properties of the mask types
        props = []
        for index, type in enumerate(self.types):
            props.append(dict(text="%d: %s" % (index + 1, type.name), color=type.color))
        # ad a button to open the mask type editor
        props.append(dict(text="+ add type", color="white"))
        # update the buttons with the properties
        self.setButtons(props)

        # update the colormap of the displayed mask
        self.mask_handler.MaskDisplay.UpdateColormap(self.types)

    def buttonPressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent, index: int) -> None:
        # right mouse button opens the mask menu
        if event.button() == QtCore.Qt.RightButton or index >= len(self.types):
            # open the menu if it is not open already
            if not self.mask_handler.mask_edit_window or not self.mask_handler.mask_edit_window.isVisible():
                self.mask_handler.mask_edit_window = MaskEditor(self.mask_handler, self.mask_handler.mask_file)
                self.mask_handler.mask_edit_window.show()
            else:
                self.mask_handler.mask_edit_window.raise_()
            # select this mask type in the menu
            self.mask_handler.mask_edit_window.setMaskType(self.types[index] if index < len(self.types) else None)
        # a left click selects this type
        elif event.button() == QtCore.Qt.LeftButton:
            # select this mask type
            self.selectType(index)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        numberkey = event.key() - 49

        if 0 <= numberkey < len(self.types) and event.modifiers() != QtCore.Qt.KeypadModifier:
            # @key 0-9: change brush type
            self.selectType(numberkey)

    def selectType(self, index: int) -> None:
        self.setActiveDrawType(index)
        if self.tool is None or not self.tool.isColorTool():
            self.mask_handler.tool_group.selectTool(0)

    def setActiveDrawType(self, new_index: int) -> None:
        # only allow valid types
        if new_index >= len(self.types):
            return
        # set the old button to inactive
        self.setInatice()
        # store the new type
        self.active_draw_type = self.types[new_index]
        self.active_index = new_index
        self.mask_handler.config.selected_draw_type = new_index
        # set the new button to active
        self.setActive()
        # update mask and draw cursor
        self.mask_handler.RedrawMask()
        self.mask_handler.UpdateDrawCursorDisplay()


class MaskTool:
    button = None

    def __init__(self, parent: "MaskHandler", scene_parent: "MaskToolGroup", image_display: BigImageDisplay) -> None:
        self.parent = parent
        self.scene_parent = scene_parent
        # event filter to grab mouse click and move events
        self.scene_event_filter = GraphicsItemEventFilter(scene_parent, self)
        image_display.AddEventFilter(self.scene_event_filter)

    def setActive(self) -> None:
        # activate the scene event filter (to receive mouse events)
        self.scene_event_filter.active = True
        # set the cursor
        self.setCursor()
        self.button.SetToActiveColor()

        self.parent.UpdateDrawCursorDisplay()

    def setInactive(self) -> None:
        # deactivate the scene event filter
        self.scene_event_filter.active = False
        # reset the cursor
        self.unsetCursor()
        # set the button to inactive
        self.button.SetToInactiveColor()
        # save the mask
        if self.parent.MaskChanged:
            self.parent.RedrawMask()
            if not self.parent.config.auto_mask_update:
                with self.parent.window.changeTracker("apply draw in mask"):
                    self.parent.save()

    def isColorTool(self) -> bool:
        return False

    def getIconName(self) -> None:
        return None

    def getIcon(self, color: Optional[QtGui.QColor] = None) -> QtGui.QIcon:
        cursor_name = self.getIconName()
        if cursor_name.startswith("fa."):
            icon = qta.icon(cursor_name, color=color)
        else:
            icon = IconFromFile(cursor_name, color=color)
        return icon

    def unsetCursor(self) -> None:
        # if no cursor is given, hide the cursor
        self.parent.ImageDisplay.unsetCursor()

    def setCursor(self) -> None:
        icon = self.getIcon(color=QtGui.QColor(255, 255, 255))
        # convert icon to numpy array
        buffer = icon.pixmap(16, 16).toImage().constBits()
        cursor2 = np.ndarray(shape=(16, 16, 4), buffer=buffer.asarray(size=16 * 16 * 4), dtype=np.uint8)
        # load the cursor image
        cursor = imageio.imread(os.path.join(os.environ["CLICKPOINTS_ICON"], "Cursor.png"))
        # compose them
        cursor3 = np.zeros([cursor.shape[0] + cursor2.shape[0], cursor.shape[1] + cursor2.shape[1], 4], cursor.dtype)
        cursor3[:cursor.shape[0], :cursor.shape[1], :] = cursor
        y, x = (cursor.shape[0] - 6, cursor.shape[1] - 4)
        cursor3[y:y + cursor2.shape[0], x:x + cursor2.shape[1], :] = cursor2
        # create a cursor
        cursor = QtGui.QCursor(QtGui.QPixmap(array2qimage(cursor3)), 0, 0)

        # and the the cursor as the active one
        self.parent.ImageDisplay.setCursor(cursor)

    def sceneEventFilter(self, event: QtCore.QEvent) -> None:
        if event.type() == QtCore.QEvent.GraphicsSceneWheel:
            try:  # PyQt 5
                angle = event.angleDelta().y()
            except AttributeError:  # PyQt 4
                angle = event.delta()

            # wheel with SHIFT means changing the opacity
            if event.modifiers() == QtCore.Qt.ShiftModifier:
                if angle > 0:
                    self.parent.changeOpacity(+0.1)
                else:
                    self.parent.changeOpacity(-0.1)
                event.accept()
                return True


class BrushTool(MaskTool):
    last_x = 0
    last_y = 0

    def getIconName(self) -> str:
        return "fa.paint-brush"

    def getTooltip(self) -> str:
        return "paint mask color <b>P</b>"

    def isColorTool(self) -> bool:
        return True

    def DrawLine(self, start_x: float, end_x: float, start_y: float, end_y: float) -> None:
        # draw the line on the mask
        if self.scene_parent.tool_index == 0:
            self.parent.MaskDisplay.DrawLine(start_x, end_x, start_y, end_y, self.parent.DrawCursorSize,
                                             self.parent.maskTypeChooser.active_draw_type)
        else:
            self.parent.MaskDisplay.DrawLine(start_x, end_x, start_y, end_y, self.parent.DrawCursorSize, 0)
        self.parent.MaskChanged = True
        self.parent.MaskUnsaved = True

        # directly update the mask or display last stroke as drawPath
        if self.parent.config.auto_mask_update:
            self.parent.RedrawMask()
        else:
            self.parent.drawPath.moveTo(start_x, start_y)
            self.parent.drawPath.lineTo(end_x, end_y)
            self.parent.drawPathItem.setPath(self.parent.drawPath)

        # if the mask was empty notify modules that a new mask was created
        if self.parent.MaskEmpty:
            self.parent.MaskEmpty = False
            BroadCastEvent(self.parent.modules, "MaskAdded")

    def sceneEventFilter(self, event: QtCore.QEvent) -> bool:
        # call the inherited method
        if MaskTool.sceneEventFilter(self, event):
            return True

        if self.parent.maskTypeChooser.active_draw_type is None:
            return True

        # Mouse wheel to change the cursor size
        if event.type() == QtCore.QEvent.GraphicsSceneWheel:
            try:  # PyQt 5
                angle = event.angleDelta().y()
            except AttributeError:  # PyQt 4
                angle = event.delta()
            # wheel with CTRL means changing the cursor size
            if event.modifiers() == QtCore.Qt.ControlModifier:
                if angle > 0:
                    self.parent.changeCursorSize(+1)
                else:
                    self.parent.changeCursorSize(-1)
                event.accept()
                return True

        # Mouse press starts drawing
        if event.type() == QtCore.QEvent.GraphicsSceneMousePress and event.button() == QtCore.Qt.LeftButton:
            # if no mask has been created, create one for painting
            if self.parent.MaskEmpty is True:
                self.parent.AddEmptyMask()
            # store the coordinates
            self.last_x = event.pos().x()
            self.last_y = event.pos().y()
            # add a first circle (so that even if the mouse isn't moved something is drawn)
            self.DrawLine(self.last_x, self.last_x + 0.00001, self.last_y, self.last_y)
            # set the changed flag for the database
            self.parent.data_file.setChangesMade()
            # accept the event
            return True
        if event.type() == QtCore.QEvent.GraphicsSceneMouseRelease and event.button() == QtCore.Qt.LeftButton:
            if self.parent.config.auto_mask_update:
                with self.parent.window.changeTracker("draw line in mask"):
                    self.parent.save()
        # Mouse move event to draw the stroke
        if event.type() == QtCore.QEvent.GraphicsSceneMouseMove:
            # get the new position
            self.parent.DrawCursor.setPos(event.pos())
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
            self.parent.DrawCursor.setPos(event.pos())
        # don't accept the event, so that others can accept it
        return False


class EraserTool(BrushTool):
    def getIconName(self) -> str:
        return "fa.eraser"

    def getTooltip(self) -> str:
        return "erase mask<br/>(<b>E</b> or hold <b>ctrl</b>)"

    def isColorTool(self) -> bool:
        return False


class PickerTool(MaskTool):
    color_under_cursor = 0

    def getIconName(self) -> str:
        return "fa.eyedropper"

    def getTooltip(self) -> str:
        return "pick mask color<br/>(<b>K</b> or hold <b>alt</b>)"

    def PickColor(self) -> None:
        # find the type which corresponds to the color_under_cursor
        for index, draw_type in enumerate(self.parent.mask_file.get_mask_type_list()):
            if draw_type.index == self.color_under_cursor:
                self.parent.maskTypeChooser.setActiveDrawType(index)
                return
        # if no color has been found, take background color
        self.parent.maskTypeChooser.setActiveDrawType(0)

    def sceneEventFilter(self, event: QtCore.QEvent) -> bool:
        if MaskTool.sceneEventFilter(self, event):
            return True
        # Mouse press starts drawing
        if event.type() == QtCore.QEvent.GraphicsSceneMousePress and event.button() == QtCore.Qt.LeftButton:
            self.PickColor()
            # accept the event
            return True
        # Mouse hover updates the color_under_cursor and displays the brush cursor
        if event.type() == QtCore.QEvent.GraphicsSceneHoverMove:
            # get color at this position
            if self.parent.MaskEmpty is True:
                self.color_under_cursor = 0
            else:
                color = self.parent.MaskDisplay.GetColor(event.pos().x(), event.pos().y())
                if color is not None:
                    self.color_under_cursor = color
        # don't accept the event, so that others can accept it
        return False


class BucketTool(MaskTool):
    def getIconName(self) -> str:
        return "Bucket.png"

    def getTooltip(self) -> str:
        return "fill with mask color <b>B</b>"

    def isColorTool(self) -> bool:
        return True

    def fillColor(self, x: float, y: float) -> None:
        if self.parent.MaskDisplay.Fill(x, y, self.parent.maskTypeChooser.active_draw_type):
            self.parent.MaskChanged = True
            self.parent.MaskUnsaved = True

    def sceneEventFilter(self, event: QtCore.QEvent) -> bool:
        if MaskTool.sceneEventFilter(self, event):
            return True
        # Mouse press starts drawing
        if event.type() == QtCore.QEvent.GraphicsSceneMousePress and event.button() == QtCore.Qt.LeftButton:
            with self.parent.window.changeTracker("bucket fill in mask"):
                self.fillColor(event.pos().x(), event.pos().y())
                self.parent.save()
            # accept the event
            return True

        # don't accept the event, so that others can accept it
        return False


class MaskToolGroup(MyToolGroup):
    active_draw_type = None

    def __init__(self, mask_handler: "MaskHandler", parent_hud: QtWidgets.QGraphicsPathItem,
                 image_display: BigImageDisplay) -> None:
        MyToolGroup.__init__(self, parent_hud, mask_handler.window.mono_font, mask_handler.window.scale_factor,
                             "Mask")

        tools = [BrushTool, EraserTool, PickerTool, BucketTool]
        self.tools = [tool(mask_handler, self, image_display) for tool in tools]
        self.setTools(self.tools, mask_handler)

        # store the mask handler
        self.mask_handler = mask_handler

    def getAlign(self) -> QtCore.Qt.AlignmentFlag:
        return QtCore.Qt.AlignRight

    def selectTool(self, index: int, temporary: bool = False) -> None:
        if self.tool_index == index:
            return
        MyToolGroup.selectTool(self, index, temporary)

        if self.tool_index >= 0:
            self.mask_handler.maskTypeChooser.toolSelected(self.tools[self.tool_index])
        else:
            self.mask_handler.maskTypeChooser.toolSelected(None)

        # and show the brush circle if necessary
        if index == 0 or index == 1:
            self.mask_handler.DrawCursor.setVisible(True)
        else:
            self.mask_handler.DrawCursor.setVisible(False)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:

        if self.isVisible():
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

        # show the erase tool highlighted when Control is pressed
        if self.tool_index != -1:
            if event.key() == QtCore.Qt.Key_Control and self.tool_index != 1:
                self.selectTool(1, temporary=True)
            if event.key() == QtCore.Qt.Key_Alt and self.tool_index != 2:
                self.selectTool(2, temporary=True)
            # if event.key() == QtCore.Qt.Key_Shift and self.tool_index != 3:
            #    self.selectTool(3, temporary=True)

    def keyReleaseEvent(self, event: QtGui.QKeyEvent) -> None:
        if self.tool_index != -1:
            # show the erase tool highlighted when Control is pressed
            if event.key() == QtCore.Qt.Key_Control:
                self.selectTool(self.tool_index_clicked)
            if event.key() == QtCore.Qt.Key_Alt:
                self.selectTool(self.tool_index_clicked)
            # if event.key() == QtCore.Qt.Key_Shift:
            #    self.selectTool(self.tool_index_clicked)


class MaskHandler:
    mask_edit_window = None

    DrawCursorSize = 10

    mask_opacity = 0

    MaskChanged = False  # if the mask has been changed and display has not been updated yet
    MaskUnsaved = False  # if the mask was changed and has to be saved
    MaskEmpty = False  # if no mask has been loaded/created
    hidden = False

    data_file = None
    config = None
    mask_file = None

    def __init__(self, window: "ClickPointsWindow", parent: QtWidgets.QGraphicsPixmapItem,
                 parent_hud: QtWidgets.QGraphicsPathItem, image_display: BigImageDisplay, modules: List[Any]) -> None:
        # store some references
        self.window = window
        self.parent_hud = parent_hud
        self.ImageDisplay = image_display
        self.modules = modules

        # create mask display
        self.MaskDisplay = BigPaintableImageDisplay(parent)
        self.drawPathItem = QtWidgets.QGraphicsPathItem(parent)
        self.drawPathItem.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255)))
        self.drawPathItem.setZValue(20)

        # the mask_type chooser (the buttons for the different mask colors)
        self.maskTypeChooser = MaskTypeChooser(self, parent_hud)

        # draw path to display last drawn stroke (only used in auto_update=False mode)
        self.drawPath = self.drawPathItem.path()
        self.drawPathItem.setPath(self.drawPath)
        self.drawPathItem.setZValue(10)

        # a cursor to display the currently used brush color and size
        self.DrawCursor = QtWidgets.QGraphicsPathItem(parent)
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

        self.tool_group = MaskToolGroup(self, self.parent_hud, image_display)

    def closeDataFile(self) -> None:
        self.data_file = None
        self.config = None
        self.mask_file = None

        # remove mask
        self.LoadMask(None)

        self.maskTypeChooser.clear()

        if self.mask_edit_window:
            self.mask_edit_window.close()

    def updateDataFile(self, data_file: DataFileExtended, new_database: bool) -> None:
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
        self.maskTypeChooser.updateButtons(self.mask_file)

        # get config options
        self.changeOpacity(self.config.mask_opacity - self.mask_opacity)
        self.changeCursorSize(self.config.mask_brush_size - self.DrawCursorSize)
        self.ToggleInterfaceEvent(hidden=self.config.mask_interface_hidden)
        if self.config.selected_draw_type >= 0:
            self.maskTypeChooser.setActiveDrawType(self.config.selected_draw_type)

        # place tick marks for already present masks
        # but lets take care that there are masks ...
        try:
            frames = np.array(self.mask_file.get_mask_frames().tuples())[:, 0]
            BroadCastEvent(self.modules, "MarkerPointsAddedList", frames)
        except IndexError:
            pass

    def maskTypesChangedEvent(self) -> None:
        # update mask interface buttons
        self.maskTypeChooser.updateButtons(self.mask_file)

    def imageLoadedEvent(self, filename: str, framenumber: int) -> None:
        # Broadcast from ClickPoints Main

        # load mask from mask database entry
        self.LoadMask(self.mask_file.get_mask())

    def ReloadMask(self) -> None:
        # load mask from mask database entry
        self.LoadMask(self.mask_file.get_mask())

    def LoadMask(self, mask_entry: None) -> None:
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

    def AddEmptyMask(self) -> None:
        # create a new empty mask display
        self.MaskDisplay.SetImage(Image.new('L', (self.ImageDisplay.image.shape[1], self.ImageDisplay.image.shape[0])))
        self.MaskDisplay.setVisible(True)

    def save(self) -> None:
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

    def RedrawMask(self) -> None:
        # redraw the mask image
        self.MaskDisplay.UpdateImage()
        # delete the stroke display
        self.drawPath = QtGui.QPainterPath()
        self.drawPathItem.setPath(self.drawPath)
        # reset the mask changed flag
        self.MaskChanged = False

    def setActiveModule(self, active: Any, first_time: bool = False) -> None:
        return

    def changeOpacity(self, value: float) -> None:
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

    def changeCursorSize(self, value: int) -> None:
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

    def UpdateDrawCursorDisplay(self) -> None:
        # if no type is selected do nothing
        if self.maskTypeChooser.active_draw_type is None:
            return

        # get the color from the current type
        color = QtGui.QColor(*HTMLColorToRGB(self.maskTypeChooser.active_draw_type.color))
        if not self.tool_group.tools[self.tool_group.tool_index].isColorTool():
            color = QtGui.QColor("black")

        # create a pen with this color and apply it to the drawPathItem
        pen = QtGui.QPen(color, self.DrawCursorSize)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        self.drawPathItem.setPen(pen)

        # update color and size of brush cursor
        draw_cursor_path = QtGui.QPainterPath()
        draw_cursor_path.addEllipse(-self.DrawCursorSize * 0.5, -self.DrawCursorSize * 0.5, self.DrawCursorSize,
                                    self.DrawCursorSize)
        pen = QtGui.QPen(color)
        pen.setCosmetic(True)
        self.DrawCursor.setPen(pen)
        self.DrawCursor.setPath(draw_cursor_path)

    def sceneEventFilter(self, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.GraphicsSceneWheel:
            try:  # PyQt 5
                angle = event.angleDelta().y()
            except AttributeError:  # PyQt 4
                angle = event.delta()
            # wheel with CTRL means changing the cursor size
            if event.modifiers() == QtCore.Qt.ControlModifier:
                if angle > 0:
                    self.changeCursorSize(+1)
                else:
                    self.changeCursorSize(-1)
                event.accept()
                return True
            # wheel with SHIFT means changing the opacity
            elif event.modifiers() == QtCore.Qt.ShiftModifier:
                if angle > 0:
                    self.changeOpacity(+0.1)
                else:
                    self.changeOpacity(-0.1)
                event.accept()
                return True
        # don't accept the event, so that others can accept it
        return False

    def optionsImported(self) -> None:
        for type_id, type_def in enumerate(self.config.draw_types):
            if len(type_def) >= 3:
                name = type_def[2]
            else:
                name = "Color%d" % type_id
            self.mask_file.set_type(type_id, name, type_def[1], type_def[0])
        self.maskTypeChooser.updateButtons(self.mask_file)

    def drawToImage0(self, image: ndarray, slicey: slice, slicex: slice) -> None:
        # only when the image has a mask
        if self.MaskDisplay.full_image is None:
            return
        # get the slice of the mask corresponding to the image to export
        mask = np.asarray(self.MaskDisplay.full_image)[slicey, slicex]
        # get the list of mask types and iterate
        type_list = self.mask_file.get_mask_type_list()
        for type in type_list:
            # get the mask for one color
            type_region = (mask == type.index)
            # cut out the mask region from the original image
            image1 = (1 - self.mask_opacity * type_region[:, :, None]) * image
            # fill the mask with the mask color
            image2 = self.mask_opacity * type_region[:, :, None] * np.array(HTMLColorToRGB(type.color))[None, None, :]
            # and compose the images
            image[:] = image1 + image2

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        numberkey = event.key() - 49
        # @key ---- Painting ----
        # if self.tool_index >= 0 and 0 <= numberkey < self.mask_file.get_mask_type_list().count()+1 and event.modifiers() != Qt.KeypadModifier:
        #    # @key 0-9: change brush type
        #    self.maskTypeChooser.selectType(numberkey)

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

        self.tool_group.keyPressEvent(event)

        # only link the mask type chooser
        if self.tool_group.tool_index >= 0:
            self.maskTypeChooser.keyPressEvent(event)

    def eventToolSelected(self, module: str, tool: int) -> None:
        if module == "Mask":
            return
        # if another module has selected a tool, we deselect our tool
        self.tool_group.selectTool(-1)

    def keyReleaseEvent(self, event: QtGui.QKeyEvent) -> None:
        self.tool_group.keyReleaseEvent(event)

    def ToggleInterfaceEvent(self, event: None = None, hidden: Optional[bool] = None) -> None:
        if hidden is None:
            # invert hidden status
            self.hidden = not self.hidden
        else:
            self.hidden = hidden
        # store in options
        if self.config is not None:
            self.config.mask_interface_hidden = self.hidden
        # update visibility status of the buttons
        self.maskTypeChooser.setVisible(not self.hidden)

        self.tool_group.setVisible(not self.hidden)
        # set the mask button to checked/unchecked
        self.buttonMask.setChecked(not self.hidden)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        # close the mask editor window when ClickPoints is closed
        if self.mask_edit_window:
            self.mask_edit_window.close()

    @staticmethod
    def file() -> str:
        # return the file (needed for the key help display)
        return __file__
