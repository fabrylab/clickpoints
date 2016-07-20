# -*- coding: utf-8 -*-
from __future__ import division, print_function
import xlwt

# connect to ClickPoints database
# database filename is supplied as command line argument when started from ClickPoints
import clickpoints
start_frame, database, port = clickpoints.GetCommandLineArgs()
db = clickpoints.DataFile(database)
com = clickpoints.Commands(port, catch_terminate_signal=True)

# prepare write to excel
wb_name = database.replace('.cdb','.xls')
wb = xlwt.Workbook()
wb_sheet = wb.add_sheet('data')

# get types and images
q_types =  db.GetTypes()
q_images = db.GetImages()

# write xls header
wb_sheet.write(0,0, "sort_idx")
wb_sheet.write(0,1, "filename")
for idx,type in enumerate(q_types):
    wb_sheet.write(0,idx+2, type.name + '_count')
header_offset = 1

# write marker counts per image
for ridx,image in enumerate(q_images):
    ridx = ridx + header_offset
    wb_sheet.write(ridx,0,image.sort_index)
    wb_sheet.write(ridx,1,image.filename)

    # extract type information
    for idx,type in enumerate(q_types):
        if type.mode == 0:
            q_marker = db.GetMarker(type=type,image=image)
        elif type.mode == 1:
            q_marker = db.GetRectangles(type=type,image=image)
        elif type.mode == 2:
            q_marker = db.GetLines(type=type,image=image)
        else:
            continue

        wb_sheet.write(ridx,idx+2,q_marker.count())

print("Writing to %s" % wb_name)
wb.save(wb_name)
print("DONE")
