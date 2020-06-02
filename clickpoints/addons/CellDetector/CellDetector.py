#!/usr/bin/env python
# -*- coding: utf-8 -*-
# CellDetector.py

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

import sys
import matplotlib.pyplot as plt
import numpy as np
from numpy.linalg import eig, inv
from skimage.measure import regionprops, label
import clickpoints


def moveInDirection(startx, starty, dir, im, factor, maximum):
    cut = np.zeros(maximum)
    for i in range(maximum):
        y, x = int(starty + i * dir[1]), int(startx + i * dir[0])
        if 0 < y < im.shape[0] and 0 < x < im.shape[1] and im[y, x] != 0:
            cut[i] = im[y, x]
        else:
            i -= 1
            break
            #        if(A(uint16(starty+i*delta(2)),uint16(startx+i*delta(1))) < lightness)
            #            break;
            #        end

    line = cut[:i]
    smooth = 5
    if len(line) > smooth + 1:
        smoothline = np.zeros(len(line) - smooth)
        for i in range(len(line) - smooth):
            smoothline[i] = np.mean(line[i:i + smooth])
        # difference = diff(smoothline)
        maxdiff = -np.min(np.diff(smoothline))  # /(max(line)-min(line))
    else:
        maxdiff = 0

    for i in range(len(line)):
        if line[i] <= np.max(line) * factor + np.min(line) * (1 - factor):
            break
    else:
        i = 0

    # i = i(1);
    #     if i ~= 1 && line(1) == min(line)
    #         'ERRRRRRRORRRR'
    #         'bla'
    #     end
    x = startx + i * dir[0]
    y = starty + i * dir[1]
    l = np.sqrt((i * dir[0]) ** 2 + (i * dir[1]) ** 2)

    return x, y, l, maxdiff


def running_mean(x, N):
    cumsum = np.cumsum(np.insert(x, 0, 0))
    return (cumsum[N:] - cumsum[:-N]) / N


def moveInDirection(startx, starty, dir, im, factor, maximum):
    pos = np.array([startx, starty])
    cut = np.zeros(maximum)
    for i in range(maximum):
        x, y = (pos + i * dir).astype(int)
        if 0 < y < im.shape[0] and 0 < x < im.shape[1] and im[y, x] != 0:
            cut[i] = im[y, x]
        else:
            i -= 1
            break

    line = cut[:i]
    smooth = 5
    if len(line) > smooth + 1:
        smoothline = running_mean(line, smooth)
        maxdiff = -np.min(np.diff(smoothline))
    else:
        maxdiff = 0

    for i in range(len(line)):
        if line[i] <= np.max(line) * factor + np.min(line) * (1 - factor):
            break
    else:
        i = 0

    x, y = pos + i * dir
    l = np.linalg.norm(i * dir)

    return x, y, l, maxdiff


def fitEllipse(x, y):
    x = x[:, np.newaxis]
    y = y[:, np.newaxis]
    D = np.hstack((x * x, x * y, y * y, x, y, np.ones_like(x)))
    S = np.dot(D.T, D)
    C = np.zeros([6, 6])
    C[0, 2] = C[2, 0] = 2
    C[1, 1] = -1
    E, V = eig(np.dot(inv(S), C))
    n = np.argmax(np.abs(E))
    a = V[:, n]
    return a


def ellipse_center(a):
    b, c, d, f, g, a = a[1] / 2, a[2], a[3] / 2, a[4] / 2, a[5], a[0]
    num = b * b - a * c
    x0 = (c * d - b * f) / num
    y0 = (a * f - b * d) / num
    return np.array([x0, y0])


def ellipse_angle_of_rotation(a):
    b, c, d, f, g, a = a[1] / 2, a[2], a[3] / 2, a[4] / 2, a[5], a[0]
    return 0.5 * np.arctan(2 * b / (a - c))


def ellipse_axis_length(a):
    b, c, d, f, g, a = a[1] / 2, a[2], a[3] / 2, a[4] / 2, a[5], a[0]
    up = 2 * (a * f * f + c * d * d + g * b * b - 2 * b * d * f - a * c * g)
    down1 = (b * b - a * c) * ((c - a) * np.sqrt(1 + 4 * b * b / ((a - c) * (a - c))) - (c + a))
    down2 = (b * b - a * c) * ((a - c) * np.sqrt(1 + 4 * b * b / ((a - c) * (a - c))) - (c + a))
    #if up < 0 or down1 < 0 or down2 < 0:
    #    return np.array([0, 0])
    res1 = np.sqrt(up / down1)
    res2 = np.sqrt(up / down2)
    return np.array([res1, res2])


