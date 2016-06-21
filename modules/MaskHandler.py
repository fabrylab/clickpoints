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
from QtShortCuts import AddQSpinBox, AddQLineEdit, AddQLabel, AddQComboBox, AddQColorChoose


class MaskFile:
    def __init__(self, datafile):
        self.data_file = datafile

        class Mask(datafile.base_model):
            image = peewee.ForeignKeyField(datafile.table_images, unique=True)
            filename = peewee.CharField()

        class MaskTypes(datafile.base_model):
            name = peewee.CharField()
            color = peewee.CharField()
            index = peewee.IntegerField(unique=True)

        self.table_mask = Mask
        self.table_maskTypes = MaskTypes
        self.data_file.tables.extend([Mask, MaskTypes])

        if not self.table_mask.table_exists():
            self.table_mask.create_table()
        if not self.table_maskTypes.table_exists():
            self.table_maskTypes.create_table()

        self.mask_path = None

    def set_type(self, id, name, rgb_tuple, index):
        try:
            type = self.table_maskTypes.get(self.table_maskTypes.id == id)
        except peewee.DoesNotExist:
            type = self.table_maskTypes(id=id, name=name, color='#%02x%02x%02x' % tuple(rgb_tuple), index=index)
            type.save(force_insert=True)
        return type

    def get_mask_type_list(self):
        return self.table_maskTypes.select()

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

        self.mask_modelitems = {}
        self.modelItems_mask = {}

        model = QtGui.QStandardItemModel(0, 0)
        types = self.db.table_maskTypes.select()
        for row, type in enumerate(types):
            item = QtGui.QStandardItem(type.name)
            item.setIcon(qta.icon("fa.paint-brush", color=QtGui.QColor(*HTMLColorToRGB(type.color))))
            item.setEditable(False)
            self.modelItems_mask[item] = type

            model.setItem(row, 0, item)
        item = QtGui.QStandardItem("add type")
        item.setIcon(qta.icon("fa.plus"))
        item.setEditable(False)
        self.new_type = self.db.table_maskTypes()
        self.modelItems_mask[item] = self.new_type
        model.setItem(row+1, 0, item)

        self.modelItems_mask = {item.index(): self.modelItems_mask[item] for item in self.modelItems_mask}

        tree.setUniformRowHeights(True)
        tree.setHeaderHidden(True)
        tree.setAnimated(True)
        tree.setModel(model)
        tree.clicked.connect(lambda x: self.setMaskType(self.modelItems_mask[x]))
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

    def setMaskType(self, data, marker_item=None):
        self.marker_item = marker_item
        if data is None:
            data = self.new_type
            data.color = "#FFFFFF"
        self.data = data

        self.pushbutton_Remove.setHidden(False)

        self.StackedWidget.setCurrentIndex(1)
        if data.name == None:
            self.pushbutton_Remove.setHidden(True)
        self.typeWidget.setTitle("Type #%s" % data.name)
        self.typeWidget.name.setText(data.name)
        self.typeWidget.color.setColor(data.color)

    def saveMaskType(self):
        print("Saving changes...")
        # set parameters

        self.data.name = self.typeWidget.name.text()
        self.data.color = self.typeWidget.color.getColor()
        if self.data.index is None:
            new_index = 1
            while True:
                try:
                    self.data_file.table_maskTypes.get(index=new_index)
                except peewee.DoesNotExist:
                    break
                new_index += 1
            self.data.index = new_index
        self.data.save()
        self.mask_handler.UpdateCounter()

        # close widget
        self.mask_handler.marker_edit_window = None
        self.close()

    def removeMarker(self):
        # delete the database entry
        self.data.delete_instance()

        # update display
        self.mask_handler.UpdateCounter()

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


