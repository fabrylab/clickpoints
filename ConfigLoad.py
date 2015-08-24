from __future__ import division
import sys

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
import os

from qimage2ndarray import array2qimage, rgb_view

from Tools import *
from regexpfilefilter import *

TYPE_Normal = 0
TYPE_Rect = 1
TYPE_Line = 2

use_filedia = True
auto_mask_update = True
tracking = False
srcpath = None
filename = None
outputpath = None
logname_tag = '_pos.txt'
maskname_tag = '_mask.png'

filterparam={}

# marker types
types = {0: ["juveniles", [255, 0, 0], TYPE_Normal],
         1: ["adults", [0, 204, 0], TYPE_Rect],
         2: ["beak", [204, 204, 0], TYPE_Line]
         }
# painter types
draw_types = [[0, (0, 0, 0)],
              [255, [255, 255, 255]],
              [124, [124, 124, 255]]]

# possible addons
addons = []

max_image_size = 2 ** 12

def LoadConfig():
    global use_filedia, auto_mask_update, tracking
    global srcpath, filename, outputpath
    global logname_tag, maskname_tag
    global types, draw_types, addons, max_image_size
    global filterparam
    # overwrite defaults with personal cfg if available
    config_filename = 'cp_cfg.txt'
    if len(sys.argv) >= 2:
        config_filename = sys.argv[1]
    if os.path.exists(config_filename):
        with open(config_filename) as f:
            code = compile(f.read(), config_filename, 'exec')
            exec(code, globals())

    # parameter pre processing
    if srcpath is None:
        srcpath = os.getcwd()
    if outputpath is not None and not os.path.exists(outputpath):
        os.makedirs(outputpath)  # recursive path creation

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


class SliderBox(QGraphicsRectItem):
    def __init__(self, parent_hud, image_display):
        QGraphicsRectItem.__init__(self, parent_hud)

        self.image = image_display
        self.setCursor(QCursor(QtCore.Qt.ArrowCursor))

        self.setBrush(QBrush(QColor(0, 0, 0, 128)))
        self.setPos(-140, -140)
        self.setZValue(19)

        self.hist = QGraphicsPathItem(self)
        self.hist.setPen(QPen(QColor(0, 0, 0, 0)))
        self.hist.setBrush(QBrush(QColor(255, 255, 255, 128)))
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

    def LoadImageEvent(self, filename="", frame_number=0):
        self.hist.setPath(QPainterPath())
        self.conv.setPath(QPainterPath())

    def mousePressEvent(self, event):
        pass

    def mousePressEvent(self, event):
        pass

    def mousePressEvent(self, event):
        pass

    def keyPressEvent(self, event):

        # @key ---- Gamma/Brightness Adjustment ---
        if event.key() == Qt.Key_Space:
            # @key Space: update rect
            QApplication.setOverrideCursor(QCursor(QtCore.Qt.WaitCursor))
            self.image.PreviewRect()
            self.image.Change()
            self.updateHist(self.image.hist)
            QApplication.restoreOverrideCursor()

    @staticmethod
    def file():
        return __file__
