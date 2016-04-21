from __future__ import print_function, division
import sys
import numpy as np
import os
import time
import argparse

# define tracking parameter
import cv2
lk_params = dict(winSize=(8, 8), maxLevel=0, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))

# connect to ClickPoints database and the running program instance
# database filename and port for communication are supplied as command line argument when started from ClickPoints
import clickpoints
df = clickpoints.DataFile()
com = clickpoints.Commands(catch_terminate_signal=True)

# get start frame from command line arguments
parser = argparse.ArgumentParser()
parser.add_argument("--start_frame", type=int, dest='start_frame', help='specify at which frame to start')
args, unknown = parser.parse_known_args()
if args.start_frame:
    start_frame = args.start_frame
else:
    start_frame = 0

image_data_current, image_id_current = com.GetImage(start_frame)
points = df.GetMarker(image=image_id_current, processed=0)
p0 = np.array([[point.x, point.y] for point in points if point.track_id]).astype(np.float32)
tracking_ids = [point.track_id for point in points if point.track_id]
types = [point.type_id for point in points if point.track_id]

if len(tracking_ids) == 0:
    print("Nothing to track")
    sys.exit(-1)

frame = start_frame
while True:
    image_data_next, image_id_next = com.GetImage(frame+1)
    if image_data_next is None:
        print("Reached end")
        break

    print("Tracking frame number %d, %d tracks" % (frame, len(tracking_ids)))
    p1, st, err = cv2.calcOpticalFlowPyrLK(image_data_current, image_data_next, p0, None, **lk_params)

    df.SetMarker(image=image_id_next, x=p1[:, 0], y=p1[:, 1], processed=0, type=types, track=tracking_ids)
    df.SetMarker(image=image_id_current, processed=1, type=types, track=tracking_ids)
    com.ReloadMarker(frame+1)
    com.JumpToFrameWait(frame+1)

    p0 = p1
    image_id_current = image_id_next
    image_data_current = image_data_next
    frame += 1

    if com.HasTerminateSignal():
        print("Cancelled Tracking")
        sys.exit(0)
