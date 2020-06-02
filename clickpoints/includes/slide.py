#!/usr/bin/env python
# -*- coding: utf-8 -*-
# slide.py

# Copyright (c) 2015-2020, Richard Gerum, Sebastian Richter, Alexander Winterl
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ClickPoints. If not, see <http://www.gnu.org/licenses/>

import tifffile
import numpy as np
from typing import Sequence, Tuple


def read_crop_of_page(page: tifffile.TiffPage, loc: Tuple[int, int], size: Tuple[int, int], crop=True):
    # split loc and size
    x1, y1 = loc
    x2, y2 = x1 + size[0], y1 + size[1]

    # if the page is not tiled, we have to read the whole page
    if not page.is_tiled:
        if crop is True:
            return page.asarray()[x1:x2, y1:y2]
        else:
            return page.asarray(), (0, 0)

    # get the positions of the tiles in the file
    offsets, bytecounts = page.dataoffsets, page.databytecounts

    # initialize some lists
    slide_indices_shapes = []
    used_offsets = []
    used_bytecounts = []
    slide_rects = []

    # iterate over all tiles
    for i in range(len(offsets)):
        # decode with empty content to obtain the position and shape of the tile
        segment, indices, shape = page.decode(None, i)
        # check if it overlaps with the target region
        if (x1 > indices[3] + shape[1]) or (x2 < indices[3]):
            continue
        # if it is outside in y, ignore
        if (y1 > indices[4] + shape[2]) or (y2 < indices[4]):
            continue
        # store the offsets
        used_offsets.append(offsets[i])
        used_bytecounts.append(bytecounts[i])

        slide_indices_shapes.append(i)
        slide_rects.append([indices[3], indices[4], indices[3]+shape[1], indices[4]+shape[2]])

    # determine the region covered by the tiles
    slide_rects = np.array(slide_rects)
    sx1, sy1 = np.min(slide_rects[:, :2], axis=0)
    sx2, sy2 = np.max(slide_rects[:, 2:], axis=0)

    # and initialize an array accordingly
    result = np.zeros((sx2-sx1, sy2-sy1, 1 if len(page.shape) == 2 else page.shape[2]), dtype=page.dtype)

    # decode the tiles
    fh = page.parent.filehandle
    segmentiter = fh.read_segments(used_offsets, used_bytecounts)
    decodeargs = {}
    if 347 in page.keyframe.tags:
        decodeargs["tables"] = page._gettags({347}, lock=None)[0][1].value
    for seg, i in zip(segmentiter, slide_indices_shapes):
        segment, indices, shape = page.decode(seg[0], i, **decodeargs)
        result[indices[3]-sx1:indices[3]+shape[1]-sx1, indices[4]-sy1:indices[4]+shape[2]-sy1] = segment

    # optionally drop the channel dimension
    if len(page.shape) == 2:
        result = result[:, :, 0]

    if crop is True:
        # crop the region covered by the tiles to the desired size
        return crop_of_crop(result, (sx1, sy1), loc, size)
    return result, (sx1, sy1)


def crop_of_crop(array: np.ndarray, loc: Tuple[int, int], loc2: Tuple[int, int], size2: Tuple[int, int]):
    """ Crop a region of an array those position is defined by loc.

    The data is cropped or padded with 0 to match the target location and size.

    Args:
        array: the array with the data
        loc: the offset of the array
        loc2: the start of the target array
        size2: the size of the target array

    Returns:
        array: the crooped/padded array
    """
    # first crop/pad at the start
    diff_start = np.array(loc2)-np.array(loc)
    pad_start = -diff_start * (diff_start < 0)
    crop_start = diff_start * (diff_start > 0)

    crop = tuple([slice(s, None) for s in crop_start])
    pad = list([(s, 0) for s in pad_start])
    if len(array.shape) == 3:
        pad.append((0, 0))

    array = np.pad(array[crop], pad, mode='constant')

    # then crop/pad at the end
    diff_end = np.array(array.shape[:2])-np.array(size2[:2])
    pad_end = -diff_end * (diff_end < 0)
    crop_end = diff_end * (diff_end > 0)
    crop = tuple([slice(None, -e if e != 0 else None) for e in crop_end])
    pad = list([(0, e) for e in pad_end])
    if len(array.shape) == 3:
        pad.append((0, 0))

    return np.pad(array[crop], pad, mode='constant')


class myslide():
    last_data = None
    last_level = None

    def __init__(self, filename: str):
        """ An interface similar to the slide of OpenSlide
        """
        # check the file ending
        if not (filename.endswith(".tif") or filename.endswith(".tiff")):
            print("ERROR incorrect file ending")
            raise IOError
        # check to open the file
        try:
            self.tif = tifffile.TiffFile(filename)
        except tifffile.tifffile.TiffFileError:
            print("load error")
            raise IOError

        # print(len(self.tif.pages))

        # get the amount of levels = pages
        self.level_count = len(self.tif.pages)
        # get the dimensions of all pages
        self.level_dimensions = []
        for page in self.tif.pages:
            # print(page)
            # if we are not the first page
            if len(self.level_dimensions) and page.is_reduced is None:
                return IOError
                #total_width, total_height = self.level_dimensions[0]
                # check if it is an integer down sampled version
                #if total_width % page.shape[1] != 0 or total_height % page.shape[0] != 0:
                #    print("ERROR a ", total_width, page.shape[1], total_height % page.shape[0])
                #    raise IOError
                # if the down sampling is different for the pages, we cant use it either
                #if total_width // page.shape[1] != total_height // page.shape[0]:
                #    print("ERROR x")
                #    raise IOError
            # append the dimensions
            self.level_dimensions.append((page.shape[1], page.shape[0]))


        # check if this is a multipage tiff stack - all pages have the same dims
        if np.all(np.array(self.level_dimensions) == self.level_dimensions[0]):
            print("Tiff page dimensions are equal indicating non-pyramid Tiff")
            raise IOError

        # if there is just one level, its not a pyramid tiff
        if len(self.level_dimensions) == 1:
            print("ERROR only one level in pyramid")
            raise IOError
        # store the level 0 dimension
        self.dimensions = self.level_dimensions[0]
        # calculate how much the pyramid pages downsample
        self.level_downsamples = [self.dimensions[0] // dim[0] for dim in self.level_dimensions]

    def read_region(self, location: Tuple[int, int], level: int, size: Tuple[int, int]):
        x, y = location
        w, h = size
        down = self.level_downsamples[level]
        x = x // down
        y = y // down
        # only decode a cropped part of the page
        crop = read_crop_of_page(self.tif.pages[level], loc=(y, x), size=(h, w))
        return crop

    def read_region_uncropped(self, location: Tuple[int, int], level: int, size: Tuple[int, int]):
        x, y = location
        w, h = size
        down = self.level_downsamples[level]
        x = x // down
        y = y // down
        # only decode a cropped part of the page
        return read_crop_of_page(self.tif.pages[level], loc=(y, x), size=(h, w), crop=False)

    def get_best_level_for_downsample(self, downsample: int):
        if downsample < 1:
            return 0
        for index, down in enumerate(self.level_downsamples):
            if down > downsample:
                return index - 1
        else:
            return len(self.level_downsamples) - 1

    def close(self):
        self.tif.close()

# some magic to make this importable similar to OpenSlide
class lowlevel:
    OpenSlideUnsupportedFormatError = IOError

class openslide:
    OpenSlide = myslide
    lowlevel = lowlevel
openslide_loaded = True