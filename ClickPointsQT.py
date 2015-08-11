from __future__ import division
import sys
import os
import re

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "mediahandler"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "qextendedgraphicsview"))
try:
    from PyQt5 import QtGui, QtCore
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except ImportError:
    from PyQt4 import QtGui, QtCore
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

from QExtendedGraphicsView import QExtendedGraphicsView

import numpy as np
import os
from os.path import join

from PIL import Image, ImageDraw, ImageQt
from qimage2ndarray import array2qimage, rgb_view

from mediahandler import MediaHandler
import uuid

# parameter and path setup
# default settings
use_filedia = True
auto_mask_update = True
tracking = False
srcpath = None
filename = None
outputpath = None
logname_tag = '_pos.txt'
maskname_tag = '_mask.png'

# marker types
types = [["juveniles", [255, 0., 0], 0],
         ["adults", [0, .8 * 255, 0], 0],
         ["border", [0.8 * 255, 0.8 * 255, 0], 1],
         ["bgroup", [0.5 * 255, 0.5 * 255, 0], 0],
         ["horizon", [0.0, 0, 0.8 * 255], 0],
         ["iceberg", [0.0, 0.8 * 255, 0.8 * 255], 0]]
# painter types
draw_types = [[0, (0, 0, 0)],
              [255, [255, 255, 255]],
              [124, [124, 124, 255]]]

# possible addons
addons = []

# overwrite defaults with personal cfg if available
config_filename = 'cp_cfg.txt'
if len(sys.argv) >= 2:
    config_filename = sys.argv[1]
if os.path.exists(config_filename):
    with open(config_filename) as f:
        code = compile(f.read(), config_filename, 'exec')
        exec(code)

# parameter pre processing
if srcpath is None:
    srcpath = os.getcwd()
if outputpath is not None and not os.path.exists(outputpath):
    os.makedirs(outputpath)  # recursive path creation

max_image_size = 2 ** 12

modules = []

w = 1.
b = 7
r2 = 10
path1 = QPainterPath()
path1.addRect(-r2, -w, b, w * 2)
path1.addRect(r2, -w, -b, w * 2)
path1.addRect(-w, -r2, w * 2, b)
path1.addRect(-w, r2, w * 2, -b)
path1.addEllipse(-r2, -r2, r2 * 2, r2 * 2)
path1.addEllipse(-r2, -r2, r2 * 2, r2 * 2)
w = 2
b = 3
o = 3
path2 = QPainterPath()
path2.addRect(-b - o, -w * 0.5, b, w)
path2.addRect(+o, -w * 0.5, b, w)
path2.addRect(-w * 0.5, -b - o, w, b)
path2.addRect(-w * 0.5, +o, w, b)
r3 = 5
path3 = QPainterPath()
path3.addEllipse(-0.5 * r3, -0.5 * r3, r3, r3)  # addRect(-0.5,-0.5, 1, 1)
point_display_types = [path1, path2, path3]
point_display_type = 0


def disk(radius):
    disk_array = np.zeros((radius * 2 + 1, radius * 2 + 1))
    for x in range(radius * 2 + 1):
        for y in range(radius * 2 + 1):
            if np.sqrt((radius - x) ** 2 + (radius - y) ** 2) < radius:
                disk_array[y, x] = True
    return disk_array


def PosToArray(pos):
    return np.array([pos.x(), pos.y()])


def Serialize(value):
    if type(value) == type(""):
        return "'"+value+"'"
    if type(value) != type([]):
        return str(value)
    elements = map(Serialize, value)
    return "["+",".join(elements)+"]"


def DeSerialize(string):
    array = []
    matches = re.findall(r"\[\s*\'([^']*?)\',\s*\[\s*([\d.]*)\s*,\s*([\d.]*)\s*,\s*([\d.]*)\s*\]\s*,\s*([\d.]*)\s*\]", string)
    for match in matches:
        array.append([match[0], map(float,match[1:4]), int(match[4])])
    return array