class MyCounter2(QtWidgets.QGraphicsRectItem):
    def __init__(self, parent, mask_handler, point_type, index):
        QtWidgets.QGraphicsRectItem.__init__(self, parent)
        self.parent = parent
        self.mask_handler = mask_handler
        self.type = point_type
        self.index = index
        self.count = 0
        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))

        self.setAcceptHoverEvents(True)
        self.active = False

        self.font = self.mask_handler.window.mono_font
        self.font.setPointSize(14)

        if self.type is None:
            self.label_text = "+ add type"
        else:
            self.label_text = "%d: %s" % (index + 1, self.type.name)

        self.text = QtWidgets.QGraphicsSimpleTextItem(self)
        self.text.setText(self.label_text)
        self.text.setFont(self.font)
        if self.type is not None:
            self.color = QtGui.QColor(*HTMLColorToRGB(self.type.color))
        else:
            self.color = QtGui.QColor("white")
        self.text.setBrush(QtGui.QBrush(self.color))
        self.text.setZValue(10)

        self.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 128)))
        self.setPos(-110, 10 + 25 * index)
        self.setZValue(9)

        count = 0
        self.AddCount(count)

    def AddCount(self, new_count):
        self.count += new_count
        self.text.setText(self.label_text)
        rect = self.text.boundingRect()
        rect.setX(-5)
        rect.setWidth(rect.width() + 5)
        self.setRect(rect)
        self.setPos(-rect.width() - 5, 10 + 25 * self.index)

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
        if event.button() == 2 or self.type is None:  # right mouse button
            # open marker edit menu
            if not self.mask_handler.mask_edit_window or not self.mask_handler.mask_edit_window.isVisible():
                self.mask_handler.mask_edit_window = MaskEditor(self.mask_handler, self.mask_handler.mask_file)
                self.mask_handler.mask_edit_window.show()
            self.mask_handler.mask_edit_window.setMaskType(self.type, self)
        elif event.button() == 1:
            if not self.mask_handler.active:
                BroadCastEvent([module for module in self.mask_handler.modules if module != self.mask_handler], "setActiveModule", False)
                self.mask_handler.setActiveModule(True)
            self.mask_handler.SetActiveDrawType(self.index)


