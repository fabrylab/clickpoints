#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ExportToExcel.py

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
import xlwt
import clickpoints
from clickpoints.includes.QtShortCuts import AddQComboBox, AddQSaveFileChoose
from qtpy import QtCore, QtGui, QtWidgets

class Addon(clickpoints.Addon):
    def __init__(self, *args, **kwargs):
        clickpoints.Addon.__init__(self, *args, **kwargs)
        # set the title and layout
        self.setWindowTitle("Excel Exporter - ClickPoints")
        layout = QtWidgets.QVBoxLayout(self)

        # add a file chooser for the output
        self.line_edit_file = AddQSaveFileChoose(layout, "Path", value=self.db._database_filename.replace('.cdb', '.xls'), file_type="Excel Workbook (*.xls)")
        # add a mode selector, which formatting should be used for the output
        self.combo_style = AddQComboBox(layout, "Mode", values=["Marker Count", "Marker Positions", "Track Positions"])
        self.button_run = QtWidgets.QPushButton("Export")
        self.button_run.clicked.connect(self.run)
        layout.addWidget(self.button_run)

    def buttonPressedEvent(self):
        self.show()

    def exportMarkerCount(self, wb):
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
                if type.mode == 1:
                    q_marker = self.db.getRectangles(type=type, image=image)
                elif type.mode == 2:
                    q_marker = self.db.getLines(type=type, image=image)
                else:
                    q_marker = self.db.getMarkers(type=type, image=image)

                wb_sheet.write(ridx, idx + 2, q_marker.count())

    def exportMarkerPositions(self, wb):

        # get types and images
        q_types = self.db.getMarkerTypes()
        q_images = self.db.getImages()

        for type in q_types:
            wb_sheet = wb.add_sheet(type.name)

            # write xls header
            wb_sheet.write(0, 0, "sort_idx")
            wb_sheet.write(0, 1, "filename")
            header_offset = 1
            maximum_header_column = -1

            # write marker counts per image
            for ridx, image in enumerate(q_images):
                ridx += header_offset
                wb_sheet.write(ridx, 0, image.sort_index)
                wb_sheet.write(ridx, 1, image.filename)

                # extract type information for markers
                try:
                    marker_query = self.db.getMarkers(image=image, type=type)
                except ValueError:
                    # not a marker type
                    continue
                for idx, marker in enumerate(marker_query):
                    wb_sheet.write(ridx, idx*2 + 2, marker.x)
                    wb_sheet.write(ridx, idx*2 + 3, marker.y)

                    # add headers x, y
                    if idx > maximum_header_column:
                        wb_sheet.write(0, idx * 2 + 2, "x")
                        wb_sheet.write(0, idx * 2 + 3, "y")
                        maximum_header_column = idx

                # extract type information for lines
                try:
                    line_query = self.db.getLines(image=image, type=type)
                except ValueError:
                    # type is not a line type
                    continue
                for idx, marker in enumerate(line_query):
                    wb_sheet.write(ridx, idx * 4 + 2, marker.x1)
                    wb_sheet.write(ridx, idx * 4 + 3, marker.y1)
                    wb_sheet.write(ridx, idx * 4 + 4, marker.x2)
                    wb_sheet.write(ridx, idx * 4 + 5, marker.y2)

                    # add headers x1, y1, x2, y2
                    if idx > maximum_header_column:
                        wb_sheet.write(0, idx * 4 + 2, "x1")
                        wb_sheet.write(0, idx * 4 + 3, "y1")
                        wb_sheet.write(0, idx * 4 + 4, "x2")
                        wb_sheet.write(0, idx * 4 + 5, "y2")
                        maximum_header_column = idx

                # extract type information for rectangles
                for idx, marker in enumerate(self.db.getRectangles(image=image, type=type)):
                    wb_sheet.write(ridx, idx * 4 + 2, marker.x)
                    wb_sheet.write(ridx, idx * 4 + 3, marker.y)
                    wb_sheet.write(ridx, idx * 4 + 4, marker.width)
                    wb_sheet.write(ridx, idx * 4 + 5, marker.height)

                    # add headers x, y, width, height
                    if idx > maximum_header_column:
                        wb_sheet.write(0, idx * 4 + 2, "x")
                        wb_sheet.write(0, idx * 4 + 3, "y")
                        wb_sheet.write(0, idx * 4 + 4, "width")
                        wb_sheet.write(0, idx * 4 + 5, "height")
                        maximum_header_column = idx

    def exportTrackPositions(self, wb):
        wb_sheet = wb.add_sheet('data')

        # get types and images
        q_types = self.db.getMarkerTypes()
        q_images = self.db.getImages()

        # write xls header
        wb_sheet.write(0, 0, "sort_idx")
        wb_sheet.write(0, 1, "filename")
        # get the tracks for each type
        tracks = []
        for idx, type in enumerate(q_types):
            try:
                track_query = self.db.getTracks(type=type)
            except ValueError:
                # ignore marker types that are not tracks
                continue
            for track in track_query:
                wb_sheet.write(0, len(tracks)*2 + 2, type.name + ' #%d' % track.id)
                tracks.append(track)
        header_offset = 1

        # write marker counts per image
        for ridx, image in enumerate(q_images):
            ridx += header_offset
            wb_sheet.write(ridx, 0, image.sort_index)
            wb_sheet.write(ridx, 1, image.filename)

            # write the marker position for each track
            for idx, track in enumerate(tracks):
                marker = self.db.getMarkers(image=image, track=track)
                if marker.count():
                    x, y = marker[0].pos()
                    wb_sheet.write(ridx, idx*2 + 2, x)
                    wb_sheet.write(ridx, idx*2 + 3, y)

    def run(self, start_frame=0):
        # prepare write to excel
        wb_name = self.line_edit_file.text()
        wb = xlwt.Workbook()

        # List Marker Count
        if self.combo_style.currentIndex() == 0:
            self.exportMarkerCount(wb)
        # List Marker Positions
        if self.combo_style.currentIndex() == 1:
            self.exportMarkerPositions(wb)
        # List Track Positions
        if self.combo_style.currentIndex() == 2:
            self.exportTrackPositions(wb)

        print("Writing to %s" % wb_name)
        try:
            wb.save(wb_name)
        except PermissionError as err:
            QtWidgets.QMessageBox.critical(self, 'Error - ClickPoints',
                                           '%s\n\nMaybe the file is still open in Excel. Please close it and try again.' % err,
                                           QtWidgets.QMessageBox.Ok)
            raise err
        QtWidgets.QMessageBox.information(self, 'Add-on - ClickPoints',
                                          'Data saved to %s.' % wb_name, QtWidgets.QMessageBox.Ok)
        print("DONE")