class BigImageDisplay:
    def __init__(self, origin, window):
        self.number_of_imagesX = 0
        self.number_of_imagesY = 0
        self.pixMapItems = []
        self.QImages = []
        self.QImageViews = []
        self.ImageSlices = []
        self.origin = origin
        self.window = window

        self.image = None
        self.hist = None
        self.conversion = None

        self.preview_pixMapItem = QGraphicsPixmapItem(self.origin)
        self.preview_pixMapItem.setZValue(10)
        self.preview_slice = None
        self.preview_qimage = None
        self.preview_qimageView = None

        self.gamma = 1
        self.min = 0
        self.max = 255

        self.eventFilters = []

    def AddEventFilter(self, event_filter):
        self.eventFilters.append(event_filter)
        for pixmap in self.pixMapItems:
            pixmap.installSceneEventFilter(event_filter)

    def UpdatePixmapCount(self):
        # Create new subimages if needed
        for i in range(len(self.pixMapItems), self.number_of_imagesX * self.number_of_imagesY):
            if i == 0:
                new_pixmap = QGraphicsPixmapItem(self.origin)
            else:
                new_pixmap = QGraphicsPixmapItem(self.pixMapItems[0])
            self.pixMapItems.append(new_pixmap)
            self.ImageSlices.append(None)
            self.QImages.append(None)
            self.QImageViews.append(None)

            new_pixmap.setAcceptHoverEvents(True)

            for event_filter in self.eventFilters:
                new_pixmap.installSceneEventFilter(event_filter)

        # Hide images which are not needed
        for i in range(self.number_of_imagesX * self.number_of_imagesY, len(self.pixMapItems)):
            im = np.zeros((1, 1, 1))
            self.pixMapItems[i].setPixmap(QPixmap(array2qimage(im)))
            self.pixMapItems[i].setOffset(0, 0)

    def SetImage(self, image):
        if len(image.shape) == 2:
            image = image.reshape((image.shape[0], image.shape[1], 1))
        self.number_of_imagesX = int(np.ceil(image.shape[1] / max_image_size))
        self.number_of_imagesY = int(np.ceil(image.shape[0] / max_image_size))
        self.UpdatePixmapCount()
        self.image = image

        for y in range(self.number_of_imagesY):
            for x in range(self.number_of_imagesX):
                i = y * self.number_of_imagesX + x
                start_x = x * max_image_size
                start_y = y * max_image_size
                end_x = min([(x + 1) * max_image_size, image.shape[1]])
                end_y = min([(y + 1) * max_image_size, image.shape[0]])
                self.ImageSlices[i] = image[start_y:end_y, start_x:end_x, :]
                self.QImages[i] = array2qimage(image[start_y:end_y, start_x:end_x, :])
                self.QImageViews[i] = rgb_view(self.QImages[i])
                self.pixMapItems[i].setPixmap(QPixmap(self.QImages[i]))
                self.pixMapItems[i].setOffset(start_x, start_y)
        self.preview_pixMapItem.setPixmap(QPixmap())
        self.preview_slice = None

    def PreviewRect(self):
        start_x, start_y, end_x, end_y = self.window.view.GetExtend()
        if start_x < 0: start_x = 0
        if start_y < 0: start_y = 0
        if end_x > self.image.shape[1]: end_x = self.image.shape[1]
        if end_y > self.image.shape[0]: end_y = self.image.shape[0]
        if end_x > start_x + max_image_size: end_x = start_x + max_image_size
        if end_y > start_y + max_image_size: end_y = start_y + max_image_size
        self.preview_slice = self.image[start_y:end_y, start_x:end_x, :]
        self.preview_qimage = array2qimage(self.image[start_y:end_y, start_x:end_x, :])
        self.preview_qimageView = rgb_view(self.preview_qimage)
        self.preview_pixMapItem.setPixmap(QPixmap(self.preview_qimage))
        self.preview_pixMapItem.setOffset(start_x, start_y)
        self.preview_pixMapItem.setParentItem(self.pixMapItems[0])
        self.hist = np.histogram(self.preview_slice.flatten(), bins=range(0, 256), normed=True)

    def ChangeGamma(self, value):
        self.gamma = value
        conversion = np.power(np.arange(0, 256) / 256., value) * 256
        for i in range(self.number_of_imagesX * self.number_of_imagesY):
            self.QImageViews[i][:, :, :] = conversion[self.ImageSlices[i]]
            self.pixMapItems[i].setPixmap(QPixmap(self.QImages[i]))
        self.window.view.scene.update()

    def Change(self, gamma=None, min_brightness=None, max_brightness=None):
        if self.preview_slice is None:
            self.PreviewRect()
        if gamma is not None:
            if gamma > 1:
                gamma = 1. / (1 - (gamma - 1) + 0.00001)
            self.gamma = gamma
        if min_brightness is not None:
            self.min = int(min_brightness)
        if max_brightness is not None:
            self.max = int(max_brightness)
        color_range = self.max - self.min
        conversion = np.arange(0, 256)
        conversion[:self.min] = 0
        conversion[self.min:self.max] = np.power(np.arange(0, color_range) / color_range, self.gamma) * 256
        conversion[self.max:] = 255
        for i in range(self.number_of_imagesX * self.number_of_imagesY):
            self.preview_qimageView[:, :, :] = conversion[self.preview_slice]
            self.preview_pixMapItem.setPixmap(QPixmap(self.preview_qimage))
        self.window.view.scene.update()
        self.conversion = conversion


