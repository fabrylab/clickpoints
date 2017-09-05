#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ExportMarkerCountToXLS.py

# Copyright (c) 2015-2016, Richard Gerum, Sebastian Richter
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ClickPoints. If not, see <http://www.gnu.org/licenses/>

from __future__ import division, print_function
import xlwt
import clickpoints


class Addon(clickpoints.Addon):
    def run(self, start_frame=0):
        # prepare write to excel
        wb_name = self.db._database_filename.replace('.cdb', '.xls')
        wb = xlwt.Workbook()
        wb_sheet = wb.add_sheet('data')

        # get types and images
        q_types = self.db.getMarkerTypes()
        q_images = self.db.getImages()

        # write xls header
        wb_sheet.write(0, 0, "sort_idx")
        wb_sheet.write(0, 1, "filename")
        for idx, type in enumerate(q_types):
            wb_sheet.write(0, idx + 2, type.name + '_count')
        header_offset = 1

        # write marker counts per image
        for ridx, image in enumerate(q_images):
            ridx += header_offset
            wb_sheet.write(ridx, 0, image.sort_index)
            wb_sheet.write(ridx, 1, image.filename)

            # extract type information
            for idx, type in enumerate(q_types):
                if type.mode == 0:
                    q_marker = self.db.getMarkers(type=type, image=image)
                elif type.mode == 1:
                    q_marker = self.db.getRectangles(type=type, image=image)
                elif type.mode == 2:
                    q_marker = self.db.getLines(type=type, image=image)
                else:
                    continue

                wb_sheet.write(ridx, idx + 2, q_marker.count())

        print("Writing to %s" % wb_name)
        wb.save(wb_name)
        print("DONE")
