#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SendCommands.py

# Copyright (c) 2015-2016, Richard Gerum, Sebastian Richter
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ClickPoints. If not, see <http://www.gnu.org/licenses/>

from __future__ import division, print_function
import time
import clickpoints
from qtpy import QtCore, QtGui, QtWidgets
from matplotlib import pyplot as plt

from .includes import CanvasWindow
from matplotlib import _pylab_helpers
import threading

figures = {}


def show():
    global figures
    canvas = _pylab_helpers.Gcf.get_active().canvas
    canvas.draw()
    if canvas.window:
        canvas.window.scheduleShow()


def figure(num=None, size=None, *args, **kwargs):
    global figures
    if num is None:
        num = len(figures)
    if num not in figures.keys():
        canvas = CanvasWindow(num, *args, **kwargs).canvas
        figures[num] = canvas
    canvas = figures[num]
    if size is not None:
        figures[num].window.setGeometry(100, 100, size[0] * 80, size[1] * 80)
    _pylab_helpers.Gcf.set_active(canvas.manager)
    return canvas.figure


class Command:
    script_launcher = None
    stop = False

    def __init__(self, script_launcher=None, script=None):
        self.script_launcher = script_launcher
        self.script = script
        if self.script_launcher is not None:
            self.window = self.script_launcher.window

    def jumpFrames(self, value):
        """
        Let ClickPoints jump the given amount of frames.

        Parameters
        ----------
        value : int
            the amount of frame which ClickPoints should jump.
        """
        # only if we are not a dummy connection
        if self.script_launcher is None:
            return
        self.window.signal_jump.emit(int(value))

    def jumpToFrame(self, value):
        """
        Let ClickPoints jump to the given frame.

        Parameters
        ----------
        value : int
            the frame to which ClickPoints should jump.
        """
        # only if we are not a dummy connection
        if self.script_launcher is None:
            return
        self.window.signal_jumpTo.emit(int(value))

    def jumpFramesWait(self, value):
        """
        Let ClickPoints jump the given amount of frames and wait for it to complete.

        Parameters
        ----------
        value : int
            the amount of frames which ClickPoints should jump.
        """
        # only if we are not a dummy connection
        if self.script_launcher is None:
            return
        self.window.signal_jump.emit(int(value))
        # wait for frame change to be completed
        while self.window.new_frame_number != int(value) or self.window.loading_image:
            time.sleep(0.01)

    def jumpToFrameWait(self, value):
        """
        Let ClickPoints jump to the given frame and wait for it to complete.

        Parameters
        ----------
        value : int
            the frame to which ClickPoints should jump.
        """
        # only if we are not a dummy connection
        if self.script_launcher is None:
            return
        self.window.signal_jumpTo.emit(int(value))
        # wait for frame change to be completed
        while self.window.new_frame_number != int(value) or self.window.loading_image:
            time.sleep(0.01)

    def reloadMask(self):
        """
        Reloads the current mask file in ClickPoints.
        """
        # only if we are not a dummy connection
        if self.script_launcher is None:
            return
        self.window.signal_broadcast.emit("ReloadMask", tuple())

    def reloadMarker(self, frame=None):
        """
        Reloads the marker from the given frame in ClickPoints.

        Parameters
        ----------
        frame : int
            the frame which ClickPoints should reload. Use `None` for the current frame.
        """
        # only if we are not a dummy connection
        if self.script_launcher is None:
            return
        # if no frame is given use the current frame
        if frame is None:
            frame = self.window.data_file.get_current_image()
        self.window.signal_broadcast.emit("ReloadMarker", (frame,))

    def reloadTypes(self):
        """
        Reloads the marker types.
        """
        # only if we are not a dummy connection
        if self.script_launcher is None:
            return
        self.window.signal_broadcast.emit("UpdateCounter", tuple())

    def getImage(self, value):
        # only if we are not a dummy connection
        if self.script_launcher is None:
            return
        image = self.window.data_file.get_image_data(int(value))
        return image

    def getCurrentFrame(self):
        """
        Get the current ClickPoints frame.
        
        Returns
        -------
        frame : int
            the currently selected frame in ClickPoints

        """
        # only if we are not a dummy connection
        if self.script_launcher is None:
            return
        return self.window.data_file.current_image_index

    def getFrameRange(self):
        """
        Get the current ClickPoints frame range from the start marker to the end marker.

        Returns
        -------
        range : list
            the start and end marker position.

        """
        # only if we are not a dummy connection
        if self.script_launcher is None:
            return
        timeline = self.window.GetModule("Timeline")
        return [timeline.frameSlider.startValue(), timeline.frameSlider.endValue()]

    def selectMarkerType(self, type):
        """
        Select a given marker type in ClickPoints.
        
        Parameters
        ----------
        type : :py:class:`MarkerType`
            the marker type which should be selected.
        """
        # only if we are not a dummy connection
        if self.script_launcher is None:
            return
        self.window.GetModule("MarkerHandler").SetActiveMarkerType(new_type=type)
        self.window.GetModule("MarkerHandler").ToggleInterfaceEvent(hidden=False)

    def updateImageCount(self):
        """
        Notify ClickPoints that the count of images has changed. Has to be called when layers of images have changed or images have been added or removed.

        """
        # only if we are not a dummy connection
        if self.script_launcher is None:
            return
        self.window.data_file.image_count = None
        self.window.GetModule("Timeline").ImagesAddedMain()

    def hasTerminateSignal(self):
        """
        Weather the run function is scheduled to stop
        """
        return self.stop

    def getHUD(self, location="upper left"):
        if location == "upper left":
            return self.window.view.hud
        elif location == "upper center":
            return self.window.view.hud_upperCenter
        elif location == "upper right":
            return self.window.view.hud_upperRight
        elif location == "left center":
            return self.window.view.hud_leftCenter
        elif location == "center":
            return self.window.view.hud_center
        elif location == "right center":
            return self.window.view.hud_rightCenter
        elif location == "lower left":
            return self.window.view.hud_lowerLeft
        elif location == "lower center":
            return self.window.view.hud_lowerCenter
        elif location == "lower right":
            return self.window.view.hud_lowerRight
        raise NameError("%s no valid location name" % location)

    STATUS_Idle = 0
    STATUS_Active = 1
    STATUS_Running = 2

    def setStatus(self, status=0):
        """
        Set the button state for the add-on.
        
        Parameters
        ----------
        status : int
            the button can have three states, STATUS_Idle for an non active button, STATUS_Active for an active button and
            STATUS_Running for an active button with an hourglass symbol.
        """
        if self.script_launcher is None:
            return

        self.script_launcher.setStatus(self.script.addon_name, status)


