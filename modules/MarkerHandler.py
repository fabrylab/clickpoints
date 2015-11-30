from __future__ import division, print_function
import os
import re
from peewee import *

try:
    from PyQt5 import QtGui, QtCore
    from PyQt5.QtWidgets import QGraphicsPixmapItem, QPixmap, QPainterPath, QGraphicsPathItem, QGraphicsRectItem, QGraphicsLineItem, QCursor, QFont, QGraphicsSimpleTextItem, QPen, QBrush, QColor
    from PyQt5.QtCore import Qt
except ImportError:
    from PyQt4 import QtGui, QtCore
    from PyQt4.QtGui import QGraphicsPixmapItem, QPixmap, QPainterPath, QGraphicsPathItem, QGraphicsRectItem, QGraphicsLineItem, QCursor, QFont, QGraphicsSimpleTextItem, QPen, QBrush, QColor
    from PyQt4.QtCore import Qt

import numpy as np

from qimage2ndarray import array2qimage, rgb_view

import uuid

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


class MarkerFile:
    def __init__(self, database_filename='marker.db'):
        exists = os.path.exists(database_filename)
        db = SqliteDatabase(database_filename, threadlocals=True)

        class BaseModel(Model):
            class Meta:
                database = db

        class Images(BaseModel):
            filename = CharField()
            ext = CharField()
            frame = IntegerField(default=0)
            index = IntegerField()

        class Tracks(BaseModel):
            uid = CharField()

        class Types(BaseModel):
            name = CharField()
            color = CharField()
            mode = IntegerField()

        class Marker(BaseModel):
            image = ForeignKeyField(Images)
            x = IntegerField()
            y = IntegerField()
            type = ForeignKeyField(Types)
            processed = IntegerField(default=0)
            partner_id = IntegerField(default=0, null=True)
            track = ForeignKeyField(Tracks, null=True)

        self.table_marker = Marker
        self.table_images = Images
        self.table_tracks = Tracks
        self.table_types = Types

        db.connect()
        if not exists:
            db.create_tables([self.table_marker, self.table_images, self.table_tracks, self.table_types])

        self.image = None
        self.next_image_index = 1
        query = self.table_images.select().order_by(-self.table_images.id).limit(1)
        for image in query:
            self.next_image_index = image.id+1

        self.image = None

    def set_image(self, filename, index, frame=0):
        #if self.image:
        #    use = self.table_marker.select(fn.count(self.table_marker.id).alias('count')).where(self.table_marker.image == self.image)[0]
        #    if use.count == 0:
        #        if self.next_image_index == self.image.id+1:
        #            self.next_image_index -= 1
        #        self.image.delete_instance()
        try:
            self.image = self.table_images.get(self.table_images.filename == filename)
        except DoesNotExist:
            self.image = self.table_images(id=self.next_image_index)
            self.next_image_index += 1
            self.image.filename = filename
            self.image.ext = os.path.splitext(filename)[1]
            self.image.frame = frame
            self.image.index = index
            self.image.save(force_insert=True)
        return self.image

    def set_track(self):
        track = self.table_tracks(uid=uuid.uuid4().hex)
        track.save()
        return track

    def set_type(self, id, name, rgb_tuple, mode):
        try:
            type = self.table_types.get(self.table_types.id == id)
        except DoesNotExist:
            type = self.table_types(id=id, name=name, color='#%02x%02x%02x' % tuple(rgb_tuple), mode=mode)
            type.save(force_insert=True)
        return type

    def add_marker(self, **kwargs):
        kwargs.update(dict(image=self.image))
        return self.table_marker(**kwargs)

    def get_marker_list(self):
        return self.table_marker.select().where(self.table_marker.image == self.image)

    def get_type_list(self):
        return self.table_types.select()

    def get_track_list(self):
        return self.table_tracks.select()

    def get_track_points(self, track):
        return self.table_marker.select().where(self.table_marker.track == track)


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
    if len(colorstring) != 6:
        raise ValueError, "input #%s is not in #RRGGBB format" % colorstring
    r, g, b = colorstring[:2], colorstring[2:4], colorstring[4:]
    r, g, b = [int(n, 16) for n in (r, g, b)]
    return (r, g, b)


