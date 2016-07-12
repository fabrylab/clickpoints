from __future__ import division, print_function
import cv2
import numpy as np
from scipy.ndimage.measurements import center_of_mass
import peewee
import sys

__icon__ = "fa.object-ungroup"

import clickpoints

# Connect to database
start_frame, database, port = clickpoints.GetCommandLineArgs()
db = clickpoints.DataFile(database)
com = clickpoints.Commands(port, catch_terminate_signal=True)

# Define parameters
compare_to_first = False
border_x = 20
border_y = 20

# Check if the marker type is present
if not db.GetType("drift_rect"):
    db.AddType("drift_rect", [0, 255, 255], db.TYPE_Rect)
    com.ReloadTypes()

# try to load marker
rect = db.GetRectangles(type_name="drift_rect")
if len(rect) < 1:
    print("ERROR: no rectangle selected.\nPlease mark a rectangle with type 'drift_rect'.")
    sys.exit(-1)
rect = rect[0]

# Get images and template
images = db.GetImageIterator(start_frame=start_frame)
template = images.next().data[rect.y1-border_y:rect.y2+border_y, rect.x1-border_x:rect.x2+border_x]

# start iteration
last_shift = np.array([0, 0])
for image in images:
    # template matching for drift correction
    res = cv2.matchTemplate(image.data[rect.slice_y, rect.slice_x], template, cv2.TM_CCOEFF)
    res += np.amin(res)
    res = res**4.

    # get 2D max
    shift = np.unravel_index(res.argmax(), res.shape)

    # get sub pixel accurate center of mass
    try:
        # fail if there it is too close to border
        if not (shift[0] > 2 and shift[1] > 2):
            raise Exception

        subres = res[shift[0]-2:shift[0]+3, shift[1]-2:shift[1]+3]
        subshift = center_of_mass(subres)

        # calculate coordinates of sub shift
        shift = shift + (subshift - np.array([2, 2]))
        # calculate full image coordinates of shift
        shift = shift - np.array([border_y, border_x])
    except:
        # calculate full image coordinates of shift
        shift = shift - np.array([border_y, border_x])

    # get new template if compare_to_first is off
    if not compare_to_first:
        template = image.data[rect.y1-border_y:rect.y2+border_y, rect.x1-border_x:rect.x2+border_x]
        shift += last_shift
        last_shift = shift

    # save the offset to the database
    try:
        offset = db.table_offset.get(image=image.id)
        offset.x = shift[1]
        offset.y = shift[0]
        offset.save()
    except peewee.DoesNotExist:
        db.table_offset(image=image.id, x=shift[1], y=shift[0]).save()
    print("Drift Correction Frame", image.sort_index, shift)

    # Check if ClickPoints wants to terminate us
    if com.HasTerminateSignal():
        print("Cancel Stabilization")
        sys.exit(0)
