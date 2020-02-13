import tifffile
import numpy
from concurrent.futures import ThreadPoolExecutor
import numpy as np

def assign_to_array_offset(target, target_slice, source, offset):
    source_slice = []
    target_slice_new = []
    j = 0
    for i, s in enumerate(target_slice):
        if isinstance(s, int):
            target_slice_new.append(s-offset[i])
            continue
        start = s.start if s.start is not None else 0
        start_new = start-offset[i]
        if start_new < 0:
            start_delta = -start_new
            start_new = 0
        else:
            start_delta = 0
        if start_new > target.shape[i]:
            return
        stop = s.stop
        stop_new = stop - offset[i]
        if stop_new < 0:
            return
        if stop_new > target.shape[i]:
            stop_delta = stop_new - target.shape[i]
            stop_new = target.shape[i]
        else:
            stop_delta = 0
        stop_delta = (source.shape[j] - start_delta) - (stop_new-start_new)
        s = slice(start_new, stop_new, s.step)
        target_slice_new.append(s)
        if stop_delta != 0:
            s = slice(start_delta, - stop_delta)
        else:
            s = slice(start_delta, None)
        source_slice.append(s)
        j += 1
    target[tuple(target_slice_new)] = source[tuple(source_slice)]


def get_used_tiles(N, tileshape, tiledshape, loc, size):
    tileddepth, tiledlength, tiledwidth = tiledshape
    tiledepth, tilelength, tilewidth, samples = tileshape
    tilesize = tiledepth * tilelength * tilewidth * samples

    x1, y1 = loc
    w, h = size
    x2, y2 = x1+w, y1+h
    use = []
    for tileindex in range(N):
        pl = tileindex // (tiledwidth * tiledlength * tileddepth)
        td = (tileindex // (tiledwidth * tiledlength)) % tileddepth * tiledepth
        tl = (tileindex // tiledwidth) % tiledlength * tilelength
        tw = tileindex % tiledwidth * tilewidth
        #print("try", tileindex, x1, x2, tw, tw+tilewidth, end="")
        if (x1 > tw + tilewidth) or (x2 < tw):
            #print("no")
            continue
        if (y1 > tl + tilelength) or (y2 < tl):
            #print("no")
            continue
            #if (tl <= y1 < tl + tilelength) or (tl <= y2 < tl + tilelength):
        use.append(tileindex)
        #print("yes")

    return use


#### monkey patch tifffile ####

def tile_decode(tile, tileindex, tileshape, tiledshape,
                lsb2msb, decompress, unpack, unpredict, nodata, out, offset=None, total_shape=None):
    """Decode tile segment bytes into 5D output array."""
    if total_shape is None:
        _, imagedepth, imagelength, imagewidth, _ = out.shape
    else:
        _, imagedepth, imagelength, imagewidth, _ = total_shape
    tileddepth, tiledlength, tiledwidth = tiledshape
    tiledepth, tilelength, tilewidth, samples = tileshape
    tilesize = tiledepth * tilelength * tilewidth * samples
    pl = tileindex // (tiledwidth * tiledlength * tileddepth)
    td = (tileindex // (tiledwidth * tiledlength)) % tileddepth * tiledepth
    tl = (tileindex // tiledwidth) % tiledlength * tilelength
    tw = tileindex % tiledwidth * tilewidth

    if tile is None:
        out[pl,
            td: td + tiledepth,
            tl: tl + tilelength,
            tw: tw + tilewidth] = nodata
        return

    if lsb2msb:
        tile = tifffile.bitorder_decode(tile, out=tile)
    tile = decompress(tile)
    tile = unpack(tile)
    # decompression / unpacking might return too many bytes
    tile = tile[:tilesize]
    try:
        # complete tile according to TIFF specification
        tile.shape = tileshape
    except ValueError:
        # tile fills remaining space; found in some JPEG compressed slides
        s = (
            min(imagedepth - td, tiledepth),
            min(imagelength - tl, tilelength),
            min(imagewidth - tw, tilewidth),
            samples,
        )
        try:
            tile.shape = s
        except ValueError:
            # incomplete tile; see gdal issue #1179
            tifffile.log_warning('tile_decode: incomplete tile %s %s',
                        tile.shape, tileshape)
            t = numpy.zeros(tilesize, tile.dtype)
            s = min(tile.size, tilesize)
            t[:s] = tile[:s]
            tile = t.reshape(tileshape)
    tile = unpredict(tile, axis=-2, out=tile)
    if offset is not None:
        assign_to_array_offset(out, (pl, slice(td, td + tiledepth), slice(tl, tl + tilelength), slice(tw, tw + tilewidth)),
                               tile[:imagedepth - td,
                               :imagelength - tl,
                               :imagewidth - tw], offset)
    else:
        out[pl,
            td: td + tiledepth,
            tl: tl + tilelength,
            tw: tw + tilewidth] = tile[:imagedepth - td,
                                       :imagelength - tl,
                                       :imagewidth - tw]

def asarray(self, out=None, squeeze=True, lock=None, reopen=True,
            maxsize=None, maxworkers=None, validate=True, loc=None, size=None):
    """Read image data from file and return as numpy array.

    Raise ValueError if format is unsupported.

    Parameters
    ----------
    out : numpy.ndarray, str, or file-like object
        Buffer where image data will be saved.
        If None (default), a new array will be created.
        If numpy.ndarray, a writable array of compatible dtype and shape.
        If 'memmap', directly memory-map the image data in the TIFF file
        if possible; else create a memory-mapped array in a temporary file.
        If str or open file, the file name or file object used to
        create a memory-map to an array stored in a binary file on disk.
    squeeze : bool
        If True (default), all length-1 dimensions (except X and Y) are
        squeezed out from the array.
        If False, the shape of the returned array might be different from
        the page.shape.
    lock : {RLock, NullContext}
        A reentrant lock used to synchronize seeks and reads from file.
        If None (default), the lock of the parent's filehandle is used.
    reopen : bool
        If True (default) and the parent file handle is closed, the file
        is temporarily re-opened and closed if no exception occurs.
    maxsize: int
        Maximum size of data before a ValueError is raised.
        Can be used to catch DOS. Default: 16 TB.
    maxworkers : int or None
        Maximum number of threads to concurrently decode compressed
        segments. If None (default), up to half the CPU cores are used.
        See remarks in TiffFile.asarray.
    validate : bool
        If True (default), validate various parameters.
        If None, only validate parameters and return None.

    Returns
    -------
    numpy.ndarray
        Numpy array of decompressed, depredicted, and unpacked image data
        read from Strip/Tile Offsets/ByteCounts, formatted according to
        shape and dtype metadata found in tags and parameters.
        Photometric conversion, pre-multiplied alpha, orientation, and
        colorimetry corrections are not applied. Specifically, CMYK images
        are not converted to RGB, MinIsWhite images are not inverted,
        and color palettes are not applied. An exception are YCbCr JPEG
        compressed images, which will be converted to RGB.

    """
    # properties from TiffPage or TiffFrame
    fh = self.parent.filehandle
    byteorder = self.parent.tiff.byteorder
    offsets, bytecounts = self._offsetscounts
    self_ = self
    self = self.keyframe  # self or keyframe

    if not self._shape or tifffile.product(self._shape) == 0:
        return None

    tags = self.tags

    if validate or validate is None:
        if maxsize is None:
            maxsize = 2**44
        if maxsize and tifffile.product(self._shape) > maxsize:
            raise ValueError('TiffPage %i: data are too large %s'
                             % (self.index, str(self._shape)))
        if self.dtype is None:
            raise ValueError(
                'TiffPage %i: data type not supported: %s%i'
                % (self.index, self.sampleformat, self.bitspersample))
        if self.compression not in tifffile.TIFF.DECOMPESSORS:
            raise ValueError('TiffPage %i: cannot decompress %s'
                             % (self.index, self.compression.name))
        if 'SampleFormat' in tags:
            tag = tags['SampleFormat']
            if (
                tag.count != 1
                and any(i - tag.value[0] for i in tag.value)
            ):
                raise ValueError(
                    'TiffPage %i: sample formats do not match %s'
                    % (self.index, tag.value))
        if self.is_subsampled and (self.compression not in (6, 7)
                                   or self.planarconfig == 2):
            raise NotImplementedError(
                'TiffPage %i: chroma subsampling not supported'
                % self.index)
        if validate is None:
            return None

    lock = fh.lock if lock is None else lock
    with lock:
        closed = fh.closed
        if closed:
            if reopen:
                fh.open()
            else:
                raise IOError('TiffPage %i: file handle is closed'
                              % self.index)

    dtype = self._dtype
    shape = self._shape
    imagewidth = self.imagewidth
    imagelength = self.imagelength
    imagedepth = self.imagedepth
    bitspersample = self.bitspersample
    typecode = byteorder + dtype.char
    lsb2msb = self.fillorder == 2
    istiled = self.is_tiled
    result_offset = None

    if istiled:
        tilewidth = self.tilewidth
        tilelength = self.tilelength
        tiledepth = self.tiledepth
        tw = (imagewidth + tilewidth - 1) // tilewidth
        tl = (imagelength + tilelength - 1) // tilelength
        td = (imagedepth + tiledepth - 1) // tiledepth
        tiledshape = (td, tl, tw)
        tileshape = (tiledepth, tilelength, tilewidth, shape[-1])
        runlen = tilewidth
    else:
        runlen = imagewidth

    if self.planarconfig == 1:
        runlen *= self.samplesperpixel

    if isinstance(out, str) and out == 'memmap' and self.is_memmappable:
        # direct memory map array in file
        with lock:
            result = fh.memmap_array(typecode, shape, offset=offsets[0])
    elif self.is_contiguous:
        # read contiguous bytes to array
        if out is not None:
            out = tifffile.create_output(out, shape, dtype)
        with lock:
            fh.seek(offsets[0])
            result = fh.read_array(typecode, tifffile.product(shape), out=out)
        if lsb2msb:
            tifffile.bitorder_decode(result, out=result)
    else:
        # decompress, unpack,... individual strips or tiles

        if loc is not None and size is not None and istiled:
            result = np.zeros(shape=(shape[0], shape[1], shape[2], size[1], size[0], shape[5]), dtype=dtype)
            result_offset = (0, 0, 0, loc[1], loc[0], 0)
        else:
            result = tifffile.create_output(out, shape, dtype)

        decompress = tifffile.TIFF.DECOMPESSORS[self.compression]

        if self.compression in (6, 7):  # COMPRESSION.JPEG
            colorspace = None
            outcolorspace = None
            jpegtables = None
            if lsb2msb:
                tifffile.log_warning('TiffPage %i: disabling LSB2MSB for JPEG',
                            self.index)
                lsb2msb = False
            if 'JPEGTables' in tags:
                # load JPEGTables from TiffFrame
                jpegtables = self_._gettags({347}, lock=lock)[0][1].value
            # TODO: obtain table from OJPEG tags
            # elif ('JPEGInterchangeFormat' in tags and
            #       'JPEGInterchangeFormatLength' in tags and
            #       tags['JPEGInterchangeFormat'].value != offsets[0]):
            #     fh.seek(tags['JPEGInterchangeFormat'].value)
            #     fh.read(tags['JPEGInterchangeFormatLength'].value)
            if 'ExtraSamples' in tags:
                pass
            elif self.photometric == 6:
                # YCBCR -> RGB
                outcolorspace = 'RGB'
            elif self.photometric == 2:
                if self.planarconfig == 1:
                    colorspace = outcolorspace = 'RGB'
            else:
                outcolorspace = tifffile.TIFF.PHOTOMETRIC(self.photometric).name
            if istiled:
                heightwidth = tilelength, tilewidth
            else:
                heightwidth = imagelength, imagewidth

            def decompress(data, bitspersample=bitspersample,
                           jpegtables=jpegtables, colorspace=colorspace,
                           outcolorspace=outcolorspace, shape=heightwidth,
                           out=None, _decompress=decompress):
                return _decompress(data, bitspersample, jpegtables,
                                   colorspace, outcolorspace, shape, out)

            def unpack(data):
                return data.reshape(-1)

        elif bitspersample in (8, 16, 32, 64, 128):
            if (bitspersample * runlen) % 8:
                raise ValueError(
                    'TiffPage %i: data and sample size mismatch'
                    % self.index)
            if self.predictor == 3:  # PREDICTOR.FLOATINGPOINT
                # the floating-point horizontal differencing decoder
                # needs the raw byte order
                typecode = dtype.char

            def unpack(data, typecode=typecode, out=None):
                try:
                    # read only numpy array
                    return numpy.frombuffer(data, typecode)
                except ValueError:
                    # strips may be missing EOI
                    # log_warning('TiffPage.asarray: ...')
                    bps = bitspersample // 8
                    xlen = (len(data) // bps) * bps
                    return numpy.frombuffer(data[:xlen], typecode)

        elif isinstance(bitspersample, tuple):

            def unpack(data, out=None):
                return tifffile.unpack_rgb(data, typecode, bitspersample)

        else:

            def unpack(data, out=None):
                return tifffile.packints_decode(data, typecode, bitspersample,
                                       runlen)

        # TODO: store decode function for future use
        # TODO: unify tile and strip decoding
        if istiled:
            unpredict = tifffile.TIFF.UNPREDICTORS[self.predictor]

            def decode(tile, tileindex, tileshape=tileshape,
                       tiledshape=tiledshape, lsb2msb=lsb2msb,
                       decompress=decompress, unpack=unpack,
                       unpredict=unpredict, nodata=self.nodata,
                       out=result[0]):
                return tile_decode(tile, tileindex, tileshape, tiledshape,
                                   lsb2msb, decompress, unpack, unpredict,
                                   nodata, out, offset=result_offset[1:] if result_offset is not None else None,
                                   total_shape=shape[1:])

            use = get_used_tiles(len(offsets), tileshape, tiledshape, loc, size)

            bytecounts = [b for i, b in enumerate(bytecounts) if i in use]
            offsets = [b for i, b in enumerate(offsets) if i in use]

            tileiter = fh.read_segments(offsets, bytecounts, lock)

            if self.compression == 1 or len(offsets) < 3:
                maxworkers = 1
            elif maxworkers is None or maxworkers < 1:
                import multiprocessing
                maxworkers = max(multiprocessing.cpu_count() // 2, 1)

            if maxworkers < 2:
                for i, tile in enumerate(tileiter):
                    decode(tile, use[i])
            else:
                # decode first tile un-threaded to catch exceptions
                decode(next(tileiter), use[0])
                with ThreadPoolExecutor(maxworkers) as executor:
                    executor.map(decode, tileiter, use[1:])

        else:
            stripsize = self.rowsperstrip * self.imagewidth
            if self.planarconfig == 1:
                stripsize *= self.samplesperpixel
            outsize = stripsize * self.dtype.itemsize
            result = result.reshape(-1)
            index = 0
            for strip in fh.read_segments(offsets, bytecounts, lock):
                if strip is None:
                    result[index:index + stripsize] = self.nodata
                    index += stripsize
                    continue
                if lsb2msb:
                    strip = tifffile.bitorder_decode(strip, out=strip)
                strip = decompress(strip, out=outsize)
                strip = unpack(strip)
                size = min(result.size, strip.size, stripsize,
                           result.size - index)
                result[index:index + size] = strip[:size]
                del strip
                index += size

    #result.shape = self._shape

    if self.predictor != 1 and not (istiled and not self.is_contiguous):
        unpredict = tifffile.TIFF.UNPREDICTORS[self.predictor]
        result = unpredict(result, axis=-2, out=result)

    if squeeze:
        try:
            if result_offset is not None:
                result = np.asarray(result)[0, 0, 0]
            else:
                result.shape = self.shape
        except ValueError:
            tifffile.log_warning('TiffPage %i: failed to reshape %s to %s',
                        self.index, result.shape, self.shape)

    if closed:
        # TODO: file should remain open if an exception occurred above
        fh.close()
    return result

tifffile.tile_decode = tile_decode
tifffile.TiffPage.asarray = asarray

class myslide():
    last_data = None
    last_level = None

    def __init__(self, filename):
        if not (filename.endswith(".tif") or filename.endswith(".tiff")):
            raise IOError
        try:
            self.tif = tifffile.TiffFile(filename)
        except tifffile.tifffile.TiffFileError:
            raise IOError
        self.level_count = len(self.tif.pages)
        self.level_dimensions = []
        for page in self.tif.pages:
            if len(self.level_dimensions) and not page.is_reduced:
                raise IOError
            self.level_dimensions.append((page.shape[1], page.shape[0]))
        if len(self.level_dimensions) == 1:
            raise IOError
        self.dimensions = self.level_dimensions[0]
        self.level_downsamples = [self.dimensions[0] // dim[0] for dim in self.level_dimensions]

    def read_region(self, location, level, size):
        x, y = location
        w, h = size
        down = self.level_downsamples[level]
        x = x // down
        y = y // down
        crop = self.tif.pages[level].asarray(loc=(x, y), size=(w, h))
        return crop

    def get_best_level_for_downsample(self, downsample):
        if downsample < 1:
            return 0
        for index, down in enumerate(self.level_downsamples):
            if down > downsample:
                return index - 1
        else:
            return len(self.level_downsamples) - 1

    def close(self):
        self.tif.close()

class lowlevel:
    OpenSlideUnsupportedFormatError = IOError

class openslide:
    OpenSlide = myslide
    lowlevel = lowlevel
openslide_loaded = True