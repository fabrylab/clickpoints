from __future__ import division, print_function
import os
import re
import peewee

try:
    from PyQt5 import QtGui, QtCore
    from PyQt5.QtWidgets import QGraphicsPixmapItem, QPixmap, QPainterPath, QGraphicsPathItem, QGraphicsRectItem, QGraphicsLineItem, QCursor, QFont, QGraphicsSimpleTextItem, QPen, QBrush, QColor
    from PyQt5.QtWidgets import QWidget, QGridLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel
    from PyQt5.QtCore import Qt
except ImportError:
    from PyQt4 import QtGui, QtCore
    from PyQt4.QtGui import QGraphicsPixmapItem, QPixmap, QPainterPath, QGraphicsPathItem, QGraphicsRectItem, QGraphicsLineItem, QCursor, QFont, QGraphicsSimpleTextItem, QPen, QBrush, QColor
    from PyQt4.QtGui import QWidget, QGridLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel
    from PyQt4.QtCore import Qt

import numpy as np
from sortedcontainers import SortedDict

from qimage2ndarray import array2qimage, rgb_view

import uuid

import json
import matplotlib.pyplot as plt
import random

from Tools import GraphicsItemEventFilter, disk, PosToArray, BroadCastEvent

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

path_circle = QPainterPath()
#path_circle.arcTo(-5, -5, 10, 10, 0, 130)
path_circle.addEllipse(-5, -5, 10, 10)

paths = dict(cross=path1, circle=path_circle)

TYPE_Normal = 0
TYPE_Rect = 1
TYPE_Line = 2
TYPE_Track = 4

class MarkerFile:
    def __init__(self, datafile):
        self.data_file = datafile

        class Tracks(datafile.base_model):
            uid = peewee.CharField()
            style = peewee.CharField(null=True)

        class Types(datafile.base_model):
            name = peewee.CharField(unique=True)
            color = peewee.CharField()
            mode = peewee.IntegerField()
            style = peewee.CharField(null=True)

        class Marker(datafile.base_model):
            image = peewee.ForeignKeyField(datafile.table_images)
            image_frame = peewee.IntegerField()
            x = peewee.FloatField()
            y = peewee.FloatField()
            type = peewee.ForeignKeyField(Types)
            processed = peewee.IntegerField(default=0)
            partner_id = peewee.IntegerField(null=True)
            track = peewee.ForeignKeyField(Tracks, null=True)
            style = peewee.CharField(null=True)
            text = peewee.CharField(null=True)
            class Meta:
                indexes = ((('image', 'image_frame', 'track'), True), )

        self.table_marker = Marker
        self.table_tracks = Tracks
        self.table_types = Types
        self.data_file.tables.extend([Marker, Tracks, Types])

        for table in [self.table_marker, self.table_tracks, self.table_types]:
            if not table.table_exists():
                table.create_table()

    def set_track(self):
        track = self.table_tracks(uid=uuid.uuid4().hex)
        track.save()
        return track

    def set_type(self, id, name, rgb_tuple, mode):
        try:
            type = self.table_types.get(self.table_types.name == name)
        except peewee.DoesNotExist:
            type = self.table_types(name=name, color='#%02x%02x%02x' % tuple(rgb_tuple), mode=mode)
            type.save(force_insert=True)
        return type

    def add_marker(self, **kwargs):
        kwargs.update(dict(image=self.data_file.image, image_frame=self.data_file.image_frame))
        self.data_file.image_uses += 1
        return self.table_marker(**kwargs)

    def get_marker_list(self, image_id=None, image_frame=None):
        if image_id is None:
            image_id = self.data_file.image.id
            image_frame = self.data_file.image_frame
        return self.table_marker.select().where(self.table_marker.image == image_id, self.table_marker.image_frame == image_frame)

    def get_type_list(self):
        return self.table_types.select()

    def get_track_list(self):
        return self.table_tracks.select()

    def get_track_points(self, track):
        return self.table_marker.select().where(self.table_marker.track == track)

    def get_marker_frames(self):
        return self.table_marker.select().group_by(self.table_marker.image.concat(self.table_marker.image_frame))


def ReadTypeDict(string):
    dictionary = {}
    matches = re.findall(
        r"(\d*):\s*\[\s*\'([^']*?)\',\s*\[\s*([\d.]*)\s*,\s*([\d.]*)\s*,\s*([\d.]*)\s*\]\s*,\s*([\d.]*)\s*\]", string)
    for match in matches:
        dictionary[int(match[0])] = [match[1], map(float, match[2:5]), int(match[5])]
    return dictionary


