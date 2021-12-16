__version__ = "0.1"

import imageio
from imageio import formats
import numpy as np
import struct
import os
import zlib

# imagio format plugin
class BoolFormat(imageio.core.Format):
    def _can_read(self, request):
        if request.mode[1] in (self.modes + '?'):
            if request.filename.lower().endswith(self.extensions):
                return True
            if request.firstbytes.startswith(b"BOOL"):
                return True

    def _can_write(self, request):
        return True

    class Reader(imageio.core.Format.Reader):
        def _open(self):

            self._fp = self.request.get_file()
            self._fp.seek(0)

            self._full_size = self._fp.seek(0, os.SEEK_END)
            self._fp.seek(0)
            self._signature = self._fp.read(4).decode("ascii")
            if self._signature != "BOOL":
                raise ValueError("File has not the correct signature!")

            # self._channels, = struct.unpack(">H", self._fp.read(2))
            self._height, = struct.unpack(">L", self._fp.read(4))
            self._width, = struct.unpack(">L", self._fp.read(4))
            # self._depth, = struct.unpack(">H", self._fp.read(2))

            self.imStart = self._fp.tell()

            self._length = 1

        def _close(self):
            pass

        def _get_length(self):
            return self._length

        def _get_data(self, index):
            # Return the data and meta data for the given index
            if index > self._length:
                raise IndexError("Image index %i > %i" % (index, self._length))
            self._fp.seek(self.imStart)
            val, = struct.unpack(">B", self._fp.read(1))
            out = np.zeros((self._height, self._width), dtype=np.uint8)
            v = 0
            LUT = [val]
            while True:
                try:
                    marker = self._fp.read(4).decode("ascii")
                    assert marker == "VALS", "Could not retrieve value marker!"
                    val, = struct.unpack(">B", self._fp.read(1))
                    LUT.append(val)
                    compressedLen, = struct.unpack(">Q", self._fp.read(8))
                    compressed = self._fp.read(compressedLen)
                    uncompressed = np.unpackbits(np.frombuffer(zlib.decompress(compressed), np.uint8))
                    m = out>=v
                    out[m] += uncompressed[:m.sum()]#*np.array(val-v).astype(np.uint8)
                    v += 1
                except AssertionError:
                    break
                    # return out ,{}
            out = np.array(LUT, dtype=np.uint8)[out]
            return out, {}

        def _get_meta_data(self, index):
            return {}

    class Writer(imageio.core.Format.Writer):
        def _open(self):
            self._fp = self.request.get_file()
        def _close(self):
            pass
        def _append_data(self, im, meta):
            im = np.asarray(im)
            if len(im.shape)==2:
                h, w = im.shape
                c = 1
            # elif len(im.shape)==3:
            #     h, w, c = im.shape
            else:
                raise ValueError("Bool format only accepts 2D Arrays!")
            self._fp.write(b"BOOL")
            # self._fp.write(struct.pack(">H", c))
            self._fp.write(struct.pack(">L", h))
            self._fp.write(struct.pack(">L", w))

            rawVals = im.flatten()
            if im.max()==1:
                vals = np.array([0,1])
            else:
                bc = np.bincount(rawVals)
                # LUT = np.sort(np.array(zip(np.arange(len(bc)), np.argsort(bc)[::-1])), kind=1)
                LUT = np.argsort(np.argsort(bc)[::-1])
                vals = (np.arange(len(bc))[bc>0])[np.argsort(LUT[bc>0])]
                rawVals = LUT[rawVals]

            self._fp.write(struct.pack(">B", vals[0]))
            # for v in vals[1:]:
            for v in range(len(vals[1:])):
                self._fp.write(b"VALS")
                self._fp.write(struct.pack(">B", vals[1:][v]))
                m = rawVals> v

                sizePointer = self._fp.tell()
                self._fp.seek(sizePointer+8)
                compressedLen = self._fp.write(
                    zlib.compress(np.packbits(m).tobytes(), level=9)
                )
                self._fp.seek(sizePointer)
                self._fp.write(struct.pack(">Q", compressedLen))
                self._fp.seek(sizePointer+8+compressedLen)
                rawVals = rawVals[m]


        def set_meta_data(self, meta):
            pass


# Register instance of Format class for VisFormat
format = BoolFormat('bool',  # short name
                   'bool format as used by Clickpoints for masks',  # description
                   '.bool',  # list of extensions
                   'i'  # modes, characters in iIvV
                   )

if "BOOL" not in formats.get_format_names():
    formats.add_format(format)

if __name__ == "__main__":
    from time import time

    class timer():
        def __init__(self, name="", end=None):
            self.st = None
            self.name = str(name)
            self.end = end

        def __enter__(self):
            self.st = time()

        def __exit__(self, exc_type, exc_val, exc_tb):
            print(self.name, time() - self.st, end=self.end)

    import numpy as np
    import os
    for i in [2,3,4,8,16,32,128,256]:
    # for i in [2]:
        print("Nvals: ", i, end="\t")
        np.random.seed(123)
        # mask = np.random.randint(i, size=(100,100)).astype(np.uint8)
        mask = np.random.choice(np.arange(256, dtype=np.uint8), i, replace=False)[np.random.randint(i, size=(1000, 1000)).astype(np.uint8)]
        # mask = (mask==mask.max()).astype(np.uint8)
        # mask = (np.random.random(size=(100, 100))>0.99).astype(np.uint8)
        path = r"test.bool"
        path2 = r"test.png"
        with timer("Write:", end="\t"):
            writer = imageio.get_writer(path)
            writer.append_data(mask, {})
            writer.close()
        with timer("Read:", end="\t"):
            reader = imageio.get_reader(path)
            m2 = reader.get_data(0)
        assert np.all(m2==mask), "Could not reproduce test image!"
        print("Size on disk", os.stat(path).st_size, end="\t")

        with timer("WritePNG:", end="\t"):
            writer = imageio.get_writer(path2)
            writer.append_data(mask, {})
            writer.close()
        with timer("ReadPNG:", end="\t"):
            reader = imageio.get_reader(path2)
            m2 = reader.get_data(0)
        assert np.all(m2==mask), "Could not reproduce test image!"
        print("Size on diskPNG", os.stat(path2).st_size)
