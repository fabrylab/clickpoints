#!/usr/bin/env python
# -*- coding: utf-8 -*-
# MemMap.py

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

import os
import numpy as np
from collections import OrderedDict
import xml.etree.ElementTree as ET
import xml.dom.minidom

class MemMap(object):

    def __init__(self, filename, layout=None, offset=0):
        self.maps = OrderedDict()
        self.layout = []
        self.single = {}
        if filename.endswith(".xml"):
            layout, filename = loadXML(filename)
        self.filename = filename
        self.start_offset = offset
        self.offset = offset
        self.add(layout)

    def add(self, layout):
        mode = 'r+' if os.path.exists(self.filename) else 'w+'
        for variable in layout:
            self.layout.append(variable)
            name = variable["name"]
            type = variable["type"]
            if "shape" in variable:
                shape = variable["shape"]
                self.single[name] = 0
            else:
                shape = (1,)
                self.single[name] = 1
            if "align" in variable:
                if self.offset % variable["align"] != 0:
                    self.offset += variable["align"] - self.offset % variable["align"]
            if type == "memmap":
                if self.single[name]:
                    map = MemMap(self.filename, variable["layout"], offset=self.offset)
                    self.offset = map.offset
                else:
                    map = []
                    for i in range(shape[0]):
                        map_child = MemMap(self.filename, variable["layout"], offset=self.offset)
                        self.offset = map_child.offset
                        map.append(map_child)
            else:
                map = np.memmap(self.filename, dtype=type, mode=mode, offset=self.offset, shape=shape)
                self.offset += map.itemsize*map.size
            self.maps[name] = map
            mode = 'r+'

    def __getattr__(self, name):
        if name != "maps" and name in self.maps:
            if self.single[name] == 1:
                return self.maps[name][0]
            return self.maps[name]
        if name in dir(self):
            return getattr(self, name)
        raise AttributeError(name)

    def __setattr__(self, name, value):
        if name != "maps" and name in self.maps:
            if self.single[name] == 1:
                self.maps[name][0] = value
            else:
                raise ValueError("Access memmap array with []")
        else:
            super(MemMap, self).__setattr__(name, value)

    def __str__(self):
        text = "<Memmap: \"%s\" from bytes %d to %d>" % (self.filename, self.start_offset, self.offset)
        for name in self.maps:
            if self.single[name]:
                text += "\n%s: %s" % (name, self.maps[name][0].__str__())
            else:
                text += "\n%s: %s" % (name, self.maps[name].__str__())
        return text

    def saveXML(self, xml_filename):
        saveXML(xml_filename, self.layout, self.filename)

def getLayout(root):
    layout = []
    for child in root:
        element = child.attrib
        if element["type"] == "memmap":
            element["layout"] = getLayout(child)
        if "align" in element:
            element["align"] = int(element["align"])
        if "shape" in element:
            element["shape"] = tuple(int(part) for part in element["shape"].split())
        layout.append(element)
    return layout

def loadXML(xml_filename):
    root = ET.parse(xml_filename).getroot()
    memmap_filename = os.path.relpath(root.get("file"), os.path.dirname(xml_filename))
    return getLayout(root), memmap_filename

def getXML(layout, root):
    for element in layout:
        element = element.copy()
        sub_layout = None
        if "layout" in element:
            sub_layout = element["layout"]
            del element["layout"]
        if "align" in element:
            element["align"] = str(element["align"])
        if "shape" in element:
            element["shape"] = " ".join([str(i) for i in element["shape"]])
        sub_elm = ET.SubElement(root, 'entry', attrib=element)
        if sub_layout is not None:
            getXML(sub_layout, sub_elm)

def saveXML(xml_filename, layout, filename):
    filename = os.path.relpath(filename, os.path.dirname(xml_filename))
    root = ET.Element('memmap', attrib=dict(file=filename))
    getXML(layout, root)
    import xml.dom.minidom
    xml_dom = xml.dom.minidom.parseString(ET.tostring(root))
    with open(xml_filename, "w") as fp:
        fp.write(xml_dom.toprettyxml())

if __name__ == "__main__":
    layout = (dict(name="busy", type="uint8"),
              dict(name="command", type="|S30", align=32),
              dict(name="image", type="memmap", shape=(10), layout=(
                  dict(name="width", type="uint16"),
                  dict(name="height", type="uint16"),
                  dict(name="length", type="uint16"),
              )),
              dict(name="list", type="uint8", shape=(10)))
    layout = loadXML('TestMemmap.xml')
    a = MemMap(r"J:\Repositories\ClickPointsProject\clickpoints\includes\testing.xml")
    a.saveXML("testing2.xml")

    a.image[0].width = 131
    a.image[0].height = 121
    a.image[0].length = 379

    #a.image[1].width = 20
    #a.image[1].height = 221
    print(a.image[0])
    print(a.image[1])
    print(a)
