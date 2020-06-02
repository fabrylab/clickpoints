#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Sorter.py

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

from __future__ import print_function, division
import clickpoints
import os
import re
from qtpy import QtCore
try:
    import ConfigParser as configparser # Python 2
except ImportError:
    import configparser  # Python 3


def parse(format, string):
    """ parse a string according to a print format string """
    format_re = ""
    # iterate over the format to find all fields and compose a regular expresion for it.
    while len(format):
        # find the beginning of a format block
        pos = format.find("{")
        # if not we are done already
        if pos == -1:
            format_re += format
            break
        # add the part before the block to the regular expression
        format_re += format[:pos]
        # and keep only the next part
        format = format[pos+1:]

        # find the end of the format block
        pos = format.find("}")
        # get the placeholder
        placeholder = format[:pos]
        # and keep the rest
        format = format[pos+1:]

        # split the placeholder in name and format
        split = placeholder.split(":")
        if len(split) > 1:
            fmt = split[1]
            # a number format
            if fmt[-1] == "d":
                fmt = "\d"*int(fmt[:-1])
            # any string
            else:
                fmt = "\S+"
        # any string
        else:
            fmt = "\S+"
        # add the format to the regular expression
        format_re += "(?P<%s>%s)" % (split[0], fmt)
    # match the regular expression
    mydict = re.match(format_re, string).groupdict()
    # split a number form the z value, thanks Chris for putting those numbers there ;-)
    if "Indices" in mydict["z"]:
        # numbers are found directly after the word "Indices"
        pos = mydict["z"].find("Indices")
        mydict["z"] = mydict["z"][:pos+len("Indices")]
    # return the dictionary
    return mydict


class Addon(clickpoints.Addon):
    finished = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        clickpoints.Addon.__init__(self, *args, **kwargs)
        self.finished.connect(lambda: self.cp.updateImageCount())

    def sort(self):
        # get the first image
        image0 = self.db.getImage(0)
        # and extract from its filename the filename of the config
        config_filename = image0.filename.split("_")[0]+"_Config.txt"
        print(config_filename)
        # load the config
        if not os.path.exists(config_filename):
            print("No Config Found - Terminating!")
            return
        config = configparser.ConfigParser()
        config.read(config_filename)
        # get the filename format string from the condig
        format = os.path.split(config.get("dynamic", "filename"))[1]

        # iterate over all images to get all unique index values
        z_values = []
        for image in self.db.getImages():
            # parse the image filename
            data = parse(format, image.filename)
            # compose the index_value
            index_value = data["pos"]+"-"+data["x"]+"-"+data["y"]+data["mode"]+data["z"]
            # add it to the list, if it isn't there already
            if index_value not in z_values:
                z_values.append(index_value)
        # sort the index list
        z_values.sort()

        last_pos_value = None
        base_layer = None

        # iterate over the images again and set the layer
        for image in self.db.getImages():
            print("parsing image", image)
            # parse the image filename
            data = parse(format, image.filename)
            # compose the index_value
            index_value = data["pos"] + "-" + data["x"] + "-" + data["y"] + data["mode"] + data["z"]
            pos_value = data["pos"] + "-" + data["x"] + "-" + data["y"]
            # set the sort_index according to the measurement repetition
            image.sort_index = int(data["repetition"])
            # and the layer as the index value
            if pos_value != last_pos_value:
                print("Differente", last_pos_value, pos_value)
                last_pos_value = pos_value
                print("Differente", last_pos_value, pos_value)
                print("get layer", index_value, pos_value, None)
                base_layer = self.db.getLayer(index_value, create=True)
                image.layer = base_layer
            else:
                print("get layer", index_value, pos_value, base_layer)
                image.layer = self.db.getLayer(index_value, base_layer=base_layer, create=True)
            # save the image
            image.save()

        # delete empty layers
        self.db.db.execute_sql("DELETE FROM layer WHERE (SELECT count(i.id) FROM image i WHERE i.layer_id = layer.id) = 0")

        # notify ClickPoints that we have meddled with the image list
        self.finished.emit()

    def run(self, *args, **kwargs):
        # sort when the user clicks the button
        self.sort()
