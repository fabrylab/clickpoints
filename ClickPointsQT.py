import sys
from PyQt4 import QtGui, QtCore
from PyQt4.QtGui import *
from PyQt4.QtCore import *

import pyqtgraph as pg
import numpy as np
import numpy
from pylab import imread
from skimage.morphology import disk
import os
import cv2

### parameter and path setup
srcpath='/media/fox/a1f5434a-74d1-4bcb-bf9c-b9fa8d1df3d0/atkaSPOT/atkaGEPAN/'
filename= '20140401-124426_atkaGEPAN.png'


use_filedia = True
if use_filedia==True:
    root = Tkinter.Tk()
    root.update()
    tmp =fd.askopenfilename(initialdir=srcpath)
    filename = os.path.split(tmp)[-1]
    root.destroy()


outputpath='/media/fox/a1f5434a-74d1-4bcb-bf9c-b9fa8d1df3d0/atkaSPOT/atkaGEPAN/results/'
logname= filename[:-4] +'_pos.txt'
maskname=filename[:-4] +'_mask.png'

if not os.path.exists(outputpath):
    os.makedirs(outputpath) # recursive path creation


#types = [ ["juveniles", [255,0.,0], 0], ["adults", [0,.8*255,0], 0], ["border", [0.8*255,0.8*255,0], 1], ["horizon", [0.0,0, 0.8*255], 0] ]
types = [ ["juveniles", [255,0.,0], 0], ["adults", [0,.8*255,0], 0], ["border", [0.8*255,0.8*255,0], 1],["bgroup", [0.5*255,0.5*255,0], 0], ["horizon", [0.0,0, 0.8*255], 0], ["iceberg", [0.0,0.8*255, 0.8*255], 0]]

type_counts = [0]*len(types)
active_type = 0

draw_types = [ [0, (0,0,0)], [255, [255,255,255]], [124 ,[124,124,255]]]
active_draw_type = 1

w = 1.
b = 7
r2 = 10
path1 = QPainterPath()
path1.addRect(-r2,-w, b,w*2)
path1.addRect( r2,-w,-b,w*2)
path1.addRect( -w,-r2,w*2, b)
path1.addRect( -w, r2,w*2,-b)
w = 0.5
b = 2
o = 1
path2 = QPainterPath()
path2.addRect(-b-o,-w*0.5, b, w)
path2.addRect(+o,-w*0.5, b, w)
path2.addRect(-w*0.5, -b-o, w, b)
path2.addRect(-w*0.5, +o, w, b)
path3 = QPainterPath()
path3.addEllipse(-0.25,-0.25,0.5,0.5)#addRect(-0.5,-0.5, 1, 1)
point_display_types = [path1, path2, path3]
point_display_type = 0

from PIL import Image, ImageQt
from qimage2ndarray import array2qimage, rgb_view, alpha_view

