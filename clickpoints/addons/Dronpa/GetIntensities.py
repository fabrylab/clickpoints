#!/usr/bin/env python
# -*- coding: utf-8 -*-
# GetIntensities.py

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

from __future__ import division, print_function
from skimage.measure import find_contours
import numpy as np
import os
import matplotlib.pyplot as plt


def stderr(values):
    return np.std(values) / np.sqrt(len(values))


def bootstrap(values):
    values = values.ravel()
    count = 10
    means = np.zeros(count)
    for i in range(count):
        indices = np.random.randint(0, len(values), len(values))
        means[i] = np.mean(values[indices])
    return np.std(means)


def getIntensities(db, delta_t, color_channel, output_folder):
    inte_list2 = []
    error_list2 = []
    error_list2B = []
    sizes = []
    times = []
    valid_cells = []
    for t, im in enumerate(db.getImages()):
        times.append(t * delta_t)
    for m, cell in enumerate(db.getMaskTypes()):
        inte_list = []
        error_list = []
        print("---------------------", m)
        size = 0
        for t, im in enumerate(db.getImages()):
            mask = (im.mask.data == cell.index)
            if not np.any(mask):
                break
            im1 = im.data
            if len(im1.shape) == 3:
                if im1.shape[2] == 1:
                    im1 = im1[:, :, 0]
                else:
                    im1 = im1[:, :, color_channel]
            inte_list.append(np.mean(im1[mask]))
            error_list.append(bootstrap(im1[mask]))
            error_list2B.append(stderr(im1[mask]))
            if t == 0:
                size = np.sum(mask)
        else:
            valid_cells.append(cell)
            sizes.append(size)
            inte_list2.append(np.array(inte_list))
            error_list2.append(np.array(error_list))

    plt.figure(0, (15, 6))
    plt.clf()
    plt.subplot(121)
    colors = []
    for m, cell in enumerate(valid_cells):
        p, = plt.plot(times, inte_list2[m] * sizes[m] - inte_list2[-1] * 0, label=cell.name)
        colors.append(p.get_color())
        plt.errorbar(times, inte_list2[m] * sizes[m] - inte_list2[-1] * 0, error_list2[m],
                     color=colors[m])  # , linestyle=styles[m])

    plt.xlabel("time (min)")
    plt.ylabel("mean intensity")
    plt.legend()

    plt.subplot(122)
    t = 2

    im1 = db.getImage(t).data
    mask1 = db.getImage(t).mask.data
    plt.imshow(im1)

    minx = im1.shape[1]
    maxx = 0
    miny = im1.shape[0]
    maxy = 0
    centers = []
    for m, cell in enumerate(valid_cells):
        mask = (mask1 == cell.index)
        line = find_contours(mask, 0.5)
        plt.plot(line[0][:, 1], line[0][:, 0], color=colors[m])

        centers.append([np.mean(line[0][:, 1]), np.mean(line[0][:, 0])])
        plt.text(np.mean(line[0][:, 1]), np.mean(line[0][:, 0]), cell.name, va="center", ha="center", color="w")
        minx = np.min([minx, min(line[0][:, 1])])
        maxx = np.max([maxx, max(line[0][:, 1])])
        miny = np.min([miny, min(line[0][:, 0])])
        maxy = np.max([maxy, max(line[0][:, 0])])

    plt.xlim(minx - 0.5 * (maxx - minx), maxx + 0.5 * (maxx - minx))
    plt.ylim(maxy + 0.5 * (maxy - miny), miny - 0.5 * (maxy - miny))
    if not os.path.exists(output_folder):
        os.mkdir(output_folder)
    plt.savefig(os.path.join(output_folder, "Intensities.png"))
    np.savetxt(os.path.join(output_folder, "cell.txt"), np.concatenate((np.array([times]), inte_list2)).T)
    np.savetxt(os.path.join(output_folder, "cell_sizes.txt"), sizes)
    np.savetxt(os.path.join(output_folder, "cell_centers.txt"), centers)
    np.savetxt(os.path.join(output_folder, "cell_indices.txt"), [cell.index for cell in valid_cells])
    np.savetxt(os.path.join(output_folder, "cell_error.txt"), error_list2)
    plt.show()
