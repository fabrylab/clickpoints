Timeline
========

.. figure:: images/ModulesTimeline.png
   :alt: Timeline Example

   Timeline example showing some tick marks from marker an annotations.

The timeline is an interface at the bottom of the screen which displays range of currently loaded frames and allows for
navigation through these frames. It can be displayed by clicking on |the play icon|.

To start/stop playback use the playback button at the left of the timeline or press ``Space``. The label next to
it displays which frame is currently displayed and how many frames the frame list has in total.
The time bar has one slider to denote the currently selected frame and two triangular marker to select start and
end frame of the playback. The keys ``b`` and ``n`` set the start/end marker to the current frame.
The two tick boxes at the right contain the current frame rate and the number of frames to skip during playback
between each frame.

Each frame which has selected marker or masks is marked with a green tick mark (see `Marker <marker.html>`_ and
`Mask <mask.html>`_) and each frame marked with an annotation (see `Annotations <annotations.html>`_) is marked with a
red tick. To jump to the next annotated frame press ``Ctrl``\ +\ ``Left`` or ``Ctrl``\ +\ ``Right``.

Config Parameter
----------------

-  ``fps =`` if not 0 overwrite the frame rate of the video
-  ``play_start =`` at which frame to start playback (if > 1) or at what
   fraction of the video to start playback (if > 0 and < 1)
-  ``play_end =`` at which frame to end playback (if > 1) or at what
   fraction of the video to end playback (if > 0 and < 1)
-  ``playing =`` whether to start playback at the program start
-  ``timeline_hide =`` whether to hide the timeline at the program start

Keys
----

-  H: hide control elements
-  Space: run/pause
-  Crtl+Left: previous annotated image
-  Ctrl+Right: next annotated image

.. |the play icon| image:: images/IconPlay.png