def HTMLColorToRGB(colorstring):
    """ convert #RRGGBB to an (R, G, B) tuple """
    colorstring = colorstring.strip()
    if colorstring[0] == '#': colorstring = colorstring[1:]
    if len(colorstring) != 6 and len(colorstring) != 8:
        raise (ValueError, "input #%s is not in #RRGGBB format" % colorstring)
    return [int(colorstring[i*2:i*2+2], 16) for i in range(int(len(colorstring)/2))]

def GetColorFromMap(identifier, id):
    match = re.match(r"([^\(]*)\((\d*)\)", identifier)
    count = 100
    if match:
        result = match.groups()
        identifier = result[0]
        count = int(result[1])
    cmap = plt.get_cmap(identifier)
    if id is None:
        id = 0
    index = int((id*255/count) % 256)
    color = np.array(cmap(index))
    color = color[:3]*255
    return color

class MarkerEditor(QWidget):
    def __init__(self, marker_item):
        QWidget.__init__(self)

        self.marker_item = marker_item

        # Widget
        self.setMinimumWidth(400)
        self.setMinimumHeight(100)
        self.setWindowTitle("MarkerEditor")
        self.layout = QGridLayout(self)

        # add Label and Line Edit for TEXT
        horizontal_layout = QHBoxLayout()
        self.label_text = QLabel('Text:',self)
        self.lineedit_text = QLineEdit('',self)
        if not self.marker_item.data.text is None:
            self.lineedit_text.setText(self.marker_item.data.text)
        horizontal_layout.addWidget(self.label_text)
        horizontal_layout.addWidget(self.lineedit_text)
        self.layout.addLayout(horizontal_layout,0,0,2,2,Qt.AlignTop)

        # add Confirm and Cancel button
        self.pushbutton_Confirm = QPushButton('S&ave', self)
        self.pushbutton_Confirm.pressed.connect(self.saveMarker)
        self.layout.addWidget(self.pushbutton_Confirm, 1, 0)

        self.pushbutton_Cancel = QPushButton('&Cancel', self)
        self.pushbutton_Cancel.pressed.connect(self.close)
        self.layout.addWidget(self.pushbutton_Cancel, 1, 1)

    def saveMarker(self):
        print("Saving changes...")
        # set parameters
        self.marker_item.data.text = self.lineedit_text.text()
        # save
        self.marker_item.saved=False
        self.marker_item.save()
        # display
        self.marker_item.text.setText(self.lineedit_text.text())

        # close widget
        self.close()


    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.close()
        if event.key() == QtCore.Qt.Key_Return:
            self.saveMarker()


