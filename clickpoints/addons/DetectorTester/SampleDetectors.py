from PenguTrack.Detectors import Detector, detection_parameters
from PenguTrack.Parameters import ParameterList, Parameter
from skimage.measure import label, regionprops
import numpy as np
import pandas as pd


class DetectorThreshold(Detector):
    """
    This Class describes the abstract function of a detector in the pengu-track package.
    It is only meant for subclassing.
    """

    def __init__(self, threshold=128):
        super(Detector, self).__init__()

        # define the parameters of the detector
        self.ParameterList = ParameterList(Parameter("threshold", threshold, range=[0, 255], desc="the threshold"),
                                           Parameter("invert", False),
                                           Parameter("mode", "test", values=["bla", "blub", "test", "heho"]))

    @detection_parameters(image=dict(frame=0))
    def detect(self, image):
        # threshold the image
        mask = (image > self.ParameterList["threshold"]).astype("uint8")
        # invert it
        if self.ParameterList["invert"]:
            mask = 1 - mask
        # find all regions
        props = regionprops(label(mask))
        # get the positions of the regions
        positions = pd.DataFrame([(prop.centroid[1] + 0.5, prop.centroid[0] + 0.5) for prop in props], columns=["PositionX", "PositionY"])
        # return positions and mask
        return positions, mask


class DetectorRandom(Detector):
    """
    This Class describes the abstract function of a detector in the pengu-track package.
    It is only meant for subclassing.
    """

    def __init__(self):
        super(Detector, self).__init__()

        self.ParameterList = ParameterList(Parameter("count", 128, min=0, max=255))

    @detection_parameters(image=dict(frame=0))
    def detect(self, image):
        df = pd.DataFrame(np.random.rand(self.ParameterList["count"], 2) * np.array(image.shape)[::-1], columns=["PositionX", "PositionY"])
        return df, None
