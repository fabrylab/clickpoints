from __future__ import division, print_function
import os
import re

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


def ReadTypeDict(string):
    dictionary = {}
    matches = re.findall(
        r"(\d*):\s*\[\s*\'([^']*?)\',\s*\[\s*([\d.]*)\s*,\s*([\d.]*)\s*,\s*([\d.]*)\s*\]\s*,\s*([\d.]*)\s*\]", string)
    for match in matches:
        dictionary[int(match[0])] = [match[1], map(float, match[2:5]), int(match[5])]
    return dictionary


class MyMarkerItem(QGraphicsPathItem):
    def __init__(self, x, y, parent, marker_handler, point_type, start_id=None, partner_id=None):
        global point_display_type

        QGraphicsPathItem.__init__(self, parent)
        self.parent = parent
        self.type = point_type
        self.marker_handler = marker_handler
        self.config = self.marker_handler.config

        self.scale_value = 1

        self.UpdatePath()

        if len(self.marker_handler.counter):
            self.marker_handler.counter[self.type].AddCount(1)

        self.setBrush(QBrush(QColor(*self.config.types[self.type][1])))
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
        if self.config.types[self.type][2] == 1 or self.config.types[self.type][2] == 2:
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
            if self.config.types[self.type][2] == 1:
                self.rectObj = QGraphicsRectItem(self.imgItem)
                self.rectObj.setPen(QPen(QColor(*self.config.types[self.type][1]), 2))
                self.UpdateRect()
            if self.config.types[self.type][2] == 2:
                self.rectObj = QGraphicsLineItem(self.imgItem)
                self.rectObj.setPen(QPen(QColor(*self.config.types[self.type][1]), 2))
                self.UpdateRect()

        self.marker_handler.PointsUnsaved = True
        self.setAcceptHoverEvents(True)
        if self.marker_handler.config.tracking is True:
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
            if self.config.tracking_show_trailing != -1 and frame < self.marker_handler.frame_number-self.config.tracking_show_trailing:
                continue
            if self.config.tracking_show_leading != -1 and frame > self.marker_handler.frame_number+self.config.tracking_show_leading:
                continue
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
        if self.partner:
            if self.rectObj:
                self.UpdateRect()
            else:
                self.partner.UpdateRect()
                self.partner.setPos(self.partner.pos())

    def OnRemove(self):
        self.marker_handler.counter[self.type].AddCount(-1)
        if self.partner and self.partner.rectObj:
            self.marker_handler.view.scene.removeItem(self.partner.rectObj)
            self.partner.rectObj = None
            self.partner.partner = None
        if self.rectObj:
            self.partner.partner = None
            self.marker_handler.view.scene.removeItem(self.rectObj)
        if self.pathItem:
            self.marker_handler.view.scene.removeItem(self.pathItem)

    def UpdateRect(self):
        x, y = self.pos().x(), self.pos().y()
        x2, y2 = self.partner.pos().x(), self.partner.pos().y()
        if self.config.types[self.type][2] == 1:
            self.rectObj.setRect(x, y, x2 - x, y2 - y)
        if self.config.types[self.type][2] == 2:
            self.rectObj.setLine(x, y, x2, y2)

    def mousePressEvent(self, event):
        if event.button() == 2:
            if self.marker_handler.config.tracking is True:
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
            self.drag_start_pos = event.pos()
            self.setCursor(QCursor(QtCore.Qt.BlankCursor))
            if self.UseCrosshair:
                self.marker_handler.Crosshair.MoveCrosshair(self.pos().x(), self.pos().y())
                self.marker_handler.Crosshair.Show(self.type)
            pass

    def mouseMoveEvent(self, event):
        if not self.dragged:
            return
        if self.config.tracking:
            self.SetTrackActive(True)
        pos = self.parent.mapFromItem(self, event.pos()-self.drag_start_pos)
        self.setPos(pos.x(), pos.y())
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
        if not self.dragged:
            return
        if event.button() == 1:
            self.marker_handler.PointsUnsaved = True
            self.dragged = False
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
            self.rectObj.setPen(QPen(QColor(*self.config.types[self.type][1]), 2 * scale))
        if self.marker_handler.config.tracking is True:
            self.pathItem.setPen(QPen(QColor(*self.config.types[self.type][1]), 2 * scale))
            self.UpdateLine()
        super(QGraphicsPathItem, self).setScale(scale)


class Crosshair(QGraphicsPathItem):
    def __init__(self, parent, view, image, config):
        QGraphicsPathItem.__init__(self, parent)
        self.parent = parent
        self.view = view
        self.image = image
        self.config = config
        self.radius = 50

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
        if not self.SetZoom(value):
            QGraphicsPathItem.setScale(self, 0)
        return True

    def SetZoom(self, new_radius):
        self.radius = int(new_radius * 50 / 3)
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
        if self.scale() == 0:
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

    def Show(self, marker_type):
        self.setVisible(True)
        self.CrosshairPathItem2.setPen(QPen(QColor(*self.config.types[marker_type][1]), 1))
        self.CrosshairPathItem.setPen(QPen(QColor(*self.config.types[marker_type][1]), 3))