class MyMarkerItem(QGraphicsPathItem):
    def __init__(self, marker_handler, data):
        QGraphicsPathItem.__init__(self, marker_handler.MarkerParent)
        self.parent = marker_handler.MarkerParent
        self.marker_handler = marker_handler
        self.data = data

        self.config = self.marker_handler.config

        self.scale_value = 1

        self.UpdatePath()
        self.setPos(self.data.x, self.data.y)
        self.setZValue(20)

        self.color = QColor(*HTMLColorToRGB(self.data.type.color))
        self.setBrush(QBrush(self.color))
        self.setPen(QPen(QColor(0, 0, 0, 0)))

        if len(self.marker_handler.counter):
            self.marker_handler.counter[self.data.type.id].AddCount(1)

        self.dragged = False
        self.setAcceptHoverEvents(True)

        self.UseCrosshair = True

        self.partner = None
        self.rectObj = None
        if self.data.type.mode == 1 or self.data.type.mode == 2:
            self.FindPartner()

        if self.partner:
            if self.data.type.mode == 1:
                self.rectObj = QGraphicsRectItem(self.parent)
            if self.data.type.mode == 2:
                self.rectObj = QGraphicsLineItem(self.parent)
            self.rectObj.setPen(QPen(self.color))
            self.UpdateRect()

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
        self.marker_handler.counter[self.data.type.id].AddCount(-1)
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
        if self.data.type.mode == 1:
            self.rectObj.setRect(x, y, x2 - x, y2 - y)
        if self.data.type.mode == 2:
            self.rectObj.setLine(x, y, x2, y2)

    def mouseRightClicked(self):
        self.delete()
        self.marker_handler.RemovePoint(self)

    def mousePressEvent(self, event):
        if event.button() == 2:
            self.mouseRightClicked()
        if event.button() == 1:
            self.drag_start_pos = event.pos()
            self.setCursor(QCursor(QtCore.Qt.BlankCursor))
            if self.UseCrosshair:
                self.marker_handler.Crosshair.MoveCrosshair(self.pos().x(), self.pos().y())
                self.marker_handler.Crosshair.Show(self)

    def mouseMoveEvent(self, event):
        pos = self.parent.mapFromItem(self, event.pos()-self.drag_start_pos)
        self.setPos(pos.x(), pos.y())
        self.data.x, self.data.y = pos.x(), pos.y()
        self.marker_handler.PointsUnsaved = True
        if self.config.tracking:
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
        if event.button() == 1:
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
        self.setPath(point_display_types[point_display_type])
        self.setActive(point_display_type != len(point_display_types) - 1)

    def setScale(self, scale):
        self.scale_value = scale
        if self.rectObj:
            self.rectObj.setPen(QPen(self.color, 2 * scale))
        super(QGraphicsPathItem, self).setScale(scale)

    def save(self):
        self.data.save()

