from __future__ import division, print_function
import os

try:
    from PyQt5 import QtCore
except ImportError:
    from PyQt4 import QtCore

from scipy.misc import imsave
try:
    import cv2
    cv2_loaded = True
    try:
        from cv2.cv import CV_CAP_PROP_POS_FRAMES as CAP_PROP_POS_FRAMES
        from cv2.cv import CV_CAP_PROP_FRAME_COUNT as CAP_PROP_FRAME_COUNT
        from cv2.cv import CV_CAP_PROP_FRAME_WIDTH as CAP_PROP_FRAME_WIDTH
        from cv2.cv import CV_CAP_PROP_FRAME_HEIGHT as CAP_PROP_FRAME_HEIGHT
        from cv2.cv import CV_CAP_PROP_FPS as CAP_PROP_FPS

        from cv2.cv import CV_FOURCC as VideoWriter_fourcc
        from cv2.cv import CV_RGB2BGR as COLOR_RGB2BGR
    except ImportError:
        from cv2 import CAP_PROP_POS_FRAMES as CAP_PROP_POS_FRAMES
        from cv2 import CAP_PROP_FRAME_COUNT as CAP_PROP_FRAME_COUNT
        from cv2 import CAP_PROP_FRAME_WIDTH as CAP_PROP_FRAME_WIDTH
        from cv2 import CAP_PROP_FRAME_HEIGHT as CAP_PROP_FRAME_HEIGHT
        from cv2 import CAP_PROP_FPS as CAP_PROP_FPS

        from cv2 import VideoWriter_fourcc
        from cv2 import COLOR_RGB2BGR as COLOR_RGB2BGR
except ImportError:
    cv2_loaded = False
import numpy as np

class VideoExporter:
    def __init__(self, window, media_handler, modules, config=None):
        # default settings and parameters
        self.window = window
        self.media_handler = media_handler
        self.config = config
        self.modules = modules


    def SaveImage(self):
        timeline = self.window.GetModule("Timeline")
        start = timeline.frameSlider.startValue()
        end = timeline.frameSlider.endValue()
        video_writer = None
        path = os.path.join(self.config.outputpath, "export.avi")
        use_video = True
        for frame in range(start, end+1):            
            self.window.JumpToFrame(frame)
            self.preview_rect = self.window.view.GetExtend(True)
            self.image = self.window.ImageDisplay.image
            start_x, start_y, end_x, end_y = self.preview_rect
            if start_x < 0: start_x = 0
            if start_y < 0: start_y = 0
            if end_x > self.image.shape[1]: end_x = self.image.shape[1]
            if end_y > self.image.shape[0]: end_y = self.image.shape[0]
            if end_x < start_x: end_x = start_x+1
            if end_y < start_y: end_y = start_y+1
            if end_x > start_x + self.config.max_image_size: end_x = start_x + self.config.max_image_size
            if end_y > start_y + self.config.max_image_size: end_y = start_y + self.config.max_image_size
            self.preview_slice = self.image[start_y:end_y, start_x:end_x, :]
            
            if self.preview_slice.shape[2] == 1:
                self.preview_slice = np.dstack((self.preview_slice,self.preview_slice,self.preview_slice))
            if use_video:
                if video_writer == None:
                    fourcc = VideoWriter_fourcc(*'XVID')
                    video_writer = cv2.VideoWriter(path, fourcc, timeline.fps, (self.preview_slice.shape[1], self.preview_slice.shape[0]))
                video_writer.write(cv2.cvtColor(self.preview_slice, COLOR_RGB2BGR))
            else:
                imsave(path % (frame-start), self.preview_slice)
        video_writer.release()

    def keyPressEvent(self, event):

        # @key Z: Export Video
        if event.key() == QtCore.Qt.Key_Z:
            self.SaveImage()

    @staticmethod
    def file():
        return __file__
