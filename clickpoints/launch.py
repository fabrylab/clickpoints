#!/usr/bin/env python
# -*- coding: utf-8 -*-
# launch.py

# Copyright (c) 2015-2022, Richard Gerum, Sebastian Richter, Alexander Winterl
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
import time

os.environ.setdefault("QT_API", "pyside6")

_startup_profile_enabled = os.environ.get("CLICKPOINTS_PROFILE_STARTUP") not in (None, "", "0", "false", "False")
_startup_profile_exit_after_show = os.environ.get("CLICKPOINTS_PROFILE_EXIT_AFTER_SHOW") not in (None, "", "0", "false", "False")
_startup_profile_start = time.perf_counter()
_startup_profile_last = _startup_profile_start


def _profile_startup(label):
    global _startup_profile_last
    if not _startup_profile_enabled:
        return
    now = time.perf_counter()
    print(
        "[CLICKPOINTS_PROFILE_STARTUP] "
        f"{label}: +{now - _startup_profile_last:.3f}s total={now - _startup_profile_start:.3f}s",
        flush=True,
    )
    _startup_profile_last = now


_profile_startup("launch module imported")


def create_clickpoints_application(QtCore, QtWidgets, args):
    class ClickPointsApplication(QtWidgets.QApplication):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.open_files = []
            self.clickpoints_window = None

        def event(self, event):
            if event.type() == QtCore.QEvent.FileOpen:
                path = event.file()
                if path:
                    window = self.clickpoints_window
                    if window is None:
                        self.open_files.append(path)
                    else:
                        QtCore.QTimer.singleShot(0, lambda path=path: window.loadUrl(path, reset=True))
                    return True
            return super().event(event)

    return ClickPointsApplication(args)


def main(*args):
    import sys
    _profile_startup("main entered")
    if len(args) == 0:
        args = sys.argv
    else:
        args = [sys.executable]+list(args)
    print("args", args)

    if len(args) > 1:
        if args[1] == "register" or args[1] == "install":
            from .includes.RegisterRegistry import install
            return install()
        elif args[1] == "unregister" or args[1] == "uninstall":
            from .includes.RegisterRegistry import install
            return install("uninstall")
        elif args[1] == "-v" or args[1] == "--version":
            import clickpoints
            print(clickpoints.__version__)
            return
        elif args[1] == "ffmpeg":
            import imageio
            import glob
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
            return

    from clickpoints import print_status
    _profile_startup("imported clickpoints.print_status")
    # print
    print_status()
    _profile_startup("printed status")

    """ some magic to prevent PyQt5 from swallowing exceptions """
    # Back up the reference to the exceptionhook
    sys._excepthook = sys.excepthook
    # Set the exception hook to our wrapping function
    sys.excepthook = lambda *args: sys._excepthook(*args)

    from qtpy import QtCore, QtWidgets, QtGui
    _profile_startup("imported Qt")
    import sys
    import ctypes
    from clickpoints.Core import ClickPointsWindow
    _profile_startup("imported ClickPointsWindow")
    from clickpoints.includes import LoadConfig
    _profile_startup("imported LoadConfig")


    from clickpoints import define_paths

    define_paths()
    _profile_startup("defined paths")

    app = create_clickpoints_application(QtCore, QtWidgets, args)
    _profile_startup("created QApplication")

    # set an application id, so that windows properly stacks them in the task bar
    if sys.platform[:3] == 'win':
        myappid = 'fabrybiophysics.clickpoints'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    # load config and exec addon code
    config = LoadConfig(*args)
    _profile_startup("loaded config")

    # Initialize and show the ClickPoints window
    window = ClickPointsWindow(config, app)
    app.clickpoints_window = window
    _profile_startup("constructed ClickPointsWindow")
    if os.environ.get("_PYI_SPLASH_IPC"):
        try:
            import pyi_splash
            pyi_splash.close()
        except ImportError:
            pass
    window.show()
    _profile_startup("showed ClickPointsWindow")
    for path in app.open_files:
        QtCore.QTimer.singleShot(0, lambda path=path: window.loadUrl(path, reset=True))
    app.open_files.clear()
    if _startup_profile_exit_after_show:
        QtCore.QTimer.singleShot(0, app.quit)
    sys.exit(app.exec_())


# Entry point
if __name__ == "__main__":
    main()