class MyMarkerItem(QGraphicsPathItem):
    def __init__(self, marker_handler, data, saved=False):
        QGraphicsPathItem.__init__(self, marker_handler.MarkerParent)
        self.parent = marker_handler.MarkerParent
        self.marker_handler = marker_handler
        self.data = data
        self.config = self.marker_handler.config
        self.saved = saved

        self.style = {}
        if self.data.type.style:
            self.style.update(json.loads(self.data.type.style))
        if self.data.style:
            self.style.update(json.loads(self.data.style))
        if "color" not in self.style:
            self.style["color"] = self.data.type.color

        if self.style["color"][0] != "#":
            self.style["color"] = GetColorFromMap(self.style["color"], self.data.id)
        else:
            self.style["color"] = HTMLColorToRGB(self.style["color"])

        self.scale_value = 1

        self.UpdatePath()
        self.setPos(self.data.x, self.data.y)
        self.setZValue(20)

        if len(self.marker_handler.counter):
            self.marker_handler.GetCounter(self.data.type).AddCount(1)

        self.dragged = False
        self.setAcceptHoverEvents(True)

        self.UseCrosshair = True


        self.font = QFont()
        self.font.setPointSize(10)
        self.text_parent = QGraphicsPathItem(self)
        self.text_parent.setFlag(QtGui.QGraphicsItem.ItemIgnoresTransformations)
        self.text = QGraphicsSimpleTextItem(self.text_parent)
        self.text.setFont(self.font)
        self.color = self.style["color"]
        self.text.setPos(5, 5)
        self.text.setBrush(QBrush(QColor(*self.color)))
        self.text.setZValue(10)

        if not self.data.text is None:
            self.text.setText(self.data.text)

        self.partner = None
        self.rectObj = None
        if self.data.type.mode & TYPE_Rect or self.data.type.mode & TYPE_Line:
            self.FindPartner()

        if self.partner:
            if self.data.type.mode & TYPE_Rect:
                self.rectObj = QGraphicsRectItem(self.parent)
            elif self.data.type.mode & TYPE_Line:
                self.rectObj = QGraphicsLineItem(self.parent)
            self.rectObj.setPen(QPen(QColor(*self.style["color"])))
            self.UpdateRect()

        self.ApplyStyle()

    def ApplyStyle(self):
        self.color = QColor(*self.style["color"])
        if self.style.get("shape", "cross") == "cross":
            self.setBrush(QBrush(self.color))
            self.setPen(QPen(QColor(0, 0, 0, 0)))
        else:
            self.setBrush(QBrush(QColor(0, 0, 0, 0)))
            self.setPen(QPen(self.color, self.style.get("line-width", 1)))
        self.UpdatePath()
        self.setScale(None)

    def FindPartner(self):
        if self.data.partner_id:
            for point in self.marker_handler.points:
                if point.data.id == self.data.partner_id:
                    self.ConnectToPartner(point)
                    break
        if not self.data.partner_id:
            possible_partners = []
            for point in self.marker_handler.points:
                if point.data.type == self.data.type and point.partner is None:
                    possible_partners.append(
                        [point, np.linalg.norm(PosToArray(self.pos()) - PosToArray(point.pos()))])
            if len(possible_partners):
                possible_partners.sort(key=lambda x: x[1])
                self.ConnectToPartner(possible_partners[0][0])

    def ConnectToPartner(self, point, back=True):
        if not self.data.id:
            self.data.save()
        point.data.partner_id = self.data.id
        self.partner = point
        self.UseCrosshair = False
        if back:
            point.ConnectToPartner(self, back=False)

    def SetProcessed(self, processed):
        self.data.processed = processed

    def delete(self):
        self.data.delete_instance()

    def OnRemove(self):
        self.marker_handler.GetCounter(self.data.type).AddCount(-1)
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
        if self.data.type.mode & TYPE_Rect:
            self.rectObj.setRect(x, y, x2 - x, y2 - y)
        elif self.data.type.mode & TYPE_Line:
            self.rectObj.setLine(x, y, x2, y2)

    def deleteMarker(self):
        self.delete()
        self.marker_handler.RemovePoint(self)

    def mousePressEvent(self, event):
        if event.button() == 2:  # right mouse button
            # open marker edit menu
            self.me = MarkerEditor(self)
            self.me.show()
        if event.button() == 1:  # left mouse button
            # left click with Ctrl -> delete
            if event.modifiers() == QtCore.Qt.ControlModifier:
                self.deleteMarker()
            # left click -> move
            else:
                self.dragged = True
                self.drag_start_pos = event.pos()
                self.setCursor(QCursor(QtCore.Qt.BlankCursor))
                if self.UseCrosshair:
                    self.marker_handler.Crosshair.Show(self)
                    self.marker_handler.Crosshair.MoveCrosshair(self.pos().x(), self.pos().y())

    def mouseMoveEvent(self, event):
        if not self.dragged:
            return
        pos = self.parent.mapFromItem(self, event.pos()-self.drag_start_pos)
        self.saved = False
        self.setPos(pos.x(), pos.y())
        self.data.x, self.data.y = pos.x(), pos.y()
        self.marker_handler.PointsUnsaved = True
        if self.data.type.mode & TYPE_Track:
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
        if event.button() == 1 and self.dragged:
            self.dragged = False
            self.marker_handler.PointsUnsaved = True
            self.SetProcessed(0)
            self.setCursor(QCursor(QtCore.Qt.OpenHandCursor))
            self.marker_handler.Crosshair.Hide()
            pass

    def setActive(self, active):
        if active:
            self.setAcceptedMouseButtons(Qt.MouseButtons(3))
            self.setCursor(QCursor(QtCore.Qt.OpenHandCursor))
        else:
            self.setAcceptedMouseButtons(Qt.MouseButtons(0))
            self.unsetCursor()
        return True

    def UpdatePath(self):
        if point_display_type == 0:
            self.setPath(paths[self.style.get("shape", "cross")])
        else:
            self.setPath(point_display_types[point_display_type])
        self.setActive(point_display_type != len(point_display_types) - 1)

    def setScale(self, scale=None):
        if scale is not None:
            self.scale_value = scale
        if self.rectObj:
            self.rectObj.setPen(QPen(self.color, 2 * self.scale_value))
        super(QGraphicsPathItem, self).setScale(self.scale_value*self.style.get("scale", 1))

    def save(self):
        if not self.saved:
            self.data.save()

    def draw(self, image, start_x, start_y, scale=1):
        w = 1.*scale
        b = (10-7)*scale
        r2 = 10*scale
        x, y = self.pos().x()-start_x, self.pos().y()-start_y
        color = (self.color.red(), self.color.green(), self.color.blue())
        if self.partner:
            if self.rectObj:
                x2, y2 = self.partner.pos().x()-start_x, self.partner.pos().y()-start_y
                if self.data.type.mode & TYPE_Rect:
                    image.line([x , y , x2, y ], color, width=3*scale)
                    image.line([x , y2, x2, y2], color, width=3*scale)
                    image.line([x , y , x , y2], color, width=3*scale)
                    image.line([x2, y , x2, y2], color, width=3*scale)
                if self.data.type.mode & TYPE_Line:
                    image.line([x, y, x2, y2], color, width=3*scale)
            return
        image.rectangle([x-w, y-r2, x+w, y-b], color)
        image.rectangle([x-w, y+b, x+w, y+r2], color)
        image.rectangle([x-r2, y-w, x-b, y+w], color)
        image.rectangle([x+b, y-w, x+r2, y+w], color)