class MaskHandler:
    mask_edit_window = None

    DrawCursorSize = 10

    mask_opacity = 0
    current_maskname = None
    last_maskname = None
    color_under_cursor = None
    image_mask_full = None
    last_x = None
    last_y = None

    DrawMode = False
    MaskChanged = False
    MaskUnsaved = False
    MaskEmpty = False
    active = False
    hidden = False

    counter = []

    active_draw_type_index = None
    active_draw_type = None

    def __init__(self, window, parent, parent_hud, view, image_display, config, modules, datafile, new_database):
        self.window = window
        self.view = view
        self.parent_hud = parent_hud
        self.ImageDisplay = image_display
        self.config = config
        self.modules = modules
        self.MaskDisplay = BigPaintableImageDisplay(parent, config=config)
        self.drawPathItem = QtWidgets.QGraphicsPathItem(parent)
        self.drawPathItem.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255)))
        self.data_file = datafile

        self.mask_file = MaskFile(datafile)

        self.scene_event_filter = GraphicsItemEventFilter(parent, self)
        image_display.AddEventFilter(self.scene_event_filter)

        self.drawPath = self.drawPathItem.path()
        self.drawPathItem.setPath(self.drawPath)
        self.drawPathItem.setZValue(10)

        self.DrawCursor = QtWidgets.QGraphicsPathItem(parent)
        self.DrawCursor.setPos(10, 10)
        self.DrawCursor.setZValue(10)
        self.DrawCursor.setVisible(False)
        self.UpdateDrawCursorSize()

        self.button = QtWidgets.QPushButton()
        self.button.setCheckable(True)
        self.button.setIcon(qta.icon("fa.paint-brush"))
        self.button.setToolTip("add/edit mask for current frame")
        self.button.clicked.connect(self.ToggleInterfaceEvent)
        self.window.layoutButtons.addWidget(self.button)

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

        self.UpdateCounter()

        # place tick marks for already present masks
        for item in self.mask_file.get_mask_frames():
            BroadCastEvent(self.modules, "MarkerPointsAdded", item.image.sort_index)

        self.changeOpacity(0.5)

    def UpdateCounter(self):
        # remove all counter
        for counter in self.counter:
            self.view.scene.removeItem(self.counter[counter])

        # create new ones
        type_list = self.mask_file.get_mask_type_list()
        self.counter = {index+1: MyCounter2(self.parent_hud, self, type, index+1) for index, type in enumerate(type_list)}
        self.counter[-1] = MyCounter2(self.parent_hud, self, None, len(self.counter)+1)
        self.counter[0] = MyCounter2(self.parent_hud, self, self.mask_file.table_mask(name="delete", color="#000000", index=0), 0)

        if len(list(self.counter.keys())):
            self.active_draw_type = self.counter[list(self.counter.keys())[0]].type
            self.active_draw_type_index = 0
        else:
            self.active_draw_type = None
            self.active_draw_type_index = None

        self.MaskDisplay.UpdateColormap(type_list)

        for key in self.counter:
            self.counter[key].setVisible(not self.hidden)

    def DatabaseSaved(self):
        # get old and new mask path
        old_path = self.mask_file.get_mask_path()
        new_path = os.path.splitext(self.data_file.database_filename)[0]+"_mask"
        # get all the masks
        masks = self.mask_file.table_mask.select()
        # create target folder if it doesn't exist and if we have masks
        if not os.path.exists(new_path) and masks.count():
            os.mkdir(new_path)
        # iterate over all masks and copy them to the new folder
        for mask in masks:
            import shutil
            shutil.copy(os.path.join(old_path, mask.filename), os.path.join(new_path, mask.filename))
        # change mask path in database meta entry
        mask_path_entry = self.data_file.table_meta.get(key="mask_path")
        mask_path_entry.value = os.path.relpath(new_path)
        mask_path_entry.save()
        # set the new path in the database class
        self.mask_file.mask_path = new_path

    def LoadImageEvent(self, filename, framenumber):
        self.frame_number = framenumber
        image = self.data_file.image
        image_frame = self.data_file.image.frame
        mask_entry = self.mask_file.get_mask()

        mask_path = self.mask_file.get_mask_path()

        if mask_entry:
            self.current_maskname = os.path.join(mask_path, mask_entry.filename)
            self.LoadMask(os.path.join(mask_path, mask_entry.filename))
        else:
            number = "_%03d" % image_frame
            basename, ext = os.path.splitext(image.filename)
            self.current_maskname = os.path.join(mask_path, basename + "_" + ext[1:] + number +"_mask.png")
            self.LoadMask(None)

    def ReloadMask(self):
        mask_entry = self.mask_file.get_mask()
        mask_path = self.mask_file.get_mask_path()
        if mask_entry:
            self.current_maskname = os.path.join(mask_path, mask_entry.filename)
            self.LoadMask(self.current_maskname)

    def LoadMask(self, maskname):
        mask_valid = False
        if maskname and os.path.exists(maskname):
            try:
                self.image_mask_full = Image.open(maskname)
                mask_valid = True
            except:
                mask_valid = False
        self.MaskEmpty = False
        if not mask_valid:
            self.image_mask_full = None
            self.MaskEmpty = True
        self.MaskUnsaved = False
        if self.active:
            self.SetActiveDrawType(self.active_draw_type.index)

        if self.image_mask_full:
            self.MaskDisplay.SetImage(self.image_mask_full)
            self.MaskDisplay.setOpacity(self.mask_opacity)
        else:
            self.MaskDisplay.setOpacity(0)

        # reset mask display
        self.drawPath = QtGui.QPainterPath()
        self.drawPathItem.setPath(self.drawPath)

    def AddEmptyMask(self):
        self.image_mask_full = Image.new('L', (self.ImageDisplay.image.shape[1], self.ImageDisplay.image.shape[0]))
        self.MaskDisplay.SetImage(self.image_mask_full)
        self.MaskDisplay.setOpacity(self.mask_opacity)

    def UpdateDrawCursorSize(self):
        if self.active_draw_type is None:
            return
        color = QtGui.QColor(*HTMLColorToRGB(self.active_draw_type.color))
        pen = QtGui.QPen(color, self.DrawCursorSize)
        pen.setCapStyle(32)
        self.drawPathItem.setPen(pen)
        draw_cursor_path = QtGui.QPainterPath()
        draw_cursor_path.addEllipse(-self.DrawCursorSize * 0.5, -self.DrawCursorSize * 0.5, self.DrawCursorSize,
                                    self.DrawCursorSize)

        self.DrawCursor.setPen(QtGui.QPen(color))
        self.DrawCursor.setPath(draw_cursor_path)

    def save(self):
        if self.MaskUnsaved:
            mask_entry = self.mask_file.get_mask()
            if mask_entry is None:
                mask_entry = self.mask_file.add_mask()
            fpath,fname = os.path.split(self.current_maskname)
            mask_entry.filename = fname
            mask_entry.save()
            self.MaskDisplay.save(self.current_maskname)
            print(self.current_maskname + " saved")
            self.MaskUnsaved = False

    def RedrawMask(self):
        self.MaskDisplay.UpdateImage()
        self.drawPath = QtGui.QPainterPath()
        self.drawPathItem.setPath(self.drawPath)
        self.MaskChanged = False

    def setActiveModule(self, active, first_time=False):
        self.scene_event_filter.active = active
        self.active = active
        self.DrawCursor.setVisible(active)
        if active:
            self.counter[self.active_draw_type_index].SetToActiveColor()
        else:
            self.counter[self.active_draw_type_index].SetToInactiveColor()
        return True

    def changeOpacity(self, value):
        self.mask_opacity += value
        if self.mask_opacity >= 1:
            self.mask_opacity = 1
        if self.mask_opacity < 0:
            self.mask_opacity = 0
        self.MaskDisplay.setOpacity(self.mask_opacity)

    def SetActiveDrawType(self, new_index):
        if new_index >= len(self.counter)-1:
            return
        if self.active_draw_type_index is not None:
            self.counter[self.active_draw_type_index].SetToInactiveColor()
        self.active_draw_type = self.counter[new_index].type
        self.active_draw_type_index = new_index
        self.counter[self.active_draw_type_index].SetToActiveColor()

        self.RedrawMask()
        self.UpdateDrawCursorSize()

    def PickColor(self):
        for index, draw_type in enumerate(self.mask_file.get_mask_type_list()):
            if draw_type.index == self.color_under_cursor:
                self.SetActiveDrawType(index+1)
                return
        self.SetActiveDrawType(0)

    def changeCursorSize(self, value):
        self.DrawCursorSize += value
        if self.DrawCursorSize < 1:
            self.DrawCursorSize = 1
        self.UpdateDrawCursorSize()
        if self.MaskChanged:
            self.RedrawMask()

    def DrawLine(self, start_x, end_x, start_y, end_y):
        self.drawPath.moveTo(start_x, start_y)
        self.drawPath.lineTo(end_x, end_y)
        self.drawPathItem.setPath(self.drawPath)

        self.MaskDisplay.DrawLine(start_x, end_x, start_y, end_y, self.DrawCursorSize, self.active_draw_type)
        self.MaskChanged = True
        self.MaskUnsaved = True
        if self.config.auto_mask_update:
            self.RedrawMask()
        if self.MaskEmpty:
            self.MaskEmpty = False
            BroadCastEvent(self.modules, "MaskAdded")

    def sceneEventFilter(self, event):
        if event.type() == 156 and event.button() == 1:  # Left Mouse ButtonPress
            # if no mask has been created, create one for painting
            if self.image_mask_full is None:
                self.AddEmptyMask()
            self.last_x = event.pos().x()
            self.last_y = event.pos().y()
            self.DrawLine(self.last_x, self.last_x + 0.00001, self.last_y, self.last_y)
            return True
        if event.type() == 155:  # Mouse Move
            self.DrawCursor.setPos(event.pos())
            pos_x = event.pos().x()
            pos_y = event.pos().y()
            self.DrawLine(pos_x, self.last_x, pos_y, self.last_y)
            self.last_x = pos_x
            self.last_y = pos_y
            return True
        if event.type() == 161:  # Mouse Hover
            self.DrawCursor.setPos(event.pos())
            if self.image_mask_full is None:
                self.color_under_cursor = 0
            else:
                color = self.MaskDisplay.GetColor(event.pos().x(), event.pos().y())
                if color is not None:
                    self.color_under_cursor = color
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
        for counter in self.counter:
            self.counter[counter].setVisible(self.hidden)
        self.hidden = not self.hidden
            
    def loadLast(self):
        self.LoadMask(self.last_maskname)
        self.MaskUnsaved = True
        self.RedrawMask()

    def closeEvent(self, event):
        if self.mask_edit_window:
            self.mask_edit_window.close()

    def canLoadLast(self):
        return self.last_maskname is not None

    @staticmethod
    def file():
        return __file__

    @staticmethod
    def can_create_module(config):
        return len(config.draw_types) > 0
