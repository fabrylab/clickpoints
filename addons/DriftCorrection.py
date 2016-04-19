from __future__ import division, print_function
import cv2
import numpy as np
from scipy.ndimage.measurements import center_of_mass
import peewee
import sys
import argparse

import clickpoints

# Connect to database
df = clickpoints.DataFile()
com = clickpoints.Commands(catch_terminate_signal=True)

# Define parameters
compare_to_first = False
border_x = 20
border_y = 20

# Check if the marker type is present
if not df.GetType("drift_rect"):
    df.AddType("drift_rect", [0, 255, 255], df.TYPE_Rect)
    com.ReloadTypes()

# try to load marker
rect = df.GetMarker(type_name="drift_rect")
x = [p.x for p in rect]
y = [p.y for p in rect]
if len(x) < 2:
    print("ERROR: no rectangle selected.\nPlease mark a rectangle with type 'drift_rect'.")
    sys.exit(-1)

# get drift correction rectangle
roi_x2 = np.min(x)
roi_width2 = np.abs(np.diff(x))
roi_y2 = np.min(y)
roi_height2 = np.abs(np.diff(y))


# get start data
# get start frame from command line arguments
parser = argparse.ArgumentParser()
parser.add_argument("--start_frame", type=int, dest='start_frame', help='specify at which frame to start')
args, unknown = parser.parse_known_args()
if args.start_frame:
    start_frame = args.start_frame
else:
    start_frame = 0

img, image_id = com.GetImage(start_frame)
template = img[roi_y2-border_y:roi_y2+roi_height2+border_y, roi_x2-border_x:roi_x2+roi_width2+border_x]

# start iteration
last_shift = np.array([0, 0])
i = start_frame
while True:
    # get next image if there is one
    i += 1
    img, image_id = com.GetImage(i)
    if img is None:
        break

    # template matching for drift correction
    res = cv2.matchTemplate(img[roi_y2:roi_y2+roi_height2, roi_x2:roi_x2+roi_width2], template, cv2.TM_CCOEFF)
    res += np.amin(res)
    res = res**4.

    # get 2D max
    shift = np.unravel_index(res.argmax(), res.shape)

    # get sub pixel accurate center of mass
    try:
        # fail if there it is too close to border
        if not (shift[0] > 2 and shift[1] > 2):
            raise Exception

        subres = res[shift[0]-2:shift[0]+3,shift[1]-2:shift[1]+3]
        subshift = center_of_mass(subres)


        # calculate coordinates of subshift
        shift = shift + (subshift - np.array([2,2]))
        # calculate full image coordinates of shift
        shift = shift - np.array([border_y, border_x])
    except:
        # calculate full image coordinates of shift
        shift = shift - np.array([border_y, border_x])

    # get new template if compare_to_first is off
    if not compare_to_first:
        template = img[roi_y2-border_y:roi_y2+roi_height2+border_y, roi_x2-border_x:roi_x2+roi_width2+border_x]
        shift += last_shift
        last_shift = shift

    # save the offset to the database
    try:
        offset = df.table_offsets.get(image=image_id)
        offset.x = shift[1]
        offset.y = shift[0]
        offset.save()
    except peewee.DoesNotExist:
        df.table_offsets(image=image_id, x=shift[1], y=shift[0]).save()
    print("Drift Correction Frame", i, shift)

    # Check if ClickPoints wants to terminate us
    if com.HasTerminateSignal():
        print("Cancelle Stabilization")
        sys.exit(0)
