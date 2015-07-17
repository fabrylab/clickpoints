
from __future__ import division
import sys, os
sys.path.append( os.path.join(os.path.dirname(__file__),"..","mediahandler") )
from PyQt4 import QtGui, QtCore
from PyQt4.QtGui import *
from PyQt4.QtCore import *

import pyqtgraph as pg
import numpy as np
from skimage.morphology import disk
import os
from os.path import join

from PIL import Image, ImageQt, ImageDraw
from qimage2ndarray import array2qimage, rgb_view


from mediahandler import MediaHandler

### parameter and path setup
# default settings
use_filedia = True
srcpath	 = None
filename	= None
outputpath  = None
logname_tag = '_pos.txt'
maskname_tag= '_mask.png'

# marker types
types	   = [ ["juveniles", [255,0.,0], 0],
				["adults", [0,.8*255,0], 0],
				["border", [0.8*255,0.8*255,0], 1],
				["bgroup", [0.5*255,0.5*255,0], 0],
				["horizon", [0.0,0, 0.8*255], 0],
				["iceberg", [0.0,0.8*255, 0.8*255], 0]]
# painter types
draw_types  = [ [0, (0,0,0)],
				[255, [255,255,255]],
				[124 ,[124,124,255]]]

# possible addons
addons = []

# overwrite defaults with personal cfg if available
config_filename = 'cp_cfg.txt'
if len(sys.argv) >= 2:
	config_filename = sys.argv[1]
if os.path.exists(config_filename):
	with open(config_filename) as f:
		code = compile(f.read(), config_filename, 'exec')
		exec(code)

# parameter pre processing
if srcpath == None:
	srcpath = os.getcwd()
if outputpath != None and not os.path.exists(outputpath):
	os.makedirs(outputpath) # recursive path creation

max_image_size = 32768

type_counts = [0]*len(types)
active_type = 0

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

class BigImageDisplay():
	def __init__(self, scene, window):
		self.number_of_imagesX = 0
		self.number_of_imagesY = 0
		self.pixMapItems = []
		self.local_scene = scene
		self.window = window

	def UpdatePixmapCount(self):
		# Create new subimages if needed
		for i in xrange(len(self.pixMapItems), self.number_of_imagesX*self.number_of_imagesY):
			if i == 0:
				new_pixmap = QGraphicsPixmapItem(self.local_scene)
			else:
				new_pixmap = QGraphicsPixmapItem(self.pixMapItems[0])
			self.pixMapItems.append(new_pixmap)
			self.local_scene.addItem(new_pixmap)

			new_pixmap.setAcceptHoverEvents(True)

			new_pixmap.mousePressEvent	=  self.window.CanvasMousePress
			new_pixmap.mouseMoveEvent	 =  self.window.CanvasMouseMove
			new_pixmap.mouseReleaseEvent  =  self.window.CanvasMouseRelease
			new_pixmap.hoverMoveEvent	 =  self.window.CanvasHoverMove
		# Hide images which are not needed
		for i in xrange(self.number_of_imagesX*self.number_of_imagesY, len(self.pixMapItems)):
			im = np.zeros((1,1,1))
			list_pixMap[i].setPixmap( QPixmap(array2qimage(im) ))
			list_pixMap[i].setOffset(0, 0)

	def SetImage(self, image):
		self.number_of_imagesX = int(np.ceil(image.shape[1]/max_image_size))
		self.number_of_imagesY = int(np.ceil(image.shape[0]/max_image_size))
		self.UpdatePixmapCount()

		for y in xrange(self.number_of_imagesY):
			for x in xrange(self.number_of_imagesX):
				i = y*self.number_of_imagesX+x
				startX = x*max_image_size
				startY = y*max_image_size
				endX = min([ (x+1)*max_image_size, image.shape[1] ])
				endY = min([ (y+1)*max_image_size, image.shape[0] ])
				self.pixMapItems[i].setPixmap( QPixmap(array2qimage(image[startY:endY,startX:endX,:]) ))
				self.pixMapItems[i].setOffset(startX, startY)