class MyTrackItem(MyMarkerItem):
    def __init__(self, marker_handler, points_data, track, saved=False):
        MyMarkerItem.__init__(self, marker_handler, points_data[0])
        self.points_data = SortedDict()
        for point in points_data:
            frame = self.marker_handler.window.media_handler.get_frame_number_by_id(point.image.filename, point.image_frame)
            if frame is not None:
                self.points_data[frame] = point

        self.track = track
        self.UpdateStyle()
        self.current_frame = 0
        self.min_frame = min(self.points_data.keys())
        self.max_frame = max(self.points_data.keys())

        self.pathItem = QGraphicsPathItem(self.parent)
        self.path = QPainterPath()
        self.pathItem.setPen(QPen(self.color))

        self.hidden = False
        self.active = True
        self.saved = saved

    def UpdateStyle(self):
        self.style = {}
        if self.data.type.style:
            self.style.update(json.loads(self.data.type.style))
        if self.track.style:
            self.style.update(json.loads(self.data.track.style))
        if "color" not in self.style:
            self.style["color"] = self.data.type.color
        if self.style["color"][0] != "#":
            self.style["color"] = GetColorFromMap(self.style["color"], self.track.id)
        else:
            self.style["color"] = HTMLColorToRGB(self.style["color"])
        self.track_style = self.style.copy()
        if self.data.style:
            self.style.update(json.loads(self.data.style))

        if self.style["color"][0] == "#":
            self.style["color"] = HTMLColorToRGB(self.style["color"])

        self.ApplyStyle()

    def FrameChanged(self, image, image_frame, frame):

        self.current_frame = frame
        hide = not self.CheckToDisplay()
        if hide != self.hidden:
            self.hidden = hide
            self.setVisible(not self.hidden)
            self.pathItem.setVisible(not self.hidden)

        if frame in self.points_data:
            self.data = self.points_data[frame]
            self.setPos(self.data.x, self.data.y)
            self.UpdateLine()
            self.SetTrackActive(True)
            if self.partner and self.rectObj:
                self.UpdateRect()
            self.UpdateStyle()
            if not self.data.text is None:
                self.text.setText(self.data.text)
            return

        if not self.hidden:
            self.UpdateLine()
        self.SetTrackActive(False)
        self.data = self.marker_handler.marker_file.add_marker(x=self.pos().x(), y=self.pos().y(), type=self.data.type, track=self.track, text=self.text.text())
        #self.UpdateStyle()

    def update(self, frame, point):
        if point is not None:
            self.AddTrackPoint(frame, point)
            if frame == self.current_frame:
                self.setPos(point.x, point.y)
                self.data = point
        else:
            self.RemoveTrackPoint(frame)
        self.UpdateLine()

    def AddTrackPoint(self, frame=None, point=None):
        if frame is None:
            frame = self.current_frame
        if point is None:
            point = self.data
        self.points_data[frame] = point
        self.min_frame = min(self.points_data.keys())
        self.max_frame = max(self.points_data.keys())
        if frame == self.current_frame:
            self.SetTrackActive(True)
        BroadCastEvent(self.marker_handler.modules, "MarkerPointsAdded")

    def RemoveTrackPoint(self, frame=None):
        if frame is None:
            frame = self.current_frame
        try:
            data = self.points_data.pop(frame)
            data.delete_instance()
        except KeyError:
            pass
        if len(self.points_data) == 0:
            self.track.delete_instance()
            self.marker_handler.RemovePoint(self)
            return
        self.min_frame = min(self.points_data.keys())
        self.max_frame = max(self.points_data.keys())
        if frame == self.current_frame:
            self.saved = True
            self.SetTrackActive(False)

    def OnRemove(self):
        MyMarkerItem.OnRemove(self)
        if self.pathItem:
            self.marker_handler.view.scene.removeItem(self.pathItem)

    def SetTrackActive(self, active):
        if active is False:
            self.active = False
            self.setOpacity(0.5)
            self.pathItem.setOpacity(0.25)
        else:
            self.active = True
            self.setOpacity(1)
            self.pathItem.setOpacity(0.5)

    def CheckToDisplay(self):
        if self.min_frame-2 <= self.current_frame <= self.max_frame+2:
            return True
        return False

    def UpdateLine(self):
        self.path = QPainterPath()
        circle_width = self.scale_value * 10 * self.track_style.get("track-point-scale", 1)
        last_frame = None
        shape = self.track_style.get("track-point-shape", "circle")
        for frame in self.points_data:
            if self.config.tracking_show_trailing != -1 and frame < self.current_frame-self.config.tracking_show_trailing:
                continue
            if self.config.tracking_show_leading != -1 and frame > self.current_frame+self.config.tracking_show_leading:
                break
            point = self.points_data[frame]
            if last_frame == frame-1:
                self.path.lineTo(point.x, point.y)
            else:
                self.path.moveTo(point.x, point.y)
            last_frame = frame
            if shape == "circle":
                self.path.addEllipse(point.x - .5 * circle_width, point.y - .5 * circle_width, circle_width, circle_width)
            if shape == "rect":
                self.path.addRect(point.x - .5 * circle_width, point.y - .5 * circle_width, circle_width, circle_width)
            self.path.moveTo(point.x, point.y)
        self.pathItem.setPath(self.path)

    def draw(self, image, start_x, start_y, scale=1):
        if self.partner:
            return MyMarkerItem.draw(self, image, start_x, start_y)
        color = (self.color.red(), self.color.green(), self.color.blue())
        circle_width = 10*scale
        last_frame = None
        last_point = np.array([0, 0])
        offset = np.array([start_x, start_y])
        for frame in self.points_data:
            if self.config.tracking_show_trailing != -1 and frame < self.current_frame-self.config.tracking_show_trailing:
                continue
            if self.config.tracking_show_leading != -1 and frame > self.current_frame+self.config.tracking_show_leading:
                break
            point = self.points_data[frame]
            point = np.array([point.x, point.y])-offset

            if last_frame == frame-1:
                image.line(np.concatenate((last_point, point)).tolist(), color, width=2*scale)
            image.arc(np.concatenate((point-.5*circle_width, point+.5*circle_width)).tolist(), 0, 360, color)
            last_point = point
            last_frame = frame
        if self.active:
            MyMarkerItem.draw(self, image, start_x, start_y)

    def deleteMarker(self):
        self.RemoveTrackPoint()

    def mousePressEvent(self, event):
        if event.button() == 1 and not event.modifiers() & Qt.ControlModifier:
            if self.active is False:
                self.AddTrackPoint()
                self.saved = False
        MyMarkerItem.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if self.dragged:
            if self.active is False:
                self.AddTrackPoint()
            self.saved = False
            self.UpdateLine()
        MyMarkerItem.mouseMoveEvent(self, event)

    def setCurrentPoint(self, x, y):
        self.setPos(x, y)
        self.data.x, self.data.y = x, y
        if self.active is False:
            self.AddTrackPoint()
        self.UpdateLine()

    def setScale(self, scale):
        MyMarkerItem.setScale(self, scale)
        try:
            line_styles = dict(solid=Qt.SolidLine, dash=Qt.DashLine, dot=Qt.DotLine, dashdot=Qt.DashDotLine, dashdotdot=Qt.DashDotDotLine)
            line_style = line_styles[self.track_style.get("track-line-style", "solid")]
            line_width = self.track_style.get("track-line-width", 2)
            self.pathItem.setPen(QPen(QColor(*self.track_style["color"]), line_width * self.scale_value, line_style))
            self.UpdateLine()
        except AttributeError:
            pass


    def save(self):
        if not self.saved:
            self.data.save()
            self.saved = True