class Addon(QtWidgets.QWidget):
    _run_thread = None
    _change_status = QtCore.Signal(int)

    def __init__(self, database, command=None, name="", database_class=None, icon=None):
        # initialize the Widget base class
        QtWidgets.QWidget.__init__(self)

        # overload two matplotlib functions to help use them from the run function from a different thread
        plt.show = show
        plt.figure = figure

        # initialize the command class to communicate with ClickPoints
        self.cp = Command(command, self)

        # get the database instance, either it is already a database object or a filename
        if isinstance(database, str):
            # if we have a filename, open the file with the provided database class type or the default type
            if database_class:
                self.db = database_class(database)
            else:
                self.db = clickpoints.DataFile(database)
        else:
            # store the database object
            self.db = database
            # if the object should have a different class, convert it
            if database_class is not None:
                # store some pointers to the options
                _options = self.db._options
                _options_by_key = self.db._options_by_key
                # initiate a new database class instance with the new class type
                self.db = database_class(self.db.db.database)
                # and put the options pointers back in place
                self.db._options = _options
                self.db._options_by_key = _options_by_key

        # remember the add-on name
        self.addon_name = name
        # create an option category for the add-on
        self._options_category = "Addon - "+name
        self.db._last_category = self._options_category

        # set the icon for the add-on, if provided
        if icon is not None:
            self.setWindowIcon(icon)

        # wrap the run function, so that it automatically updates the current state of the add-on (for the button state in ClickPoints)
        function = self.run
        def run_wrapper(*args, **kwargs):
            self.run_started()
            try:
                function(*args, **kwargs)
            finally:
                self.run_stopped()
        self.run = run_wrapper

        # connect the status changed signal (to be able to change the status from another thread)
        self._change_status.connect(self.cp.setStatus)

    def _warpOptionKey(self, key):
        # wrap an option keyword with the add-on's name
        return "addon_" + self.addon_name.replace(" ", "") + "_" + key

    def addOption(self, key="", **kwargs):
        # add an option for the add-on
        self.db._AddOption(key=self._warpOptionKey(key), **kwargs)

    def getOption(self, key):
        # get the option value for the add-on
        return self.db.getOption(key=self._warpOptionKey(key))

    def getOptions(self):
        # get a list of all options as options objects
        return self.db._options_by_key[self._options_category]

    def setOption(self, key, value):
        # set the value of an option
        return self.db.setOption(key=self._warpOptionKey(key), value=value)

    def buttonPressedEvent(self):
        # callback that gets called when the user clicks the button of the add-on in ClickPoints
        self.run_threaded()

    def terminate(self):
        # when the add-on wants to tell it's run thread to terminate
        self.cp.stop = True
        self._run_thread.join(1)
        self._run_thread = None

    def is_running(self):
        # check if the run thread is running
        if self._run_thread and self._run_thread.isAlive():
            return True
        return False

    def run_started(self):
        # called before run, by the run_wrapper to update the state of the add-on
        self.cp.stop = False
        self._change_status.emit(self.cp.STATUS_Running)

    def run_stopped(self):
        # called after run, by the run_wrapper to update the state of the add-on
        if self.isVisible():
            self._change_status.emit(self.cp.STATUS_Active)
        else:
            self._change_status.emit(self.cp.STATUS_Idle)

    def run_threaded(self, start_frame=None):
        # start the run function in another thread, or stop it, if it is already running
        if self.is_running():
            self.terminate()
        else:
            if start_frame is None or isinstance(start_frame, bool):
                start_frame = self.cp.getCurrentFrame()
            self._run_thread = threading.Thread(target=self.run, args=(start_frame,))
            self._run_thread.daemon = True
            self._run_thread.start()

    def run(self, start_frame=0):
        # here the add-on can implement it's run routine
        pass

    def delete(self):
        # callback that gets called if ClickPoints wants to remove the add-on (also used before reloading the add-on)
        pass

    def showEvent(self, event):
        # when the add-on displays it's GUI, we change the status of the add-on
        if not self.is_running():
            self.cp.setStatus(self.cp.STATUS_Active)

    def closeEvent(self, event):
        # when the add-on hides it's GUI, we change the status of the add-on
        if not self.is_running():
            self.cp.setStatus(self.cp.STATUS_Idle)