class BigPaintableImageDisplay():

	def __init__(self, scene):
		self.number_of_imagesX = 0
		self.number_of_imagesY = 0
		self.pixMapItems = []
		self.local_scene = scene
		self.full_image = None
		self.images = []

		self.opacity = 0
		self.colormap = [QColor(i,i,i).rgba() for i in xrange(256)]
		for drawtype in draw_types:
		   self.colormap[drawtype[0]] = QColor(*drawtype[1]).rgba()

	def UpdatePixmapCount(self):
		# Create new subimages if needed
		for i in xrange(len(self.pixMapItems), self.number_of_imagesX*self.number_of_imagesY):
			self.images.append(None)
			if i == 0:
				new_pixmap = QGraphicsPixmapItem(self.local_scene)
			else:
				new_pixmap = QGraphicsPixmapItem(self.pixMapItems[0])
			self.pixMapItems.append(new_pixmap)
			self.local_scene.addItem(new_pixmap)
			new_pixmap.setOpacity(self.opacity)
		# Hide images which are not needed
		for i in xrange(self.number_of_imagesX*self.number_of_imagesY, len(self.pixMapItems)):
			im = np.zeros((1,1,1))
			list_pixMap[i].setPixmap( QPixmap(array2qimage(im) ))
			list_pixMap[i].setOffset(0, 0)

	def SetImage(self, image):
		self.number_of_imagesX = int(np.ceil(image.shape[1]/max_image_size))
		self.number_of_imagesY = int(np.ceil(image.shape[0]/max_image_size))
		self.UpdatePixmapCount()
		self.full_image = image

		for y in xrange(self.number_of_imagesY):
			for x in xrange(self.number_of_imagesX):
				i = y*self.number_of_imagesX+x
				startX = x*max_image_size
				startY = y*max_image_size
				endX = min([ (x+1)*max_image_size, image.shape[1] ])
				endY = min([ (y+1)*max_image_size, image.shape[0] ])

				self.images[i]  = Image.fromarray(image[startY:endY,startX:endX].astype(np.uint8),'L')
				qimage = QImage(ImageQt.ImageQt(self.images[i]))
				qimage.setColorTable(self.colormap)
				pixmap = QPixmap(qimage)
				self.pixMapItems[i].setPixmap(pixmap)
				self.pixMapItems[i].setOffset(startX, startY)

	def UpdateImage(self):
		for i in xrange(self.number_of_imagesY*self.number_of_imagesX):
			qimage = QImage(ImageQt.ImageQt(self.images[i]))
			qimage.setColorTable(self.colormap)
			pixmap = QPixmap(qimage)
			self.pixMapItems[i].setPixmap(pixmap)#QPixmap(QImage(ImageQt.ImageQt(self.images[i]))))

	def DrawLine(self, x1, x2, y1, y2, size):
		for y in xrange(self.number_of_imagesY):
			for x in xrange(self.number_of_imagesX):
				i = y*self.number_of_imagesX+x
				if x*max_image_size < x1 < (x+1)*max_image_size or x*max_image_size < x2 < (x+1)*max_image_size:
					if y*max_image_size < y1 < (y+1)*max_image_size or y*max_image_size < y2 < (y+1)*max_image_size:
						draw = ImageDraw.Draw(self.images[i])
						draw.line(( x1-x*max_image_size,y1-y*max_image_size, x2-x*max_image_size, y2-y*max_image_size ), fill=draw_types[active_draw_type][0], width=size+1)
						draw.ellipse( ( x1-x*max_image_size-size//2, y1-y*max_image_size-size//2, x1-x*max_image_size+size//2, y1-y*max_image_size+size//2 ),  fill=draw_types[active_draw_type][0])

	def setOpacity(self, opacity):
		self.opacity = opacity
		for pixmap in self.pixMapItems:
			pixmap.setOpacity(opacity)

	def save(self, filename):
		for y in xrange(self.number_of_imagesY):
			 for x in xrange(self.number_of_imagesX):
				 i = y*self.number_of_imagesX + x
				 startX = x*max_image_size
				 startY = y*max_image_size
				 endX = min([ (x+1)*max_image_size, self.full_image.shape[1] ])
				 endY = min([ (y+1)*max_image_size, self.full_image.shape[0] ])
				 self.full_image[startY:endY,startX:endX] = self.images[i]

		im = Image.fromarray(self.full_image.astype(np.uint8), 'L')
		im.save(filename)

class MyMarkerItem(QGraphicsPathItem):

	def __init__(self, x,y, parent, window, point_type):
		global type_counts, types, point_display_type

		QGraphicsPathItem.__init__(self,parent)
		self.UpdatePath()

		self.type = point_type
		self.window = window
		if len(self.window.counter):
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
		if types[self.type][2] == 1 or types[self.type][2] == 2:
			for point in self.window.points:
				if point.type == self.type:
					if point.partner == None:
						self.partner = point
						point.partner = self
						self.UseCrosshair = False
						self.partner.UseCrosshair = False

		if self.partner:
			if types[self.type][2] == 1:
				self.rectObj = QGraphicsRectItem(self.imgItem)
				self.rectObj.setPen(QPen(QColor(*types[self.type][1]), 2))
				self.UpdateRect()
			if types[self.type][2] == 2:
				self.rectObj = QGraphicsLineItem(self.imgItem)
				self.rectObj.setPen(QPen(QColor(*types[self.type][1]), 2))
				self.UpdateRect()

		self.window.PointsUnsaved = True

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
		if types[self.type][2] == 1:
			self.rectObj.setRect(x,y,x2-x,y2-y)
		if types[self.type][2] == 2:
			self.rectObj.setLine(x,y,x2,y2)

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
			self.window.PointsUnsaved = True
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
		self.d[:,:,:] = 0
		x,y = int(x),int(y)
		h,w = self.window.im.shape[:2]
		y1 = y-50; y1b = 0
		x1 = x-50; x1b = 0
		y2 = y+50+1; y2b = 101
		x2 = x+50+1; x2b = 101
		if x2 > 0 and y2 > 0 and x1 < w and y1 < h:
			if y1 < 0:
				y1b = -y1
				y1 = 0
			if x1 < 0:
				x1b = -x1
				x1 = 0
			if y2 >= h:
				y2 = h-1
				y2b = y2-y1+y1b
			if x2 >= w:
				x2 = w-1
				x2b = x2-x1+x1b
			self.d[y1b:y2b,x1b:x2b,:] = self.window.im[y1:y2,x1:x2,:]
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

		count = 0
		for point in self.window.points:
			if point.type == self.type:
				count += 1
		self.AddCount(count)

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

	def ViewBox_wheelEvent(self, event):
		self.ViewBox_old_wheelEvent(event)
		self.UpdateScale()

	def UpdateScale(self):
		self.scale = self.local_scene.viewPixelSize()[0]
		if self.scale < 1:
			self.scale = 1
		for point in self.points:
			point.setScale(self.scale)

	def ViewBox_mouseMoveEvent(self,event):
		pos = self.local_scene.mapFromView(event.pos())
		if self.pan:
			dx = (self.last_x-pos.x())*self.local_scene.viewPixelSize()[0]
			dy = (self.last_y-pos.y())*self.local_scene.viewPixelSize()[1]
			self.local_scene.translateBy((dx, dy))
			self.local_scene.mapFromView(event.pos()) # without the view shakes for strange reasons
			self.last_x = pos.x()
			self.last_y = pos.y()

	def ViewBox_mousePressEvent(self,event):
		if event.button() == 2:
			self.pan = True
			pos = self.local_scene.mapFromView(event.pos())
			self.last_x = pos.x()
			self.last_y = pos.y()

	def ViewBox_mouseReleaseEvent(self,event):
		if event.button() == 2:
			self.pan = False

	def __init__(self, parent=None):
		super(QMainWindow, self).__init__(parent)
		self.setWindowTitle('Select Window')

		self.local_grview = pg.GraphicsLayoutWidget()
		self.setCentralWidget( self.local_grview )
		self.local_scene = self.local_grview.addViewBox(enableMenu=False)

		self.local_scene.setAspectLocked(True)
		self.local_scene.invertY(True)

		self.points = []

		self.mask_opacity = 0

		self.local_images = []
		self.pixMapItems = []
		self.ImageDisplay = BigImageDisplay(self.local_scene, self)
		self.MaskDisplay = BigPaintableImageDisplay(self.local_scene)

		self.counter = []

		self.MarkerParent = QGraphicsPixmapItem(QPixmap(array2qimage(np.zeros([1,1,4]))), self.local_scene)
		self.MarkerParent.setZValue(10)
		self.local_scene.addItem(self.MarkerParent )

		self.scale = 1
		self.ViewBox_old_wheelEvent = self.local_scene.wheelEvent
		self.local_scene.wheelEvent = self.ViewBox_wheelEvent

		self.pan = False
		self.local_scene.mouseMoveEvent = self.ViewBox_mouseMoveEvent
		self.local_scene.mousePressEvent = self.ViewBox_mousePressEvent
		self.local_scene.mouseReleaseEvent = self.ViewBox_mouseReleaseEvent

		self.MediaHandler = MediaHandler(join(srcpath, filename))
		self.UpdateImage()

		self.Crosshair = Crosshair(self.MarkerParent, self.local_scene, self)

		self.counter = [MyCounter(self.local_scene, self, i) for i in xrange(len(types))]
		self.counter[active_type].SetToActiveColor()

		self.DrawCursorSize = 10
		self.drawPathItem = QGraphicsPathItem(self.MarkerParent)
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

		self.DrawCursor = QGraphicsPathItem(self.DrawCursorPath, self.MarkerParent)
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
		self.MaskUnsaved = False

	def UpdateImage(self):
		self.MaskChanged = False

		filepath, filename = self.MediaHandler.getCurrentFilename()
		base_filename = os.path.splitext(filename)[0]
		self.current_maskname = os.path.join(outputpath, base_filename+maskname_tag)
		self.current_logname  = os.path.join(outputpath, base_filename+logname_tag)

		self.setWindowTitle(filename)

		self.LoadImage(filename)
		self.LoadMask(self.current_maskname)
		self.LoadLog(self.current_logname)

	def LoadImage(self, filename):
		self.im = self.MediaHandler.getCurrentImg()
		self.ImageDisplay.SetImage(self.im)

	def LoadMask(self, maskname):
		self.current_maskname = maskname
		mask_valid = False
		print(maskname)
		if os.path.exists(maskname):
			print("Load Mask")
			try:
				self.image_mask_full = self.MediaHandler.ReadImage(maskname)
				if self.image_mask_full.shape[:2] != self.im.shape[:2]:
					mask_valid = False
					print("ERROR: Mask file",maskname,"doesn't have the same dimensions as the image")
				else:
					mask_valid = True
				if len(self.image_mask_full.shape) == 3:
					self.image_mask_full = np.mean(self.image_mask_full, axis=2)
			except:
				mask_valid = False
				print("ERROR: Can't read mask file")
			print("...done")
		if mask_valid == False:
			self.image_mask_full = np.zeros((self.im.shape[0],self.im.shape[1]), dtype=np.uint8)
		self.MaskUnsaved = False

		self.MaskDisplay.SetImage(self.image_mask_full)

	def LoadLog(self,logname):
		self.current_logname = logname
		print logname
		while len(self.points):
			self.RemovePoint(self.points[0])
		if os.path.exists(logname):
			try:
				data = np.loadtxt(logname)
				if data.shape == (3,):
					data = np.array([data])
				if data.shape[1] == 3:
					data_valid = True
				else:
					data_valid = False
			except:
				data_valid = False
			if data_valid:
				for point in data:
					self.points.append(MyMarkerItem(point[0],  point[1], self.MarkerParent, self, int(point[2])))
			else:
				print("ERROR: Can't read file",logname)
		self.PointsUnsaved = False

	def CanvasHoverMove(self, event):
		#print("CanvasHoverMove")
		if self.DrawMode:
			self.DrawCursor.setPos(event.pos())

	def CanvasMousePress( self, event):
		#print("MousePress")
		self.last_x = event.pos().x()
		self.last_y = event.pos().y()
		if event.button() == 1:
			if not self.DrawMode:
				pos = event.pos()
				self.points.append(MyMarkerItem(pos.x(),  pos.y(), self.MarkerParent, self, active_type))
				self.points[-1].setScale(self.scale)
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
		#print("CanvasMouseMove")
		if self.DrawMode:
			#print("Drawing")
			pos_x = event.pos().x()
			pos_y = event.pos().y()
			self.drawPath.moveTo(self.last_x, self.last_y)
			self.drawPath.lineTo(pos_x,pos_y)
			self.MaskChanged = True
			self.MaskUnsaved = True

			self.MaskDisplay.DrawLine(pos_x,self.last_x,pos_y,self.last_y, self.DrawCursorSize)
			self.last_x = pos_x
			self.last_y = pos_y
			self.drawPathItem.setPath(self.drawPath)
		else:
			return self.local_scene.mouseMoveEvent(event)

	def CanvasMouseRelease(self, event):
		#print("CanvasMouseRelease")
		return self.local_scene.mouseReleaseEvent(event)

	def UpdateDrawCursorSize(self):
		global active_draw_type
		pen = QPen(QColor(*draw_types[active_draw_type][1]), self.DrawCursorSize)
		pen.setCapStyle(32)
		self.drawPathItem.setPen(pen)
		self.DrawCursorPath = QPainterPath()
		self.DrawCursorPath.addEllipse(-self.DrawCursorSize*0.5,-self.DrawCursorSize*0.5,self.DrawCursorSize,self.DrawCursorSize)

		self.DrawCursor.setPen(QPen(QColor(*draw_types[active_draw_type][1])))
		self.DrawCursor.setPath(self.DrawCursorPath)

	def RemovePoint(self, point):
		#print("Remove",point)
		point.OnRemove()
		self.points.remove(point)
		self.local_scene.removeItem(point)
		self.PointsUnsaved = True

	def SaveMaskAndPoints(self):
		if self.PointsUnsaved:
			if len(self.points) == 0:
				if os.path.exists(self.current_logname):
					os.remove(self.current_logname)
			else:
				data = [ [point.pos().x(), point.pos().y(), point.type] for point in self.points]
				np.savetxt(self.current_logname, data, "%f %f %d")
			print(self.current_logname, " saved")
			self.PointsUnsaved = False

		if self.MaskUnsaved:
			self.MaskDisplay.save(self.current_maskname)
			print(self.current_maskname, " saved")
			self.MaskUnsaved = False

	def keyPressEvent(self,event):
		global active_type, point_display_type, active_draw_type
		sys.stdout.flush()
		numberkey = event.key()-49

		if self.DrawMode == False and 0 <= numberkey < len(types):
			self.counter[active_type].SetToInactiveColor()
			active_type = numberkey
			self.counter[active_type].SetToActiveColor()
		if self.DrawMode == True and 0 <= numberkey < len(draw_types):
			active_draw_type = numberkey
			self.RedrawMask()
			print("Changed Draw type", active_draw_type)
			self.UpdateDrawCursorSize()

		if event.key() == QtCore.Qt.Key_T:
			point_display_type += 1
			if point_display_type >= len(point_display_types):
				point_display_type = 0
			for point in self.points:
				point.UpdatePath()

		if event.key() == QtCore.Qt.Key_S:
			self.SaveMaskAndPoints()

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
			self.MaskDisplay.setOpacity(self.mask_opacity)

		if event.key() == QtCore.Qt.Key_I:
			self.mask_opacity -= 0.1
			if self.mask_opacity <= 0:
				self.mask_opacity = 0
			self.MaskDisplay.setOpacity(self.mask_opacity)

		if event.key() == QtCore.Qt.Key_D:
			x1,x2 = self.local_scene.viewRange()[0]
			self.local_scene.translateBy(( (x2-x1)*0.9, 0 ))
		if event.key() == QtCore.Qt.Key_A:
			x1,x2 = self.local_scene.viewRange()[0]
			self.local_scene.translateBy((-(x2-x1)*0.9, 0))
		if event.key() == QtCore.Qt.Key_S:
			y1,y2 = self.local_scene.viewRange()[1]
			self.local_scene.translateBy(( 0, (y2-y1)*0.9))
		if event.key() == QtCore.Qt.Key_W:
			y1,y2 = self.local_scene.viewRange()[1]
			self.local_scene.translateBy(( 0, -(y2-y1)*0.9))

		if event.key() == QtCore.Qt.Key_M:
			self.RedrawMask()
		if event.key() == QtCore.Qt.Key_F:
			self.local_scene.autoRange()
			self.UpdateScale()

		if event.key() == QtCore.Qt.Key_Left:
			self.SaveMaskAndPoints()
			self.drawPath = QPainterPath()
			self.drawPathItem.setPath(self.drawPath)

			if self.MediaHandler.setCurrentPos(self.MediaHandler.getCurrentPos()-1):
				self.UpdateImage()
		if event.key() == QtCore.Qt.Key_Right:
			self.SaveMaskAndPoints()
			self.drawPath = QPainterPath()
			self.drawPathItem.setPath(self.drawPath)

			if self.MediaHandler.setCurrentPos(self.MediaHandler.getCurrentPos()+1):
				self.UpdateImage()

		if event.key() == QtCore.Qt.Key_L:
			# saveguard/confirmation with MessageBox
			reply=QMessageBox.question(None,'Warning','Load Mask & Points of last Image?',QMessageBox.Yes,QMessageBox.No)
			if reply== QMessageBox.Yes:
				print('Loading last mask & points ...')
				# load mask and log of last image
				self.LoadMask(self.index-1)
				self.LoadLog(self.index-1)
				# force save of mask and log
				self.MaskUnsaved=True
				self.PointsUnsaved=True
				# refresh display
				self.RedrawMask()


	def RedrawMask(self):
		self.MaskDisplay.UpdateImage()
		self.drawPath = QPainterPath()
		self.drawPathItem.setPath(self.drawPath)
		self.MaskChanged = False

for addon in addons:
	with open(addon+".py") as f:
		code = compile(f.read(), addon+".py", 'exec')
		exec(code)

if __name__ == '__main__':
	app = QtGui.QApplication(sys.argv)

	if use_filedia==True or filename == None:
		tmp = QFileDialog.getOpenFileName(None,"Choose Image",srcpath)
		srcpath = os.path.split(str(tmp))[0]
		filename = os.path.split(str(tmp))[-1]
		print(srcpath)
		print(filename)
	if outputpath == None:
		outputpath = srcpath

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