class Crosshair(QGraphicsPathItem):
    def __init__(self, parent, view, image, config):
        QGraphicsPathItem.__init__(self, parent)
        self.parent = parent
        self.view = view
        self.image = image
        self.config = config
        self.radius = 50
        self.not_scaled = True
        self.scale = 1

        self.RGB = np.zeros((self.radius * 2 + 1, self.radius * 2 + 1, 3))
        self.Alpha = disk(self.radius) * 255
        self.Image = np.concatenate((self.RGB, self.Alpha[:, :, None]), axis=2)
        self.CrosshairQImage = array2qimage(self.Image)
        self.CrosshairQImageView = rgb_view(self.CrosshairQImage)

        self.Crosshair = QGraphicsPixmapItem(QPixmap(self.CrosshairQImage), self)
        self.Crosshair.setOffset(-self.radius, -self.radius)
        self.setPos(self.radius * 3, self.radius * 3)
        self.Crosshair.setZValue(-5)
        self.setZValue(30)
        self.setVisible(False)

        self.pathCrosshair = QPainterPath()
        self.pathCrosshair.addEllipse(-self.radius, -self.radius, self.radius * 2, self.radius * 2)

        w = 0.333 * 0.5
        b = 40
        r2 = 50
        self.pathCrosshair2 = QPainterPath()
        self.pathCrosshair2.addRect(-r2, -w, b, w * 2)
        self.pathCrosshair2.addRect(r2, -w, -b, w * 2)
        self.pathCrosshair2.addRect(-w, -r2, w * 2, b)
        self.pathCrosshair2.addRect(-w, r2, w * 2, -b)

        self.CrosshairPathItem = QGraphicsPathItem(self.pathCrosshair, self)
        # self.setPath(self.pathCrosshair)
        self.CrosshairPathItem2 = QGraphicsPathItem(self.pathCrosshair2, self)

    def setScale(self, value):
        QGraphicsPathItem.setScale(self, value)
        self.scale = value
        if not self.SetZoom(value):
            QGraphicsPathItem.setScale(self, 0)
        return True

    def SetZoom(self, new_radius=None):
        if new_radius is not None:
            self.radius = int(new_radius * 50 / 3)
        if not self.isVisible():
            self.not_scaled = True
            return False
        self.not_scaled = False
        if self.radius <= 10:
            return False
        self.RGB = np.zeros((self.radius * 2 + 1, self.radius * 2 + 1, 3))
        self.Alpha = disk(self.radius) * 255
        self.Image = np.concatenate((self.RGB, self.Alpha[:, :, None]), axis=2)
        self.CrosshairQImage = array2qimage(self.Image)
        self.CrosshairQImageView = rgb_view(self.CrosshairQImage)
        self.Crosshair.setPixmap(QPixmap(self.CrosshairQImage))
        self.Crosshair.setScale(1 / self.radius * 50)
        self.Crosshair.setOffset(-self.radius - 0.5, -self.radius - 0.5)
        self.MoveCrosshair(self.pos().x(), self.pos().y())
        return True

    def MoveCrosshair(self, x, y):
        y = int(y)
        x = int(x)
        self.setPos(x, y)
        if not self.isVisible() or self.radius <= 10:
            return
        self.CrosshairQImageView[:, :, :] = self.SaveSlice(self.image.image,
                                                           [[y - self.radius, y + self.radius + 1],
                                                            [x - self.radius, x + self.radius + 1], [0, 3]])
        self.Crosshair.setPixmap(QPixmap(self.CrosshairQImage))

    @staticmethod
    def SaveSlice(source, slices):
        shape = []
        slices1 = []
        slices2 = []
        empty = False
        for length, slice_border in zip(source.shape, slices):
            slice_border = [int(b) for b in slice_border]
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
        new_slice[slices2[0], slices2[1], :] = source[slices1[0], slices1[1], :3]
        return new_slice

    def Hide(self):
        self.setVisible(False)

    def Show(self, point):
        self.setVisible(True)
        if self.not_scaled:
            if self.SetZoom():
                self.setScale(self.scale)
            else:
                self.setScale(0)
        self.CrosshairPathItem2.setPen(QPen(point.color))
        self.CrosshairPathItem.setPen(QPen(point.color))


