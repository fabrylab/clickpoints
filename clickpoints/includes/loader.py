#!/usr/bin/env python
# -*- coding: utf-8 -*-
# loader.py

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

import glob
import os
import sys

from typing import Iterable
from pathlib import Path
import asyncio

import imageio
import natsort
import peewee

from clickpoints import DataFile
from clickpoints.includes import BroadCastEvent
from clickpoints.includes import Database

formats = None
def loadFileFormats(verbose=False):
    global natsorted, openslide_loaded, imgformats, vidformats, specialformats, formats
    def do_print(*args, **kwargs):
        if verbose is True:
            print(*args, **kwargs)

    do_print("Using ImageIO", imageio.__version__)
    try:
        from natsort import natsorted
    except (ImportError, ModuleNotFoundError):
        natsorted = sorted

    try:
        import openslide
        openslide_loaded = True
        print("openslide", openslide.__version__)
    except (ImportError, ModuleNotFoundError):
        from .slide import myslide
        openslide_loaded = False
        print("use custom openslide variant with tifffile")

    # add plugins to imageIO if available
    plugin_searchpath = os.path.join(os.path.split(__file__)[0], '..', r'addons/imageio_plugin')
    sys.path.append(plugin_searchpath)
    if os.path.exists(plugin_searchpath):
        print("Searching ImageIO Plugins ...")
        plugin_list = os.listdir(os.path.abspath(plugin_searchpath))
        for plugin in plugin_list:
            if plugin.startswith('imageio_plugin_') and plugin.endswith('.py'):
                # importlib.import_module(os.path.splitext(plugin)[0])
                print(os.path.sep.join([os.path.abspath(plugin_searchpath), plugin]))
                import importlib.util

                spec = importlib.util.spec_from_file_location(plugin.replace(".py", ""),
                                                              os.path.sep.join([os.path.abspath(plugin_searchpath), plugin])
                                                              )
                imageio_plugin = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(imageio_plugin)
                # importlib.import_module(os.path.sep.join([os.path.abspath(plugin_searchpath), plugin]))
                # print(os.path.abspath(plugin_searchpath))
                print('Adding %s' % plugin)

    # check for ffmpeg
    try:
        # check if imageio already has an exe file
        imageio.plugins.ffmpeg.get_exe()
        print("ffmpeg found from imageio")
    except imageio.core.fetching.NeedDownloadError:
        # try to find an ffmpeg.exe in the ClickPoints folder
        files = glob.glob(os.path.join(os.path.dirname(__file__), "..", "ffmpeg*.exe"))
        files.extend(glob.glob(os.path.join(os.path.dirname(__file__), "..", "external", "ffmpeg*.exe")))
        # if an ffmpeg exe has been found, set the environmental variable accordingly
        if len(files):
            print("ffmpeg found", files[0])
            os.environ['IMAGEIO_FFMPEG_EXE'] = files[0]
        # if not, try to download it
        else:
            print("try to download ffmpeg")
            imageio.plugins.ffmpeg.download()


    imgformats = []
    for format in imageio.formats:
        if 'i' in format.modes:
            imgformats.extend(format._extensions)
    imgformats = [fmt if fmt[0] == "." else "." + fmt for fmt in imgformats]
    vidformats = []
    for format in imageio.formats:
        if 'I' in format.modes:
            vidformats.extend(format._extensions)
    vidformats = [fmt if fmt[0] == "." else "." + fmt for fmt in vidformats]

    formats = tuple(imgformats + vidformats)
    imgformats = tuple(imgformats)
    specialformats = ['.gif'] + [".vms"] + [".tif", ".tiff"]  # potential animated gif = video or gif = image



def reset_database(filename: str = "", window=None) -> None:
    if window is not None and window.data_file is not None:
        # ask to save current data
        window.testForUnsaved()
        # close database
        window.data_file.closeEvent(None)
        BroadCastEvent(window.modules, "closeDataFile")

    config = None
    # open new database
    data_file = Database.DataFileExtended(filename, config, storage_path=os.environ["CLICKPOINTS_TMP"])
    # self.data_file.signals.loaded.connect(self.FrameLoaded)
    if window is not None:
        window.data_file = data_file
        # apply image rotation from config
        if data_file.getOption("rotation") != 0:
            window.view.rotate(data_file.getOption("rotation"))
        BroadCastEvent(window.modules, "updateDataFile", data_file, filename == "")
        window.GetModule("Timeline").ImagesAdded()
    return data_file


