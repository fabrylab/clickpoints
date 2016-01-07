from __future__ import division, print_function

try:
    from PyQt5 import QtGui, QtCore
    from PyQt5.QtWidgets import QGraphicsPixmapItem, QPixmap
except ImportError:
    from PyQt4 import QtGui, QtCore
    from PyQt4.QtGui import QGraphicsPixmapItem, QPixmap

import numpy as np

from qimage2ndarray import array2qimage, rgb_view


class ImageDisplaySignal(QtCore.QObject):
    display = QtCore.pyqtSignal()

class BigImageDisplay:
    def __init__(self, origin, window, config):
        self.number_of_imagesX = 0
        self.number_of_imagesY = 0
        self.pixMapItems = []
        self.QImages = []
        self.QImageViews = []
        self.ImageSlices = []
        self.origin = origin
        self.window = window
        self.config = config

        self.image = None
        self.hist = None
        self.conversion = None

        self.preview_pixMapItem = QGraphicsPixmapItem(self.origin)
        self.preview_pixMapItem.setZValue(10)
        self.preview_slice = None
        self.preview_qimage = None
        self.preview_qimageView = None

        self.preview_rect = None

        self.gamma = 1
        self.min = 0
        self.max = 255

        self.eventFilters = []

        self.signal =ImageDisplaySignal()
        self.signal.display.connect(self.UpdatePixmaps)

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
        import thread
        thread.start_new_thread(self.SetImage2, (image,))

    def SetImage2(self, image):
        if len(image.shape) == 2:
            image = image.reshape((image.shape[0], image.shape[1], 1))
        self.number_of_imagesX = int(np.ceil(image.shape[1] / self.config.max_image_size))
        self.number_of_imagesY = int(np.ceil(image.shape[0] / self.config.max_image_size))
        self.UpdatePixmapCount()
        self.image = image

        for y in range(self.number_of_imagesY):
            for x in range(self.number_of_imagesX):
                i = y * self.number_of_imagesX + x
                start_x = x * self.config.max_image_size
                start_y = y * self.config.max_image_size
                end_x = min([(x + 1) * self.config.max_image_size, image.shape[1]])
                end_y = min([(y + 1) * self.config.max_image_size, image.shape[0]])
                self.ImageSlices[i] = image[start_y:end_y, start_x:end_x, :]
                self.QImages[i] = array2qimage(image[start_y:end_y, start_x:end_x, :])
                self.QImageViews[i] = rgb_view(self.QImages[i])
                self.pixMapItems[i].setOffset(start_x, start_y)
        self.signal.display.emit()

    def UpdatePixmaps(self):
        for i in range(len(self.pixMapItems)):
            self.pixMapItems[i].setPixmap(QPixmap(self.QImages[i]))
        self.preview_pixMapItem.setPixmap(QPixmap())
        self.preview_slice = None
        if self.preview_rect is not None:
            self.UpdatePreviewImage()
            self.Change()
        self.window.view.painted = False

    def ResetPreview(self):
        self.preview_pixMapItem.setPixmap(QPixmap())
        self.preview_slice = None
        self.preview_rect = None

    def PreviewRect(self):
        self.preview_rect = self.window.view.GetExtend(True)
        self.UpdatePreviewImage()

    def UpdatePreviewImage(self):
        start_x, start_y, end_x, end_y = self.preview_rect
        if start_x < 0: start_x = 0
        if start_y < 0: start_y = 0
        if end_x > self.image.shape[1]: end_x = self.image.shape[1]
        if end_y > self.image.shape[0]: end_y = self.image.shape[0]
        if end_x < start_x: end_x = start_x+1
        if end_y < start_y: end_y = start_y+1
        if end_x > start_x + self.config.max_image_size: end_x = start_x + self.config.max_image_size
        if end_y > start_y + self.config.max_image_size: end_y = start_y + self.config.max_image_size
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
            self.preview_qimageView[:, :, :] = conversion[self.preview_slice.astype(np.uint8)[:,:,:3]]
            self.preview_pixMapItem.setPixmap(QPixmap(self.preview_qimage))
        self.window.view.scene.update()
        self.conversion = conversion

