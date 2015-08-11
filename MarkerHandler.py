from __future__ import division
import os
import re

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

from qimage2ndarray import array2qimage, rgb_view

import uuid

from Tools import *
from ConfigLoad import *

LoadConfig()

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


def Serialize(value):
    if type(value) == type(""):
        return "'"+value+"'"
    if type(value) == type({}):
        string = "{"
        for key in value:
            string += str(key)+": "+Serialize(value[key])+", "
        return string[:-2]+"}"
    if type(value) != type([]):
        return str(value)
    elements = map(Serialize, value)
    return "["+",".join(elements)+"]"


def DeSerialize(string):
    dictionary = {}
    matches = re.findall(r"(\d*):\s*\[\s*\'([^']*?)\',\s*\[\s*([\d.]*)\s*,\s*([\d.]*)\s*,\s*([\d.]*)\s*\]\s*,\s*([\d.]*)\s*\]", string)
    for match in matches:
        dictionary[int(match[0])] = [match[1], map(float,match[2:5]), int(match[5])]
    return dictionary


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
        self.setPos(10, 10 + 25 * types.keys().index(self.type))
        self.setZValue(9)

        count = 0
        for point in self.window.points:
            if point.type == self.type:
                count += 1
        self.AddCount(count)

    def AddCount(self, new_count):
        self.count += new_count
        self.text.setText(str(self.type+1)+": "+types[self.type][0] + " %d" % self.count)
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



class MarkerHandler:
    def __init__(self, parent, parent_hud, view, image_display, outputpath):
        self.view = view
        self.parent_hud = parent_hud
        self.points = []
        self.counter = []
        self.active_type = 0
        self.scale = 1
        self.outputpath = outputpath

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

        self.counter = []
        self.UpdateCounter()

    def UpdateCounter(self):
        for counter in self.counter:
            self.view.scene.removeItem(self.counter[counter])
        self.counter = {i: MyCounter(self.parent_hud, self, i) for i in types.keys()}

    def LoadImageEvent(self, filename, framenumber):
        if self.current_logname is not None:
            self.last_logname = self.current_logname
        self.frame_number = framenumber
        base_filename = os.path.splitext(filename)[0]
        self.current_logname = os.path.join(self.outputpath, base_filename + logname_tag)

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
                        type_string = line[7:].strip()
                        if type_string[0] == "{":
                            try:
                                types = DeSerialize(line[7:])
                            except:
                                print("ERROR: Type specification in %s broken, use types from config instead" % logname)
                            continue
                    if line[0] == '#':
                        continue
                    line = line.split(" ")
                    x = float(line[0])
                    y = float(line[1])
                    marker_type = int(line[2])
                    if marker_type not in types.keys():
                        np.random.seed(marker_type)
                        types[marker_type] = ["id%d"%marker_type, np.random.randint(0, 255, 3), 0]
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
                self.UpdateCounter()
        else:
            for index in range(0, len(self.points)):
                self.points[index].setInvalidNewPoint()
        print("...done")
        if self.active_type not in types.keys():
            self.active_type = types.keys()[0]
        if self.active:
            self.SetActiveMarkerType(self.active_type)
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
        if new_type not in self.counter.keys():
            return
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