class MyMarkerItem(QGraphicsPathItem):

    def __init__(self, x,y, parent, window, point_type):
        global type_counts, types, point_display_type

        QGraphicsPathItem.__init__(self,parent)
        self.UpdatePath()

        self.type = point_type
        self.window = window
        self.window.counter[self.type].AddCount(1)

        self.setBrush(QBrush(QColor(*types[self.type][1])))
        self.setPen(QPen(QColor(0,0,0,0)))

        self.setPos(x,y)
        self.setZValue(20)
        self.imgItem = parent
        self.dragged = False

        self.UseCrosshair = True

        self.partner = None
        self.rectObj = None
        if types[self.type][2] == 1:
            for point in self.window.points:
                if point.type == self.type:
                    if point.partner == None:
                        self.partner = point
                        point.partner = self
                        self.UseCrosshair = False
                        self.partner.UseCrosshair = False

        if self.partner:
            self.rectObj = QGraphicsRectItem(self.imgItem)
            self.rectObj.setPen(QPen(QColor(*types[self.type][1]), 2))
            self.UpdateRect()

    def OnRemove(self):
        self.window.counter[self.type].AddCount(-1)
        if self.partner and self.partner.rectObj:
            self.window.local_scene.removeItem(self.partner.rectObj)
            self.partner.rectObj = None
            self.partner.partner = None     
        if self.rectObj:
            self.partner.partner = None
            self.window.local_scene.removeItem(self.rectObj)
          

    def UpdateRect(self):
        x ,y  = self.pos().x(), self.pos().y()
        x2,y2 = self.partner.pos().x(), self.partner.pos().y()
        self.rectObj.setRect(x,y,x2-x,y2-y)

    def hoverEnterEvent(self, event):
        QApplication.setOverrideCursor(QCursor(QtCore.Qt.OpenHandCursor))

    def hoverLeaveEvent(self, event):
        QApplication.setOverrideCursor(QCursor(QtCore.Qt.ArrowCursor))

    def mousePressEvent(self, event):
        if event.button() == 2:
            self.window.RemovePoint(self)
        if event.button() == 1:
            self.dragged = True
            QApplication.setOverrideCursor(QCursor(QtCore.Qt.BlankCursor))
            if self.UseCrosshair:
                self.window.Crosshair.MoveCrosshair(self.pos().x(),self.pos().y())
                self.window.Crosshair.Show(self.type)
            pass

    def mouseMoveEvent(self, event):
        if not self.dragged:
            return
        self.setPos(self.pos()+event.pos()*0.25)
        self.window.Crosshair.MoveCrosshair(self.pos().x(),self.pos().y())
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
            self.dragged = False
            QApplication.setOverrideCursor(QCursor(QtCore.Qt.OpenHandCursor))
            self.window.Crosshair.Hide()
            pass

    def UpdatePath(self):
        self.setPath(point_display_types[point_display_type])
        if point_display_type == len(point_display_types)-1:
            self.setAcceptedMouseButtons(Qt.MouseButtons(0))
            self.setAcceptHoverEvents(False)
        else:
            self.setAcceptedMouseButtons(Qt.MouseButtons(3))
            self.setAcceptHoverEvents(True)

class Crosshair():
    def __init__(self, parent, scene, window):
        self.parent = parent
        self.scene = scene
        self.window = window

        self.a = self.window.im[-102:-1,0:101].copy()
        self.b = disk(50)*255
        self.c = np.concatenate((self.a,self.b[:,:,None]),axis=2)
        self.CrosshairX = array2qimage(self.c)
        self.d = rgb_view(self.CrosshairX)

        self.Crosshair = QGraphicsPixmapItem(QPixmap(self.CrosshairX), self.scene)
        self.d[:,:,0] = 255
        self.Crosshair.setOffset(-50, -50)
        self.Crosshair.setZValue(30)
        self.Crosshair.setScale(3)
        self.scene.addItem(self.Crosshair)

        self.pathCrosshair = QPainterPath()
        self.pathCrosshair.addEllipse(-50,-50,100,100)

        w = 0.333*0.5
        b = 40
        r2 = 50
        self.pathCrosshair2 = QPainterPath()
        self.pathCrosshair2.addRect(-r2,-w, b,w*2)
        self.pathCrosshair2.addRect( r2,-w,-b,w*2)
        self.pathCrosshair2.addRect( -w,-r2,w*2, b)
        self.pathCrosshair2.addRect( -w, r2,w*2,-b)

        self.CrosshairPathItem = QGraphicsPathItem(self.pathCrosshair, self.Crosshair)
        self.CrosshairPathItem.setBrush(QBrush(QColor(0,0,0,0)))
        self.CrosshairPathItem.setPen(QPen(QColor(*types[0][1]),5))

        self.CrosshairPathItem2 = QGraphicsPathItem(self.pathCrosshair2, self.Crosshair)
        self.CrosshairPathItem2.setBrush(QBrush(QColor(0,0,0,0)))
        self.CrosshairPathItem2.setPen(QPen(QColor(*types[0][1]),5))

        self.Crosshair.setScale(0)

    def MoveCrosshair(self, x,y):
        self.d[:,:,:] = self.window.im[y-50:y+50+1,x-50:x+50+1]
        self.Crosshair.setPixmap(QPixmap(self.CrosshairX))
        self.Crosshair.setPos(x,y)
        #self.CrosshairPathItem.setPos(x,y)

    def Hide(self):
        self.Crosshair.setScale(0)

    def Show(self, type):
        self.Crosshair.setScale(3*self.scene.viewPixelSize()[0])
        self.CrosshairPathItem2.setPen(QPen(QColor(*types[type][1]),1))
        self.CrosshairPathItem.setPen(QPen(QColor(*types[type][1]),3))

