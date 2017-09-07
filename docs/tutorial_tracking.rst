Manual Tracking
===============
This tutorial gives a shot introduction how to get started manually labeling your own tracks,
for a quick evaluation or ground truths for the evaluation of automated algorithms.


Getting started
---------------

1. Open the image sequence or video(s) in ClickPoints
*****************************************************

   For example: right click on the folder containing your images and select ClickPoints on the context menue

2. Save the project
*******************

   Marked results and correlated images must be stored some where, there for the project hast to be named and saved.
   Click on the save button |the save button| and select a storage location and file name.

   .. note::

        Reference to images and video is stored relative as long a the files reside parallel or below in the path tree.
        If the files reside above or on a different branch, drive, or network location, the absolute path is stored.

3. Define Marker types
**********************

    Before we can get started we have to specify a marker type. Marker types are like classes of objects, e.g. we might use
    a class for birds and another one for ships. Every marker type can have multible tracks.

    To open the marker menu either press ``F2`` or click on the Marker button |the marker button| to switch to edit mode (Fig. A).
    Then right click onto the marker list to open the marker menu (Fig. B). You can reuse the default marker or create a new marker
    by selecting ``+ add type``. Choose a name and color for your new marker type and make sure to set the type to ``TYPE_track``.
    Confirm your changes by pressing ``save``.
    To add more tracking types select  ``+ add type`` and repeat the procedure.

    .. figure:: images/tutorial_tracking_marker.png
       :alt: Defining a marker for tracking
       :scale: 60%

       Figure 1 | Defining a marker for tracking


4. Navigating the dataset
*************************
    * Navigating the current frame:

        ``right mouse button (hold)`` - to pan the image

        ``mouse wheel`` - zoom the image

        ``F`` - fit to view

        ``W`` - full screen mode

        ``H`` - hide time line

        See `General <general.html#zooming-panning-rotating>`_

    * Navigating the dataset:

        ``left`` & ``right`` cursor keys to go one frame forward and backward

        * Jump a specified set of frames with the numbad keys. See `Jumping Frames <general.html#jumping-frames>`_

        * Use the frame and time navigation slider to by clicking or dragging the cursor to the desired position.

        * Jump to a specific frame by clicking on the frame counter and entering the desired frame number

        * Press |the play icon| to play the dataset with the specifed frame rate or as fast as feasible.

.. note::
    Due to the sequential compression of videos, traversing a video backwards is computational expensive. ClickPoints provides a
    buffer so that the last N frames are stored and can be retrieved without any further computational cost. The default buffer size
    can be specified in the config.

.. warning::
    Be careful not to reserve too much RAM for the frame buffer as it will drastically reduce performance!


5. Basic Tracking Procedure
***************************
The setup steps are completed, we can begin to mark some tracks.

    #. Activite the type of marker you want to use by clicking on the label "bird" or press the associated number key.

    #. Set the first marker by clicking on the image.

    #. Switch to the next frame using the ``right`` cursor key.

    #. The track now shows up with reduced opacity, indicating there is no marker for the current frame.

    #. Upon dragging the marker (left click & hold) to the current position (release) a line indicates the connection to the last position. The track shows up with full opacity again.

    #. If a frame is skipped, the marker can be dragged as usual but no connecting line will appear. Indicating a fragmentation of the track.

    #. To create a second track, repeat step 1.

    #. Markers are automatically save upon frame change or by pressing the ``S`` key.

    .. figure:: images/tutorial_tracking_tracks.jpg
       :alt: Track states
       :scale: 60%

       Figure 2 | Track States

       A - Track without update in current frame B - Track with update in current frame C - Track with missing marker

6. "Connect-nearest" Tracking Mode
**********************************
For low density tracks ClickPoints provides the "connect nearest" mode. Clicking on the image will automatically connect
the new marker to the closest Track in the last frame. Speeding up tracking for low track density scenes. The dragging of
markers is still support and is usefull for intersecting tracks.

To activate "connect nearest" mode, set the config parameter ``tracking_connect_nearest = True``.

See `ConfigFiles <recipes_configfiles.html#using-configfiles>`_ for more details.



7. Important Controls
*********************
A list of useful controls for labeling tracks. Connect-nearest mode extends the list of default controls

* default
    ``left click`` - create new track (default mode)
    ``ctrl`` + ``left click`` - remove marker
    ``right click`` - open marker menu, see XXXXX

* connect-nearest mode
    ``left click`` - place marker, autoconnect to nearest track
    ``alt`` + ``left click`` - create new track
    ``shift`` + ``left click` - place marker & load next frame


8. Advances Options
*******************

* Use SmartText to display additional information

  See `SmartText <XXX>`_

  Example:
    **Display Track IDs**

    * open the marker menu

    * navigate to "bird" marker type

    * edit the text field by inserting

        .. code-block:: python

            $track_id

    All current markers of the type ``bird`` now display their internal track ID

    .. figure:: images/tutorial_tracking_smarttext.png
       :alt: Tracks with SmartText ID
       :scale: 60%

       Figure 3 | Tracks with SmartText ID

* Use Styles to modify the display of markers and tracks

  See `Marker Styles <marker.html#marker-style-definitions>`_

  Example:
    **Change track point display**

    * open the marker menu

    * navigate to "bird" marker type

    * edit the style field by inserting

        .. code-block:: python

            {"track-line-style": "dash", "track-point-shape": "none"}

    All tracks of the type ``bird`` now are displayed with dashed lines and without track points

    .. figure:: images/tutorial_tracking_styles.png
       :alt: Tracks with modified style
       :scale: 60%

       Figure 3 | Tracks with modified style


.. |the save button| image:: images/IconSave.png
.. |the marker button| image:: images/IconMarker.png
.. |the play icon| image:: images/IconPlay.png