import tifffile


class myslide():
    last_data = None
    last_level = None

    def __init__(self, filename):
        self.tif = tifffile.TiffFile(filename)
        self.level_count = len(self.tif.pages)
        self.level_dimensions = []
        for page in self.tif.pages:
            if len(self.level_dimensions) and not page.is_reduced:
                raise IOError
            self.level_dimensions.append((page.shape[1], page.shape[0]))
        self.dimensions = self.level_dimensions[0]
        self.level_downsamples = [self.dimensions[0] // dim[0] for dim in self.level_dimensions]

    def read_region(self, location, level, size):
        x, y = location
        w, h = size
        down = self.level_downsamples[level]
        x = x // down
        y = y // down
        if self.last_level != level:
            self.last_data = self.tif.pages[level].asarray()
            self.last_level = level
        return self.last_data[y:y + h, x:x + w]

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