class MyCounter(QGraphicsRectItem):
    def __init__(self, parent, marker_handler, type, index):
        QGraphicsRectItem.__init__(self, parent)
        self.parent = parent
        self.marker_handler = marker_handler
        self.type = type
        self.index = index
        self.count = 0
        self.setCursor(QCursor(QtCore.Qt.ArrowCursor))

        self.setAcceptHoverEvents(True)
        self.active = False

        self.font = self.marker_handler.window.mono_font
        self.font.setPointSize(14)

        self.text = QGraphicsSimpleTextItem(self)
        self.text.setFont(self.font)
        self.color = QColor(*HTMLColorToRGB(self.type.color))
        self.text.setBrush(QBrush(self.color))
        self.text.setZValue(10)

        self.setBrush(QBrush(QColor(0, 0, 0, 128)))
        self.setPos(10, 10 + 25 * self.index)
        self.setZValue(9)

        count = 0
        for point in self.marker_handler.points:
            if point.data.type == self.type:
                count += 1
        self.AddCount(count)

    def AddCount(self, new_count):
        self.count += new_count
        self.text.setText(
            str(self.index) + ": " + self.type.name + " %d" % self.count)
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
        if event.button() == 1:
            if not self.marker_handler.active:
                BroadCastEvent([module for module in self.marker_handler.modules if module != self.marker_handler], "setActiveModule", False)
                self.marker_handler.setActiveModule(True)
            self.marker_handler.SetActiveMarkerType(self.index)


