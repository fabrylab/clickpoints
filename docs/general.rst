General
=======

This is the main functionality of the program

Basics
------

ClickPoints can be started by either starting the ``ClickPoints.bat``,
or respectively ``ClickPoints`` in Linux. This will open ClickPoints
with an empty project. The project can be saved by clicking on |the save
button|. Images can be added to the project by using |the folder
button|.

If the ``ClickPoints.bat`` file isn't present in the ClickPoints
directory the ``install_bat.py`` script needs to be executed first.

ClickPoints can also be used to directly open images, videos or folder
by right clicking on them, which will open an unsaved project which
already contains some images. This feature also allows to use
ClickPoints as an image viewing tool.

ClickPoints can be opened with

-  an **image**, then ClickPoints loads all images in the folder of this
   image.
-  a **video** file, then ClickPoints loads only this video.
-  a **folder**, then ClickPoints loads all image and video files of the
   folder and its sub folders, which are concatenated to one single
   image stream.

``Esc`` closes ClickPoints. If no project has been specified, all
changes are lost, if a project was specified, the changes are saved.

Zooming, Panning, Rotating
--------------------------

ClickPoints openes with a display of the current image fit to the
window. The display can be zoomed using the mouse wheel and panned
holding down the right mouse button. To fit the image to the view again
press ``F``. The display can be set to fullscreen pressing ``W``. The
image can be rotated using ``R``. How much the image is rotated at the
beginning or how much to rotate with each press of ``R`` can be defined
in the ConfigClickPoints.txt with the entries ``rotation =`` and
``rotation_steps =``.

Jumping frames
--------------

Changing frames is a key element of ClickPoints and therefore vagarious
possibilities exists to change the current frame. The keys ``Left`` and
``Right`` go to the previous or next frame. The keys ``Home`` and
``End`` jump to the first or last frame. Key pairs on the numpad allow
for jumps of ``2`` ``3`` -/+ 1, ``5`` ``6`` -/+ 10, ``8`` ``9`` -/+ 100
and ``/`` ``*`` -/+ 1000. If other jumps are required, the entry
``jumps =`` in the ConfigClickPoints.txt can redefine these jumps, by
giving a list of a new definition of these 8 jumps. For continuous
playback of frames see `timeline <timeline.html>`_.

Interfaces
----------

The interfaces for Marker, Mask and GammaCorretion can be shown/hidden
pressing ``F2``. Marker and Masks are saved by pressing ``S`` or
changing the current frame. Marker and Mask of


.. |the save button| image:: images/IconSave.png
.. |the folder button| image:: images/IconFolder.png

