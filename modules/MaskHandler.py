from __future__ import division, print_function
import os
import peewee

from qtpy import QtGui, QtCore, QtWidgets
from qtpy.QtCore import Qt
import qtawesome as qta

import numpy as np

from PIL import Image, ImageDraw
import ImageQt_Stride as ImageQt
from qimage2ndarray import array2qimage

from Tools import GraphicsItemEventFilter, disk, PosToArray, BroadCastEvent, HTMLColorToRGB
from QtShortCuts import AddQSpinBox, AddQLineEdit, AddQLabel, AddQComboBox, AddQColorChoose, GetColorByIndex


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
            return self.table_mask.get(self.table_mask.image == self.data_file.image.id)
        except peewee.DoesNotExist:
            return None

    def get_mask_frames(self):
        return self.table_mask.select().group_by(self.table_mask.image)

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
    def __init__(self, origin, max_image_size=2**12, config=None):
        self.number_of_imagesX = 0
        self.number_of_imagesY = 0
        self.pixMapItems = []
        self.origin = origin
        self.full_image = None
        self.images = []
        self.DrawImages = []
        self.qimages = []
        self.max_image_size = max_image_size
        self.config = config

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
    def __init__(self, mask_handler, data_file):
        QtWidgets.QWidget.__init__(self)

        self.data_file = data_file

        # Widget
        self.setMinimumWidth(500)
        self.setMinimumHeight(200)
        self.setWindowTitle("MaskEditor - ClickPoints")
        self.setWindowIcon(qta.icon("fa.paint-brush"))
        main_layout = QtWidgets.QHBoxLayout(self)

        self.mask_handler = mask_handler
        self.db = mask_handler.mask_file

        """ Tree View """
        tree = QtWidgets.QTreeView()
        main_layout.addWidget(tree)

        model = QtGui.QStandardItemModel(0, 0)
        types = self.db.table_masktype.select()
        row = -1
        for row, type in enumerate(types):
            item = QtGui.QStandardItem(type.name)
            item.setIcon(qta.icon("fa.paint-brush", color=QtGui.QColor(*HTMLColorToRGB(type.color))))
            item.setEditable(False)
            item.entry = type

            model.setItem(row, 0, item)
        item = QtGui.QStandardItem("add type")
        item.setIcon(qta.icon("fa.plus"))
        item.setEditable(False)
        self.new_type = self.db.table_masktype()
        self.new_type.color = GetColorByIndex(types.count() + 16)
        item.entry = self.new_type
        model.setItem(row+1, 0, item)

        tree.setUniformRowHeights(True)
        tree.setHeaderHidden(True)
        tree.setAnimated(True)
        tree.setModel(model)
        tree.clicked.connect(lambda index: self.setMaskType(index.model().itemFromIndex(index).entry))
        self.tree = tree

        self.layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(self.layout)

        self.StackedWidget = QtWidgets.QStackedWidget(self)
        self.layout.addWidget(self.StackedWidget)

        """ Type Properties """
        self.typeWidget = QtWidgets.QGroupBox()
        self.StackedWidget.addWidget(self.typeWidget)
        layout = QtWidgets.QVBoxLayout(self.typeWidget)
        self.typeWidget.name = AddQLineEdit(layout, "Name:")
        self.typeWidget.color = AddQColorChoose(layout, "Color:")
        #self.typeWidget.text = AddQLineEdit(layout, "Text:")
        layout.addStretch()

        """ Control Buttons """
        horizontal_layout = QtWidgets.QHBoxLayout()
        self.layout.addLayout(horizontal_layout)
        self.pushbutton_Confirm = QtWidgets.QPushButton('S&ave', self)
        self.pushbutton_Confirm.pressed.connect(self.saveMaskType)
        horizontal_layout.addWidget(self.pushbutton_Confirm)

        self.pushbutton_Remove = QtWidgets.QPushButton('R&emove', self)
        self.pushbutton_Remove.pressed.connect(self.removeMarker)
        horizontal_layout.addWidget(self.pushbutton_Remove)

        self.pushbutton_Cancel = QtWidgets.QPushButton('&Cancel', self)
        self.pushbutton_Cancel.pressed.connect(self.close)
        horizontal_layout.addWidget(self.pushbutton_Cancel)

    def setMaskType(self, data):
        self.data = data if data is not None else self.new_type

        self.pushbutton_Remove.setHidden(False)

        self.StackedWidget.setCurrentIndex(1)
        if data is None or data.name is None:
            self.pushbutton_Remove.setHidden(True)
            self.typeWidget.setTitle("Add Type")
        else:
            self.pushbutton_Remove.setHidden(False)
            self.typeWidget.setTitle("Type #%s" % self.data.name)
        self.typeWidget.name.setText(self.data.name)
        self.typeWidget.color.setColor(self.data.color)

    def saveMaskType(self):
        print("Saving changes...")
        # set parameters

        self.data.name = self.typeWidget.name.text()
        self.data.color = self.typeWidget.color.getColor()
        if self.data.index is None:
            new_index = 1
            while True:
                try:
                    self.data_file.table_masktype.get(index=new_index)
                except peewee.DoesNotExist:
                    break
                new_index += 1
            self.data.index = new_index
        self.data.save()
        self.mask_handler.UpdateButtons()

        # close widget
        self.mask_handler.marker_edit_window = None
        self.close()

    def removeMarker(self):
        # delete the database entry
        self.data.delete_instance()

        # update display
        self.mask_handler.UpdateButtons()

        # close widget
        self.mask_handler.marker_edit_window = None
        self.close()

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
        self.setPos(-rect.width() - 5, 10 + 25 * self.index)

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
            # open the menu if it is not open alread
            if not self.mask_handler.mask_edit_window or not self.mask_handler.mask_edit_window.isVisible():
                self.mask_handler.mask_edit_window = MaskEditor(self.mask_handler, self.mask_handler.mask_file)
                self.mask_handler.mask_edit_window.show()
            # select this mask type in the menu
            self.mask_handler.mask_edit_window.setMaskType(self.type)
        # a left click selects this type
        elif event.button() == QtCore.Qt.LeftButton:
            # when mask editing is not active, activate it
            if not self.mask_handler.active:
                BroadCastEvent([module for module in self.mask_handler.modules if module != self.mask_handler], "setActiveModule", False)
                self.mask_handler.setActiveModule(True)
            # select this mask type
            self.mask_handler.SetActiveDrawType(self.index)

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
    active = False
    hidden = False

    buttons = []

    active_draw_type_index = None
    active_draw_type = None

    def __init__(self, window, parent, parent_hud, image_display, config, modules, datafile, new_database):
        # store some references
        self.window = window
        self.parent_hud = parent_hud
        self.ImageDisplay = image_display
        self.config = config
        self.modules = modules

        # create mask display
        self.MaskDisplay = BigPaintableImageDisplay(parent, config=config)
        self.drawPathItem = QtWidgets.QGraphicsPathItem(parent)
        self.drawPathItem.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255)))

        # database access
        self.data_file = datafile
        self.mask_file = MaskFile(datafile)

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

        # take hidden flag from config
        if self.config.hide_interfaces:
            self.hidden = True

        # if a new database is created take mask types from config
        if new_database:
            for type_id, type_def in enumerate(self.config.draw_types):
                if len(type_def) >= 3:
                    name = type_def[2]
                else:
                    name = "Color"
                self.mask_file.set_type(type_id, name, type_def[1], type_def[0])

        # update mask interface buttons
        self.UpdateButtons()

        # place tick marks for already present masks
        for item in self.mask_file.get_mask_frames():
            BroadCastEvent(self.modules, "MarkerPointsAdded", item.image.sort_index)

        # set the mask opacity to 0.5
        self.changeOpacity(0.5)

    def UpdateButtons(self):
        # remove all counter
        for button in self.buttons:
            self.buttons[button].delete()

        # create new ones
        type_list = self.mask_file.get_mask_type_list()
        # create buttons for types
        self.buttons = {index + 1: MaskTypeButton(self.parent_hud, self, type, index + 1) for index, type in enumerate(type_list)}
        # create button for "add_type"
        self.buttons[-1] = MaskTypeButton(self.parent_hud, self, None, len(self.buttons) + 1)
        # create button for background "delete"
        self.buttons[0] = MaskTypeButton(self.parent_hud, self, self.mask_file.table_mask(name="delete", color="#000000", index=0), 0)

        # set "delete" the active draw type
        self.active_draw_type = self.buttons[0].type
        self.active_draw_type_index = 0

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
        # activate the scene event filter (to receive mouse events)
        self.scene_event_filter.active = active
        self.active = active
        # display the brush cursor
        self.DrawCursor.setVisible(active)
        # set the current active button to active or inactive color
        if active:
            self.buttons[self.active_draw_type_index].SetToActiveColor()
        else:
            self.buttons[self.active_draw_type_index].SetToInactiveColor()
        return True

    def changeOpacity(self, value):
        # alter the opacity by value
        self.mask_opacity += value
        # the opacity has to be maximally 1
        if self.mask_opacity >= 1:
            self.mask_opacity = 1
        # and minimally 0
        if self.mask_opacity < 0:
            self.mask_opacity = 0
        # set the opacity
        self.MaskDisplay.setOpacity(self.mask_opacity)

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
        # set the new button to active
        self.buttons[self.active_draw_type_index].SetToActiveColor()
        # update mask and draw cursor
        self.RedrawMask()
        self.UpdateDrawCursorDisplay()

    def PickColor(self):
        # find the type which corresponds to the color_under_cursor
        for index, draw_type in enumerate(self.mask_file.get_mask_type_list()):
            if draw_type.index == self.color_under_cursor:
                self.SetActiveDrawType(index+1)
                return
        # if no color has been found, take background color
        self.SetActiveDrawType(0)

    def changeCursorSize(self, value):
        # increase/decrease the brush size by value
        self.DrawCursorSize += value
        # size has to be at least 1
        if self.DrawCursorSize < 1:
            self.DrawCursorSize = 1
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
        self.MaskDisplay.DrawLine(start_x, end_x, start_y, end_y, self.DrawCursorSize, self.active_draw_type)
        self.MaskChanged = True
        self.MaskUnsaved = True

        # directly update the mask or display last stroke as drawPath
        if self.config.auto_mask_update:
            self.RedrawMask()
        else:
            self.drawPath.moveTo(start_x, start_y)
            self.drawPath.lineTo(end_x, end_y)
            self.drawPathItem.setPath(self.drawPath)

        # if the mask was empty notifiy moduels that a new mask was created
        if self.MaskEmpty:
            self.MaskEmpty = False
            BroadCastEvent(self.modules, "MaskAdded")

    def sceneEventFilter(self, event):
        # only draw if an image is currently displayed
        if self.data_file.image is None:
            return False
        # Mouse press starts drawing
        if event.type() == QtCore.QEvent.GraphicsSceneMousePress and event.button() == QtCore.Qt.LeftButton:
            # if no mask has been created, create one for painting
            if self.MaskEmpty is True:
                self.AddEmptyMask()
            # store the coordinates
            self.last_x = event.pos().x()
            self.last_y = event.pos().y()
            # add a first circle (so that even if the mouse isn't moved something is drawn)
            self.DrawLine(self.last_x, self.last_x + 0.00001, self.last_y, self.last_y)
            # accept the event
            return True
        # Mouse move event to draw the stroke
        if event.type() == QtCore.QEvent.GraphicsSceneMouseMove:
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

    def keyPressEvent(self, event):
        numberkey = event.key() - 49
        # @key ---- Painting ----
        if self.active and 0 <= numberkey < self.mask_file.get_mask_type_list().count()+1 and event.modifiers() != Qt.KeypadModifier:
            # @key 0-9: change brush type
            self.SetActiveDrawType(numberkey)

        if event.key() == QtCore.Qt.Key_K:
            # @key K: pick color of brush
            self.PickColor()

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

        if event.key() == QtCore.Qt.Key_M:
            # @key M: redraw the mask
            self.RedrawMask()
            
    def ToggleInterfaceEvent(self):
        # invert hidden status
        self.hidden = not self.hidden
        # update visibility status of the buttons
        for button in self.buttons:
            self.buttons[button].setVisible(not self.hidden)
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