def ellipse_angle_of_rotation2(a):
    b, c, d, f, g, a = a[1] / 2, a[2], a[3] / 2, a[4] / 2, a[5], a[0]
    if b == 0:
        if a > c:
            return 0
        else:
            return np.pi / 2
    else:
        if a > c:
            return np.arctan(2 * b / (a - c)) / 2
        else:
            return np.pi / 2 + np.arctan(2 * b / (a - c)) / 2


def mask_polygon(poly_verts, shape):
    from matplotlib.nxutils import points_inside_poly

    nx, ny = shape

    # Create vertex coordinates for each grid cell...
    # (<0,0> is at the top left of the grid in this system)
    x, y = np.meshgrid(np.arange(nx), np.arange(ny))
    x, y = x.flatten(), y.flatten()

    points = np.vstack((x, y)).T

    grid = points_inside_poly(points, poly_verts)
    grid = grid.reshape((ny, nx))

    return grid


def mask_polygon(polygon, width, height):
    from PIL import Image, ImageDraw

    # polygon = [(x1,y1),(x2,y2),...] or [x1,y1,x2,y2,...]
    # width = ?
    # height = ?

    img = Image.new('L', (width, height), 0)
    ImageDraw.Draw(img).polygon(polygon, outline=1, fill=1)
    mask = np.array(img)
    return mask


def count_old(im):
    # im = plt.imread(bild)

    im = im.astype("float") / im.max()

    # declare variables
    steps = 16
    points = np.zeros([steps, 2])
    rot = np.array([[np.cos(np.pi * 2 / steps), np.sin(np.pi * 2 / steps)],
                    [-np.sin(np.pi * 2 / steps), np.cos(np.pi * 2 / steps)]])  # rotation matrix

    points_found = []

    sizes = []

    for i in np.arange(0.9, 0.1, -0.05):
        print(i)

        labels = label(im > i)
        props = regionprops(labels)
        for prop in props:
            # reject small areas
            if not (10 * 10 < prop.area < 10000):
                continue

            # get coordinates of the object
            y, x = prop.centroid

            # test if the center is inside the object
            if labels[int(y), int(x)] == 0:
                continue

            # get main axis
            a = prop.orientation

            # starting direction
            dir = np.array([np.cos(a), -np.sin(a)])

            # Test 20 pixels in every direction and find the point where the
            # relative intensity reaches 30% of the maximum
            for k in range(steps):
                dir = np.dot(rot, dir)
                x1, x2, l, maxdiff = moveInDirection(x, y, dir, im, 0.3, 30)
                points[k, :] = [x1, x2]

            # Fit an ellipse and plot it
            try:
                ellipse = fitEllipse(points[:, 0], points[:, 1])
            except np.linalg.linalg.LinAlgError:
                continue

            # get the parameter of the ellipse
            center = ellipse_center(ellipse)
            x0, y0 = center
            phi = ellipse_angle_of_rotation(ellipse)
            a, b = ellipse_axis_length(ellipse)

            # if it is not valid continue
            if np.isnan(a) or np.isnan(b):
                continue

            # calculate points of the ellipse
            R = np.linspace(0, 2 * np.pi, steps)
            X = center[0] + a * np.cos(R) * np.cos(phi) - b * np.sin(R) * np.sin(phi)
            Y = center[1] + a * np.cos(R) * np.sin(phi) + b * np.sin(R) * np.cos(phi)

            # Test 20 pixels in every direction and find the point where the
            # relative intensity reaches 30% of the maximum
            dist = 0
            maxdiffsum = np.zeros(steps)
            for k in range(steps):
                len = np.sqrt((X[k] - x0) ** 2 + (Y[k] - y0) ** 2)
                x1, x2, l, maxdiff = moveInDirection(x0, y0, np.array([(X[k] - x0), (Y[k] - y0)]) / len, im, 0.3, 30)
                points[k, :] = [x1, x2]
                dist = dist + np.sqrt((X[k] - x1) ** 2 + (Y[k] - x2) ** 2)
                maxdiffsum[k] = maxdiff

            EllipseSize = a * b * np.pi
            if min(maxdiffsum) * steps < 0.3:
                pass
                # plt.plot(x0, y0, '*r')
                # continue

            if EllipseSize < 10:
                plt.plot(x0, y0, '*b')
                continue

            if dist > 30:
                plt.plot(x0, y0, '*y')
                continue

            sizes.append(EllipseSize)

            # mask the found ellipse area
            x1 = int(np.min(X))
            y1 = int(np.min(Y))
            w = int(np.max(X)) - x1
            h = int(np.max(Y)) - y1
            polygon = [(x - x1, y - y1) for x, y in zip(X[:-1], Y[:-1])]
            mask = 1 - mask_polygon(polygon, int(w), int(h))
            im[y1:y1 + h, x1:x1 + w] *= mask

            # add the point to the found points
            points_found.append((float(x0), float(y0)))

    #plt.imshow(im)
    #plt.show()
    print(max(sizes))

    # return the result
    return np.array(points_found)