class MyTrackItem(MyMarkerItem):
    def __init__(self, marker_handler, points_data, track):
        MyMarkerItem.__init__(self, marker_handler, points_data[0])
        self.points_data = points_data
        self.track = track

        self.pathItem = QGraphicsPathItem(self.parent)
        self.path = QPainterPath()

        self.active = True

    def FrameChanged(self, image):
        for point in self.points_data:
            if point.image == image:
                self.data = point
                self.setPos(self.data.x, self.data.y)
                self.UpdateLine()
                self.SetTrackActive(True)
                if self.partner and self.rectObj:
                    self.UpdateRect()
                return
        self.SetTrackActive(False)
        self.data = self.marker_handler.marker_file.add_marker(x=self.pos().x(), y=self.pos().y(), type=self.data.type, track=self.track)

    def AddTrackPoint(self):
        self.points_data.append(self.data)
        self.SetTrackActive(True)

    def RemoveTrackPoint(self):
        try:
            self.points_data.remove(self.data)
        except ValueError:
            pass
        self.data.delete_instance()
        if len(self.points_data) == 0:
            self.track.delete_instance()
            self.marker_handler.RemovePoint(self)
        else:
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

    def UpdateLine(self):
        self.path = QPainterPath()
        frames = sorted([point.image.index for point in self.points_data])
        circle_width = self.scale_value * 10
        last_frame = frames[0]
        for frame in frames:
            if (self.config.tracking_show_trailing != -1 and frame < self.marker_handler.frame_number-self.config.tracking_show_trailing) or \
               (self.config.tracking_show_leading != -1 and frame > self.marker_handler.frame_number+self.config.tracking_show_leading):
                    continue
            point = [point for point in self.points_data if point.image.index == frame][0]
            if last_frame == frame-1:
                self.path.lineTo(point.x, point.y)
            else:
                self.path.moveTo(point.x, point.y)
            last_frame = frame
            self.path.addEllipse(point.x - .5 * circle_width, point.y - .5 * circle_width, circle_width, circle_width)
            self.path.moveTo(point.x, point.y)
        self.pathItem.setPath(self.path)

    def mouseRightClicked(self):
        self.RemoveTrackPoint()

    def mouseMoveEvent(self, event):
        if self.active is False:
            self.AddTrackPoint()
        self.UpdateLine()
        MyMarkerItem.mouseMoveEvent(self, event)

    def setCurrentPoint(self, x, y):
        self.setPos(x, y)
        self.data.x, self.data.y = x, y
        if self.active is False:
            self.AddTrackPoint()
        self.UpdateLine()

    def setScale(self, scale):
        self.pathItem.setPen(QPen(self.color, 2 * scale))
        self.UpdateLine()
        MyMarkerItem.setScale(self, scale)

    def save(self):
        if self.active is True:
            self.data.save()


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
    def __init__(self, parent, marker_handler, type):
        QGraphicsRectItem.__init__(self, parent)
        self.parent = parent
        self.marker_handler = marker_handler
        self.type = type
        self.count = 0
        self.setCursor(QCursor(QtCore.Qt.ArrowCursor))

        self.setAcceptHoverEvents(True)
        self.active = False

        self.font = QFont()
        self.font.setPointSize(14)

        self.text = QGraphicsSimpleTextItem(self)
        self.text.setFont(self.font)
        self.color = QColor(*HTMLColorToRGB(self.type.color))
        self.text.setBrush(QBrush(self.color))
        self.text.setZValue(10)

        self.setBrush(QBrush(QColor(0, 0, 0, 128)))
        self.setPos(10, 10 + 25 * (self.type.id-1))
        self.setZValue(9)

        count = 0
        for point in self.marker_handler.points:
            if point.data.type == self.type:
                count += 1
        self.AddCount(count)

    def AddCount(self, new_count):
        self.count += new_count
        self.text.setText(
            str(self.type.id) + ": " + self.type.name + " %d" % self.count)
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
            self.marker_handler.SetActiveMarkerType(self.type.id)


