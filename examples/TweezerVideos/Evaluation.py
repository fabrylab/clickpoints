from __future__ import print_function, division
import os
import sys
import numpy as np
import matplotlib.pyplot as plt

from MarkerLoad import LoadLog

folder = sys.argv[1]
pos = "frame%04d_pos.txt"
img = "frame%04d.tif"
tracks = None
track_ids = None
for frame in range(80):
    try:
        points, types = LoadLog(os.path.join(folder, pos % frame))
    except IOError:
        break
    if tracks is None:
        tracks = [[[point["x"], point["y"]]] for point in points]
        track_ids = [point["id"] for point in points]
    else:
        for point in points:
            index = track_ids.index(point["id"])
            tracks[index].append([point["x"], point["y"]])

tracks = np.array(tracks)

for track in tracks:
    y = np.array([(pt-track[0, 0]) for pt in track[:, 0]])*6.45/40.
    plt.plot(y)

plt.show()
