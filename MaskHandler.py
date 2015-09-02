from __future__ import division
import os

try:
    from PyQt5 import QtGui, QtCore
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except ImportError:
    from PyQt4 import QtGui, QtCore
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

import numpy as np

from PIL import Image, ImageDraw
import ImageQt
from qimage2ndarray import array2qimage

from Tools import GraphicsItemEventFilter


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
        self.colormap = [QColor(i, i, i).rgba() for i in range(256)]

    def UpdatePixmapCount(self):
        # Create new subimages if needed
        for i in range(len(self.pixMapItems), self.number_of_imagesX * self.number_of_imagesY):
            self.images.append(None)
            self.DrawImages.append(None)
            self.qimages.append(None)
            if i == 0:
                new_pixmap = QGraphicsPixmapItem(self.origin)
            else:
                new_pixmap = QGraphicsPixmapItem(self.origin)
            self.pixMapItems.append(new_pixmap)
            new_pixmap.setOpacity(self.opacity)
        # Hide images which are not needed
        for i in range(self.number_of_imagesX * self.number_of_imagesY, len(self.pixMapItems)):
            im = np.zeros((1, 1, 1))
            self.pixMapItems[i].setPixmap(QPixmap(array2qimage(im)))
            self.pixMapItems[i].setOffset(0, 0)

    def SetImage(self, image):
        for drawtype in self.config.draw_types:
            self.colormap[drawtype[0]] = QColor(*drawtype[1]).rgba()
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
            qimage = QImage(self.qimages[i])
            qimage.setColorTable(self.colormap)
            pixmap = QPixmap(qimage)
            self.pixMapItems[i].setPixmap(pixmap)

    def DrawLine(self, x1, x2, y1, y2, size, line_type):
        for y in range(self.number_of_imagesY):
            for x in range(self.number_of_imagesX):
                i = y * self.number_of_imagesX + x
                if x * self.max_image_size < x1 < (x + 1) * self.max_image_size or x * self.max_image_size < x2 < (
                            x + 1) * self.max_image_size:
                    if y * self.max_image_size < y1 < (y + 1) * self.max_image_size or y * self.max_image_size < y2 < (
                                y + 1) * self.max_image_size:
                        draw = self.DrawImages[i]
                        draw.line((x1 - x * self.max_image_size, y1 - y * self.max_image_size, x2 - x * self.max_image_size,
                                   y2 - y * self.max_image_size), fill=self.config.draw_types[line_type][0], width=size + 1)
                        draw.ellipse((x1 - x * self.max_image_size - size // 2, y1 - y * self.max_image_size - size // 2,
                                      x1 - x * self.max_image_size + size // 2, y1 - y * self.max_image_size + size // 2),
                                     fill=self.config.draw_types[line_type][0])
        draw = ImageDraw.Draw(self.full_image)
        draw.line((x1, y1, x2, y2), fill=self.config.draw_types[line_type][0], width=size + 1)
        draw.ellipse((x1 - size // 2, y1 - size // 2, x1 + size // 2, y1 + size // 2), fill=self.config.draw_types[line_type][0])

    def GetColor(self, x1, y1):
        if 0 < x1 < self.full_image.size[0] and 0 < y1 < self.full_image.size[1]:
            return self.full_image.getpixel((x1, y1))
        return None

    def setOpacity(self, opacity):
        self.opacity = opacity
        print(self.opacity)
        for pixmap in self.pixMapItems:
            pixmap.setOpacity(opacity)

    def save(self, filename):
        lut = np.zeros(3 * 256, np.uint8)
        for draw_type in self.config.draw_types:
            index = draw_type[0]
            lut[index * 3:(index + 1) * 3] = draw_type[1]
        self.full_image.putpalette(lut)
        self.full_image.save(filename)


class MyCounter2(QGraphicsRectItem):
    def __init__(self, parent, mask_handler, point_type):
        QGraphicsRectItem.__init__(self, parent)
        self.parent = parent
        self.mask_handler = mask_handler
        self.type = point_type
        self.count = 0
        self.setCursor(QCursor(QtCore.Qt.ArrowCursor))

        self.setAcceptHoverEvents(True)
        self.active = False

        self.font = QFont()
        self.font.setPointSize(14)

        self.label_text = "%d: Color %s" % (point_type + 1, chr(ord('A') + point_type))
        if len(self.mask_handler.config.draw_types[self.type]) == 3:
            self.label_text = self.mask_handler.config.draw_types[self.type][2]

        self.text = QGraphicsSimpleTextItem(self)
        self.text.setText(self.label_text)
        self.text.setFont(self.font)
        self.text.setBrush(QBrush(QColor(*self.mask_handler.config.draw_types[self.type][1])))
        self.text.setZValue(10)

        self.setBrush(QBrush(QColor(0, 0, 0, 128)))
        self.setPos(-110, 10 + 25 * self.type)
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
        self.setPos(-rect.width() - 5, 10 + 25 * self.type)

    def SetToActiveColor(self):
        self.active = True
        self.setBrush(QBrush(QColor(255, 255, 255, 128)))

    def SetToInactiveColor(self):
        self.active = False
        self.setBrush(QBrush(QColor(0, 0, 0, 128)))

    def hoverEnterEvent(self, event):
        if self.active is False:
            self.setBrush(QBrush(QColor(128, 128, 128, 128)))

    def hoverLeaveEvent(self, event):
        if self.active is False:
            self.setBrush(QBrush(QColor(0, 0, 0, 128)))

    def mousePressEvent(self, event):
        if event.button() == 1:
            if not self.mask_handler.active:
                for module in self.mask_handler.modules:
                    if module != self.mask_handler:
                        module.setActive(False)
                self.mask_handler.setActive(True)
            self.mask_handler.SetActiveDrawType(self.type)


class MaskHandler:
    def __init__(self, parent, parent_hud, view, image_display, config, modules):
        self.view = view
        self.parent_hud = parent_hud
        self.ImageDisplay = image_display
        self.config = config
        self.modules = modules
        self.MaskDisplay = BigPaintableImageDisplay(parent, config=config)
        self.DrawCursorSize = 10
        self.drawPathItem = QGraphicsPathItem(parent)
        self.drawPathItem.setBrush(QBrush(QColor(255, 255, 255)))

        self.active_draw_type = 1

        self.mask_opacity = 0
        self.current_maskname = None
        self.last_maskname = None
        self.color_under_cursor = None
        self.image_mask_full = None
        self.last_x = None
        self.last_y = None

        self.scene_event_filter = GraphicsItemEventFilter(parent, self)
        image_display.AddEventFilter(self.scene_event_filter)

        self.drawPath = self.drawPathItem.path()
        self.drawPathItem.setPath(self.drawPath)
        self.drawPathItem.setZValue(10)

        self.DrawCursor = QGraphicsPathItem(parent)
        self.DrawCursor.setPos(10, 10)
        self.DrawCursor.setZValue(10)
        self.DrawCursor.setVisible(False)
        self.UpdateDrawCursorSize()

        self.DrawMode = False
        self.MaskChanged = False
        self.MaskUnsaved = False
        self.active = False

        self.counter = []
        self.UpdateCounter()

    def UpdateCounter(self):
        for counter in self.counter:
            self.view.scene.removeItem(counter)
        self.counter = [MyCounter2(self.parent_hud, self, i) for i in range(len(self.config.draw_types))]

    def LoadImageEvent(self, filename, frame_number):
        if self.current_maskname is not None:
            self.last_maskname = self.current_maskname
        self.MaskChanged = False
        self.drawPath = QPainterPath()
        self.drawPathItem.setPath(self.drawPath)
        base_filename = os.path.splitext(filename)[0]
        self.current_maskname = os.path.join(self.config.outputpath, base_filename + self.config.maskname_tag)
        self.LoadMask(self.current_maskname)

    def LoadMask(self, maskname):
        mask_valid = False
        print("Loading " + maskname)
        if os.path.exists(maskname):
            print("Load Mask")
            try:
                self.image_mask_full = Image.open(maskname)
                mask_valid = True
            except:
                mask_valid = False
                print("ERROR: Can't read mask file")
            print("...done")
        if not mask_valid:
            self.image_mask_full = Image.new('L', (self.ImageDisplay.image.shape[1], self.ImageDisplay.image.shape[0]))
        self.MaskUnsaved = False
        if self.image_mask_full.mode == 'P':
            a = np.array(map(ord, self.image_mask_full.palette.getdata()[1])).reshape(256, 3)
            new_draw_types = []
            for index, color in enumerate(a):
                if index == 0 or sum(color) != 0:
                    new_draw_types.append([index, color])
            self.config.draw_types = new_draw_types
            self.UpdateCounter()
        if self.active_draw_type >= len(self.config.draw_types):
            self.active_draw_type = 0
        if self.active:
            self.SetActiveDrawType(self.active_draw_type)

        self.MaskDisplay.SetImage(self.image_mask_full)

    def UpdateDrawCursorSize(self):
        pen = QPen(QColor(*self.config.draw_types[self.active_draw_type][1]), self.DrawCursorSize)
        pen.setCapStyle(32)
        self.drawPathItem.setPen(pen)
        draw_cursor_path = QPainterPath()
        draw_cursor_path.addEllipse(-self.DrawCursorSize * 0.5, -self.DrawCursorSize * 0.5, self.DrawCursorSize,
                                    self.DrawCursorSize)

        self.DrawCursor.setPen(QPen(QColor(*self.config.draw_types[self.active_draw_type][1])))
        self.DrawCursor.setPath(draw_cursor_path)

    def save(self):
        if self.MaskUnsaved:
            self.MaskDisplay.save(self.current_maskname)
            print(self.current_maskname + " saved")
            self.MaskUnsaved = False

    def RedrawMask(self):
        self.MaskDisplay.UpdateImage()
        self.drawPath = QPainterPath()
        self.drawPathItem.setPath(self.drawPath)
        self.MaskChanged = False

    def setActive(self, active, first_time=False):
        self.scene_event_filter.active = active
        self.active = active
        self.DrawCursor.setVisible(active)
        if active:
            self.view.setCursor(QCursor(QtCore.Qt.BlankCursor))
            self.counter[self.active_draw_type].SetToActiveColor()
        else:
            self.counter[self.active_draw_type].SetToInactiveColor()
        if first_time:
            self.changeOpacity(0.5)
        return True

    def changeOpacity(self, value):
        self.mask_opacity += value
        if self.mask_opacity >= 1:
            self.mask_opacity = 1
        if self.mask_opacity < 0:
            self.mask_opacity = 0
        self.MaskDisplay.setOpacity(self.mask_opacity)

    def SetActiveDrawType(self, value):
        self.counter[self.active_draw_type].SetToInactiveColor()
        self.active_draw_type = value
        self.counter[self.active_draw_type].SetToActiveColor()
        self.RedrawMask()
        print("Changed Draw type", self.active_draw_type)
        self.UpdateDrawCursorSize()

    def PickColor(self):
        global draw_types
        for index, draw_type in enumerate(draw_types):
            if draw_type[0] == self.color_under_cursor:
                self.SetActiveDrawType(index)
                break

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

    def sceneEventFilter(self, event):
        if event.type() == 156 and event.button() == 1:  # Left Mouse ButtonPress
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
            color = self.MaskDisplay.GetColor(event.pos().x(), event.pos().y())
            if color is not None:
                self.color_under_cursor = color
        return False

    def keyPressEvent(self, event):
        numberkey = event.key() - 49
        # @key ---- Painting ----
        if self.active and 0 <= numberkey < len(self.config.draw_types) and event.modifiers() != Qt.KeypadModifier:
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

    def loadLast(self):
        self.LoadMask(self.last_maskname)
        self.MaskUnsaved = True
        self.RedrawMask()

    def canLoadLast(self):
        return self.last_maskname is not None

    @staticmethod
    def file():
        return __file__

    @staticmethod
    def can_create_module(config):
        return len(config.draw_types) > 0