class BigPaintableImageDisplay:
    def __init__(self, origin):
        self.number_of_imagesX = 0
        self.number_of_imagesY = 0
        self.pixMapItems = []
        self.origin = origin
        self.full_image = None
        self.images = []
        self.DrawImages = []
        self.qimages = []

        self.opacity = 0
        self.colormap = [QColor(i, i, i).rgba() for i in range(256)]
        for drawtype in draw_types:
            self.colormap[drawtype[0]] = QColor(*drawtype[1]).rgba()

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
        self.number_of_imagesX = int(np.ceil(image.size[0] / max_image_size))
        self.number_of_imagesY = int(np.ceil(image.size[1] / max_image_size))
        self.UpdatePixmapCount()
        self.full_image = image

        for y in range(self.number_of_imagesY):
            for x in range(self.number_of_imagesX):
                i = y * self.number_of_imagesX + x
                start_x = x * max_image_size
                start_y = y * max_image_size
                end_x = min([(x + 1) * max_image_size, image.size[0]])
                end_y = min([(y + 1) * max_image_size, image.size[1]])

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
                if x * max_image_size < x1 < (x + 1) * max_image_size or x * max_image_size < x2 < (
                            x + 1) * max_image_size:
                    if y * max_image_size < y1 < (y + 1) * max_image_size or y * max_image_size < y2 < (
                                y + 1) * max_image_size:
                        draw = self.DrawImages[i]
                        draw.line((x1 - x * max_image_size, y1 - y * max_image_size, x2 - x * max_image_size,
                                   y2 - y * max_image_size), fill=draw_types[line_type][0], width=size + 1)
                        draw.ellipse((x1 - x * max_image_size - size // 2, y1 - y * max_image_size - size // 2,
                                      x1 - x * max_image_size + size // 2, y1 - y * max_image_size + size // 2),
                                     fill=draw_types[line_type][0])
        draw = ImageDraw.Draw(self.full_image)
        draw.line((x1, y1, x2, y2), fill=draw_types[line_type][0], width=size + 1)
        draw.ellipse((x1 - size // 2, y1 - size // 2, x1 + size // 2, y1 + size // 2), fill=draw_types[line_type][0])

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
        self.full_image.save(filename)


class MyMarkerItem(QGraphicsPathItem):
    def __init__(self, x, y, parent, marker_handler, point_type, start_id=None, partner_id=None):
        global types, point_display_type

        QGraphicsPathItem.__init__(self, parent)
        self.parent = parent
        self.type = point_type
        self.marker_handler = marker_handler

        self.scale_value = None

        self.UpdatePath()

        if len(self.marker_handler.counter):
            self.marker_handler.counter[self.type].AddCount(1)

        self.setBrush(QBrush(QColor(*types[self.type][1])))
        self.setPen(QPen(QColor(0, 0, 0, 0)))

        self.setPos(x, y)
        self.setZValue(20)
        self.imgItem = parent
        self.dragged = False

        if start_id is not None:
            self.id = start_id
        else:
            self.id = uuid.uuid4().hex

        self.UseCrosshair = True

        self.partner = None
        self.rectObj = None
        self.partner_id = partner_id
        if types[self.type][2] == 1 or types[self.type][2] == 2:
            if self.partner_id is not None:
                for point in self.marker_handler.points:
                    if point.id == self.partner_id:
                        self.ConnectToPartner(point)
                        break
            if self.partner_id is None:
                possible_partners = []
                for point in self.marker_handler.points:
                    if point.type == self.type and point.partner is None:
                        possible_partners.append(
                            [point, np.linalg.norm(PosToArray(self.pos()) - PosToArray(point.pos()))])
                if len(possible_partners):
                    possible_partners.sort(key=lambda x: x[1])
                    self.ConnectToPartner(possible_partners[0][0])
        if self.partner:
            if types[self.type][2] == 1:
                self.rectObj = QGraphicsRectItem(self.imgItem)
                self.rectObj.setPen(QPen(QColor(*types[self.type][1]), 2))
                self.UpdateRect()
            if types[self.type][2] == 2:
                self.rectObj = QGraphicsLineItem(self.imgItem)
                self.rectObj.setPen(QPen(QColor(*types[self.type][1]), 2))
                self.UpdateRect()

        self.marker_handler.PointsUnsaved = True
        self.setAcceptHoverEvents(True)
        if tracking is True:
            self.track = {self.marker_handler.frame_number: [x, y, point_type]}
            self.pathItem = QGraphicsPathItem(self.imgItem)
            self.path = QPainterPath()
            self.path.moveTo(x, y)
        self.active = True

    def ConnectToPartner(self, point):
        self.partner_id = point.id
        point.partner_id = self.id
        self.partner = point
        point.partner = self
        self.UseCrosshair = False
        self.partner.UseCrosshair = False

    def setInvalidNewPoint(self):
        self.addPoint(self.pos().x(), self.pos().y(), -1)

    def UpdateLine(self):
        self.track[self.marker_handler.frame_number][:2] = [self.pos().x(), self.pos().y()]
        self.path = QPainterPath()
        frames = sorted(self.track.keys())
        last_active = False
        circle_width = self.scale_value * 10
        for frame in frames:
            x, y, marker_type = self.track[frame]
            if marker_type != -1:
                if last_active:
                    self.path.lineTo(x, y)
                else:
                    self.path.moveTo(x, y)
                if frame != self.marker_handler.frame_number:
                    self.path.addEllipse(x - .5 * circle_width, y - .5 * circle_width, circle_width, circle_width)
                self.path.moveTo(x, y)
            last_active = marker_type != -1
        self.pathItem.setPath(self.path)

    def SetTrackActive(self, active):
        if active is False:
            self.active = False
            self.setOpacity(0.5)
            self.pathItem.setOpacity(0.25)
            self.track[self.marker_handler.frame_number][2] = -1
        else:
            self.active = True
            self.setOpacity(1)
            self.pathItem.setOpacity(0.5)
            self.track[self.marker_handler.frame_number][2] = self.type

    def addPoint(self, x, y, marker_type):
        if marker_type == -1:
            x, y = self.pos().x(), self.pos().y()
        self.setPos(x, y)
        self.track[self.marker_handler.frame_number] = [x, y, marker_type]
        if marker_type == -1:
            self.SetTrackActive(False)
        else:
            self.SetTrackActive(True)
            self.setOpacity(1)
        self.UpdateLine()

    def OnRemove(self):
        self.marker_handler.counter[self.type].AddCount(-1)
        if self.partner and self.partner.rectObj:
            self.marker_handler.view.scene.removeItem(self.partner.rectObj)
            self.partner.rectObj = None
            self.partner.partner = None
        if self.rectObj:
            self.partner.partner = None
            self.marker_handler.view.scene.removeItem(self.rectObj)

    def UpdateRect(self):
        x, y = self.pos().x(), self.pos().y()
        x2, y2 = self.partner.pos().x(), self.partner.pos().y()
        if types[self.type][2] == 1:
            self.rectObj.setRect(x, y, x2 - x, y2 - y)
        if types[self.type][2] == 2:
            self.rectObj.setLine(x, y, x2, y2)

    def mousePressEvent(self, event):
        if event.button() == 2:
            if tracking is True:
                self.SetTrackActive(self.active is False)
                self.marker_handler.PointsUnsaved = True  #
                self.UpdateLine()
                valid_frame_found = False
                for frame in self.track:
                    if self.track[frame][2] != -1:
                        valid_frame_found = True
                if not valid_frame_found:
                    self.marker_handler.RemovePoint(self)
            else:
                self.marker_handler.RemovePoint(self)
        if event.button() == 1:
            self.dragged = True
            self.setCursor(QCursor(QtCore.Qt.BlankCursor))
            if self.UseCrosshair:
                self.marker_handler.Crosshair.MoveCrosshair(self.pos().x(), self.pos().y())
                self.marker_handler.Crosshair.Show(self.type)
            pass

    def mouseMoveEvent(self, event):
        if not self.dragged:
            return
        if tracking:
            self.SetTrackActive(True)
        pos = self.parent.mapFromItem(self, event.pos())
        self.setPos(pos.x(), pos.y())
        if tracking:
            self.UpdateLine()
        if self.UseCrosshair:
            self.marker_handler.Crosshair.MoveCrosshair(pos.x(), pos.y())
        if self.partner:
            if self.rectObj:
                self.UpdateRect()
            else:
                self.partner.UpdateRect()
                self.partner.setPos(self.partner.pos())

    def mouseReleaseEvent(self, event):
        if not self.dragged:
            return
        if event.button() == 1:
            self.marker_handler.PointsUnsaved = True
            self.dragged = False
            self.setCursor(QCursor(QtCore.Qt.OpenHandCursor))
            self.marker_handler.Crosshair.Hide()
            pass

    def SetActive(self, active):
        if active:
            self.setAcceptedMouseButtons(Qt.MouseButtons(3))
            self.setCursor(QCursor(QtCore.Qt.OpenHandCursor))
        else:
            self.setAcceptedMouseButtons(Qt.MouseButtons(0))
            self.unsetCursor()

    def UpdatePath(self):
        self.setPath(point_display_types[point_display_type])
        self.SetActive(point_display_type != len(point_display_types) - 1)

    def setScale(self, scale):
        self.scale_value = scale
        if self.rectObj:
            self.rectObj.setPen(QPen(QColor(*types[self.type][1]), 2 * scale))
        if tracking is True:
            self.pathItem.setPen(QPen(QColor(*types[self.type][1]), 2 * scale))
            self.UpdateLine()
        super(QGraphicsPathItem, self).setScale(scale)


class Crosshair:
    def __init__(self, parent, view, image):
        self.parent = parent
        self.view = view
        self.image = image

        self.RGB = np.zeros((101, 101, 3))
        self.Alpha = disk(50) * 255
        self.Image = np.concatenate((self.RGB, self.Alpha[:, :, None]), axis=2)
        self.CrosshairQImage = array2qimage(self.Image)
        self.CrosshairQImageView = rgb_view(self.CrosshairQImage)

        self.Crosshair = QGraphicsPixmapItem(QPixmap(self.CrosshairQImage), self.parent)
        self.CrosshairQImageView[:, :, 0] = 255
        self.Crosshair.setOffset(-50, -50)
        self.Crosshair.setPos(150, 150)
        self.Crosshair.setZValue(30)
        self.Crosshair.setVisible(False)

        self.pathCrosshair = QPainterPath()
        self.pathCrosshair.addEllipse(-50, -50, 100, 100)

        w = 0.333 * 0.5
        b = 40
        r2 = 50
        self.pathCrosshair2 = QPainterPath()
        self.pathCrosshair2.addRect(-r2, -w, b, w * 2)
        self.pathCrosshair2.addRect(r2, -w, -b, w * 2)
        self.pathCrosshair2.addRect(-w, -r2, w * 2, b)
        self.pathCrosshair2.addRect(-w, r2, w * 2, -b)

        self.CrosshairPathItem = QGraphicsPathItem(self.pathCrosshair, self.Crosshair)
        self.CrosshairPathItem2 = QGraphicsPathItem(self.pathCrosshair2, self.Crosshair)

    def MoveCrosshair(self, x, y):
        y = int(y)
        x = int(x)
        self.CrosshairQImageView[:, :, :] = self.SaveSlice(self.image.image,
                                                           [[y - 50, y + 50 + 1], [x - 50, x + 50 + 1], [0, 3]])
        self.Crosshair.setPos(x, y)
        self.Crosshair.setPixmap(QPixmap(self.CrosshairQImage))

    @staticmethod
    def SaveSlice(source, slices):
        shape = []
        slices1 = []
        slices2 = []
        empty = False
        for length, slice_border in zip(source.shape, slices):
            slice_border = map(int, slice_border)
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
        new_slice[slices2[0], slices2[1], slices2[2]] = source[slices1[0], slices1[1], slices1[2]]
        return new_slice

    def Hide(self):
        self.Crosshair.setVisible(False)

    def Show(self, marker_type):
        self.Crosshair.setVisible(True)
        self.CrosshairPathItem2.setPen(QPen(QColor(*types[marker_type][1]), 1))
        self.CrosshairPathItem.setPen(QPen(QColor(*types[marker_type][1]), 3))


class MyCounter(QGraphicsRectItem):
    def __init__(self, parent, window, point_type):
        QGraphicsRectItem.__init__(self, parent)
        self.parent = parent
        self.window = window
        self.type = point_type
        self.count = 0
        self.setCursor(QCursor(QtCore.Qt.ArrowCursor))

        self.setAcceptHoverEvents(True)
        self.active = False

        self.font = QFont()
        self.font.setPointSize(14)

        self.text = QGraphicsSimpleTextItem(self)
        self.text.setText(types[self.type][0] + " %d" % 0)
        self.text.setFont(self.font)
        self.text.setBrush(QBrush(QColor(*types[self.type][1])))
        self.text.setZValue(10)

        self.setBrush(QBrush(QColor(0, 0, 0, 128)))
        self.setPos(10, 10 + 25 * self.type)
        self.setZValue(9)

        count = 0
        for point in self.window.points:
            if point.type == self.type:
                count += 1
        self.AddCount(count)

    def AddCount(self, new_count):
        self.count += new_count
        self.text.setText(types[self.type][0] + " %d" % self.count)
        rect = self.text.boundingRect()
        rect.setX(-5)
        rect.setWidth(rect.width() + 5)
        self.setRect(rect)

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
        global modules
        if event.button() == 1:
            if not self.window.active:
                for module in modules:
                    if module != self.window:
                        module.setActive(False)
                self.window.setActive(True)
            self.window.SetActiveMarkerType(self.type)


class MyCounter2(QGraphicsRectItem):
    def __init__(self, parent, window, point_type):
        QGraphicsRectItem.__init__(self, parent)
        self.parent = parent
        self.window = window
        self.type = point_type
        self.count = 0
        self.setCursor(QCursor(QtCore.Qt.ArrowCursor))

        self.setAcceptHoverEvents(True)
        self.active = False

        self.font = QFont()
        self.font.setPointSize(14)

        self.label_text = "Color %d" % (point_type + 1)
        if len(draw_types[self.type]) == 3:
            self.label_text = draw_types[self.type][2]

        self.text = QGraphicsSimpleTextItem(self)
        self.text.setText(self.label_text)
        self.text.setFont(self.font)
        self.text.setBrush(QBrush(QColor(*draw_types[self.type][1])))
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
            if not self.window.active:
                for module in modules:
                    if module != self.window:
                        module.setActive(False)
                self.window.setActive(True)
            self.window.SetActiveDrawType(self.type)


class HelpText(QGraphicsRectItem):
    def __init__(self, window):
        QGraphicsRectItem.__init__(self, window.view.hud)

        self.setCursor(QCursor(QtCore.Qt.ArrowCursor))

        self.help_text = QGraphicsSimpleTextItem(self)
        self.help_text.setFont(QFont("", 11))
        self.help_text.setPos(0, 10)

        self.setBrush(QBrush(QColor(255, 255, 255, 255 - 32)))
        self.setPos(100, 100)
        self.setZValue(19)

        self.UpdateText()
        BoxGrabber(self)
        self.setVisible(False)

    def ShowHelpText(self):
        if self.isVisible():
            self.setVisible(False)
        else:
            self.setVisible(True)

    def UpdateText(self):
        import re
        text = ""
        with open(__file__) as fp:
            for line in fp.readlines():
                m = re.match(r'\w*# @key (.*)$', line.strip())
                if m:
                    text += m.groups()[0].replace(":", ":\t", 1) + "\n"
        self.help_text.setText(text[:-1])
        rect = self.help_text.boundingRect()
        rect.setX(-5)
        rect.setWidth(rect.width() + 5)
        rect.setHeight(rect.height() + 15)
        self.setRect(rect)

    def mousePressEvent(self, event):
        pass

    def mouseMoveEvent(self, event):
        pass

    def mouseReleaseEvent(self, event):
        pass


class MySlider(QGraphicsRectItem):
    def __init__(self, parent, name="", max_value=100, min_value=0):
        QGraphicsRectItem.__init__(self, parent)

        self.parent = parent
        self.name = name
        self.maxValue = max_value
        self.minValue = min_value
        self.format = "%.2f"

        self.setCursor(QCursor(QtCore.Qt.OpenHandCursor))
        self.setPen(QPen(QColor(255, 255, 255, 0)))

        self.text = QGraphicsSimpleTextItem(self)
        self.text.setFont(QFont("", 11))
        self.text.setPos(0, -23)

        self.sliderMiddel = QGraphicsRectItem(self)
        self.sliderMiddel.setRect(QRectF(0, 0, 100, 1))

        path = QPainterPath()
        path.addEllipse(-5, -5, 10, 10)
        self.slideMarker = QGraphicsPathItem(path, self)
        self.slideMarker.setBrush(QBrush(QColor(255, 0, 0, 255)))

        self.setRect(QRectF(-5, -5, 110, 10))
        self.dragged = False

        self.value = (self.maxValue + self.minValue) * 0.5
        self.setValue(self.value)

    def mousePressEvent(self, event):
        if event.button() == 1:
            self.dragged = True

    def mouseMoveEvent(self, event):
        if self.dragged:
            pos = event.pos()
            x = pos.x()
            if x < 0: x = 0
            if x > 100: x = 100
            self.setValue(x / 100. * self.maxValue + self.minValue)

    def setValue(self, value):
        self.value = value
        self.text.setText(self.name + ": " + self.format % value)
        self.slideMarker.setPos((value - self.minValue) * 100 / self.maxValue, 0)
        self.valueChanged(value)

    def valueChanged(self, value):
        pass

    def mouseReleaseEvent(self, event):
        self.dragged = False


class BoxGrabber(QGraphicsRectItem):
    def __init__(self, parent):
        QGraphicsRectItem.__init__(self, parent)

        self.parent = parent
        self.setCursor(QCursor(QtCore.Qt.OpenHandCursor))
        width = parent.rect().width()
        self.setRect(QRectF(0, 0, width, 10))
        self.setPos(parent.rect().x(), 0)

        self.setBrush(QBrush(QColor(255, 255, 255, 255 - 32)))

        path = QPainterPath()
        path.addRect(QRectF(5, 3, width - 10, 1))
        path.addRect(QRectF(5, 6, width - 10, 1))
        QGraphicsPathItem(path, self)

        self.dragged = False
        self.drag_offset = None

    def mousePressEvent(self, event):
        if event.button() == 1:
            self.dragged = True
            self.drag_offset = self.parent.mapToParent(self.mapToParent(event.pos())) - self.parent.pos()

    def mouseMoveEvent(self, event):
        if self.dragged:
            pos = self.parent.mapToParent(self.mapToParent(event.pos())) - self.drag_offset
            self.parent.setPos(pos.x(), pos.y())

    def mouseReleaseEvent(self, event):
        self.dragged = False


class SliderBox(QGraphicsRectItem):
    def __init__(self, parent, image):
        QGraphicsRectItem.__init__(self, parent)

        self.image = image
        self.setCursor(QCursor(QtCore.Qt.ArrowCursor))

        self.setBrush(QBrush(QColor(255, 255, 255, 255 - 32)))
        self.setPos(100, 100)
        self.setZValue(19)

        self.hist = QGraphicsPathItem(self)
        self.hist.setPen(QPen(QColor(0, 0, 0, 0)))
        self.hist.setBrush(QBrush(QColor(0, 0, 0, 128)))
        self.hist.setPos(0, 110)

        self.conv = QGraphicsPathItem(self)
        self.conv.setPen(QPen(QColor(255, 0, 0, 128), 2))
        self.conv.setBrush(QBrush(QColor(0, 0, 0, 0)))
        self.conv.setPos(0, 110)

        self.sliders = []
        functions = [self.updateGamma, self.updateBrightnes, self.updateContrast]
        min_max = [[0, 2], [0, 255], [0, 255]]
        start = [1, 255, 0]
        formats = ["%.2f", "%d", "%d"]
        for i, name in enumerate(["Gamma", "Max", "Min"]):
            slider = MySlider(self, name, max_value=min_max[i][1], min_value=min_max[i][0])
            slider.format = formats[i]
            slider.setValue(start[i])
            slider.setPos(5, 40 + i * 30)
            slider.valueChanged = functions[i]
            self.sliders.append(slider)

        self.setRect(QRectF(0, 0, 110, 110))
        BoxGrabber(self)
        self.dragged = False

    def updateHist(self, hist):
        histpath = QPainterPath()
        w = 100 / 256.
        for i, h in enumerate(hist[0]):
            histpath.addRect(i * w + 5, 0, w, -h * 100 / max(hist[0]))
        self.hist.setPath(histpath)

    def updateConv(self):
        convpath = QPainterPath()
        w = 100 / 256.
        for i, h in enumerate(self.image.conversion):
            convpath.lineTo(i * w + 5, -h * 98 / 255.)
        self.conv.setPath(convpath)

    def updateGamma(self, value):
        QApplication.setOverrideCursor(QCursor(QtCore.Qt.WaitCursor))
        self.image.Change(gamma=value)
        self.updateConv()
        QApplication.restoreOverrideCursor()

    def updateBrightnes(self, value):
        QApplication.setOverrideCursor(QCursor(QtCore.Qt.WaitCursor))
        self.image.Change(max_brightness=value)
        self.updateConv()
        QApplication.restoreOverrideCursor()

    def updateContrast(self, value):
        QApplication.setOverrideCursor(QCursor(QtCore.Qt.WaitCursor))
        self.image.Change(min_brightness=value)
        self.updateConv()
        QApplication.restoreOverrideCursor()

    def LoadImageEvent(self):
        self.hist.setPath(QPainterPath())
        self.conv.setPath(QPainterPath())

    def mousePressEvent(self, event):
        pass

    def mousePressEvent(self, event):
        pass

    def mousePressEvent(self, event):
        pass


class GraphicsItemEventFilter(QGraphicsItem):
    def __init__(self, parent, command_object):
        super(GraphicsItemEventFilter, self).__init__(parent)
        self.commandObject = command_object
        self.active = False

    def paint(self, *args):
        pass

    def boundingRect(self):
        return QRectF(0, 0, 0, 0)

    def sceneEventFilter(self, scene_object, event):
        if not self.active:
            return False
        return self.commandObject.sceneEventFilter(event)


class MarkerHandler:
    def __init__(self, parent, parent_hud, view, image_display):
        self.view = view
        self.parent_hud = parent_hud
        self.points = []
        self.counter = []
        self.active_type = 0
        self.scale = 1

        self.current_logname = None
        self.last_logname = None
        self.PointsUnsaved = False
        self.active = False
        self.frame_number = None

        self.MarkerParent = QGraphicsPixmapItem(QPixmap(array2qimage(np.zeros([1, 1, 4]))), parent)
        self.MarkerParent.setZValue(10)

        self.scene_event_filter = GraphicsItemEventFilter(parent, self)
        image_display.AddEventFilter(self.scene_event_filter)

        self.Crosshair = Crosshair(parent, view, image_display)

        self.counter = [] #[MyCounter(parent_hud, self, i) for i in range(len(types))]
        self.UpdateCounter()

    def UpdateCounter(self):
        for counter in self.counter:
            self.view.scene.removeItem(counter)
        self.counter = [MyCounter(self.parent_hud, self, i) for i in range(len(types))]

    def LoadImageEvent(self, filename, framenumber):
        if self.current_logname is not None:
            self.last_logname = self.current_logname
        self.frame_number = framenumber
        base_filename = os.path.splitext(filename)[0]
        self.current_logname = os.path.join(outputpath, base_filename + logname_tag)

        self.LoadLog(self.current_logname)

    def LoadLog(self, logname):
        global types
        print("Loading " + logname)
        if not tracking:
            while len(self.points):
                self.RemovePoint(self.points[0])
        if os.path.exists(logname):
            if tracking:
                for point in self.points:
                    point.setInvalidNewPoint()
            with open(logname) as fp:
                for index, line in enumerate(fp.readlines()):
                    line = line.strip()
                    if line[:7] == "#@types":
                        try:
                            types = DeSerialize(line[7:])
                            self.UpdateCounter()
                        except:
                            print("ERROR: Type specification in %s broken, use types from config instead" % logname)
                        continue
                    if line[0] == '#':
                        continue
                    line = line.split(" ")
                    x = float(line[0])
                    y = float(line[1])
                    marker_type = int(line[2])
                    if len(line) == 3:
                        if index >= len(self.points):
                            self.points.append(MyMarkerItem(x, y, self.MarkerParent, self, marker_type))
                            self.points[-1].setScale(1 / self.view.getOriginScale())
                        else:
                            self.points[index].addPoint(x, y, marker_type)
                        continue
                    active = int(line[3])
                    if marker_type == -1 or active == 0:
                        continue
                    marker_id = line[4]
                    partner_id = None
                    if len(line) >= 6:
                        partner_id = line[5]
                    found = False
                    if tracking is True:
                        for point in self.points:
                            if point.id == marker_id:
                                point.addPoint(x, y, marker_type)
                                found = True
                                break
                    if not found:
                        self.points.append(MyMarkerItem(x, y, self.MarkerParent, self, marker_type, marker_id, partner_id))
                        self.points[-1].setScale(1 / self.scale)
                        self.points[-1].setActive(active)
        else:
            for index in range(0, len(self.points)):
                self.points[index].setInvalidNewPoint()
        print("...done")
        self.PointsUnsaved = False

    def RemovePoint(self, point):
        point.OnRemove()
        self.points.remove(point)
        self.view.scene.removeItem(point)
        self.PointsUnsaved = True

    def SavePoints(self):
        if self.PointsUnsaved:
            if len(self.points) == 0:
                if os.path.exists(self.current_logname):
                    os.remove(self.current_logname)
            else:
                data = ["%f %f %d %d %s %s\n" % (
                    point.pos().x(), point.pos().y(), point.type, point.active, point.id, point.partner_id)
                    for point in self.points if point.active]
                with open(self.current_logname, 'w') as fp:
                    fp.write("#@types "+Serialize(types)+"\n")
                    for line in data:
                        fp.write(line)
            print(self.current_logname + " saved")
            self.PointsUnsaved = False

    def SetActiveMarkerType(self, new_type):
        self.counter[self.active_type].SetToInactiveColor()
        self.active_type = new_type
        self.counter[self.active_type].SetToActiveColor()

    def zoomEvent(self, scale, pos):
        self.scale = scale
        for point in self.points:
            point.setScale(1 / scale)
        self.Crosshair.Crosshair.setScale(1 / scale)

    def setActive(self, active):
        self.scene_event_filter.active = active
        self.active = active
        for point in self.points:
            point.SetActive(active)
        if active:
            self.view.setCursor(QCursor(QtCore.Qt.ArrowCursor))
            self.counter[self.active_type].SetToActiveColor()
        else:
            self.counter[self.active_type].SetToInactiveColor()

    def toggleMarkerShape(self):
        global point_display_type
        point_display_type += 1
        if point_display_type >= len(point_display_types):
            point_display_type = 0
        for point in self.points:
            point.UpdatePath()

    def sceneEventFilter(self, event):
        if event.type() == 156 and event.button() == 1:  # QtCore.QEvent.MouseButtonPress:
            self.points.append(
                MyMarkerItem(event.pos().x(), event.pos().y(), self.MarkerParent, self, self.active_type))
            self.points[-1].setScale(1 / self.scale)
            return True
        return False


class MaskHandler:
    def __init__(self, parent, parent_hud, view, image_display):
        self.view = view
        self.ImageDisplay = image_display
        self.MaskDisplay = BigPaintableImageDisplay(parent)
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

        self.counter = [MyCounter2(parent_hud, self, i) for i in range(len(draw_types))]

        self.UpdateDrawCursorSize()
        self.DrawMode = False

        self.MaskChanged = False
        self.MaskUnsaved = False
        self.active = False

    def LoadImageEvent(self, filename):
        if self.current_maskname is not None:
            self.last_maskname = self.current_maskname
        self.MaskChanged = False
        self.drawPath = QPainterPath()
        self.drawPathItem.setPath(self.drawPath)
        base_filename = os.path.splitext(filename)[0]
        self.current_maskname = os.path.join(outputpath, base_filename + maskname_tag)
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

        self.MaskDisplay.SetImage(self.image_mask_full)

    def UpdateDrawCursorSize(self):
        pen = QPen(QColor(*draw_types[self.active_draw_type][1]), self.DrawCursorSize)
        pen.setCapStyle(32)
        self.drawPathItem.setPen(pen)
        draw_cursor_path = QPainterPath()
        draw_cursor_path.addEllipse(-self.DrawCursorSize * 0.5, -self.DrawCursorSize * 0.5, self.DrawCursorSize,
                                  self.DrawCursorSize)

        self.DrawCursor.setPen(QPen(QColor(*draw_types[self.active_draw_type][1])))
        self.DrawCursor.setPath(draw_cursor_path)

    def SaveMask(self):
        if self.MaskUnsaved:
            self.MaskDisplay.save(self.current_maskname)
            print(self.current_maskname + " saved")
            self.MaskUnsaved = False

    def RedrawMask(self):
        self.MaskDisplay.UpdateImage()
        self.drawPath = QPainterPath()
        self.drawPathItem.setPath(self.drawPath)
        self.MaskChanged = False

    def setActive(self, active):
        self.scene_event_filter.active = active
        self.active = active
        self.DrawCursor.setVisible(active)
        if active:
            self.view.setCursor(QCursor(QtCore.Qt.BlankCursor))
            self.counter[self.active_draw_type].SetToActiveColor()
        else:
            self.counter[self.active_draw_type].SetToInactiveColor()

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
        if auto_mask_update:
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


class ClickPointsWindow(QMainWindow):
    def zoomEvent(self, scale, pos):
        if self.MarkerHandler is not None:
            self.MarkerHandler.zoomEvent(scale, pos)

    def __init__(self, parent=None):
        global modules
        super(QMainWindow, self).__init__(parent)
        self.setWindowTitle('Select Window')

        self.view = QExtendedGraphicsView()
        self.view.zoomEvent = self.zoomEvent
        self.setCentralWidget(self.view)
        self.local_scene = self.view.scene
        self.origin = self.view.origin

        self.ImageDisplay = BigImageDisplay(self.origin, self)

        if len(types):
            self.MarkerHandler = MarkerHandler(self.view.origin, self.view.hud, self.view, self.ImageDisplay)
            modules.append(self.MarkerHandler)
        else:
            self.MarkerHandler = None
        if len(draw_types):
            self.MaskHandler = MaskHandler(self.view.origin, self.view.hud_upperRight, self.view, self.ImageDisplay)
            modules.append(self.MaskHandler)
            if len(types) == 0:
                self.MaskHandler.changeOpacity(0.5)
        else:
            self.MaskHandler = None
        modules[0].setActive(True)

        self.MediaHandler = MediaHandler(join(srcpath, filename))

        self.HelpText = HelpText(self)

        self.slider = SliderBox(self.view.hud_lowerRight, self.ImageDisplay)
        self.slider.setPos(-140, -140)

        self.UpdateImage()

    def UpdateImage(self):
        filename = self.MediaHandler.getCurrentFilename()[1]
        frame_number = self.MediaHandler.getCurrentPos()

        self.setWindowTitle(filename)

        self.LoadImage()
        if self.MarkerHandler:
            self.MarkerHandler.LoadImageEvent(filename, frame_number)
        if self.MaskHandler:
            self.MaskHandler.LoadImageEvent(filename)
        self.slider.LoadImageEvent()

    def LoadImage(self):
        self.ImageDisplay.SetImage(self.MediaHandler.getCurrentImg())

    def SaveMaskAndPoints(self):
        if self.MarkerHandler is not None:
            self.MarkerHandler.SavePoints()
        if self.MaskHandler is not None:
            self.MaskHandler.SaveMask()

    def JumpFrames(self, amount):
        QApplication.setOverrideCursor(QCursor(QtCore.Qt.WaitCursor))
        self.SaveMaskAndPoints()
        if self.MediaHandler.setCurrentPos(self.MediaHandler.getCurrentPos() + amount):
            self.UpdateImage()
        QApplication.restoreOverrideCursor()

    def keyPressEvent(self, event):
        sys.stdout.flush()

        # @key ---- General ----
        if event.key() == QtCore.Qt.Key_F1:
            # @key F1: toggle help window
            self.HelpText.ShowHelpText()

        if event.key() == QtCore.Qt.Key_F:
            # @key F: fit image to view
            self.view.fitInView()

        numberkey = event.key() - 49

        if event.key() == QtCore.Qt.Key_S:
            # @key S: save marker and mask
            self.SaveMaskAndPoints()

        if event.key() == QtCore.Qt.Key_L:
            # @key L: load marker and mask from last image
            if (self.MarkerHandler and self.MarkerHandler.last_logname) or \
                    (self.MaskHandler and self.MaskHandler.last_maskname):
                # saveguard/confirmation with MessageBox
                reply = QMessageBox.question(None, 'Warning', 'Load Mask & Points of last Image?', QMessageBox.Yes,
                                             QMessageBox.No)
                if reply == QMessageBox.Yes:
                    print('Loading last mask & points ...')
                    # load mask and log of last image
                    if self.MarkerHandler:
                        self.MarkerHandler.LoadLog(self.MarkerHandler.last_logname)
                        self.MarkerHandler.PointsUnsaved = True
                    if self.MaskHandler:
                        self.MaskHandler.LoadMask(self.MaskHandler.last_maskname)
                        self.MaskHandler.MaskUnsaved = True
                        self.MaskHandler.RedrawMask()

        # @key ---- Marker ----
        if self.MarkerHandler is not None:
            if self.MarkerHandler.active and 0 <= numberkey < len(types):
                # @key 0-9: change marker type
                self.MarkerHandler.SetActiveMarkerType(numberkey)

            if event.key() == QtCore.Qt.Key_T:
                # @key T: toggle marker shape
                self.MarkerHandler.toggleMarkerShape()

        # @key ---- Painting ----
        if event.key() == QtCore.Qt.Key_P:
            # @key P: toogle brush mode
            if self.MarkerHandler is not None and self.MaskHandler is not None:
                self.MarkerHandler.setActive(not self.MarkerHandler.active)
                self.MaskHandler.setActive(not self.MaskHandler.active)

        if self.MaskHandler is not None:
            if self.MaskHandler.active and 0 <= numberkey < len(draw_types):
                # @key 0-9: change brush type
                self.MaskHandler.SetActiveDrawType(numberkey)

            if event.key() == QtCore.Qt.Key_K:
                # @key K: pick color of brush
                self.MaskHandler.PickColor()

            if event.key() == QtCore.Qt.Key_Plus:
                # @key +: increase brush radius
                self.MaskHandler.changeCursorSize(+1)
            if event.key() == QtCore.Qt.Key_Minus:
                # @key -: decrease brush radius
                self.MaskHandler.changeCursorSize(-1)
            if event.key() == QtCore.Qt.Key_O:
                # @key O: increase mask transparency
                self.MaskHandler.changeOpacity(+0.1)

            if event.key() == QtCore.Qt.Key_I:
                # @key I: decrease mask transparency
                self.MaskHandler.changeOpacity(-0.1)

            if event.key() == QtCore.Qt.Key_M:
                # @key M: redraw the mask
                self.MaskHandler.RedrawMask()

        # @key ---- Frame jumps ----
        if event.key() == QtCore.Qt.Key_Left:
            # @key Left: previous image
            self.JumpFrames(-1)
        if event.key() == QtCore.Qt.Key_Right:
            # @key Right: next image
            self.JumpFrames(+1)

        # JUMP keys
        if event.key() == Qt.Key_2 and event.modifiers() == Qt.KeypadModifier:
            # @key Numpad 2: Jump -1 frame
            self.JumpFrames(-1)
            print('-1')
        if event.key() == Qt.Key_3 and event.modifiers() == Qt.KeypadModifier:
            # @key Numpad 3: Jump +1 frame
            self.JumpFrames(+1)
            print('+1')
        if event.key() == Qt.Key_5 and event.modifiers() == Qt.KeypadModifier:
            # @key Numpad 5: Jump -10 frame
            self.JumpFrames(-10)
            print('-10')
        if event.key() == Qt.Key_6 and event.modifiers() == Qt.KeypadModifier:
            # @key Numpad 6: Jump +10 frame
            self.JumpFrames(+10)
            print('+10')
        if event.key() == Qt.Key_8 and event.modifiers() == Qt.KeypadModifier:
            # @key Numpad 8: Jump -100 frame
            self.JumpFrames(-100)
            print('-100')
        if event.key() == Qt.Key_9 and event.modifiers() == Qt.KeypadModifier:
            # @key Numpad 9: Jump +100 frame
            self.JumpFrames(+100)
            print('+100')
        if event.key() == Qt.Key_Slash and event.modifiers() == Qt.KeypadModifier:
            # @key Numpad /: Jump -1000 frame
            self.JumpFrames(-1000)
            print('-1000')
        if event.key() == Qt.Key_Asterisk and event.modifiers() == Qt.KeypadModifier:
            # @key Numpad *: Jump +1000 frame
            self.JumpFrames(+1000)
            print('+1000')

        # @key ---- Gamma/Brightness Adjustment ---
        if event.key() == Qt.Key_Space:
            # @key Space: update rect
            QApplication.setOverrideCursor(QCursor(QtCore.Qt.WaitCursor))
            self.ImageDisplay.PreviewRect()
            self.ImageDisplay.Change()
            self.slider.updateHist(self.ImageDisplay.hist)
            QApplication.restoreOverrideCursor()


for addon in addons:
    with open(addon + ".py") as f:
        code = compile(f.read(), addon + ".py", 'exec')
        exec(code)

if __name__ == '__main__':
    app = QApplication(sys.argv)

    if use_filedia is True or filename is None:
        tmp = QFileDialog.getOpenFileName(None, "Choose Image", srcpath)
        srcpath = os.path.split(str(tmp))[0]
        filename = os.path.split(str(tmp))[-1]
        print(srcpath)
        print(filename)
    if outputpath is None:
        outputpath = srcpath

    window = ClickPointsWindow()
    window.show()
    app.exec_()
