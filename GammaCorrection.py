from __future__ import division

try:
    from PyQt5 import QtGui, QtCore
    from PyQt5.QtWidgets import QGraphicsRectItem, QCursor, QPen, QBrush, QColor, QGraphicsPathItem
    from PyQt5.QtCore import QRectF
except ImportError:
    from PyQt4 import QtGui, QtCore
    from PyQt4.QtGui import QGraphicsRectItem, QCursor, QPen, QBrush, QColor, QGraphicsPathItem
    from PyQt4.QtCore import QRectF

from Tools import MySlider, BoxGrabber

class GammaCorrection(QGraphicsRectItem):
    def __init__(self, parent_hud, image_display, config):
        QGraphicsRectItem.__init__(self, parent_hud)
        self.config = config

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
            slider = MySlider(self, name, start_value=start[i], max_value=min_max[i][1], min_value=min_max[i][0])
            slider.format = formats[i]
            slider.setPos(5, 40 + i * 30)
            slider.valueChanged = functions[i]
            self.sliders.append(slider)

        self.setRect(QRectF(0, 0, 110, 110))
        BoxGrabber(self)
        self.dragged = False

        self.hidden = False
        if self.config.gamma_corretion_hide:
            self.setVisible(False)
            self.hidden = True

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
        if self.image.preview_rect is not None:
            self.updateHist(self.image.hist)

    def mousePressEvent(self, event):
        if event.button() == 2:
            for slider in self.sliders:
                slider.reset()
            self.image.ResetPreview()
            self.hist.setPath(QPainterPath())
            self.conv.setPath(QPainterPath())
        pass

    def keyPressEvent(self, event):

        # @key ---- Gamma/Brightness Adjustment ---
        if event.key() == Qt.Key_G:
            # @key G: update rect
            QApplication.setOverrideCursor(QCursor(QtCore.Qt.WaitCursor))
            self.image.PreviewRect()
            self.image.Change()
            self.updateHist(self.image.hist)
            QApplication.restoreOverrideCursor()

        if event.key() == Qt.Key_F2:
            # @key F2: hide/show gamma correction box
            self.setVisible(self.hidden)
            self.hidden = not self.hidden

    @staticmethod
    def file():
        return __file__
