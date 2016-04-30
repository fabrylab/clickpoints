from __future__ import division, print_function

try:
    from PyQt5 import QtGui, QtCore
except ImportError:
    from PyQt4 import QtGui, QtCore

import numpy as np

from qimage2ndarray import array2qimage, rgb_view

from threading import Thread

def BoundBy(value, min, max):
    # return value bound by min and max
    if value is None:
        return min
    if value < min:
        return min
    if value > max:
        return max
    return value

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

        self.preview_pixMapItem = QtGui.QGraphicsPixmapItem(self.origin)
        self.preview_pixMapItem.setZValue(10)
        self.preview_slice = None
        self.preview_qimage = None
        self.preview_qimageView = None

        self.preview_rect = None

        self.gamma = 1
        self.min = 0
        self.max = 255

        self.eventFilters = []

        self.signal_images_prepared = ImageDisplaySignal()
        self.signal_images_prepared.display.connect(self.UpdatePixmaps)
        self.thread = None

        self.last_offset = np.array([0, 0])

    def AddEventFilter(self, event_filter):
        # add a new event filter to the pixmaps
        self.eventFilters.append(event_filter)
        for pixmap in self.pixMapItems:
            pixmap.installSceneEventFilter(event_filter)

    def UpdatePixmapCount(self):
        # Create new tiles if needed
        for i in range(len(self.pixMapItems), self.number_of_imagesX * self.number_of_imagesY):
            # the first has the origin as parent, all others have the first image as parent
            if i == 0:
                new_pixmap = QtGui.QGraphicsPixmapItem(self.origin)
            else:
                new_pixmap = QtGui.QGraphicsPixmapItem(self.pixMapItems[0])
            # create new entries in the arrays
            self.pixMapItems.append(new_pixmap)
            self.ImageSlices.append(None)
            self.QImages.append(None)
            self.QImageViews.append(None)

            # install all eventfilters for the new pixmaps
            new_pixmap.setAcceptHoverEvents(True)
            for event_filter in self.eventFilters:
                new_pixmap.installSceneEventFilter(event_filter)

        # Hide images which are not needed at the moment
        for i in range(self.number_of_imagesX * self.number_of_imagesY, len(self.pixMapItems)):
            im = np.zeros((1, 1, 1))
            self.pixMapItems[i].setPixmap(QtGui.QPixmap(array2qimage(im)))
            self.pixMapItems[i].setOffset(0, 0)

    def SetImage(self, image, offset, no_threaded_load):
        # call PrepareImageDisplay threaded or directly
        offset = np.array(offset)
        if self.config.threaded_image_display and not no_threaded_load:
            self.thread = Thread(target=self.PrepareImageDisplay, args=(image, offset))
            self.thread.start()
        else:
            self.PrepareImageDisplay(image, offset)

    def closeEvent(self, QCloseEvent):
        if self.config.threaded_image_display and self.thread:
            self.thread.join()

    def PrepareImageDisplay(self, image, offset):
        # if image doesn't have a dimension for color channels, add one
        if len(image.shape) == 2:
            image = image.reshape((image.shape[0], image.shape[1], 1))
        # get number of tiles
        self.number_of_imagesX = int(np.ceil(image.shape[1] / self.config.max_image_size))
        self.number_of_imagesY = int(np.ceil(image.shape[0] / self.config.max_image_size))
        # update pixmaps to new number of tiles
        self.UpdatePixmapCount()

        # store the image
        self.image = image

        # revert last offset and apply new one
        self.window.view.DoTranslateOrigin(-self.last_offset)
        self.window.view.DoTranslateOrigin(offset)
        self.last_offset = offset

        # iterate over tiles
        for y in range(self.number_of_imagesY):
            for x in range(self.number_of_imagesX):
                # determine tile region
                i = y * self.number_of_imagesX + x
                start_x = x * self.config.max_image_size
                start_y = y * self.config.max_image_size
                end_x = min([(x + 1) * self.config.max_image_size, image.shape[1]])
                end_y = min([(y + 1) * self.config.max_image_size, image.shape[0]])
                # retrieve image slice and convert it to qimage
                self.ImageSlices[i] = image[start_y:end_y, start_x:end_x, :]
                self.QImages[i] = array2qimage(image[start_y:end_y, start_x:end_x, :])
                self.QImageViews[i] = rgb_view(self.QImages[i])
                # set the offset for the tile
                self.pixMapItems[i].setOffset(start_x, start_y)

        # emmit signal which calls UpdatePixmaps
        self.signal_images_prepared.display.emit()

    def UpdatePixmaps(self):
        # fill all pixmaps with the corresponding qimages
        for i in range(len(self.pixMapItems)):
            self.pixMapItems[i].setPixmap(QtGui.QPixmap(self.QImages[i]))
        # if display region is choosen update it
        if self.preview_rect is not None:
            self.UpdatePreviewImage()
            self.Change()
        # set painted flag to false and execute callback
        self.window.view.painted = False
        self.window.DisplayedImage()

    def ResetPreview(self):
        # reset pixmap, display image, recgion and conversion
        self.preview_pixMapItem.setPixmap(QtGui.QPixmap())
        self.preview_slice = None
        self.preview_rect = None
        self.conversion = None
        self.min = 0
        self.max = 255
        self.gamma = 1

    def PreviewRect(self):
        # get currently displayed rect as int (add one pixel to account for fraction values)
        self.preview_rect = np.array(self.window.view.GetExtend(True)).astype("int")+np.array([0, 0, 1, 1])
        # add currently used display offset
        self.preview_rect += np.hstack((self.last_offset, self.last_offset)).astype("int")
        # update the displayed gamma correction
        self.UpdatePreviewImage()

    def GetImageRect(self, rect, use_max_image_size=False):
        # extract start and end points from rect
        start_x, start_y, end_x, end_y = rect
        # constrain start points
        start_x = BoundBy(start_x, 0, self.image.shape[1])
        start_y = BoundBy(start_y, 0, self.image.shape[0])
        # constrain end points
        end_x = BoundBy(end_x, start_x+1, self.image.shape[1])
        end_y = BoundBy(end_y, start_y+1, self.image.shape[0])
        if use_max_image_size:
            end_x = BoundBy(end_x, start_x+1, start_x + self.config.max_image_size)
            end_y = BoundBy(end_y, start_y+1, start_y + self.config.max_image_size)
        # return image rect
        return self.image[int(start_y):int(end_y), int(start_x):int(end_x), :], int(start_x), int(start_y)

    def UpdatePreviewImage(self):
        # get the gamma correction rect minus the display offsets
        rect = self.preview_rect-np.hstack((self.last_offset, self.last_offset))
        # extract the image rect
        self.preview_slice, start_x, start_y = self.GetImageRect(rect, use_max_image_size=True)
        # crate a qimage and a view to it
        self.preview_qimage = array2qimage(self.preview_slice)
        self.preview_qimageView = rgb_view(self.preview_qimage)
        # add pixmap and set offsets
        self.preview_pixMapItem.setPixmap(QtGui.QPixmap(self.preview_qimage))
        self.preview_pixMapItem.setOffset(start_x, start_y)
        self.preview_pixMapItem.setParentItem(self.pixMapItems[0])
        # calculate histogram over image patch
        self.hist = np.histogram(self.preview_slice.flatten(), bins=range(0, 256), normed=True)

    def Change(self, gamma=None, min_brightness=None, max_brightness=None):
        # if no display rect is selected choose current region
        if self.preview_slice is None:
            self.PreviewRect()
        # update gamma if set
        if gamma is not None:
            if gamma > 1:
                gamma = 1. / (1 - (gamma - 1) + 0.00001)
            self.gamma = gamma
        # update min brightness if set
        if min_brightness is not None:
            self.min = int(min_brightness)
        # update max brightness if set
        if max_brightness is not None:
            self.max = int(max_brightness)
        # calculate conversion look up table
        color_range = self.max - self.min
        self.conversion = np.arange(0, 256)
        self.conversion[:self.min] = 0
        self.conversion[self.min:self.max] = np.power(np.arange(0, color_range) / color_range, self.gamma) * 256
        self.conversion[self.max:] = 255
        # apply changes
        self.preview_qimageView[:, :, :] = self.conversion[self.preview_slice.astype(np.uint8)[:, :, :3]]
        self.preview_pixMapItem.setPixmap(QtGui.QPixmap(self.preview_qimage))