class MyCounter():
    def __init__(self, parent, window, point_type):
        self.parent = parent
        self.window = window
        self.type = point_type
        self.count = 0

        self.font = QFont()
        self.font.setPointSize(14)

        self.text = QGraphicsSimpleTextItem(self.parent)
        self.text.setText(types[self.type][0]+" %d"%0)
        self.text.setFont(self.font)
        self.text.setBrush(QBrush(QColor(*types[self.type][1])))
        self.text.setPos(10, 10+25*self.type)
        self.text.setZValue(10)

        self.rect =  QGraphicsRectItem(self.parent)
        self.rect.setBrush(QBrush(QColor(0,0,0,128)))
        self.rect.setPos(10, 10+25*self.type)
        self.rect.setZValue(9)

        self.AddCount(0)

    def AddCount(self, new_count):
        self.count += new_count
        self.text.setText(types[self.type][0]+" %d"%self.count)
        rect = self.text.boundingRect()
        rect.setX(-5)
        rect.setWidth(rect.width()+5)
        self.rect.setRect(rect)
        
    def SetToActiveColor(self):
        self.rect.setBrush(QBrush(QColor(255,255,255,128)))
    def SetToInactiveColor(self):
        self.rect.setBrush(QBrush(QColor(0,0,0,128)))