def count(im):
    import cv2
    from scipy.signal import wiener
    print(cv2.__version__)
    # im = plt.imread(bild)

    # Take the mean over all colors
    # a = np.mean(A, 3)
    # normalize the image to 1
    im = im - im.min()
    im = im.astype("float") / im.max()
    im = wiener(im, 5)
    im = (im * 255).astype("uint8")
    print(im, im.dtype, im.max(), im.min())
    # plt.imshow(im)
    # plt.show()

    # Setup SimpleBlobDetector parameters.
    params = cv2.SimpleBlobDetector_Params()
    # Change thresholds
    params.minThreshold = 10;
    params.maxThreshold = 200;

    # Filter by Area.
    params.filterByArea = False
    params.minArea = 1500

    # Filter by Circularity
    params.filterByCircularity = False
    params.minCircularity = 0.1

    # Filter by Convexity
    params.filterByConvexity = False
    params.minConvexity = 0.87

    # Filter by Inertia
    params.filterByInertia = False
    params.minInertiaRatio = 0.01

    params.filterByColor = 1
    params.blobColor = 255

    for name in dir(params):
        print(name)

    # params.minDistBetweenBlobs = 10
    print(
    params.minThreshold, params.maxThreshold, params.filterByArea, params.thresholdStep, params.minDistBetweenBlobs)

    # Set up the detector with default parameters.
    ver = (cv2.__version__).split('.')
    if int(ver[0]) < 3:
        detector = cv2.SimpleBlobDetector(params)
    else:
        detector = cv2.SimpleBlobDetector_create(params)

    # Detect blobs.
    keypoints = detector.detect(im)

    # Draw detected blobs as red circles.
    # cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS ensures the size of the circle corresponds to the size of blob
    im_with_keypoints = cv2.drawKeypoints(im, keypoints, np.array([]), (0, 0, 255),
                                          cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)

    # Show keypoints
    # cv2.imshow("Keypoints", im_with_keypoints)
    # cv2.waitKey(0)

    print(keypoints)
    for key in keypoints:
        print(key.octave)
        # plt.plot(key.pt[0], key.pt[1], 'ro')
        # plt.text(key.pt[0], key.pt[1], key.size)
    print(np.array([key.pt for key in keypoints]))
    return np.array([key.pt for key in keypoints])
    # plt.imshow(im, cmap="gray")
    # plt.show()


class Addon(clickpoints.Addon):
    def __init__(self, *args, **kwargs):
        clickpoints.Addon.__init__(self, *args, **kwargs)

        # Check if the marker type is present
        if not self.db.getMarkerType("cell_nucleus"):
            self.marker_type = self.db.setMarkerType("cell_nucleus", [255, 0, 255], self.db.TYPE_Normal)
            self.cp.reloadTypes()
        else:
            self.marker_type = self.db.getMarkerType("cell_nucleus")

    def run(self, start_frame=0):
        # get images and mask_types
        images = self.db.getImages()

        # iterate over all images
        for image in images:
            print(image.filename)
            data = image.data
            if len(data.shape) == 3:
                data = np.mean(image.data, axis=2)
            p1 = count_old(data)

            self.db.table_marker.delete().where(self.db.table_marker.image == image.id).execute()
            self.db.setMarkers(image=image.id, x=p1[:, 0], y=p1[:, 1], type=self.marker_type)
            self.cp.reloadMarker(image.sort_index)

            # check if we should terminate
            if self.cp.hasTerminateSignal():
                print("Cancelled cell detection")
                return

        print("done")
