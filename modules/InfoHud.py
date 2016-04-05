from __future__ import division, print_function

try:
    from PyQt5 import QtCore
    from PyQt5.QtWidgets import QGraphicsRectItem, QCursor, QBrush, QColor, QGraphicsSimpleTextItem, QFont, QGraphicsPixmapItem, QPixmap
    from PyQt5.QtCore import QRectF
except ImportError:
    from PyQt4 import QtCore
    from PyQt4.QtGui import QGraphicsRectItem, QCursor, QBrush, QColor, QGraphicsSimpleTextItem, QFont, QGraphicsPixmapItem, QPixmap
    from PyQt4.QtCore import QRectF

from Tools import BoxGrabber

from PIL import Image
from PIL.ExifTags import TAGS
import os, re, json
try:
    import tifffile
    tifffile_loaded = True
except ImportError:
    tifffile_loaded = False

import string
class PartialFormatter(string.Formatter):
    def __init__(self, missing='~', bad_fmt='!!'):
        self.missing, self.bad_fmt=missing, bad_fmt

    def get_field(self, field_name, args, kwargs):
        # Handle a key not found
        try:
            val=super(PartialFormatter, self).get_field(field_name, args, kwargs)
            # Python 3, 'super().get_field(field_name, args, kwargs)' works
        except (KeyError, AttributeError):
            val=None,field_name
        return val

    def format_field(self, value, spec):
        # handle an invalid format
        if value==None: return self.missing
        try:
            return super(PartialFormatter, self).format_field(value, spec)
        except ValueError:
            if self.bad_fmt is not None: return self.bad_fmt
            else: raise

def get_exif(file):
    if not file.lower().endswith((".jpg", ".jpeg")):
        return {}
    ret = {}
    i = Image.open(file)
    info = i._getexif()
    if info:
        for tag, value in info.items():
            decoded = TAGS.get(tag, tag)
            ret[decoded] = value
    return ret

def get_meta(file):
    if not file.lower().endswith((".tif", ".tiff")):
        return {}
    if not tifffile_loaded:
        return {}
    with tifffile.TiffFile(file) as tif:
        try:
            metadata = tif[0].image_description
        except AttributeError:
            return {}
        return json.loads(metadata.decode('utf-8'))

class InfoHud(QGraphicsRectItem):
    def __init__(self, parent_hud, window, config):
        QGraphicsRectItem.__init__(self, parent_hud)
        self.config = config

        self.window = window
        self.setCursor(QCursor(QtCore.Qt.ArrowCursor))

        self.setBrush(QBrush(QColor(0, 0, 0, 128)))
        self.setPos(20, -140)
        self.setZValue(19)

        self.font = QFont()
        self.font.setPointSize(12)
        self.font.setStyleHint(QFont.Monospace)
        self.font.setFixedPitch(True)

        self.text = QGraphicsSimpleTextItem(self)
        self.text.setFont(self.font)
        self.text.setBrush(QBrush(QColor("white")))
        self.text.setZValue(10)
        self.text.setPos(5,10)

        self.setRect(QRectF(0, 0, 110, 110))
        BoxGrabber(self)
        self.dragged = False

        self.hidden = False
        if self.config.hide_interfaces:
            self.setVisible(False)
            self.hidden = True

    def LoadImageEvent(self, filename="", frame_number=0):
        if not self.config.info_hud_string=="@script":
            file = os.path.join(*self.window.data_file.image.filename)
            regex = re.match(self.config.filename_data_regex, file)
            if regex:
                regex = regex.groupdict()
            else:
                regex = dict()
            values = dict(exif=get_exif(file), regex=regex, meta=get_meta(file))
            fmt=PartialFormatter()
            self.text.setText(fmt.format(self.config.info_hud_string, **values))
            rect = self.text.boundingRect()
            rect.setWidth(rect.width() + 10)
            rect.setHeight(rect.height() + 10)
            self.setRect(rect)

    def ToggleInterfaceEvent(self):
        self.setVisible(self.hidden)
        self.hidden = not self.hidden

    def updateHUD(self,info_string):
        fmt=PartialFormatter()
        self.text.setText(fmt.format(info_string))
        rect = self.text.boundingRect()
        rect.setWidth(rect.width() + 10)
        rect.setHeight(rect.height() + 10)
        self.setRect(rect)

    @staticmethod
    def can_create_module(config):
        return len(config.info_hud_string) > 0

    @staticmethod
    def file():
        return __file__
