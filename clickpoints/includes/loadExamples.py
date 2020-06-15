from pathlib import Path
from urllib.request import urlretrieve


def downloadFiles(path, files):
    for file in files:
        url = f"https://raw.githubusercontent.com/fabrylab/clickpointsexamples/master/{path}/{file}"
        target = Path(file)
        if not target.exists():
            print("Downloading File", file)
            urlretrieve(str(url), str(file))


def loadExample(name):
    if name == "king_penguins":
        downloadFiles("PenguinCount", ["count.cdb", "20150312-110000_microbs_GoPro.jpg", "20150408-150001_microbs_GoPro.jpg", "20150514-110000_microbs_GoPro.jpg"])
    if name == "magnetic_tweezer":
        downloadFiles("TweezerVideos/001", ["track.cdb"] + [f"frame{i:04d}.jpg" for i in range(68)])
    if name == "plant_root":
        downloadFiles("PlantRoot", ["plant_root.cdb", "1-0min.tif", "1-2min.tif", "1-4min.tif", "1-6min.tif", "1-8min.tif", "1-10min.tif"])
