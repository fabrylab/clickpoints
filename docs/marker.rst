Marker
======

Objects in the image can be marked using marker of this module. Marker
can have different types to mark different objects. They can also be
used in tracking mode to recognize an object over different frames.

Basics
------

.. figure:: images/ModulesMarker.png
   :alt: Marker Example

   Marker Example

The marker editor can be opened by clicking on |the marker icon|.

The list of available markers is displayed at the top left corner. A
marker type can be selected either by clicking on its name or by
pressing the corresponding number key. A left click in the image places
a new marker of the currently selected type. Existing markers can be
dragged with the left mouse button and deleted by clicking on them while
holding control.

To save the markers press ``S`` or change to the next image, which
automatically saves the current markers.

Define marker types
~~~~~~~~~~~~~~~~~~~

A right click on any marker or type opens the Marker Editor window.
There types can be created, modified or deleted.

Marker types have a name, which is displayed in the HUD, a color and a
mode.

.. figure:: images/ModulesMarkerTypes.png
   :alt: Marker Type Modes

   Marker Type Modes

TYPE\_Normal results in single markers. TYPE\_Rect joins every two
consecutive markers as a rectangle. TYPE\_Line joins every two
consecutive markers as a line. TYPE\_Track specifies that this markers
should use tracking mode (see section Tracking Mode).

Marker display
--------------

Pressing ``T`` toggles between three different marker displays. If the
smallest size is selected, the markers can’t be moved. This makes it
easier to work with a lot of markers on a small area.

.. figure:: images/ModulesMarkerSizes.png
   :alt: Marker Sizes

   Marker Sizes

Tracking mode
-------------

Often objects which occur in one image also occur in another image
(e.g. the images are part of a video). Then it is necessary to make a
connection between the object in the first image and the object in the
second image. Therefore ClickPoints features a tracking mode, where
markers can be associated between images. It can be enabled using the
TYPE\_Track for a marker type. The following images displays the
difference between normal mode (left) and tracking mode (right):

.. figure:: images/ModulesMarkerTracking.png
   :alt: Marker Sizes

   Marker Sizes

To start a track, mark the object in the first image. Then switch to the
next image and the marker from the first image will still be displayed
but only half transparent. To add a second point to the track grab the
marker and move it to the new position of the object. Continue this
process thought the images where you want to track the object. If the
object didn’t move from the last frame or isn’t visible, an image can be
left out, which results in a gap in the track. To remove a point from
the track, click it while holding control in the image you want to
delete the point

.. |the marker icon| image:: images/IconMarker.png

