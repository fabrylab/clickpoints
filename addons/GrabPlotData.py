from __future__ import division, print_function
import os, sys
import clickpoints
__icon__ = "fa.th"

def Remap(value, minmax1, minmax2):
    """ Map from range minmax1 to range minmax2 """
    length1 = minmax1[1]-minmax1[0]
    length2 = minmax2[1]-minmax2[0]
    if length1 == 0:
        return 0
    percentage = (value-minmax1[0])/length1
    return percentage*length2 + minmax2[0]

# Connect to database
start_frame, database, port = clickpoints.GetCommandLineArgs()
db = clickpoints.DataFile(database)
com = clickpoints.Commands(port, catch_terminate_signal=True)

# Check if the marker types are present
reload_types = False
if not db.getMarkerType("x_axis"):
    db.setMarkerType("x_axis", [0, 200, 0], db.TYPE_Line)
    reload_types = True
if not db.setMarkerType("y_axis"):
    db.setMarkerType("y_axis", [200, 200, 0], db.TYPE_Line)
    reload_types = True
if not db.getMarkerType("data"):
    db.setMarkerType("data", [200, 0, 0], db.TYPE_Normal)
    reload = True
if reload_types:
    com.ReloadTypes()

# get the current image
image = db.getImageIterator(start_frame).next()

# try to load axis
x_axis = db.getLines(image=image, type="x_axis")
y_axis = db.getLines(image=image, type="y_axis")
if len(x_axis) != 1 or len(y_axis) != 1:
    print("ERROR: Please mark exactly one line with type 'x_axis' and exactly one with 'y_axis'.\nFound %d x_axis and %d y_axis" % (len(x_axis), len(y_axis)))
    sys.exit(-1)
x_axis = x_axis[0]
y_axis = y_axis[0]

# create remap functions for x and y axis
remap_x = lambda x: Remap(x, [x_axis.marker1.x, x_axis.marker2.x], [float(x_axis.marker1.text), float(x_axis.marker2.text)])
remap_y = lambda y: Remap(y, [y_axis.marker1.y, y_axis.marker2.y], [float(y_axis.marker1.text), float(y_axis.marker2.text)])

# get all markers
markers = db.getMarkers(image=image, type="data")
# compose the output filename
filename = os.path.splitext(image.filename)[0]+".txt"
# iterate over all data markers
with open(filename, "w") as fp:
    for data in markers:
        print(remap_x(data.x), remap_y(data.y))
        fp.write("%f %f\n" % (remap_x(data.x), remap_y(data.y)))
# print success
print("%d datepoints written to file \"%s\"" % (markers.count(), filename))
