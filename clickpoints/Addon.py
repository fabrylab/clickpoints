#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Addon.py

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
import time
import clickpoints
from qtpy import QtCore, QtGui, QtWidgets
from matplotlib import pyplot as plt

from .includes import CanvasWindow
from .includes import QtShortCuts
from .modules.OptionEditor import getOptionInputWidget
from matplotlib import _pylab_helpers
import threading
import asyncio

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

        # if this is the main thread, we have to call processEvents
        if isinstance(threading.current_thread(), threading._MainThread):
            # wait for frame change to be completed
            while self.window.target_frame != int(value):
                self.window.app.processEvents()
            return

        # wait for frame change to be completed
        while self.window.target_frame != int(value):
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

        # if this is the main thread, we have to call processEvents
        if isinstance(threading.current_thread(), threading._MainThread):
            # wait for frame change to be completed
            while self.window.target_frame != int(value):
                self.window.app.processEvents()
            return

        # wait for frame change to be completed
        while self.window.target_frame != int(value):
            time.sleep(0.01)

    def reloadMask(self):
        """
        Reloads the current mask file in ClickPoints.
        """
        # only if we are not a dummy connection
        if self.script_launcher is None:
            return
        self.window.signal_broadcast.emit("ReloadMask", tuple())

    def reloadImage(self, frame_index=None, layer_id=None):
        """
        Reloads the an image file in ClickPoints. Defaults to the current image.

        Parameters
        ----------
        frame_index : int, optional
            the sort_index of the image to reload.
        layer_id : int, optional
            the layer to reload.
        """
        # only if we are not a dummy connection
        if self.script_launcher is None:
            return
        self.window.reloadImage(frame_index, layer_id)

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

    def reloadMaskTypes(self):
        """
        Reloads the mask types.
        """
        # only if we are not a dummy connection
        if self.script_launcher is None:
            return
        self.window.signal_broadcast.emit("maskTypesChangedEvent", tuple())

    def reloadTracks(self):
        """
        Reloads all tracks.
        """
        # only if we are not a dummy connection
        if self.script_launcher is None:
            return
        # get the marker handler
        marker_handler = self.window.GetModule("MarkerHandler")
        # get all track types
        track_types = self.window.data_file.getMarkerTypes(mode=self.window.data_file.TYPE_Track)
        # and reload them
        for type in track_types:
            marker_handler.ReloadTrackType(type)

    def getImage(self):
        """
        Get the current image displayed in ClickPoints.

        Returns
        -------
        image : :py:class:`Image`
            the currently displayed image in ClickPoints

        """
        # only if we are not a dummy connection
        if self.script_launcher is None:
            return
        image = self.window.data_file.image
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
            the start and end marker position, as well, as the skip

        """
        # only if we are not a dummy connection
        if self.script_launcher is None:
            return
        timeline = self.window.GetModule("Timeline")
        return [timeline.frameSlider.startValue(), timeline.frameSlider.endValue(), timeline.skip]

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
        self.window.current_layer = None
        self.window.layer_index = 1
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

    def centerOn(self, x, y):
        """
        Center the image view on the given coordinates.

        Parameters
        ----------
        x : number
            the x coordinate
        y : number
            the y coordinate
        """
        if self.script_launcher is None:
            return

        self.window.CenterOn(x, y)

    def save(self):
        """
        Save currently usaved data in the current frame.
        """
        if self.script_launcher is None:
            return

        self.window.Save()


class Addon(QtWidgets.QWidget):
    _run_thread = None
    _run_task = None
    _change_status = QtCore.Signal(int)
    _option_widgets = None
    _input_widgets = []

    def __init__(self, database, command=None, name="", database_class=None, icon=None):
        # initialize the Widget base class
        QtWidgets.QWidget.__init__(self)

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
        self._option_widgets = {}
        self.db._last_category = self._options_category

        # set the icon for the add-on, if provided
        if icon is not None:
            self.setWindowIcon(icon)

        # wrap the run function, so that it automatically updates the current state of the add-on (for the button state in ClickPoints)
        function = self.run
        if not asyncio.iscoroutinefunction(self.run):
            # overload two matplotlib functions to help use them from the run function from a different thread
            plt.show = show
            plt.figure = figure

            function = self.run
            def run_wrapper(*args, **kwargs):
                self.run_started()
                try:
                    return function(*args, **kwargs)
                finally:
                    self.run_stopped()
            self.run = run_wrapper
        else:
            function = self.run

            async def run_wrapper(*args, **kwargs):
                self.run_started()
                try:
                    return await function(*args, **kwargs)
                finally:
                    self.run_stopped()

            self.run = run_wrapper
            self.run_threaded = self.run_async

        self._input_widgets = []

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
        res = self.db.setOption(key=self._warpOptionKey(key), value=value)
        if key in self._option_widgets:
            self._option_widgets[key].setValue(self.getOption(key))
        return res

    def linkOption(self, key, widget):
        signal = None
        if isinstance(widget, QtWidgets.QSpinBox) or isinstance(widget, QtWidgets.QDoubleSpinBox):
            signal = widget.valueChanged
        elif isinstance(widget, QtWidgets.QLineEdit):
            signal = widget.textChanged
        elif isinstance(widget, QtWidgets.QComboBox):
            signal = widget.editTextChanged
        elif isinstance(widget, QtWidgets.QCheckBox):
            signal = widget.stateChanged
        elif isinstance(widget, QtShortCuts.QInput):
            signal = widget.valueChanged
        signal.connect(lambda value, key=key: self.optionInputChanged(value, key))

    def inputOption(self, key, layout=None, **kwargs):
        if layout is None:
            layout = self.layout()
        option = self.db._options_by_key[self._warpOptionKey(key)]
        widget = getOptionInputWidget(option, layout, **kwargs)
        widget.options_key = key
        self._input_widgets.append(widget)
        def callSetOption(value):
            self.setOption(key, value)
            if getattr(self, "optionsChanged", None) is not None:
                try:
                    self.optionsChanged(key)
                except TypeError:
                    self.optionsChanged()
        widget.valueChanged.connect(callSetOption)
        self._option_widgets[key] = widget
        return widget

    def setHiddenInputs(self, filter, hidden):
        for widget in self._input_widgets:
            if widget.options_key.contains(filter):
                widget.setHidden(hidden)

    def optionInputChanged(self, value, key):
        self.setOption(key, value)

    def buttonPressedEvent(self):
        # callback that gets called when the user clicks the button of the add-on in ClickPoints
        self.run_threaded()

    def terminate(self):
        # when the add-on wants to tell it's run thread to terminate
        self.cp.stop = True
        if self._run_thread is not None:
            self._run_thread.join(1)
        if self._run_task is not None:
            self._run_task.cancel()
        self._run_thread = None
        self._run_task = None

    def is_running(self):
        # check if the run thread is running
        if (self._run_task and not self._run_task.done()) or (self._run_thread and self._run_thread.isAlive()):
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

    def run_threaded(self, start_frame=None, function=None):
        if function is not None:
            def run_wrapper(*args, **kwargs):
                self.run_started()
                try:
                    function(*args, **kwargs)
                finally:
                    self.run_stopped()
            self.run = run_wrapper
        # start the run function in another thread, or stop it, if it is already running
        if self.is_running():
            self.terminate()
        else:
            if start_frame is None or isinstance(start_frame, bool):
                start_frame = self.cp.getCurrentFrame()
            self._run_thread = threading.Thread(target=self.run, args=(start_frame,))
            self._run_thread.daemon = True
            self._run_thread.start()

    def run_async(self, start_frame=None, function=None):
        if function is not None:
            def run_wrapper(*args, **kwargs):
                self.run_started()
                try:
                    function(*args, **kwargs)
                finally:
                    self.run_stopped()
            self.run = run_wrapper
        # start the run function in another thread, or stop it, if it is already running
        if self.is_running():
            self.terminate()
        else:
            if start_frame is None or isinstance(start_frame, bool):
                start_frame = self.cp.getCurrentFrame()
            self._run_task = asyncio.ensure_future(self.run(start_frame), loop=self.cp.window.app.loop)

    def run(self, start_frame=0):
        # here the add-on can implement it's run routine
        pass

    def delete(self):
        # callback that gets called if ClickPoints wants to remove the add-on (also used before reloading the add-on)
        self.close()

    def showEvent(self, event):
        # when the add-on displays it's GUI, we change the status of the add-on
        if not self.is_running():
            self.cp.setStatus(self.cp.STATUS_Active)

    def closeEvent(self, event):
        # when the add-on hides it's GUI, we change the status of the add-on
        if not self.is_running():
            self.cp.setStatus(self.cp.STATUS_Idle)
