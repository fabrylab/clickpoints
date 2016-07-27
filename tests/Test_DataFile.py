__key__ = "DATAFILE"
__testname__ = "Data File"

import os
import unittest

from clickpoints import DataFile


class Test_DataFile(unittest.TestCase):

    def tearDown(self):
        self.db.db.close()
        os.remove(self.db.database_filename)

    def test_getDbVersion(self):
        """ Test if the getDbVersion function returns the version properly """
        self.db = DataFile("getDbVersion.cdb", "w")

        self.assertEqual(self.db.getDbVersion(), "14", "Database version is not returned correctly.")

    ''' Test Path functions '''
    def test_setPath(self):
        """ Test the setPath function """
        self.db = DataFile("setPath.cdb", "w")

        # try to set a path
        path = self.db.setPath(path_string="test")
        self.assertEqual(path.path, "test", "Path was not set properly")

    def test_getPath(self):
        """ Test the getPath function """
        self.db = DataFile("getPath.cdb", "w")

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
        self.db = DataFile("getPaths.cdb", "w")

        p1 = os.path.join("foo", "bar1")
        p2 = os.path.join("foo", "bar2")
        p3 = os.path.join("loo", "bar1")
        self.db.setPath(path_string=p1)
        self.db.setPath(path_string=p2)
        self.db.setPath(path_string=p3)
        paths = self.db.getPaths(path_strings=p2)
        self.assertEqual([p.path for p in paths], [p2], "Retrieving a single path works does not work.")

        paths = self.db.getPaths(path_strings=[p1, p2])
        self.assertEqual([p.path for p in paths], [p1, p2], "Retrieving multiple paths does not work.")

        paths = self.db.getPaths()
        self.assertEqual(paths.count(), 3, "Retrieving all paths does not work.")

        paths = self.db.getPaths(base_path="foo")
        self.assertEqual([p.path for p in paths], [p1, p2], "Retrieving paths with basepath does not work.")

    def test_deletePaths(self):
        """ Test the deletePaths function """
        self.db = DataFile("deletePaths.cdb", "w")

        p1 = os.path.join("foo", "bar1")
        p2 = os.path.join("foo", "bar2")
        p3 = os.path.join("loo", "bar1")
        self.db.setPath(path_string=p1)
        self.db.setPath(path_string=p2)
        self.db.setPath(path_string=p3)

        self.db.deletePaths(path_strings=p1)
        paths = self.db.getPaths()
        self.assertEqual(paths.count(), 2, "Deleting one path does not work")
        self.db.setPath(path_string=p1)

        self.db.deletePaths(path_strings=[p1, p3])
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
        self.db = DataFile("setImage.cdb", "w")

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
        self.db = DataFile("getImages.cdb", "w")

        self.db.setImage("test1.jpg")
        self.db.setImage("test2.jpg")
        self.db.setImage("test3.jpg")

        ims = self.db.getImages([1, 2])
        self.assertEqual(ims.count(), 2, "Getting images does not work")

        ims = self.db.getImageIterator(1)
        self.assertEqual([im.filename for im in ims], ["test2.jpg", "test3.jpg"], "Getting images does not work")

    def test_deleteImages(self):
        """ Test the deleteImages function """
        self.db = DataFile("deleteImages.cdb", "w")

        self.db.setImage("test1.jpg")
        self.db.setImage("test2.jpg")
        self.db.setImage("test3.jpg")

        ims = self.db.getImages()
        self.assertEqual(ims.count(), 3, "Getting images does not work")

        self.db.deleteImages(filenames="test1.jpg")

        ims = self.db.getImages()
        self.assertEqual(ims.count(), 2, "Deleting image does not work")

        self.db.deleteImages(filenames=["test2.jpg", "test3.jpg"])

        ims = self.db.getImages()
        self.assertEqual(ims.count(), 0, "Deleting images does not work")

    ''' Test MarkerType functions '''
    def test_setgetMarkerType_Insert(self):
        """ Test set and get MarkerType - insert variant"""

        self.db = DataFile("setgetmarkertypeinsert.cdb", "r+")
        self.db.setMarkerType('rectangle', color='#00ff00', mode=1)
        item = self.db.getMarkerType('rectangle')

        self.assertEqual(item.name, 'rectangle',"Insert MarkerType - name failed")
        self.assertEqual(item.mode, 1,"Insert MarkerType - mode failed")
        self.assertEqual(item.color, '#00ff00',"Insert MarkerType - color failed")


    def test_setgetMarkerType_Update(self):
        """ Test set and get MarkerType - update variant """
        self.db = DataFile("getmarkertypeupdate.cdb", "r+")

        self.db.setMarkerType('rectangle', color='#00ff00', mode=1)
        self.db.setMarkerType('rectangle', color='#00ff00')

        item = self.db.getMarkerType('rectangle')

        self.assertEqual(item.name, 'rectangle', "Update MarkerType - mode failed")
        self.assertEqual(item.mode, 1, "Update MarkerType - mode failed")
        self.assertEqual(item.color, '#00ff00', "Update MarkerType - mode failed")


    def test_getMarkerTypes(self):
        """ Test getMarkerTypes to recover a query of all available marker types"""
        self.db = DataFile("getmarkertypes_compare.cdb", "r+")

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
        self.db = DataFile("deletemarkertypes.cdb", "r+")

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
        self.db = DataFile("setgettrack.cdb", "r+")

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
        q_tracks = self.db.getTracks(types='track')
        self.assertEqual(q_tracks.count(), 2, "Get specific Tracks by type failed")

        # specific getTrack - success
        track = self.db.getTrack(id=1)
        self.assertTrue(track.id == 1, "Get specific track by ID failed")

        # specific getTrack - failed
        track = self.db.getTrack(id=100000)
        self.assertIsNone(track, "Failing to get specific track by ID failed")

    def test_deleteTrack(self):
        """ Test deleteMarkerType to delete marker type instance"""
        self.db = DataFile("deltrack.cdb", "r+")

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
        self.db.deleteTacks(ids=1)
        q_tracks = self.db.getTracks()
        self.assertEqual(q_tracks.count(), 5, "Failed to delete track by ID")

        # delete specific by type
        self.db.deleteTacks(types='track2')
        q_tracks = self.db.getTracks()
        self.assertEqual(q_tracks.count(), 3, "Failed to delete track by type")

        # delete all
        self.db.deleteTacks()
        q_tracks = self.db.getTracks()
        self.assertEqual(q_tracks.count(), 0, "Failed to complete generic delete")

    ''' Test MaskType functions '''
    def test_getMaskType(self):
        """ Test the getMaskType function """
        self.db = DataFile("getMaskType.cdb", "w")

        masktype = self.db.getMaskType(name="color")
        self.assertEqual(masktype, None, "Getting non-existent mask does not work")

    def test_setMaskType(self):
        """ Test the setMaskType function """
        self.db = DataFile("setMaskType.cdb", "w")

        self.db.setMaskType(name="color", color="#FF0000", index=2)
        masktype = self.db.getMaskType(name="color")
        self.assertEqual(masktype.name, "color", "Creating a new mask type does not work")

        self.db.setMaskType(id=masktype.id, name="color2", color="#FF0000", index=2)
        masktype = self.db.getMaskType(id=masktype.id)
        self.assertEqual(masktype.name, "color2", "Alterning a mask type does not work")

    def test_getMaskTypes(self):
        """ Test the getMaskTypes function """
        self.db = DataFile("getMaskTypes.cdb", "w")

        self.db.setMaskType(name="color1", color="#FF0000", index=1)
        self.db.setMaskType(name="color2", color="#FF0000", index=2)
        self.db.setMaskType(name="color3", color="#FF0000", index=3)
        masktypes = self.db.getMaskTypes(names="color1")
        self.assertEqual([m.name for m in masktypes], ["color1"], "Retrieving one mask type does not work")

        masktypes = self.db.getMaskTypes(names=["color1", "color2"])
        self.assertEqual([m.name for m in masktypes], ["color1", "color2"], "Retrieving two mask types does not work")

    def test_deleteMaskTypes(self):
        """ Test the deleteMaskTypes function """
        self.db = DataFile("deleteMaskTypes.cdb", "w")

        self.db.setMaskType(name="color1", color="#FF0000", index=1)
        self.db.setMaskType(name="color2", color="#FF0000", index=2)
        self.db.setMaskType(name="color3", color="#FF0000", index=3)

        self.db.deleteMaskTypes(names="color1")
        masktypes = self.db.getMaskTypes()
        self.assertEqual(masktypes.count(), 2, "Deleting one mask type does not work")

        self.db.deleteMaskTypes(names=["color2", "color3"])
        masktypes = self.db.getMaskTypes()
        self.assertEqual(masktypes.count(), 0, "Deleting two mask types does not work")

    ''' Test Mask functions '''
    def test_setMask(self):
        """ Test the setMask function """
        self.db = DataFile("setMask.cdb", "w")

        im = self.db.setImage(filename="test.jpg", width=100, height=100)
        masktype = self.db.setMaskType(name="color", color="#FF0000", index=2)
        mask = self.db.setMask(image=im)
        masktype = self.db.getMaskType(name="color")
        self.assertEqual(masktype.name, "color", "Creating a new mask type does not work")

        self.db.setMaskType(id=masktype.id, name="color2", color="#FF0000", index=2)
        masktype = self.db.getMaskType(id=masktype.id)
        self.assertEqual(masktype.name, "color2", "Alterning a mask type does not work")

if __name__ == '__main__':
    __path__ = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(__path__, 'log_'+__key__+'.txt')
    with open(log_file, "w") as f:
        runner = unittest.TextTestRunner(f)
        unittest.main(testRunner=runner)
