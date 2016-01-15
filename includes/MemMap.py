import os
import numpy as np
from collections import OrderedDict
class MemMap(object):

    def __init__(self, filename, layout, offset=0):
        self.maps = OrderedDict()
        self.single = {}
        self.filename = filename
        self.start_offset = offset
        self.offset = offset
        self.add(layout)

    def add(self, layout):
        mode = 'r+' if os.path.exists(self.filename) else 'w+'
        for variable in layout:
            name = variable["name"]
            type = variable["type"]
            if "shape" in variable:
                shape = variable["shape"]
                self.single[name] = 0
            else:
                shape = (1)
                self.single[name] = 1
            if "align" in variable:
                if self.offset % variable["align"] != 0:
                    self.offset += variable["align"] - self.offset % variable["align"]
            self.names = name
            if type == "memmap":
                if self.single[name]:
                    map = MemMap(self.filename, variable["layout"], offset=self.offset)
                    self.offset = map.offset
                else:
                    map = []
                    for i in range(shape):
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

if __name__ == "__main__":
    layout = (dict(name="busy", type="uint8"),
              dict(name="command", type="|S30", align=32),
              dict(name="image", type="memmap", shape=(10), layout=(
                  dict(name="width", type="uint16"),
                  dict(name="height", type="uint16"),
                  dict(name="length", type="uint16"),
              )),
              dict(name="list", type="uint8", shape=(10)))
    a = MemMap("test.dat", layout)

    a.image[0].width = 131
    a.image[0].height = 121
    a.image[0].length = 379

    #a.image[1].width = 20
    #a.image[1].height = 221
    print(a.image[0])
    print(a.image[1])
    print(a)