class DrawImage(QMainWindow):
    def __init__(self, parent=None):
        super(QMainWindow, self).__init__(parent)
        self.setWindowTitle('Select Window')

        self.local_grview = pg.GraphicsLayoutWidget()
        self.setCentralWidget( self.local_grview )
        self.local_scene = self.local_grview.addViewBox(enableMenu=False)

        self.local_scene.setAspectLocked(True)
        self.local_scene.invertY(True)

        offset = 0
        self.local_images = []
        self.pixMapItems = []
        self.offsets = []

        print "Loading Image"
        self.im = imread(srcpath + filename)*255
        print "... done"
        #self.im = 255*np.ones(self.im.shape)
        if os.path.exists(outputpath + maskname):
            print "Load Mask"
            self.image_mask_full = (imread(outputpath + maskname)*255)#.astype(np.uint8)
            print "...done"
        else:
            self.image_mask_full = np.zeros((self.im.shape[0],self.im.shape[1]), dtype=np.uint8)
        w = self.image_mask_full.shape[1]//3
        self.part_width = w
        self.image_mask = [self.image_mask_full[:,i*self.part_width:(i+1)*self.part_width] for i in xrange(3)]

        w = self.im.shape[1]//3

        self.mask_opacity = 0

        self.MaskQImages = []
        self.MaskQImageViews = []
        self.MaskPixMaps = []
        for i in [1,2,3]:#xrange(3):
            #self.local_images.append( QImage('Fused_1_part%d.jpg'%i) )
            #self.pixMapItems.append( QGraphicsPixmapItem(QPixmap(self.local_images[-1]), self.local_scene) )

            self.pixMapItems.append( QGraphicsPixmapItem(QPixmap(array2qimage(self.im[:,(i-1)*w:i*w,:])), self.local_scene) )

            self.local_scene.addItem(self.pixMapItems[-1])
            self.pixMapItems[-1].setOffset(offset, 0)
            self.offsets.append(offset)
            #offset += self.local_images[-1].width()


            self.pixMapItems[-1].setAcceptHoverEvents(True)

            self.pixMapItems[-1].mousePressEvent    =  self.CanvasMousePress
            self.pixMapItems[-1].mouseMoveEvent     =  self.CanvasMouseMove
            self.pixMapItems[-1].mouseReleaseEvent  =  self.CanvasMouseRelease
            self.pixMapItems[-1].hoverMoveEvent     =  self.CanvasHoverMove

            self.MaskQImages.append(array2qimage(self.image_mask[i-1][:,:]))
            self.MaskQImageViews.append(rgb_view(self.MaskQImages[-1]))
            self.MaskPixMaps.append(QGraphicsPixmapItem(QPixmap(self.MaskQImages[-1]), self.local_scene))
            self.MaskPixMaps[-1].setOffset(offset, 0)
            self.MaskPixMaps[-1].setOpacity(self.mask_opacity)
            self.local_scene.addItem(self.MaskPixMaps[-1])

            offset += w




        self.Crosshair = Crosshair(self.pixMapItems[-1], self.local_scene, self)

        self.counter = [MyCounter(self.local_scene, self, i) for i in xrange(len(types))]
        self.counter[active_type].SetToActiveColor()
        self.points = []

        if os.path.exists(outputpath + logname):
            data = np.loadtxt(outputpath + logname)
            for point in data:
                self.points.append(MyMarkerItem(point[0],  point[1], self.pixMapItems[2], self, int(point[2])))

        self.DrawCursorSize = 10
        self.drawPathItem = QGraphicsPathItem(self.pixMapItems[-1])
        self.drawPathItem.setBrush(QBrush(QColor(255,255,255)))
        #self.drawPathItem.setBrush(QBrush(QtCore.Qt.blue))
        #pen = QPen(QtCore.Qt.blue, self.DrawCursorSize)
        #pen.setCapStyle(1)
        #self.drawPathItem.setPen(pen)

        self.drawPath = self.drawPathItem.path()
        #self.drawPath.lineTo(10,10)
        #self.drawPath.lineTo(50,30)
        self.drawPathItem.setPath(self.drawPath)
        self.drawPathItem.setZValue(10)

        self.last_x = 0
        self.last_y = 0

        self.DrawCursorPath = QPainterPath()
        self.DrawCursorPath.addEllipse(-self.DrawCursorSize*0.5,-self.DrawCursorSize*0.5,self.DrawCursorSize,self.DrawCursorSize)

        self.DrawCursor = QGraphicsPathItem(self.DrawCursorPath, self.pixMapItems[-1])
        self.DrawCursor.setBrush(QBrush(QColor(0,0,0,0)))
        self.DrawCursor.setPen(QPen(QColor(0,0,255)))
        self.DrawCursor.setScale(0)

        self.UpdateDrawCursorSize()
        #a =  QImage('Fused_1_part%d.jpg'%1)
        #b = QGraphicsPixmapItem(QPixmap(a), self.local_scene)
        #b.setPos(100,200)
        #self.local_scene.addItem(b)
        self.DrawMode = False
        self.MaskChanged = False
        #
    def CanvasHoverMove(self, event):
        #print "CanvasHoverMove"
        if self.DrawMode:
            self.DrawCursor.setPos(event.pos())

    def CanvasMousePress( self, event):
        #print "MousePress"
        if event.button() == 1:
            if not self.DrawMode:
                pos = event.pos()
                self.points.append(MyMarkerItem(pos.x(),  pos.y(), self.pixMapItems[2], self, active_type))
            else:
                self.last_x = event.pos().x()
                self.last_y = event.pos().y()
            #self.Crosshair = QGraphicsPixmapItem(QPixmap(imread("Fused_1_part1.jpg")), self.local_scene)
            #self.Crosshair.setPos(pos.x(),  pos.y())
            #self.local_scene.addItem(self.Crosshair)
        else:
            return self.local_scene.mousePressEvent(event)

    def CanvasMouseMove(self, event):
        global active_draw_type
        #print "CanvasMouseMove"
        if self.DrawMode:
            #print "Drawing"
            x = event.pos().x()
            y = event.pos().y()
            self.drawPath.moveTo(self.last_x, self.last_y)
            self.drawPath.lineTo(x,y)
            self.MaskChanged = True

            for i in xrange(3):
                if i*self.part_width < x < (i+1)*self.part_width or i*self.part_width < self.last_x < (i+1)*self.part_width:
                    cv2.line(self.image_mask[i], (int(x)-i*self.part_width,int(y)), (int(self.last_x-i*self.part_width), int(self.last_y)), draw_types[active_draw_type][0], self.DrawCursorSize)

            self.last_x = x
            self.last_y = y
            self.drawPathItem.setPath(self.drawPath)
        else:
            return self.local_scene.mouseMoveEvent(event)

    def CanvasMouseRelease(self, event):
        #print "CanvasMouseRelease"
        return self.local_scene.mouseReleaseEvent(event)

    def UpdateDrawCursorSize(self):
        global active_draw_type
        print draw_types[active_draw_type][1]
        pen = QPen(QColor(*draw_types[active_draw_type][1]), self.DrawCursorSize)
        pen.setCapStyle(32)
        self.drawPathItem.setPen(pen)
        self.DrawCursorPath = QPainterPath()
        self.DrawCursorPath.addEllipse(-self.DrawCursorSize*0.5,-self.DrawCursorSize*0.5,self.DrawCursorSize,self.DrawCursorSize)

        self.DrawCursor.setPen(QPen(QColor(*draw_types[active_draw_type][1])))
        self.DrawCursor.setPath(self.DrawCursorPath)

    def RemovePoint(self, point):
        print "Remove",point
        point.OnRemove()
        self.points.remove(point)
        self.local_scene.removeItem(point)

    def keyPressEvent(self,event):
        global active_type, point_display_type, active_draw_type
        print('press', event.key())
        sys.stdout.flush()
        numberkey = event.key()-49

        if self.DrawMode == False and 0 <= numberkey < len(types):
            self.counter[active_type].SetToInactiveColor()
            active_type = numberkey
            self.counter[active_type].SetToActiveColor()
        if self.DrawMode == True and 0 <= numberkey < len(draw_types):
            active_draw_type = numberkey
            print "Changed Draw type", active_draw_type
            self.UpdateDrawCursorSize()

        if event.key() == QtCore.Qt.Key_T:
            point_display_type += 1
            if point_display_type >= len(point_display_types):
                point_display_type = 0
            for point in self.points:
                point.UpdatePath()

        if event.key() == QtCore.Qt.Key_S:
            data = [ [point.pos().x(), point.pos().y(), point.type] for point in self.points]
            np.savetxt(outputpath + logname, data, "%f %f %d")
            print outputpath + logname, " saved"
            for i in xrange(3):
                self.image_mask_full[:,i*self.part_width:(i+1)*self.part_width] = self.image_mask[i]
            im = Image.fromarray(self.image_mask_full.astype(np.uint8), 'L')
            im.save(outputpath + maskname)
            print outputpath + maskname, " saved"

        if event.key() == QtCore.Qt.Key_P:
            if self.DrawMode:
                self.DrawMode = False
                self.DrawCursor.setScale(0)
                for point in self.points:
                    point.setAcceptHoverEvents(True)
                    point.setAcceptedMouseButtons(Qt.MouseButtons(3))
            else:
                self.DrawMode = True
                self.DrawCursor.setScale(1)
                for point in self.points:
                    point.setAcceptHoverEvents(False)
                    point.setAcceptedMouseButtons(Qt.MouseButtons(0))

        if event.key() == QtCore.Qt.Key_Plus:
            self.DrawCursorSize += 1
            self.UpdateDrawCursorSize()
            if self.MaskChanged:
                self.RedrawMask()
        if event.key() == QtCore.Qt.Key_Minus:
            self.DrawCursorSize -= 1
            self.UpdateDrawCursorSize()
            if self.MaskChanged:
                self.RedrawMask()
        if event.key() == QtCore.Qt.Key_O:
            self.mask_opacity += 0.1
            if self.mask_opacity >= 1:
                self.mask_opacity = 1
            for i in xrange(3):
                self.MaskPixMaps[i].setOpacity(self.mask_opacity)

        if event.key() == QtCore.Qt.Key_I:
            self.mask_opacity -= 0.1
            if self.mask_opacity <= 0:
                self.mask_opacity = 0
            for i in xrange(3):
                self.MaskPixMaps[i].setOpacity(self.mask_opacity)

        if event.key() == QtCore.Qt.Key_M:
            print "M"
            self.RedrawMask()
        if event.key() == QtCore.Qt.Key_F:
            self.local_scene.autoRange()

    def RedrawMask(self):
        for i in xrange(3):
            self.MaskQImageViews[i][:,:,0] = self.image_mask[i][:,:]
            self.MaskQImageViews[i][:,:,1] = self.image_mask[i][:,:]
            self.MaskQImageViews[i][:,:,2] = self.image_mask[i][:,:]
            self.MaskPixMaps[i].setPixmap(QPixmap(self.MaskQImages[i]))
        self.drawPath = QPainterPath()
        self.drawPathItem.setPath(self.drawPath)
        self.MaskChanged = False



if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    window = DrawImage()
    window.show()
    app.exec_()


"""
from pylab import *
data = loadtxt("data.txt")
im = imread("Fused_1_part1.jpg")
plot(data[:,0],data[:,1],'o')
imshow(im)

im = imread('Fused_1.png')
im1 = im[:,:im.shape[1]//3]
im2 = im[:,im.shape[1]//3:2*im.shape[1]//3]
im3 = im[:,2*im.shape[1]//3:]
imsave("Fused_1_part1.jpg", im1)
imsave("Fused_1_part2.jpg", im2)
imsave("Fused_1_part3.jpg", im3)
"""