class MyCounter(QGraphicsRectItem):
    def __init__(self, parent, marker_handler, point_type):
        QGraphicsRectItem.__init__(self, parent)
        self.parent = parent
        self.marker_handler = marker_handler
        self.type = point_type
        self.count = 0
        self.setCursor(QCursor(QtCore.Qt.ArrowCursor))

        self.setAcceptHoverEvents(True)
        self.active = False

        self.font = QFont()
        self.font.setPointSize(14)

        self.text = QGraphicsSimpleTextItem(self)
        self.text.setText(self.marker_handler.config.types[self.type][0] + " %d" % 0)
        self.text.setFont(self.font)
        self.text.setBrush(QBrush(QColor(*self.marker_handler.config.types[self.type][1])))
        self.text.setZValue(10)

        self.setBrush(QBrush(QColor(0, 0, 0, 128)))
        self.setPos(10, 10 + 25 * self.marker_handler.config.types.keys().index(self.type))
        self.setZValue(9)

        count = 0
        for point in self.marker_handler.points:
            if point.type == self.type:
                count += 1
        self.AddCount(count)

    def AddCount(self, new_count):
        self.count += new_count
        self.text.setText(
            str(self.type + 1) + ": " + self.marker_handler.config.types[self.type][0] + " %d" % self.count)
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
            self.marker_handler.SetActiveMarkerType(self.type)


class MarkerHandler:
    def __init__(self, parent, parent_hud, view, image_display, config, modules):
        self.view = view
        self.parent_hud = parent_hud
        self.modules = modules
        self.points = []
        self.counter = []
        self.active_type = 0
        self.scale = 1
        self.config = config

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

    def UpdateCounter(self):
        for counter in self.counter:
            self.view.scene.removeItem(self.counter[counter])
        self.counter = {i: MyCounter(self.parent_hud, self, i) for i in self.config.types.keys()}
        for key in self.counter:
            self.counter[key].setVisible(not self.hidden)

    def LoadImageEvent(self, filename, framenumber):
        if self.current_logname is not None:
            self.last_logname = self.current_logname
        self.frame_number = framenumber
        base_filename = os.path.splitext(filename)[0]
        self.config["outputpath"]
        self.current_logname = os.path.join(self.config.outputpath, base_filename + self.config.logname_tag)

        self.LoadLog(self.current_logname)

    def FolderChangeEvent(self):
        while len(self.points):
            self.RemovePoint(self.points[0], no_notice=True)
        self.PointsUnsaved = False

    def LoadLog(self, logname):
        global types
        print("Loading " + logname)
        if not self.config.tracking:
            while len(self.points):
                self.RemovePoint(self.points[0], no_notice=True)
        if os.path.exists(logname):
            if self.config.tracking:
                for point in self.points:
                    point.setInvalidNewPoint()
            with open(logname) as fp:
                for index, line in enumerate(fp.readlines()):
                    line = line.strip()
                    if line[:7] == "#@types":
                        type_string = line[7:].strip()
                        if type_string[0] == "{":
                            try:
                                self.config["types"] = ReadTypeDict(line[7:])
                            except:
                                print("ERROR: Type specification in %s broken, use types from config instead" % logname)
                            else:
                                self.UpdateCounter()
                            continue
                    if line[0] == '#':
                        continue
                    line = line.split(" ")
                    x = float(line[0])
                    y = float(line[1])
                    marker_type = int(line[2])
                    if marker_type == -1:
                        continue
                    if marker_type not in self.config["types"].keys():
                        np.random.seed(marker_type)
                        self.config["types"][marker_type] = ["id%d" % marker_type, np.random.randint(0, 255, 3), 0]
                        print("self.config[types]", self.config["types"])
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
                    if self.config.tracking is True:
                        for point in self.points:
                            if point.id == marker_id:
                                point.addPoint(x, y, marker_type)
                                found = True
                                break
                    if not found:
                        self.points.append(
                            MyMarkerItem(x, y, self.MarkerParent, self, marker_type, marker_id, partner_id))
                        self.points[-1].setScale(1 / self.scale)
                        self.points[-1].setActive(active)
                self.UpdateCounter()
        else:
            for index in range(0, len(self.points)):
                self.points[index].setInvalidNewPoint()
        print("...done")
        if self.active_type not in self.config.types.keys():
            self.active_type = self.config.types.keys()[0]
        if self.active:
            self.SetActiveMarkerType(self.active_type)
        self.PointsUnsaved = False

    def RemovePoint(self, point, no_notice=False):
        point.OnRemove()
        self.points.remove(point)
        self.view.scene.removeItem(point)
        self.PointsUnsaved = True
        if len(self.points) == 0 and no_notice is False:
            BroadCastEvent(self.modules, "MarkerPointsRemoved")

    def save(self):
        if self.PointsUnsaved:
            if len(self.points) == 0:
                if os.path.exists(self.current_logname):
                    os.remove(self.current_logname)
            else:
                data = ["%f %f %d %d %s %s\n" % (
                    point.pos().x(), point.pos().y(), point.type, point.active, point.id, point.partner_id)
                        for point in self.points if point.active]
                with open(self.current_logname, 'w') as fp:
                    fp.write("#@types " + str(self.config.types) + "\n")
                    for line in data:
                        fp.write(line)
            print(self.current_logname + " saved")
            self.PointsUnsaved = False

    def SetActiveMarkerType(self, new_type):
        if new_type not in self.counter.keys():
            return
        self.counter[self.active_type].SetToInactiveColor()
        self.active_type = new_type
        self.counter[self.active_type].SetToActiveColor()

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
            self.counter[self.active_type].SetToActiveColor()
        else:
            self.counter[self.active_type].SetToInactiveColor()
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
            points = [point for point in self.points if point.type == self.active_type]
            if self.config.tracking and self.config.tracking_connect_nearest and len(
                    points) and not event.modifiers() & Qt.ControlModifier:
                distances = [np.linalg.norm(PosToArray(point.pos() - event.pos())) for point in points]
                index = np.argmin(distances)
                points[index].addPoint(event.pos().x(), event.pos().y(), points[index].type)
                self.PointsUnsaved = True
            else:
                self.points.append(
                    MyMarkerItem(event.pos().x(), event.pos().y(), self.MarkerParent, self, self.active_type))
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