class MarkerHandler:
    def __init__(self, window, parent, parent_hud, view, image_display, config, modules, datafile):
        self.window = window
        self.view = view
        self.parent_hud = parent_hud
        self.modules = modules
        self.points = []
        self.tracks = []
        self.counter = []
        self.scale = 1
        self.config = config
        self.data_file = datafile
        self.text=None

        self.marker_file = MarkerFile(datafile)

        self.active = False
        self.frame_number = None
        self.hidden = False
        if self.config.hide_interfaces:
            self.hidden = True

        self.MarkerParent = QGraphicsPixmapItem(QPixmap(array2qimage(np.zeros([1, 1, 4]))), parent)
        self.MarkerParent.setZValue(10)

        self.scene_event_filter = GraphicsItemEventFilter(parent, self)
        image_display.AddEventFilter(self.scene_event_filter)

        self.Crosshair = Crosshair(parent, view, image_display, config)

        self.UpdateCounter()
        self.active_type = self.counter[list(self.counter.keys())[0]].type
        self.active_type_index = 0

        # place tick marks for already present markers
        for item in self.marker_file.get_marker_frames():
            frame = self.window.media_handler.get_frame_number_by_id(item.image.filename, item.image_frame)
            if frame is not None:
                BroadCastEvent(self.modules, "MarkerPointsAdded", frame)

    def drawToImage(self, image, start_x, start_y, scale=1):
        for point in self.points:
            point.draw(image, start_x, start_y, scale)
        for track in self.tracks:
            track.draw(image, start_x, start_y, scale)

    def UpdateCounter(self):
        for counter in self.counter:
            self.view.scene.removeItem(self.counter[counter])

        type_list = [self.marker_file.set_type(type_id, type_def[0], type_def[1], type_def[2]) for type_id, type_def in self.config.types.items()]
        type_list = self.marker_file.get_type_list()
        self.counter = {index: MyCounter(self.parent_hud, self, type, index) for index, type in enumerate(type_list)}
        self.active_type = self.counter[list(self.counter.keys())[0]].type

        for key in self.counter:
            self.counter[key].setVisible(not self.hidden)

    def GetCounter(self, type):
        for index in self.counter:
            if self.counter[index].type == type:
                return self.counter[index]
        raise NameError("A non existant type was referenced")

    def ReloadMarker(self, frame):
        image, image_frame = self.window.media_handler.id_lookup[frame]
        # Tracks
        marker_list = self.marker_file.get_marker_list(image, image_frame)
        marker_list = {marker.track.id: marker for marker in marker_list if marker.track}
        for track in self.tracks:
            if track.track.id in marker_list:
                track.update(frame, marker_list[track.track.id])
                marker_list.pop(track.track.id)
            else:
                track.update(frame, None)
        # Points
        if frame == self.frame_number:
            self.LoadPoints()

    def LoadImageEvent(self, filename, framenumber):
        self.frame_number = framenumber
        image = self.data_file.image
        image_frame = self.data_file.image_frame

        if len(self.tracks) == 0:
            self.LoadTracks()
        else:
            for track in self.tracks:
                track.FrameChanged(image, image_frame, framenumber)
        self.LoadPoints()

    def FolderChangeEvent(self):
        while len(self.points):
            self.RemovePoint(self.points[0], no_notice=True)
        while len(self.tracks):
            self.RemovePoint(self.tracks[0], no_notice=True)

    def LoadTracks(self):
        track_list = self.marker_file.get_track_list()
        for track in track_list:
            data = [point for point in self.marker_file.get_track_points(track)]
            if len(data):
                self.tracks.append(MyTrackItem(self, data, track, saved=True))

    def LoadPoints(self):
        while len(self.points):
            self.RemovePoint(self.points[0], no_notice=True)
        marker_list = self.marker_file.get_marker_list()
        for marker in marker_list:
            if not marker.track:
                self.points.append(MyMarkerItem(self, marker, saved=True))
                self.points[-1].setScale(1 / self.scale)

    def RemovePoint(self, point, no_notice=False):
        point.OnRemove()
        try:
            self.points.remove(point)
        except ValueError:
            self.tracks.remove(point)
        self.view.scene.removeItem(point)
        if len(self.points) == 0 and no_notice is False:
            BroadCastEvent(self.modules, "MarkerPointsRemoved")

    def save(self):
        for point in self.points:
            point.save()
        for track in self.tracks:
            track.save()

    def SetActiveMarkerType(self, new_index):
        try:
            counter_list = [c for i, c in self.counter.items() if c.index == new_index]
            counter = counter_list[0]
        except IndexError:
            return
        self.counter[self.active_type_index].SetToInactiveColor()
        self.active_type = counter.type
        self.active_type_index = new_index
        self.counter[self.active_type_index].SetToActiveColor()

    def zoomEvent(self, scale, pos):
        self.scale = scale
        for point in self.points:
            point.setScale(1 / scale)
        for track in self.tracks:
            track.setScale(1 / scale)
        self.Crosshair.setScale(1 / scale)

    def setActiveModule(self, active, first_time=False):
        self.scene_event_filter.active = active
        self.active = active
        for point in self.points:
            point.setActive(active)
        if active:
            self.view.setCursor(QCursor(QtCore.Qt.ArrowCursor))
            self.counter[self.active_type_index].SetToActiveColor()
        else:
            self.counter[self.active_type_index].SetToInactiveColor()
        return True

    def toggleMarkerShape(self):
        global point_display_type
        point_display_type += 1
        if point_display_type >= len(point_display_types):
            point_display_type = 0
        for point in self.points:
            point.UpdatePath()
        for track in self.tracks:
            track.UpdatePath()

    def sceneEventFilter(self, event):
        if self.hidden:
            return False
        if event.type() == 156 and event.button() == 1 and not event.modifiers() & Qt.ControlModifier:  # QtCore.QEvent.MouseButtonPress:
            if len(self.points) >= 0:
                BroadCastEvent(self.modules, "MarkerPointsAdded")
            tracks = [track for track in self.tracks if track.data.type.id == self.active_type.id]
            if self.active_type.mode & TYPE_Track and self.config.tracking_connect_nearest and \
                    len(tracks) and not event.modifiers() & Qt.ControlModifier:
                distances = [np.linalg.norm(PosToArray(point.pos() - event.pos())) for point in tracks]
                index = np.argmin(distances)
                tracks[index].setCurrentPoint(event.pos().x(), event.pos().y())
            elif self.active_type.mode & TYPE_Track:
                track = self.marker_file.set_track()
                data = self.marker_file.add_marker(x=event.pos().x(), y=event.pos().y(), type=self.active_type, track=track)
                self.tracks.append(MyTrackItem(self, [data], track, saved=False))
                self.tracks[-1].setScale(1 / self.scale)
            else:
                data = self.marker_file.add_marker(x=event.pos().x(), y=event.pos().y(), type=self.active_type, text=self.text)
                self.points.append(MyMarkerItem(self, data, saved=False))
                self.points[-1].setScale(1 / self.scale)
            return True
        return False

    def keyPressEvent(self, event):

        numberkey = event.key() - 49

        # @key ---- Marker ----
        if self.active and 0 <= numberkey < 9 and event.modifiers() != Qt.KeypadModifier:
            # @key 0-9: change marker type
            self.SetActiveMarkerType(numberkey)

        if event.key() == QtCore.Qt.Key_T:
            # @key T: toggle marker shape
            self.toggleMarkerShape()
            
    def ToggleInterfaceEvent(self):
        for key in self.counter:
            #(self.counter[key])
            try:
                self.counter[key].setVisible(self.hidden)
            except:
                pass
        self.hidden = not self.hidden

    def loadLast(self):
        return("ERROR: not implemented at the moment")

    def canLoadLast(self):
        return self.last_logname is not None

    @staticmethod
    def file():
        return __file__

    @staticmethod
    def can_create_module(config):
        return len(config.types) > 0
