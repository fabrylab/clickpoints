#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ClickPointsBooster.py

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

from __future__ import division, print_function

import os
import sys
import time
from qtpy import QtCore, QtWidgets

class Booster(QtWidgets.QWidget):
    new_window = QtCore.Signal(str)

    def __init__(self, command_file, parent=None):
        from ClickPoints import ClickPointsWindow
        from includes import LoadConfig
        global start_new_time
        super(QtWidgets.QWidget, self).__init__(parent)
        self.new_window.connect(self.OpenNewWindow)
        self.windows = []

        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        start_new_time = 0
        class MyHandler(FileSystemEventHandler):
            def __init__(self, file_path, window):
                FileSystemEventHandler.__init__(self)
                self.file_path = os.path.normpath(file_path)
                self.last_position = 0
                self.signal = None
                self.signal = window.new_window
                self.ProcessCommands()

            def on_modified(self, event):
                global start_new_time
                start_new_time = time.time()
                if os.path.normpath(event.src_path) == self.file_path:
                    self.ProcessCommands()

            def ProcessCommands(self):
                if self.last_position > os.path.getsize(self.file_path):
                    self.last_position = 0

                with open(self.file_path) as fp:
                    fp.seek(self.last_position)
                    commands = fp.read()
                    self.last_position = fp.tell()
                    for command in commands.split("\n"):
                        command = command.strip()
                        if command.startswith('"'):
                            command = command[1:-1]
                        if os.path.exists(command):
                            self.signal.emit(command)

        event_handler = MyHandler(command_file, self)
        observer = Observer()
        observer.schedule(event_handler, path=os.path.dirname(command_file),
                          recursive=False)
        observer.start()
        print("Ready")

    def OpenNewWindow(self, command):
        from ClickPoints import ClickPointsWindow
        from includes import LoadConfig
        global app
        config = LoadConfig(command)
        config.srcpath = command
        window = ClickPointsWindow(config, app)
        self.setWindowTitle("blabalba")
        print("ClickPoints started", time.time()-start_new_time, "s")
        if sys.platform[:3] == 'win':
            from win32gui import SetWindowPos
            import win32con

            SetWindowPos(window.winId(),
                         win32con.HWND_TOPMOST,  # = always on top. only reliable way to bring it to the front on windows
                         0, 0, 0, 0,
                         win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
            SetWindowPos(window.winId(),
                         win32con.HWND_NOTOPMOST,  # disable the always on top, but leave window at its top position
                         0, 0, 0, 0,
                         win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
        window.raise_()
        window.show()
        window.activateWindow()
        new_window_list = []
        for win in self.windows:
            if not win.isHidden():
                new_window_list.append(win)
        self.windows = new_window_list
        self.windows.append(window)
        print(self.windows)


def BoosterRunning():
    import psutil
    pid = os.getpid()
    python_filename = os.path.basename(__file__)
    python_filename = python_filename.replace(".pyc", ".py")
    for process in psutil.process_iter():
        try:
            process_name = process.name()
        except psutil.AccessDenied:
            continue
        if process_name.startswith("python"):
            for command in process.cmdline():
                script_name = os.path.split(command)[1]
                if script_name == python_filename and process.pid != pid:
                    sys.exit(-1)
    return 0

def main():
    global app
    BoosterRunning()

    if sys.platform[:3] == 'win':
        command_file = os.path.join(os.getenv('APPDATA'), "..", "Local", "Temp", "ClickPoints.txt")
    else:
        command_file = os.path.expanduser("~/.clickpoints/ClickPoints.txt")

    with open(command_file, "w") as fp:
        fp.write("")

    app = QtWidgets.QApplication(sys.argv)

    # start window
    window = Booster(command_file)

    while True:
        app.exec_()

if __name__ == '__main__':
    main()
