from __future__ import print_function, division
import sys
import numpy as np

# define tracking parameter
import cv2
lk_params = dict(winSize=(8, 8), maxLevel=0, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))

# connect to ClickPoints database and the running program instance
# database filename and port for communication are supplied as command line argument when started from ClickPoints
import clickpoints
start_frame, database, port = clickpoints.GetCommandLineArgs()
db = clickpoints.DataFile(database)
com = clickpoints.Commands(port, catch_terminate_signal=True)

# get the images
images = db.GetImages(start_frame=start_frame)

# retrieve first image
image_last = images[0]

# get points and corresponding tracks
points = db.GetMarker(image=image_last.id, processed=0)
p0 = np.array([[point.x, point.y] for point in points if point.track_id]).astype(np.float32)
tracking_ids = [point.track_id for point in points if point.track_id]
types = [point.type_id for point in points if point.track_id]

# if no tracks are supplied, stop
if len(tracking_ids) == 0:
    print("Nothing to track")
    sys.exit(-1)

# start iterating over all images
for image in images[1:]:
    print("Tracking frame number %d, %d tracks" % (image.sort_index, len(tracking_ids)))

    # calculate next positions
    p1, st, err = cv2.calcOpticalFlowPyrLK(image_last.data8, image.data8, p0, None, **lk_params)

    # set the new positions
    db.SetMarker(image=image.id, x=p1[:, 0], y=p1[:, 1], processed=0, type=types, track=tracking_ids)

    # mark the marker in the last frame as processed
    db.SetMarker(image=image_last.id, processed=1, type=types, track=tracking_ids)

    # update ClickPoints
    com.ReloadMarker(image.sort_index)
    com.JumpToFrameWait(image.sort_index)

    # store positions and image
    p0 = p1
    image_last = image

    # check if we should terminate
    if com.HasTerminateSignal():
        print("Cancelled Tracking")
        sys.exit(0)