class MarkerHandler:
    def __init__(self, parent, parent_hud, view, image_display, config, modules):
        self.view = view
        self.parent_hud = parent_hud
        self.modules = modules
        self.points = []
        self.counter = []
        self.scale = 1
        self.config = config

        self.marker_file = MarkerFile()

        self.current_logname = None
        self.last_logname = None
        self.PointsUnsaved = False
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
        self.active_type = self.counter[self.counter.keys()[0]].type

    def drawToImage(self, image, start_x, start_y):
        # TODO check if marker is outside of image
        # TODO draw marker history in tracking mode
        # TODO size settings for export
        w = 1.
        b = 10-7
        r2 = 10
        print("Saving", image.shape)
        for point in self.points:
            color = np.array(self.config.types[point.type][1]).reshape(1, 1, 3)
            x, y = point.pos().x()-start_x, point.pos().y()-start_y
            image[y-r2:y-b,x-w:x+w,:] = color
            image[y+b:y+r2,x-w:x+w,:] = color
            image[y-w:y+w,x-r2:x-b,:] = color
            image[y-w:y+w,x+b:x+r2,:] = color

    def UpdateCounter(self):
        for counter in self.counter:
            self.view.scene.removeItem(self.counter[counter])

        type_list = [self.marker_file.set_type(type_id, type_def[0], type_def[1], type_def[2]) for type_id, type_def in self.config.types.items()]
        self.counter = {type.id: MyCounter(self.parent_hud, self, type) for type in type_list}
        self.active_type = self.counter[self.counter.keys()[0]].type

        for key in self.counter:
            self.counter[key].setVisible(not self.hidden)

    def GetLogName(self, filename):
        base_filename = os.path.splitext(filename)[0]
        return os.path.join(self.config.outputpath, base_filename + self.config.logname_tag)

    def LoadImageEvent(self, filename, framenumber):
        self.frame_number = framenumber
        image = self.marker_file.set_image(filename, framenumber)
        if self.config.tracking:
            if len(self.points) == 0:
                self.LoadTracks()
            else:
                for track in self.points:
                    track.FrameChanged(image)
        else:
            self.LoadLog("")

    def FolderChangeEvent(self):
        while len(self.points):
            self.RemovePoint(self.points[0], no_notice=True)
        self.PointsUnsaved = False

    def LoadTracks(self):
        track_list = self.marker_file.get_track_list()
        for track in track_list:
            data = [point for point in self.marker_file.get_track_points(track)]
            if len(data):
                self.points.append(MyTrackItem(self, data, track))

    def LoadLog(self, logname):
        while len(self.points):
            self.RemovePoint(self.points[0], no_notice=True)
        marker_list = self.marker_file.get_marker_list()
        for marker in marker_list:
            self.points.append(MyMarkerItem(self, marker))

    def RemovePoint(self, point, no_notice=False):
        point.OnRemove()
        self.points.remove(point)
        self.view.scene.removeItem(point)
        self.PointsUnsaved = True
        if len(self.points) == 0 and no_notice is False:
            BroadCastEvent(self.modules, "MarkerPointsRemoved")

    def save(self):
        for point in self.points:
            point.save()

    def SetActiveMarkerType(self, new_type):
        if new_type not in self.counter.keys():
            return
        self.counter[self.active_type.id].SetToInactiveColor()
        self.active_type = self.counter[new_type].type
        self.counter[self.active_type.id].SetToActiveColor()

    def zoomEvent(self, scale, pos):
        self.scale = scale
        for point in self.points:
            point.setScale(1 / scale)
        self.Crosshair.setScale(1 / scale)

    def setActiveModule(self, active, first_time=False):
        self.scene_event_filter.active = active
        self.active = active
        for point in self.points:
            point.setActive(active)
        if active:
            self.view.setCursor(QCursor(QtCore.Qt.ArrowCursor))
            self.counter[self.active_type.id].SetToActiveColor()
        else:
            self.counter[self.active_type.id].SetToInactiveColor()
        return True

    def toggleMarkerShape(self):
        global point_display_type
        point_display_type += 1
        if point_display_type >= len(point_display_types):
            point_display_type = 0
        for point in self.points:
            point.UpdatePath()

    def sceneEventFilter(self, event):
        if self.hidden:
            return False
        if event.type() == 156 and event.button() == 1:  # QtCore.QEvent.MouseButtonPress:
            if len(self.points) >= 0:
                BroadCastEvent(self.modules, "MarkerPointsAdded")
            points = [point for point in self.points if point.data.type.id == self.active_type.id]
            if self.config.tracking and self.config.tracking_connect_nearest and len(
                    points) and not event.modifiers() & Qt.ControlModifier:
                distances = [np.linalg.norm(PosToArray(point.pos() - event.pos())) for point in points]
                index = np.argmin(distances)
                points[index].setCurrentPoint(event.pos().x(), event.pos().y())
            elif self.config.tracking:
                track = self.marker_file.set_track()
                data = self.marker_file.add_marker(x=event.pos().x(), y=event.pos().y(), type=self.active_type, track=track)
                self.points.append(MyTrackItem(self, [data], track))
                self.points[-1].setScale(1 / self.scale)
            else:
                data = self.marker_file.add_marker(x=event.pos().x(), y=event.pos().y(), type=self.active_type)
                self.points.append(MyMarkerItem(self, data))
                self.points[-1].setScale(1 / self.scale)
            return True
        return False

    def keyPressEvent(self, event):

        numberkey = event.key() - 49

        # @key ---- Marker ----
        if self.active and 0 <= numberkey < 9 and event.modifiers() != Qt.KeypadModifier:
            # @key 0-9: change marker type
            self.SetActiveMarkerType(numberkey+1)

        if event.key() == QtCore.Qt.Key_T:
            # @key T: toggle marker shape
            self.toggleMarkerShape()
            
    def ToggleInterfaceEvent(self):
        for key in self.counter:
            print(self.counter[key])
            try:
                self.counter[key].setVisible(self.hidden)
            except:
                pass
        self.hidden = not self.hidden

    def loadLast(self):
        self.LoadLog(self.last_logname)
        self.PointsUnsaved = True

    def canLoadLast(self):
        return self.last_logname is not None

    @staticmethod
    def file():
        return __file__

    @staticmethod
    def can_create_module(config):
        return len(config.types) > 0
