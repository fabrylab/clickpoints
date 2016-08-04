#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Test_DataFile.py

# Copyright (c) 2015-2016, Richard Gerum, Sebastian Richter
#
# This file is part of ClickPoints.
#
# ClickPoints is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ClickPoints is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ClickPoints. If not, see <http://www.gnu.org/licenses/>

from __future__ import print_function, division

__key__ = "DATAFILE"
__testname__ = "Data File"

import os
import unittest
import numpy as np

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "package"))

from clickpoints import DataFile
import clickpoints


class Test_DataFile(unittest.TestCase):

    def setUp(self):
        self.db = DataFile(self.id().split(".")[-1]+".cdb", "w")

    def tearDown(self):
        self.db.db.close()
        os.remove(self.db.database_filename)

    def test_getDbVersion(self):
        """ Test if the getDbVersion function returns the version properly """
        self.assertEqual(self.db.getDbVersion(), "14", "Database version is not returned correctly.")

    ''' Test Path functions '''
    def test_setPath(self):
        """ Test the setPath function """

        # try to set a path
        path = self.db.setPath(path_string="test")
        self.assertEqual(path.path, "test", "Path was not set properly")

    def test_getPath(self):
        """ Test the getPath function """

        # set a new path
        self.db.setPath(path_string="test")

        # try to get the path
        path = self.db.getPath(path_string="test")
        self.assertEqual(path.path, "test", "Retrieving a path does not work")

        # try to get a non-existent path
        path = self.db.getPath(path_string="testX")
        self.assertEqual(path, None, "Retrieving an non existent path does not work")

        # try to create a non-existent path
        path = self.db.getPath(path_string="testX", create=True)
        self.assertEqual(path.path, "testX", "Creating a non existent path does not work")

    def test_getPaths(self):
        """ Test the getPaths function """

        p1 = os.path.join("foo", "bar1")
        p2 = os.path.join("foo", "bar2")
        p3 = os.path.join("loo", "bar1")
        self.db.setPath(path_string=p1)
        self.db.setPath(path_string=p2)
        self.db.setPath(path_string=p3)
        paths = self.db.getPaths(path_string=p2)
        self.assertEqual([p.path for p in paths], [p2], "Retrieving a single path works does not work.")

        paths = self.db.getPaths(path_string=[p1, p2])
        self.assertEqual([p.path for p in paths], [p1, p2], "Retrieving multiple paths does not work.")

        paths = self.db.getPaths()
        self.assertEqual(paths.count(), 3, "Retrieving all paths does not work.")

        paths = self.db.getPaths(base_path="foo")
        self.assertEqual([p.path for p in paths], [p1, p2], "Retrieving paths with basepath does not work.")

    def test_deletePaths(self):
        """ Test the deletePaths function """

        p1 = os.path.join("foo", "bar1")
        p2 = os.path.join("foo", "bar2")
        p3 = os.path.join("loo", "bar1")
        self.db.setPath(path_string=p1)
        self.db.setPath(path_string=p2)
        self.db.setPath(path_string=p3)

        self.db.deletePaths(path_string=p1)
        paths = self.db.getPaths()
        self.assertEqual(paths.count(), 2, "Deleting one path does not work")
        self.db.setPath(path_string=p1)

        self.db.deletePaths(path_string=[p1, p3])
        paths = self.db.getPaths()
        self.assertEqual(paths.count(), 1, "Deleting two paths does not work")
        self.db.setPath(path_string=p1)
        self.db.setPath(path_string=p3)

        self.db.deletePaths(base_path="foo")
        paths = self.db.getPaths()
        self.assertEqual(paths.count(), 1, "Deleting two paths with base_path does not work")

    ''' Test Image functions '''
    def test_setImage(self):
        """ Test the setImage function """

        im1 = self.db.setImage("test.jpg")
        self.assertEqual(im1.filename, "test.jpg", "Creating an image didn't work")

    def test_getImage(self):
        """ Test the setImage function """
        self.db = DataFile("getImage.cdb", "w")

        self.db.setImage("test1.jpg")
        self.db.setImage("test2.jpg")
        self.db.setImage("test3.jpg")

        im = self.db.getImage(2)
        self.assertEqual(im.filename, "test3.jpg", "Getting an image does not work.")

    def test_getImages(self):
        """ Test the getImages function """

        self.db.setImage("test1.jpg")
        self.db.setImage("test2.jpg")
        self.db.setImage("test3.jpg")

        ims = self.db.getImages([1, 2])
        self.assertEqual(ims.count(), 2, "Getting images does not work")

        ims = self.db.getImageIterator(1)
        self.assertEqual([im.filename for im in ims], ["test2.jpg", "test3.jpg"], "Getting images does not work")

        self.db.setImage("test4.jpg")
        self.db.setImage("test5.jpg")
        self.db.setImage("test6.jpg")
        self.db.setImage("test7.jpg")

        ims = self.db.getImages(frame=slice(1,5))
        self.assertTrue([im.sort_index for im in ims] == [1, 2, 3, 4, 5], "Failed get by slice uppder and lower limit")

        ims = self.db.getImages(frame=slice(4, None))
        self.assertTrue([im.sort_index for im in ims] == [4, 5, 6], "Failed get by slice lower limit")

        ims = self.db.getImages(frame=slice(None, 3))
        self.assertTrue([im.sort_index for im in ims] == [0, 1, 2], "Failed get by slice uppder limit")

    def test_deleteImages(self):
        """ Test the deleteImages function """

        self.db.setImage("test1.jpg")
        self.db.setImage("test2.jpg")
        self.db.setImage("test3.jpg")

        ims = self.db.getImages()
        self.assertEqual(ims.count(), 3, "Getting images does not work")

        self.db.deleteImages(filename="test1.jpg")

        ims = self.db.getImages()
        self.assertEqual(ims.count(), 2, "Deleting image does not work")

        self.db.deleteImages(filename=["test2.jpg", "test3.jpg"])

        ims = self.db.getImages()
        self.assertEqual(ims.count(), 0, "Deleting images does not work")

    ''' Test MarkerType functions '''
    def test_setgetMarkerType_Insert(self):
        """ Test set and get MarkerType - insert variant"""

        self.db.setMarkerType('rectangle', color='#00ff00', mode=1)
        item = self.db.getMarkerType('rectangle')

        self.assertEqual(item.name, 'rectangle',"Insert MarkerType - name failed")
        self.assertEqual(item.mode, 1,"Insert MarkerType - mode failed")
        self.assertEqual(item.color, '#00ff00',"Insert MarkerType - color failed")


    def test_setgetMarkerType_Update(self):
        """ Test set and get MarkerType - update variant """

        self.db.setMarkerType('rectangle', color='#00ff00', mode=1)
        self.db.setMarkerType('rectangle', color='#00ff00')

        item = self.db.getMarkerType('rectangle')

        self.assertEqual(item.name, 'rectangle', "Update MarkerType - mode failed")
        self.assertEqual(item.mode, 1, "Update MarkerType - mode failed")
        self.assertEqual(item.color, '#00ff00', "Update MarkerType - mode failed")


    def test_getMarkerTypes(self):
        """ Test getMarkerTypes to recover a query of all available marker types"""

        markertypes = ['rectangle', 'default', 'line', 'track']
        self.db.setMarkerType('rectangle', color='#00ff00', mode=1)
        self.db.setMarkerType('default', color='#00ff00', mode=0)
        self.db.setMarkerType('line', color='#00ff00', mode=2)
        self.db.setMarkerType('track', color='#00ff00', mode=4)

        q_markertypes = self.db.getMarkerTypes()
        markertypes_from_db = [q.name for q in q_markertypes]

        self.assertEqual(markertypes, markertypes_from_db, "getMarkerTypes failed")


    def test_deleteMarkerType(self):
        """ Test deleteMarkerType to delete marker type instance"""

        self.db.setMarkerType('rectangle', color='#00ff00', mode=1)
        self.db.setMarkerType('default', color='#00ff00', mode=0)
        self.db.setMarkerType('line', color='#00ff00', mode=2)
        self.db.setMarkerType('track', color='#00ff00', mode=4)

        count = self.db.deleteMarkerTypes('line')

        q_markertypes = self.db.getMarkerTypes()
        markertypes_from_db = [q.name for q in q_markertypes]

        q_markertype = self.db.getMarkerType('line')

        self.assertEqual(count, 1)
        self.assertNotIn('line', markertypes_from_db)
        self.assertIsNone(q_markertype)


    ''' Test Track functions '''
    def test_setgetTrack(self):
        """ Test deleteMarkerType to delete marker type instance"""

        self.db.setMarkerType('track', color='#00ff00', mode=4)
        self.db.setMarkerType('track2', color='#00ff00', mode=4)

        # setTracks
        self.db.setTrack(type='track')
        self.db.setTrack(type='track')
        self.db.setTrack(type='track2')

        # unspecific getTracks
        q_tracks = self.db.getTracks()
        self.assertEqual(q_tracks.count(), 3, "Get all Tracks failed")

        # specific getTracks
        q_tracks = self.db.getTracks(type='track')
        self.assertEqual(q_tracks.count(), 2, "Get specific Tracks by type failed")

        # specific getTrack - success
        track = self.db.getTrack(id=1)
        self.assertTrue(track.id == 1, "Get specific track by ID failed")

        # specific getTrack - failed
        track = self.db.getTrack(id=100000)
        self.assertIsNone(track, "Failing to get specific track by ID failed")

    def test_deleteTrack(self):
        """ Test deleteMarkerType to delete marker type instance"""

        self.db.setMarkerType('track', color='#00ff00', mode=4)
        self.db.setMarkerType('track2', color='#00ff00', mode=4)
        self.db.setMarkerType('track3', color='#00ff00', mode=4)

        # setTracks
        self.db.setTrack(type='track')
        self.db.setTrack(type='track')
        self.db.setTrack(type='track2')
        self.db.setTrack(type='track2')
        self.db.setTrack(type='track')
        self.db.setTrack(type='track3')

        # delete specific by id
        self.db.deleteTracks(id=1)
        q_tracks = self.db.getTracks()
        self.assertEqual(q_tracks.count(), 5, "Failed to delete track by ID")

        # delete specific by type
        self.db.deleteTracks(type='track2')
        q_tracks = self.db.getTracks()
        self.assertEqual(q_tracks.count(), 3, "Failed to delete track by type")

        # delete all
        self.db.deleteTracks()
        q_tracks = self.db.getTracks()
        self.assertEqual(q_tracks.count(), 0, "Failed to complete generic delete")

    ''' Test MaskType functions '''
    def test_getMaskType(self):
        """ Test the getMaskType function """

        masktype = self.db.getMaskType(name="color")
        self.assertEqual(masktype, None, "Getting non-existent mask does not work")

        self.db.setMaskType("mask1","#FF00FF",index=10)
        mask = self.db.getMaskType(color="#ff00FF")
        self.assertIsNotNone(mask, "Failed retrieving mask type by color")


    def test_setMaskType(self):
        """ Test the setMaskType function """

        self.db.setMaskType(name="color", color="#FF0000", index=2)
        masktype = self.db.getMaskType(name="color")
        self.assertEqual(masktype.name, "color", "Creating a new mask type does not work")

        self.db.setMaskType(id=masktype.id, name="color2", color="#FF0000", index=2)
        masktype = self.db.getMaskType(id=masktype.id)
        self.assertEqual(masktype.name, "color2", "Alterning a mask type does not work")

        # suppose free indieces are 1,3,4
        self.db.setMaskType(name="color3", color="#FF0000")
        self.db.setMaskType(name="color4", color="#FF0000")
        masktype = self.db.setMaskType(name="color5", color="#FF0000")
        self.assertTrue(masktype.index == 4,"Failed to automatically create correct index entries")

    def test_getMaskTypes(self):
        """ Test the getMaskTypes function """

        self.db.setMaskType(name="color1", color="#FF1c00", index=1)
        self.db.setMaskType(name="color2", color="#FF00ff", index=2)
        self.db.setMaskType(name="color3", color="#FF00FF", index=3)
        self.db.setMaskType(name="color4", color="#FFFFFF", index=4)

        # get by single name
        masktypes = self.db.getMaskTypes(name="color1")
        self.assertEqual([m.name for m in masktypes], ["color1"], "Retrieving one mask type does not work")

        # get by  multiple names
        masktypes = self.db.getMaskTypes(name=["color1", "color2"])
        self.assertEqual([m.name for m in masktypes], ["color1", "color2"], "Retrieving two mask types does not work")

        # get by multiple colors (checking NormalizeColor function)
        masktypes = self.db.getMaskTypes(color=["#ff00ff", "#ff1c00"])
        self.assertTrue(masktypes.count() == 3, "Retrieving multiple mask by colors (normalized string) failed")

    def test_deleteMaskTypes(self):
        """ Test the deleteMaskTypes function """

        self.db.setMaskType(name="color1", color="#FF0000", index=1)
        self.db.setMaskType(name="color2", color="#FF0000", index=2)
        self.db.setMaskType(name="color3", color="#FF0000", index=3)

        # delete by single name
        self.db.deleteMaskTypes(name="color1")
        masktypes = self.db.getMaskTypes()
        self.assertEqual(masktypes.count(), 2, "Deleting one mask type does not work")

        #delete by multiple names
        self.db.deleteMaskTypes(name=["color2", "color3"])
        masktypes = self.db.getMaskTypes()
        self.assertEqual(masktypes.count(), 0, "Deleting two mask types does not work")

        # delete by color (check normalize)
        self.db.setMaskType(name="color1", color="#FF0000", index=1)
        self.db.setMaskType(name="color2", color="#FF0000", index=2)
        self.db.setMaskType(name="color3", color="#FF0000", index=3)

        self.db.deleteMaskTypes(color=["#ff0000"])
        masktypes = self.db.getMaskTypes()
        self.assertEqual(masktypes.count(), 0, "Failed deleting mask types by color")

        # check for exception
        # self.db.deleteMaskTypes(color=["#ff000"])
        # self.assertRaises(DataFile.CheckValidColor.NoValidColor)


    ''' Test Mask functions '''
    def test_setMask(self):
        """ Test the setMask function """
        im = self.db.setImage(filename="test.jpg", width=100, height=100)
        im2 = self.db.setImage(filename="test2.jpg", width=100, height=100)
        im3 = self.db.setImage(filename="test3.jpg", width=100, height=100)
        masktype = self.db.setMaskType(name="color", color="#FF0000", index=2)
        masktype2 = self.db.setMaskType(name="color2", color="#FF0000")
        mask = self.db.setMask(image=im)
        self.assertTrue(mask.image==im,  "Failed adding a new mask")

        mdata = np.ones((100,100),dtype='uint8')
        mask = self.db.setMask(image=im, data=mdata)
        mask = self.db.getMask(image=im)
        self.assertTrue(np.array_equal(mask.data,mdata), "Failed updating mask data")

        # update with wrong dtype
        mdata = np.ones((100,100),dtype='int16')
        self.assertRaises(clickpoints.MaskDtypeMismatch, self.db.setMask,image=im, data=mdata)
        # insert with wrong dimension
        mdata = np.ones((100, 50), dtype='uint8')
        self.assertRaises(clickpoints.MaskDimensionMismatch, self.db.setMask, image=im, data=mdata)

        # insert with wrong dtype
        mdata = np.ones((100,100),dtype='int8')
        self.assertRaises(clickpoints.MaskDtypeMismatch, self.db.setMask,image=im2, data=mdata)
        # insert with wrong dimension
        mdata = np.ones((100, 50), dtype='uint8')
        self.assertRaises(clickpoints.MaskDimensionMismatch, self.db.setMask, image=im3, data=mdata)

    def test_getMask(self):
        im1 = self.db.setImage(filename="test1.jpg", width=100, height=100)
        im2 = self.db.setImage(filename="test2.jpg", width=100, height=100)
        im3 = self.db.setImage(filename="test3.jpg", width=100, height=100)
        im4 = self.db.setImage(filename="test4.jpg", width=100, height=100)
        im5 = self.db.setImage(filename="test5.jpg")

        mask = self.db.setMask(image=im1)
        mask = self.db.setMask(image=im2)

        # retrieve by filename
        mask = self.db.getMask(filename='test2.jpg')
        self.assertTrue(mask.image.filename == im2.filename,"Failed retrieving mask by image filename")

        # retrieve by filename + create
        mask = self.db.getMask(filename='test3.jpg',create=True)
        self.assertTrue(mask.image.filename == 'test3.jpg', "Failed creating mask on getMask")

        # retrieve by image + create
        mask = self.db.getMask(image=im4, create=True)
        self.assertTrue(mask.image.filename == 'test4.jpg', "Failed creating mask on getMask")

        # retrieve by filename which doesn't have an image entry
        self.assertRaises(clickpoints.ImageDoesNotExist, self.db.getMask, filename='testDOESNTEXIST.jpg', create=True)
        # retrieve by image where image has now width and height or file
        self.assertRaises(clickpoints.MaskDimensionUnknown, self.db.getMask, image=im5, create=True)


    def test_getMasks(self):
        im1 = self.db.setImage(filename="test1.jpg", width=100, height=100)
        im2 = self.db.setImage(filename="test2.jpg", width=100, height=100)
        im3 = self.db.setImage(filename="test3.jpg", width=100, height=100)

        mask = self.db.setMask(image=im1)
        mask = self.db.setMask(image=im2)
        mask = self.db.setMask(image=im3)

        # get all
        masks = self.db.getMasks()
        self.assertTrue(masks.count() == 3, 'Failed to retrieve all masks without parameter')

        # get multiple by image list
        masks = self.db.getMasks(image=[im1,im2])
        self.assertTrue(masks.count() == 2, 'Failed to retrieve masks by images ')

        # get multiple by image ids
        masks = self.db.getMasks(frame=[1,2])
        self.assertTrue(masks.count() == 2, 'Failed to retrieve masks by frames ')

        # get multiple by image filenames
        masks = self.db.getMasks(filename=['test1.jpg','test3.jpg'])
        self.assertTrue(masks.count() == 2, 'Failed to retrieve masks by filenames ')

        # get multiple by image ids
        masks = self.db.getMasks(frame=[0, 2])
        self.assertTrue(masks.count() == 2, 'Failed to retrieve masks by ids ')

    def test_deleteMasks(self):
        """ test delete masks function """
        im1 = self.db.setImage(filename="test1.jpg", width=100, height=100)
        im2 = self.db.setImage(filename="test2.jpg", width=100, height=100)
        im3 = self.db.setImage(filename="test3.jpg", width=100, height=100)

        mask = self.db.setMask(image=im1)
        mask = self.db.setMask(image=im2)
        mask = self.db.setMask(image=im3)

        # single delete by images
        self.db.deleteMasks(image=im1)
        masks = self.db.getMasks()
        self.assertTrue(masks.count() == 2, 'Failed to to delete single mask by image')

        # single delete by filename
        self.db.deleteMasks(filename="test3.jpg")
        masks = self.db.getMasks()
        self.assertTrue(masks.count() == 1, 'Failed to to delete single mask by image')

        # delete all masks
        self.db.deleteMasks()
        masks = self.db.getMasks()
        self.assertTrue(masks.count() == 0, 'Failed to to delete all masks')

    ''' Test Marker functions '''

    def test_setMarker(self):
        """ Test the setMarker function """

        # Basic db structure
        marker_type = self.db.setMarkerType(name="Test", color="#FF0000")
        image = self.db.setImage("test.jpg")

        # test to set a marker with image_id
        marker = self.db.setMarker(image=image.id, x=123, y=0, type=marker_type)
        self.assertEqual(marker.x, 123, "Setting marker does not work properly.")

        # with filename and type name
        marker = self.db.setMarker(filename="test.jpg", x=123, y=20, type="Test")
        self.assertEqual(marker.x, 123, "Setting marker does not work properly.")

        # with frame number
        marker = self.db.setMarker(frame=0, x=123, y=0, type=marker_type)
        self.assertEqual(marker.x, 123, "Setting marker does not work properly.")

        # with id
        marker = self.db.setMarker(x=123, y=0, id=marker)
        self.assertEqual(marker.x, 123, "Setting marker does not work properly.")

        # with invalid frame number
        self.assertRaises(clickpoints.ImageDoesNotExist, self.db.setMarker, frame=1, x=123, y=0, type=marker_type)

        # with invalid filename
        self.assertRaises(clickpoints.ImageDoesNotExist, self.db.setMarker, filename="no.jpg", x=123, y=0,
                          type=marker_type)

        # with invalid type na,e
        self.assertRaises(clickpoints.MarkerTypeDoesNotExist, self.db.setMarker, image=1, x=123, y=0, type="NoType")

        # without image
        self.assertRaises(AssertionError, self.db.setMarker, x=123, y=0)

        # without id
        self.assertRaises(AssertionError, self.db.setMarker, x=123, y=0, type=marker_type)

    def test_getMarker(self):
        """ Test the getMarker function """

        # basic db structure
        marker_type1 = self.db.setMarkerType(name="Test1", color="#FF0000")
        image1 = self.db.setImage("test1.jpg")
        self.db.setMarker(image=image1, x=456, y=2, type=marker_type1)

        # get a valid marker
        marker = self.db.getMarker(id=1)
        self.assertEqual(marker.x, 456, "Getting marker does not work properly.")

        # get an invalid marker
        marker = self.db.getMarker(id=0)
        self.assertEqual(marker, None, "Getting marker does not work properly.")

    def test_getMarkers(self):
        """ Test the getMarker function """

        # basic db structure
        marker_type1 = self.db.setMarkerType(name="Test1", color="#FF0000")
        marker_type2 = self.db.setMarkerType(name="Test2", color="#00FF00")
        marker_type3 = self.db.setMarkerType(name="Track", color="#00FF00")

        image1 = self.db.setImage("test1.jpg")
        image2 = self.db.setImage("test2.jpg")
        image3 = self.db.setImage("test3.jpg")
        image4 = self.db.setImage("test4.jpg")

        track1 = self.db.setTrack(marker_type3)
        track2 = self.db.setTrack(marker_type3)

        self.db.setMarkers(image=image1, x=[1, 2, 3, 4, 5], y=[0, 0, 0, 0, 0], type=marker_type1)
        self.db.setMarkers(image=image1, x=[1, 2, 3, 4, 5], y=[0, 0, 0, 0, 0], type=marker_type2)
        self.db.setMarkers(image=image2, x=[1, 2, 3, 4, 5], y=[0, 0, 0, 0, 0], type=marker_type1)
        self.db.setMarkers(image=[image3, image4], x=[10, 20], y=[0, 0], track=track1)
        self.db.setMarkers(image=[image3, image4], x=[10, 20], y=[0, 0], track=track2)

        # get image list
        markers = self.db.getMarkers(image=[image1, image2])
        self.assertEqual(markers.count(), 15, "Getting markers does not work properly.")

        # get single image
        markers = self.db.getMarkers(image=image1)
        self.assertEqual(markers.count(), 10, "Getting markers does not work properly.")

        # get by image frame
        markers = self.db.getMarkers(frame=0)
        self.assertEqual(markers.count(), 10, "Getting markers does not work properly.")

        # get by image filenames
        markers = self.db.getMarkers(filename=["test1.jpg", "test2.jpg"])
        self.assertEqual(markers.count(), 15, "Getting markers does not work properly.")

        # get by x coordinates
        markers = self.db.getMarkers(x=[2, 3])
        self.assertEqual(markers.count(), 6, "Getting markers does not work properly.")

        # get by x and y coordinates
        markers = self.db.getMarkers(x=[2, 3], y=[0, 1, 2])
        self.assertEqual(markers.count(), 6, "Getting markers does not work properly.")

        # get by type
        markers = self.db.getMarkers(type=marker_type1)
        self.assertEqual(markers.count(), 10, "Getting markers does not work properly.")

        # get by type list
        markers = self.db.getMarkers(type=["Test1", "Test2"])
        self.assertEqual(markers.count(), 15, "Getting markers does not work properly.")

        # test invalid type name
        self.assertRaises(clickpoints.MarkerTypeDoesNotExist, self.db.getMarkers, type=["NoType"])

        # test by track
        markers = self.db.getMarkers(track=track1)
        self.assertEqual(markers.count(), 2, "Getting markers does not work properly.")

    def test_setMarkersX(self):
        print(self.db.table_marker.processed.default)
        print(self.db.table_marker.image.default)

    def test_setMarkers(self):
        """ Test the setMarkers function """

        # set up db
        marker_type1 = self.db.setMarkerType(name="Test1", color="#FF0000")
        marker_type2 = self.db.setMarkerType(name="Test2", color="#00FF00")
        marker_type3 = self.db.setMarkerType(name="Track", color="#00FF00", mode=self.db.TYPE_Track)

        image1 = self.db.setImage("test1.jpg")
        image2 = self.db.setImage("test2.jpg")
        image3 = self.db.setImage("test3.jpg")
        image4 = self.db.setImage("test4.jpg")

        track1 = self.db.setTrack(marker_type3)
        track2 = self.db.setTrack(marker_type3)

        # test multiple markers for one image
        self.db.setMarkers(image=image1, x=[1, 2, 3, 4, 5], y=[0, 0, 0, 0, 0], type=marker_type1)
        self.assertEqual(self.db.getMarkers().count(), 5, "Setting markers does not work properly.")
        self.db.deleteMarkers()

        # test multiple images
        self.db.setMarkers(image=[image1, image2], x=[1, 2], y=[0, 0], type=marker_type1)
        self.assertEqual(self.db.getMarkers().count(), 2, "Setting markers does not work properly.")
        self.db.deleteMarkers()

        # test multiple types
        self.db.setMarkers(image=image1, x=1, y=0, type=[marker_type1, marker_type2])
        self.assertEqual(self.db.getMarkers().count(), 2, "Setting markers does not work properly.")
        self.db.deleteMarkers()

        # test multiple texts and one style
        self.db.setMarkers(image=image1, x=1, y=0, type=marker_type1, text=["foo", "bar", "hu"], style="{}")
        self.assertEqual(self.db.getMarkers().count(), 3, "Setting markers does not work properly.")
        self.db.deleteMarkers()

        # test image by filename
        self.db.setMarkers(filename="test2.jpg", x=1, y=0, type=marker_type2)
        self.assertEqual(self.db.getMarkers().count(), 1, "Setting markers does not work properly.")
        self.db.deleteMarkers()

        # test images by frames
        self.db.setMarkers(frame=[0, 1, 2], x=1, y=0, type=marker_type2)
        self.assertEqual(self.db.getMarkers().count(), 3, "Setting markers does not work properly.")
        self.db.deleteMarkers()

        # test to set for one track multiple images
        self.db.setMarkers(frame=0, x=1, y=0, track=track1)
        self.assertEqual(self.db.getMarkers().count(), 1, "Setting markers does not work properly.")
        ms = self.db.getMarkers(track=track1)
        for m in ms:
            print("a", m)
        self.db.setMarkers(frame=0, processed=1, track=track1)
        ms = self.db.getMarkers(track=track1)
        for m in ms:
            print("b", m)
        self.assertEqual(self.db.getMarkers().count(), 1, "Setting markers does not work properly.")
        self.db.deleteMarkers()

        # test set and update two tracks
        track1 = self.db.setTrack(marker_type3)
        track2 = self.db.setTrack(marker_type3)
        self.db.setMarkers(image=image1, x=np.array([1, 2]), y=np.array([10, 20]), track=[track1, track2])
        self.assertEqual(sum(m.processed == 0 for m in self.db.getMarkers(image=image1)), 2, "Setting markers does not work properly.")
        self.db.setMarkers(frame=0, processed=1, track=[track1, track2])
        self.assertEqual(sum(m.processed == 1 for m in self.db.getMarkers(image=image1)), 2, "Setting markers does not work properly.")
        self.db.deleteMarkers()

        # test one track multiple coordinates -> should result in only one marker
        track2 = self.db.setTrack(marker_type3)
        self.db.setMarkers(image=image1, x=[0, 1, 2], y=0, track=track2)
        self.assertEqual(self.db.getMarkers().count(), 1, "Setting markers does not work properly.")
        self.db.deleteMarkers()

        # set and update markers
        self.db.setMarkers(image=image1, x=[0, 1, 2], y=[0, 1, 2], type=marker_type1)
        markers = self.db.getMarkers()
        self.assertTrue(all(m.x < 10 for m in markers), "Setting markers does not work properly.")
        self.db.setMarkers(x=[10, 20, 30], y=[0, 1, 2], id=[m for m in markers])
        markers = self.db.getMarkers()
        self.assertTrue(all(m.x >= 10 for m in markers), "Setting markers does not work properly.")
        self.db.deleteMarkers()

    def test_deleteMarkers(self):
        """ Test the deleteMarkers function """

        # set up db
        marker_type1 = self.db.setMarkerType(name="Test1", color="#FF0000")
        marker_type2 = self.db.setMarkerType(name="Test2", color="#00FF00")
        marker_type3 = self.db.setMarkerType(name="Track", color="#00FF00", mode=self.db.TYPE_Track)

        image1 = self.db.setImage("test1.jpg")
        image2 = self.db.setImage("test2.jpg")
        image3 = self.db.setImage("test3.jpg")
        image4 = self.db.setImage("test4.jpg")

        track1 = None
        track2 = None

        def CreateMarkers():
            global track1, track2
            self.db.deleteMarkers()
            self.db.deleteTracks()
            track1 = self.db.setTrack(marker_type3)
            track2 = self.db.setTrack(marker_type3)
            self.db.setMarkers(image=image1, x=[1, 2, 3, 4, 5], y=[0, 0, 0, 0, 0], type=marker_type1)
            self.db.setMarkers(image=image2, x=[1, 2, 3, 4, 5], y=[0, 0, 0, 0, 0], processed=True, text="foo",
                               type=marker_type1)
            self.db.setMarkers(image=image1, x=[1, 2, 3, 4, 5], y=[0, 0, 0, 0, 0], text="bar", type=marker_type2)
            self.db.setMarkers(image=[image1, image2, image3, image4], x=1, y=3, track=track1)

        # delete from one image
        CreateMarkers()
        self.db.deleteMarkers(image=image1)
        self.assertEqual(self.db.getMarkers().count(), 8, "Deleting markers does not work properly.")
        self.db.deleteMarkers()

        # delete from two images
        CreateMarkers()
        self.db.deleteMarkers(image=[image1, image2])
        self.assertEqual(self.db.getMarkers().count(), 2, "Deleting markers does not work properly.")
        self.db.deleteMarkers()

        # delete by filename
        CreateMarkers()
        self.db.deleteMarkers(filename="test2.jpg")
        self.assertEqual(self.db.getMarkers().count(), 13, "Deleting markers does not work properly.")
        self.db.deleteMarkers()

        # delete by filename
        CreateMarkers()
        self.db.deleteMarkers(frame=1)
        self.assertEqual(self.db.getMarkers().count(), 13, "Deleting markers does not work properly.")
        self.db.deleteMarkers()

        # delete by x coordinate
        CreateMarkers()
        self.db.deleteMarkers(x=slice(2, 4))
        self.assertEqual(self.db.getMarkers().count(), 10, "Deleting markers does not work properly.")
        self.db.deleteMarkers()

        # delete by processed
        CreateMarkers()
        self.db.deleteMarkers(processed=True)
        self.assertEqual(self.db.getMarkers().count(), 14, "Deleting markers does not work properly.")
        self.db.deleteMarkers()

        # delete by text
        CreateMarkers()
        self.db.deleteMarkers(text="foo")
        self.assertEqual(self.db.getMarkers().count(), 14, "Deleting markers does not work properly.")
        self.db.deleteMarkers()

        # delete by id
        CreateMarkers()
        ids = [m.id for m in self.db.getMarkers(text="foo")]
        self.db.deleteMarkers(id=ids)
        self.assertEqual(self.db.getMarkers().count(), 14, "Deleting markers does not work properly.")
        self.db.deleteMarkers()

        # delete by track
        CreateMarkers()
        self.db.deleteMarkers(track=self.db.getTracks())
        self.assertEqual(self.db.getMarkers().count(), 15, "Deleting markers does not work properly.")
        self.db.deleteMarkers()

        # delete by type
        CreateMarkers()
        self.db.deleteMarkers(type="Test1")
        self.assertEqual(self.db.getMarkers().count(), 9, "Deleting markers does not work properly.")
        self.db.deleteMarkers()

    ''' Test Line functions '''

    def test_setLine(self):
        """ Test the setLine function """

        # Basic db structure
        Line_type = self.db.setMarkerType(name="Test", color="#FF0000", mode=self.db.TYPE_Line)
        image = self.db.setImage("test.jpg")

        # test to set a Line with image_id
        Line = self.db.setLine(image=image.id, x1=123, y1=0, x2=10, y2=10, type=Line_type)
        self.assertEqual(Line.x1, 123, "Setting Line does not work properly.")

        # with filename and type name
        Line = self.db.setLine(filename="test.jpg", x1=123, y1=0, x2=10, y2=10, type="Test")
        self.assertEqual(Line.x1, 123, "Setting Line does not work properly.")

        # with frame number
        Line = self.db.setLine(frame=0, x1=123, y1=0, x2=10, y2=10, type=Line_type)
        self.assertEqual(Line.x1, 123, "Setting Line does not work properly.")

        # with id
        Line = self.db.setLine(x1=123, y1=0, x2=10, y2=10, id=Line)
        self.assertEqual(Line.x1, 123, "Setting Line does not work properly.")

        # with invalid frame number
        self.assertRaises(clickpoints.ImageDoesNotExist, self.db.setLine, frame=1, x1=123, y1=0, x2=10, y2=10, type=Line_type)

        # with invalid filename
        self.assertRaises(clickpoints.ImageDoesNotExist, self.db.setLine, filename="no.jpg", x1=123, y1=0, x2=10, y2=10, type=Line_type)

        # with invalid type na,e
        self.assertRaises(clickpoints.MarkerTypeDoesNotExist, self.db.setLine, image=1, x1=123, y1=0, x2=10, y2=10, type="NoType")

        # without image
        self.assertRaises(AssertionError, self.db.setLine, x1=123, y1=0, x2=10, y2=10,)

        # without id
        self.assertRaises(AssertionError, self.db.setLine, x1=123, y1=0, x2=10, y2=10, type=Line_type)

    def test_getLine(self):
        """ Test the getLine function """

        # basic db structure
        Line_type1 = self.db.setMarkerType(name="Test1", color="#FF0000")
        image1 = self.db.setImage("test1.jpg")
        self.db.setLine(image=image1, x1=456, y1=0, x2=10, y2=10, type=Line_type1)

        # get a valid Line
        Line = self.db.getLine(id=1)
        self.assertEqual(Line.x1, 456, "Getting Line does not work properly.")

        # get an invalid Line
        Line = self.db.getLine(id=0)
        self.assertEqual(Line, None, "Getting Line does not work properly.")

    def test_getLines(self):
        """ Test the getLine function """

        # basic db structure
        Line_type1 = self.db.setMarkerType(name="Test1", color="#FF0000")
        Line_type2 = self.db.setMarkerType(name="Test2", color="#00FF00")
        Line_type3 = self.db.setMarkerType(name="Track", color="#00FF00")

        image1 = self.db.setImage("test1.jpg")
        image2 = self.db.setImage("test2.jpg")
        image3 = self.db.setImage("test3.jpg")
        image4 = self.db.setImage("test4.jpg")

        self.db.setLines(image=image1, x1=[1, 2, 3, 4, 5], y1=[0, 0, 0, 0, 0], x2=[1, 2, 3, 4, 5], y2=[1, 1, 1, 1, 1], type=Line_type1)
        self.db.setLines(image=image1, x1=[1, 2, 3, 4, 5], y1=[0, 0, 0, 0, 0], x2=[1, 2, 3, 4, 5], y2=[1, 1, 1, 1, 1], type=Line_type2)
        self.db.setLines(image=image2, x1=[1, 2, 3, 4, 5], y1=[0, 0, 0, 0, 0], x2=[1, 2, 3, 4, 5], y2=[1, 1, 1, 1, 1], type=Line_type1)

        # get image list
        Lines = self.db.getLines(image=[image1, image2])
        self.assertEqual(Lines.count(), 15, "Getting Lines does not work properly.")

        # get single image
        Lines = self.db.getLines(image=image1)
        self.assertEqual(Lines.count(), 10, "Getting Lines does not work properly.")

        # get by image frame
        Lines = self.db.getLines(frame=0)
        self.assertEqual(Lines.count(), 10, "Getting Lines does not work properly.")

        # get by image filenames
        Lines = self.db.getLines(filename=["test1.jpg", "test2.jpg"])
        self.assertEqual(Lines.count(), 15, "Getting Lines does not work properly.")

        # get by x coordinates
        Lines = self.db.getLines(x1=[2, 3])
        self.assertEqual(Lines.count(), 6, "Getting Lines does not work properly.")

        # get by x and y coordinates
        Lines = self.db.getLines(x1=[2, 3], y1=[0, 1, 2])
        self.assertEqual(Lines.count(), 6, "Getting Lines does not work properly.")

        # get by type
        Lines = self.db.getLines(type=Line_type1)
        self.assertEqual(Lines.count(), 10, "Getting Lines does not work properly.")

        # get by type list
        Lines = self.db.getLines(type=["Test1", "Test2"])
        self.assertEqual(Lines.count(), 15, "Getting Lines does not work properly.")

        # test invalid type name
        self.assertRaises(clickpoints.MarkerTypeDoesNotExist, self.db.getLines, type=["NoType"])

    def test_setLines(self):
        """ Test the setLines function """

        # set up db
        Line_type1 = self.db.setMarkerType(name="Test1", color="#FF0000")
        Line_type2 = self.db.setMarkerType(name="Test2", color="#00FF00")
        Line_type3 = self.db.setMarkerType(name="Track", color="#00FF00", mode=self.db.TYPE_Track)

        image1 = self.db.setImage("test1.jpg")
        image2 = self.db.setImage("test2.jpg")
        image3 = self.db.setImage("test3.jpg")
        image4 = self.db.setImage("test4.jpg")

        track1 = self.db.setTrack(Line_type3)
        track2 = self.db.setTrack(Line_type3)

        # test multiple Lines for one image
        self.db.setLines(image=image1, x1=[1, 2, 3, 4, 5], y1=[0, 0, 0, 0, 0], x2=[1, 2, 3, 4, 5], y2=[0, 0, 0, 0, 0], type=Line_type1)
        self.assertEqual(self.db.getLines().count(), 5, "Setting Lines does not work properly.")
        self.db.deleteLines()

        # test multiple images
        self.db.setLines(image=[image1, image2], x1=[1, 2], y1=[0, 0], x2=[1, 2], y2=[0, 0], type=Line_type1)
        self.assertEqual(self.db.getLines().count(), 2, "Setting Lines does not work properly.")
        self.db.deleteLines()

        # test multiple types
        self.db.setLines(image=image1, x1=1, y1=0, x2=10, y2=20, type=[Line_type1, Line_type2])
        self.assertEqual(self.db.getLines().count(), 2, "Setting Lines does not work properly.")
        self.db.deleteLines()

        # test multiple texts and one style
        self.db.setLines(image=image1, x1=1, y1=0, x2=10, y2=20, type=Line_type1, text=["foo", "bar", "hu"], style="{}")
        self.assertEqual(self.db.getLines().count(), 3, "Setting Lines does not work properly.")
        self.db.deleteLines()

        # test image by filename
        self.db.setLines(filename="test2.jpg", x1=1, y1=0, x2=10, y2=20, type=Line_type2)
        self.assertEqual(self.db.getLines().count(), 1, "Setting Lines does not work properly.")
        self.db.deleteLines()

        # test images by frames
        self.db.setLines(frame=[0, 1, 2], x1=1, y1=0, x2=10, y2=20, type=Line_type2)
        self.assertEqual(self.db.getLines().count(), 3, "Setting Lines does not work properly.")
        self.db.deleteLines()

        # set and update Lines
        self.db.setLines(image=image1, x1=[0, 1, 2], y1=[0, 1, 2], x2=0, y2=0, type=Line_type1)
        Lines = self.db.getLines()
        self.assertTrue(all(m.x1 < 10 for m in Lines), "Setting Lines does not work properly.")
        self.db.setLines(x1=[10, 20, 30], y1=[0, 1, 2], x2=0, y2=0, id=[m for m in Lines])
        Lines = self.db.getLines()
        self.assertTrue(all(m.x1 >= 10 for m in Lines), "Setting Lines does not work properly.")
        self.db.deleteLines()

    def test_deleteLines(self):
        """ Test the deleteLines function """

        # set up db
        Line_type1 = self.db.setMarkerType(name="Test1", color="#FF0000")
        Line_type2 = self.db.setMarkerType(name="Test2", color="#00FF00")
        Line_type3 = self.db.setMarkerType(name="Track", color="#00FF00", mode=self.db.TYPE_Track)

        image1 = self.db.setImage("test1.jpg")
        image2 = self.db.setImage("test2.jpg")
        image3 = self.db.setImage("test3.jpg")
        image4 = self.db.setImage("test4.jpg")

        def CreateLines():
            track1 = self.db.setTrack(Line_type3)
            track2 = self.db.setTrack(Line_type3)
            self.db.setLines(image=image1, x1=[1, 2, 3, 4, 5], y1=[0, 0, 0, 0, 0], x2=0, y2=0, type=Line_type1)
            self.db.setLines(image=image2, x1=[1, 2, 3, 4, 5], y1=[0, 0, 0, 0, 0], x2=0, y2=0, processed=True, text="foo",
                             type=Line_type1)
            self.db.setLines(image=image1, x1=[1, 2, 3, 4, 5], y1=[0, 0, 0, 0, 0], x2=0, y2=0, text="bar", type=Line_type2)

        # delete from one image
        CreateLines()
        self.db.deleteLines(image=image1)
        self.assertEqual(self.db.getLines().count(), 5, "Deleting Lines does not work properly.")
        self.db.deleteLines()

        # delete from two images
        CreateLines()
        self.db.deleteLines(image=[image1, image2])
        self.assertEqual(self.db.getLines().count(), 0, "Deleting Lines does not work properly.")
        self.db.deleteLines()

        # delete by filename
        CreateLines()
        self.db.deleteLines(filename="test2.jpg")
        self.assertEqual(self.db.getLines().count(), 10, "Deleting Lines does not work properly.")
        self.db.deleteLines()

        # delete by filename
        CreateLines()
        self.db.deleteLines(frame=1)
        self.assertEqual(self.db.getLines().count(), 10, "Deleting Lines does not work properly.")
        self.db.deleteLines()

        # delete by x coordinate
        CreateLines()
        self.db.deleteLines(x1=slice(2, 4))
        self.assertEqual(self.db.getLines().count(), 6, "Deleting Lines does not work properly.")
        self.db.deleteLines()

        # delete by processed
        CreateLines()
        self.db.deleteLines(processed=True)
        self.assertEqual(self.db.getLines().count(), 10, "Deleting Lines does not work properly.")
        self.db.deleteLines()

        # delete by text
        CreateLines()
        self.db.deleteLines(text="foo")
        self.assertEqual(self.db.getLines().count(), 10, "Deleting Lines does not work properly.")
        self.db.deleteLines()

        # delete by id
        CreateLines()
        ids = [m.id for m in self.db.getLines(text="foo")]
        self.db.deleteLines(id=ids)
        self.assertEqual(self.db.getLines().count(), 10, "Deleting Lines does not work properly.")
        self.db.deleteLines()

        # delete by type
        CreateLines()
        self.db.deleteLines(type="Test1")
        self.assertEqual(self.db.getLines().count(), 5, "Deleting Lines does not work properly.")
        self.db.deleteLines()

    ''' Test Rectangle functions '''

    def test_setRectangle(self):
        """ Test the setRectangle function """

        # Basic db structure
        Rectangle_type = self.db.setMarkerType(name="Test", color="#FF0000", mode=self.db.TYPE_Rect)
        image = self.db.setImage("test.jpg")

        # test to set a Rectangle with image_id
        Rectangle = self.db.setRectangle(image=image.id, x=123, y=0, width=10, height=10, type=Rectangle_type)
        self.assertEqual(Rectangle.x, 123, "Setting Rectangle does not work properly.")

        # with filename and type name
        Rectangle = self.db.setRectangle(filename="test.jpg", x=123, y=0, width=10, height=10, type="Test")
        self.assertEqual(Rectangle.x, 123, "Setting Rectangle does not work properly.")

        # with frame number
        Rectangle = self.db.setRectangle(frame=0, x=123, y=0, width=10, height=10, type=Rectangle_type)
        self.assertEqual(Rectangle.x, 123, "Setting Rectangle does not work properly.")

        # with id
        Rectangle = self.db.setRectangle(x=123, y=0, width=10, height=10, id=Rectangle)
        self.assertEqual(Rectangle.x, 123, "Setting Rectangle does not work properly.")

        # with invalid frame number
        self.assertRaises(clickpoints.ImageDoesNotExist, self.db.setRectangle, frame=1, x=123, y=0, width=10, height=10,
                          type=Rectangle_type)

        # with invalid filename
        self.assertRaises(clickpoints.ImageDoesNotExist, self.db.setRectangle, filename="no.jpg", x=123, y=0, width=10,
                          height=10, type=Rectangle_type)

        # with invalid type na,e
        self.assertRaises(clickpoints.MarkerTypeDoesNotExist, self.db.setRectangle, image=1, x=123, y=0, width=10,
                          height=10, type="NoType")

        # without image
        self.assertRaises(AssertionError, self.db.setRectangle, x=123, y=0, width=10, height=10, )

        # without id
        self.assertRaises(AssertionError, self.db.setRectangle, x=123, y=0, width=10, height=10, type=Rectangle_type)

    def test_getRectangle(self):
        """ Test the getRectangle function """

        # basic db structure
        Rectangle_type1 = self.db.setMarkerType(name="Test1", color="#FF0000")
        image1 = self.db.setImage("test1.jpg")
        self.db.setRectangle(image=image1, x=456, y=0, width=10, height=10, type=Rectangle_type1)

        # get a valid Rectangle
        Rectangle = self.db.getRectangle(id=1)
        self.assertEqual(Rectangle.x, 456, "Getting Rectangle does not work properly.")

        # get an invalid Rectangle
        Rectangle = self.db.getRectangle(id=0)
        self.assertEqual(Rectangle, None, "Getting Rectangle does not work properly.")

    def test_getRectangles(self):
        """ Test the getRectangle function """

        # basic db structure
        Rectangle_type1 = self.db.setMarkerType(name="Test1", color="#FF0000")
        Rectangle_type2 = self.db.setMarkerType(name="Test2", color="#00FF00")
        Rectangle_type3 = self.db.setMarkerType(name="Track", color="#00FF00")

        image1 = self.db.setImage("test1.jpg")
        image2 = self.db.setImage("test2.jpg")
        image3 = self.db.setImage("test3.jpg")
        image4 = self.db.setImage("test4.jpg")

        self.db.setRectangles(image=image1, x=[1, 2, 3, 4, 5], y=[0, 0, 0, 0, 0], width=[1, 2, 3, 4, 5],
                              height=[1, 1, 1, 1, 1], type=Rectangle_type1)
        self.db.setRectangles(image=image1, x=[1, 2, 3, 4, 5], y=[0, 0, 0, 0, 0], width=[1, 2, 3, 4, 5],
                              height=[1, 1, 1, 1, 1], type=Rectangle_type2)
        self.db.setRectangles(image=image2, x=[1, 2, 3, 4, 5], y=[0, 0, 0, 0, 0], width=[1, 2, 3, 4, 5],
                              height=[1, 1, 1, 1, 1], type=Rectangle_type1)

        # get image list
        Rectangles = self.db.getRectangles(image=[image1, image2])
        self.assertEqual(Rectangles.count(), 15, "Getting Rectangles does not work properly.")

        # get single image
        Rectangles = self.db.getRectangles(image=image1)
        self.assertEqual(Rectangles.count(), 10, "Getting Rectangles does not work properly.")

        # get by image frame
        Rectangles = self.db.getRectangles(frame=0)
        self.assertEqual(Rectangles.count(), 10, "Getting Rectangles does not work properly.")

        # get by image filenames
        Rectangles = self.db.getRectangles(filename=["test1.jpg", "test2.jpg"])
        self.assertEqual(Rectangles.count(), 15, "Getting Rectangles does not work properly.")

        # get by x coordinates
        Rectangles = self.db.getRectangles(x=[2, 3])
        self.assertEqual(Rectangles.count(), 6, "Getting Rectangles does not work properly.")

        # get by x and y coordinates
        Rectangles = self.db.getRectangles(x=[2, 3], y=[0, 1, 2])
        self.assertEqual(Rectangles.count(), 6, "Getting Rectangles does not work properly.")

        # get by type
        Rectangles = self.db.getRectangles(type=Rectangle_type1)
        self.assertEqual(Rectangles.count(), 10, "Getting Rectangles does not work properly.")

        # get by type list
        Rectangles = self.db.getRectangles(type=["Test1", "Test2"])
        self.assertEqual(Rectangles.count(), 15, "Getting Rectangles does not work properly.")

        # test invalid type name
        self.assertRaises(clickpoints.MarkerTypeDoesNotExist, self.db.getRectangles, type=["NoType"])

    def test_setRectangles(self):
        """ Test the setRectangles function """

        # set up db
        Rectangle_type1 = self.db.setMarkerType(name="Test1", color="#FF0000")
        Rectangle_type2 = self.db.setMarkerType(name="Test2", color="#00FF00")
        Rectangle_type3 = self.db.setMarkerType(name="Track", color="#00FF00", mode=self.db.TYPE_Track)

        image1 = self.db.setImage("test1.jpg")
        image2 = self.db.setImage("test2.jpg")
        image3 = self.db.setImage("test3.jpg")
        image4 = self.db.setImage("test4.jpg")

        track1 = self.db.setTrack(Rectangle_type3)
        track2 = self.db.setTrack(Rectangle_type3)

        # test multiple Rectangles for one image
        self.db.setRectangles(image=image1, x=[1, 2, 3, 4, 5], y=[0, 0, 0, 0, 0], width=[1, 2, 3, 4, 5],
                              height=[0, 0, 0, 0, 0], type=Rectangle_type1)
        self.assertEqual(self.db.getRectangles().count(), 5, "Setting Rectangles does not work properly.")
        self.db.deleteRectangles()

        # test multiple images
        self.db.setRectangles(image=[image1, image2], x=[1, 2], y=[0, 0], width=[1, 2], height=[0, 0],
                              type=Rectangle_type1)
        self.assertEqual(self.db.getRectangles().count(), 2, "Setting Rectangles does not work properly.")
        self.db.deleteRectangles()

        # test multiple types
        self.db.setRectangles(image=image1, x=1, y=0, width=10, height=20,
                              type=[Rectangle_type1, Rectangle_type2])
        self.assertEqual(self.db.getRectangles().count(), 2, "Setting Rectangles does not work properly.")
        self.db.deleteRectangles()

        # test multiple texts and one style
        self.db.setRectangles(image=image1, x=1, y=0, width=10, height=20, type=Rectangle_type1,
                              text=["foo", "bar", "hu"], style="{}")
        self.assertEqual(self.db.getRectangles().count(), 3, "Setting Rectangles does not work properly.")
        self.db.deleteRectangles()

        # test image by filename
        self.db.setRectangles(filename="test2.jpg", x=1, y=0, width=10, height=20, type=Rectangle_type2)
        self.assertEqual(self.db.getRectangles().count(), 1, "Setting Rectangles does not work properly.")
        self.db.deleteRectangles()

        # test images by frames
        self.db.setRectangles(frame=[0, 1, 2], x=1, y=0, width=10, height=20, type=Rectangle_type2)
        self.assertEqual(self.db.getRectangles().count(), 3, "Setting Rectangles does not work properly.")
        self.db.deleteRectangles()

        # set and update Rectangles
        self.db.setRectangles(image=image1, x=[0, 1, 2], y=[0, 1, 2], width=0, height=0, type=Rectangle_type1)
        Rectangles = self.db.getRectangles()
        self.assertTrue(all(m.x < 10 for m in Rectangles), "Setting Rectangles does not work properly.")
        self.db.setRectangles(x=[10, 20, 30], y=[0, 1, 2], width=0, height=0, id=[m for m in Rectangles])
        Rectangles = self.db.getRectangles()
        self.assertTrue(all(m.x >= 10 for m in Rectangles), "Setting Rectangles does not work properly.")
        self.db.deleteRectangles()

    def test_deleteRectangles(self):
        """ Test the deleteRectangles function """

        # set up db
        Rectangle_type1 = self.db.setMarkerType(name="Test1", color="#FF0000")
        Rectangle_type2 = self.db.setMarkerType(name="Test2", color="#00FF00")
        Rectangle_type3 = self.db.setMarkerType(name="Track", color="#00FF00", mode=self.db.TYPE_Track)

        image1 = self.db.setImage("test1.jpg")
        image2 = self.db.setImage("test2.jpg")
        image3 = self.db.setImage("test3.jpg")
        image4 = self.db.setImage("test4.jpg")

        def CreateRectangles():
            track1 = self.db.setTrack(Rectangle_type3)
            track2 = self.db.setTrack(Rectangle_type3)
            self.db.setRectangles(image=image1, x=[1, 2, 3, 4, 5], y=[0, 0, 0, 0, 0], width=0, height=0,
                                  type=Rectangle_type1)
            self.db.setRectangles(image=image2, x=[1, 2, 3, 4, 5], y=[0, 0, 0, 0, 0], width=0, height=0,
                                  processed=True, text="foo", type=Rectangle_type1)
            self.db.setRectangles(image=image1, x=[1, 2, 3, 4, 5], y=[0, 0, 0, 0, 0], width=0, height=0,
                                  text="bar", type=Rectangle_type2)

        # delete from one image
        CreateRectangles()
        self.db.deleteRectangles(image=image1)
        self.assertEqual(self.db.getRectangles().count(), 5, "Deleting Rectangles does not work properly.")
        self.db.deleteRectangles()

        # delete from two images
        CreateRectangles()
        self.db.deleteRectangles(image=[image1, image2])
        self.assertEqual(self.db.getRectangles().count(), 0, "Deleting Rectangles does not work properly.")
        self.db.deleteRectangles()

        # delete by filename
        CreateRectangles()
        self.db.deleteRectangles(filename="test2.jpg")
        self.assertEqual(self.db.getRectangles().count(), 10, "Deleting Rectangles does not work properly.")
        self.db.deleteRectangles()

        # delete by filename
        CreateRectangles()
        self.db.deleteRectangles(frame=1)
        self.assertEqual(self.db.getRectangles().count(), 10, "Deleting Rectangles does not work properly.")
        self.db.deleteRectangles()

        # delete by x coordinate
        CreateRectangles()
        self.db.deleteRectangles(x=slice(2, 4))
        self.assertEqual(self.db.getRectangles().count(), 6, "Deleting Rectangles does not work properly.")
        self.db.deleteRectangles()

        # delete by processed
        CreateRectangles()
        self.db.deleteRectangles(processed=True)
        self.assertEqual(self.db.getRectangles().count(), 10, "Deleting Rectangles does not work properly.")
        self.db.deleteRectangles()

        # delete by text
        CreateRectangles()
        self.db.deleteRectangles(text="foo")
        self.assertEqual(self.db.getRectangles().count(), 10, "Deleting Rectangles does not work properly.")
        self.db.deleteRectangles()

        # delete by id
        CreateRectangles()
        ids = [m.id for m in self.db.getRectangles(text="foo")]
        self.db.deleteRectangles(id=ids)
        self.assertEqual(self.db.getRectangles().count(), 10, "Deleting Rectangles does not work properly.")
        self.db.deleteRectangles()

        # delete by type
        CreateRectangles()
        self.db.deleteRectangles(type="Test1")
        self.assertEqual(self.db.getRectangles().count(), 5, "Deleting Rectangles does not work properly.")
        self.db.deleteRectangles()

    def test_setgetTag(self):

        tag1 = self.db.setTag(name='tag1')
        self.assertTrue(tag1.name == 'tag1', "Failed setting Tag")

        self.assertRaises(AssertionError, self.db.setTag)

        tag1 = self.db.getTag(name='tag1')
        self.assertTrue(tag1.name == 'tag1', "Failed retrieving single Tag by Name ")

        tag1 = self.db.getTag(id=1)
        self.assertTrue(tag1.name == 'tag1', "Failed retrieving single Tag by ID ")

        self.assertRaises(AssertionError, self.db.getTag)

        tag1b = self.db.setTag(id=1, name='tag1b')
        tags = self.db.getTags()
        self.assertTrue(tags.count()==1,'Failed updating tag entry - nr tags')
        self.assertTrue(tags[0].name == 'tag1b','Failed updating tag entry - tag name' )

    def test_getTags(self):
        tag1 = self.db.setTag(name='tag1')
        tag2 = self.db.setTag(name='tag2')
        tag3 = self.db.setTag(name='tag3')

        # all
        tags = self.db.getTags()
        self.assertEqual(tags.count(),3, 'Failed retrieving all tags')

        # by names
        tags = self.db.getTags(name=['tag1','tag3'])
        self.assertEqual(tags.count(), 2, 'Failed retrieving tags by name list')

        # by ids
        tags = self.db.getTags(id=[1,2])
        self.assertEqual(tags.count(), 2, 'Failed retrieving tags by ID list')

    def test_deleteTags(self):
        tag1 = self.db.setTag(name='tag1')
        tag2 = self.db.setTag(name='tag2')
        tag3 = self.db.setTag(name='tag3')

        count = self.db.deleteTags()
        self.assertEqual(count,3,'Failed delete all tags')

        tag1 = self.db.setTag(name='tag1')
        tag2 = self.db.setTag(name='tag2')
        tag3 = self.db.setTag(name='tag3')
        count = self.db.deleteTags(name=['tag1','tag3'])
        self.assertEqual(count, 2, 'Failed delete tags by name list')

    ''' Test Annotation functions '''
    def test_getAnnotation(self):
        im = self.db.setImage("test.jpg")
        self.db.setAnnotation(im, comment="foo")

        annotation = self.db.getAnnotation(image=im)
        self.assertEqual(annotation.comment, "foo", "Failed to get annotation by image.")

        annotation = self.db.getAnnotation(frame=0)
        self.assertEqual(annotation.comment, "foo", "Failed to get annotation by frame.")

        annotation = self.db.getAnnotation(filename="test.jpg")
        self.assertEqual(annotation.comment, "foo", "Failed to get annotation by filename.")

        annotation = self.db.getAnnotation(id=1)
        self.assertEqual(annotation.comment, "foo", "Failed to get annotation by id.")

        annotation = self.db.getAnnotation(filename="test2.jpg")
        self.assertEqual(annotation, None, "Failed to get non existent annotation.")

    def test_getAnnotations(self):
        im1 = self.db.setImage("test1.jpg")
        self.db.setAnnotation(im1, comment="foo", rating=1)
        im2 = self.db.setImage("test2.jpg")
        self.db.setAnnotation(im2, comment="bar", rating=3)
        im3 = self.db.setImage("test3.jpg")
        self.db.setAnnotation(im3, comment="foo")
        im4 = self.db.setImage("test4.jpg")

        annotations = self.db.getAnnotations(image=[im1, im2, im4])
        self.assertEqual(annotations.count(), 2, "Failed to get annotations by images.")

        annotations = self.db.getAnnotations(filename="test2.jpg")
        self.assertEqual(annotations.count(), 1, "Failed to get annotation by filename.")

        annotations = self.db.getAnnotations(comment="foo")
        self.assertEqual(annotations.count(), 2, "Failed to get annotation by comment.")

        annotations = self.db.getAnnotations(rating=1)
        self.assertEqual(annotations.count(), 1, "Failed to get annotation by rating.")

        annotations = self.db.getAnnotations()
        self.assertEqual(annotations.count(), 3, "Failed to get annotation without filter.")

    def test_setAnnotation(self):
        im1 = self.db.setImage("test1.jpg")
        im2 = self.db.setImage("test2.jpg")
        im3 = self.db.setImage("test3.jpg")
        im4 = self.db.setImage("test4.jpg")

        self.db.setAnnotation(image=im1, comment="foo")
        self.assertEqual(self.db.getAnnotation(image=im1).comment, "foo", "Failed to set annotation.")

        self.db.setAnnotation(image=im1, rating=2)
        self.assertEqual(self.db.getAnnotation(image=im1).rating, 2, "Failed to set annotation.")

        self.db.setAnnotation(id=1, rating=3)
        self.assertEqual(self.db.getAnnotation(image=im1).rating, 3, "Failed to set annotation.")

        self.assertRaises(AssertionError, self.db.setAnnotation, comment="", rating=2)

    def test_deleteAnnotations(self):
        im1 = self.db.setImage("test1.jpg")
        im2 = self.db.setImage("test2.jpg")
        im3 = self.db.setImage("test3.jpg")
        im4 = self.db.setImage("test4.jpg")

        def CreateAnnotations():
            self.db.deleteAnnotations()
            self.db.setAnnotation(im1, comment="foo", rating=1)
            self.db.setAnnotation(im2, comment="bar", rating=3)
            self.db.setAnnotation(im3, comment="foo")

        CreateAnnotations()
        self.db.deleteAnnotations()
        self.assertEqual(self.db.getAnnotations().count(), 0, "Failed to delete all annotation.")

        CreateAnnotations()
        self.db.deleteAnnotations(rating=[1, 3])
        self.assertEqual(self.db.getAnnotations().count(), 1, "Failed to delete all annotation.")

        CreateAnnotations()
        self.db.deleteAnnotations(comment="bar")
        self.assertEqual(self.db.getAnnotations().count(), 2, "Failed to delete all annotation.")

        CreateAnnotations()
        self.db.deleteAnnotations(image=[im1, im4])
        self.assertEqual(self.db.getAnnotations().count(), 2, "Failed to delete all annotation.")

        CreateAnnotations()
        self.db.deleteAnnotations(filename="test3.jpg")
        anns = self.db.getAnnotations()
        for an in anns:
            print(an)
        print(self.db.getAnnotations().count())
        self.assertEqual(self.db.getAnnotations().count(), 2, "Failed to delete all annotation.")


if __name__ == '__main__':
    __path__ = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(__path__, 'log_'+__key__+'.txt')
    with open(log_file, "w") as f:
        runner = unittest.TextTestRunner(f)
        unittest.main(testRunner=runner)