def loadUrl(url: str, data_file: DataFile = None, reset: bool = False, use_natsort: bool = True, window = None, loop = None, callback_finished: callable = None) -> None:
    global formats
    if formats is None:
        loadFileFormats()
    print("Loading url", url)

    def call(function):
        if loop is None:
            asyncio.run(function)
        else:
            asyncio.ensure_future(function, loop=loop)

    if url == "":
        if data_file is None:
            data_file = reset_database(window=window)
        if callback_finished is not None:
            callback_finished(data_file)
        return data_file

    url = Path(url)

    # open an existing database
    if url.suffix == ".cdb":
        data_file = reset_database(url, window=window)
        if callback_finished is not None:
            callback_finished(data_file)
        return data_file

    # if the datafile is not defined, reset the database
    if data_file is None or reset:
        data_file = reset_database(window=window)

    # if the url is a glob string
    if '*' in str(url):
        print("Glob string detected - building list")
        # obj can be directory or files
        obj_list = glob.glob(str(url))
        if use_natsort is True:
            obj_list = natsort.natsorted(obj_list)
        call(addPath(data_file, InputIteratorList(obj_list), callback_finished=callback_finished))

        if loop is None and callback_finished is not None:
            callback_finished(data_file)
        return data_file
    # if it is a directory add it
    elif url.is_dir():
        call(addPath(data_file, InputIteratorFolder(url), callback_finished=callback_finished))
    # if not check what type of file it is
    # for images load the folder
    elif url.suffix.lower() in imgformats and \
            (url.suffix.lower() not in specialformats or getFrameNumber(url, url.suffix) == 1):
        call(addPath(data_file, InputIteratorGlob(url.parent, "*" + url.suffix.lower()), window=window, select_file=url,
                     callback_finished=callback_finished))
        if window is not None:
            window.first_frame = None
    # for videos just load the file
    elif (url.suffix.lower() in vidformats) or (url.suffix.lower() == ".vms") or (
            url.suffix.lower() in specialformats and getFrameNumber(url, url.suffix) != 1):
        call(addPath(data_file, InputIteratorList([url]), callback_finished=callback_finished))
    elif url.suffix.lower() == ".txt":
        call(addPath(data_file, InputIteratorFile(url), callback_finished=callback_finished))

    # if the extension is not known, raise an exception
    else:
        raise Exception("unknown file extension " + url.suffix, url)

    if loop is None and callback_finished is not None:
            callback_finished(data_file)
    return data_file

class InputIterator:
    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

class InputIteratorList(InputIterator):
    def __init__(self, list):
        # store the filename
        self.list = list

    def __iter__(self):
        for path in self.list:
            yield Path(path)

class InputIteratorGlob(InputIterator):
    def __init__(self, url, query):
        # store the filename
        self.url = Path(url)
        self.query = query

    def __iter__(self):
        for path in self.url.glob(self.query):
            yield path

class InputIteratorFolder(InputIterator):
    def __init__(self, url):
        # store the filename
        self.url = Path(url)

    def __iter__(self):
        for path in self.url.iterdir():
            if path.is_file() and path.suffix in formats:
                yield path

class InputIteratorFile(InputIterator):
    def __init__(self, url):
        # store the filename
        self.url = Path(url)

    def __enter__(self):
        # open the file
        self.fp = self.url.open("r").__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        # close the file
        self.fp.__exit__(exc_type, exc_val, exc_tb)

    def __iter__(self):
        # iterate over all lines
        for line in self.fp:
            path = Path(line.strip().split()[0])
            if path != "":
                yield path

async def addPath(data_file: DataFile,
            iterator: Iterable,
            layer_entry: "Layer" = None,
            select_file: str = None,
            window: "ClickPointsWindow" = None,
            callback_finished=None):
    paths = {}
    data = []

    if layer_entry is None:
        # get a layer for the paths
        layer_entry = data_file.getLayer("default", create=True)

    with iterator:
        for filename in iterator:
            # ensure that the path is already in the database
            file_path = filename.parent
            if file_path not in paths.keys():
                paths[file_path] = data_file.table_path(path=file_path)
                try:
                    paths[file_path].save()
                except peewee.IntegrityError:
                    # if the path is already in the database, query it
                    paths[file_path] = data_file.getPath(path_string=file_path)

            # extract the extension and frame number
            extension = filename.suffix
            frames = getFrameNumber(filename, extension)

            # if the file is not properly readable, skip it
            if frames == 0:
                continue
            # add the file to the database
            try:
                data.extend(
                    data_file.add_image(filename.name, extension, None, frames, path=paths[file_path], layer=layer_entry,
                                        full_path=filename, commit=False))
            except OSError as err:
                print("ERROR:", err)

            if len(data) > 100 or filename == select_file:
                # split the data array in slices of 100
                for i in range(int(len(data) / 100) + 1):
                    try:
                        data_file.add_bulk(data[i * 100:i * 100 + 100])
                    except peewee.IntegrityError:
                        pass
                data = []
                # if the file is the file which should be selected jump to that frame
                if filename == select_file:
                    file = data_file.table_image.get(filename=select_file.name)
                    window.first_frame = file.sort_index
                    select_file = None

                await asyncio.sleep(0)

        data_file.add_bulk(data)
    if callback_finished is not None:
        callback_finished(data_file)


def getFrameNumber(file: str, extension: str) -> int:
    # for image we are already done, they only contain one frame
    if extension.lower() in imgformats and extension.lower() not in specialformats:
        frames = 1
    else:
        # for other formats let imagio choose a reader
        if openslide_loaded is True:
            try:
                reader = openslide.OpenSlide(file)
                reader.close()
                return 1
            except IOError:
                pass
        try:
            reader = imageio.get_reader(file)
        except (IOError, ValueError):
            print("ERROR: can't read file", file)
            return 0
        frames = reader.get_length()
        # for imagio ffmpeg > 2.5.0, check if frames might be inf
        if not isinstance(frames, int):
            frames = reader.count_frames()
        reader.close()
    # return the number of frames
    return frames