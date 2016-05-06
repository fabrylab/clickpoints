General
=======

Once ClickPoints has been `installed <installation.html>`_ it can be started directly from the Start Menu/Program launcher
or by using the ``ClickPoints.bat``, or respectively ``ClickPoints`` in Linux.

This will open ClickPoints with an empty project. The project can be saved by clicking on |the save button|. Images can be
added to the project by using |the folder button|.

.. attention::
    If the ``ClickPoints.bat`` file isn't present in the ClickPoints directory the ``install_bat.py`` script needs to be
    executed first.

ClickPoints can also be used to directly open images, videos or folder by right clicking on them, which will open an
unsaved project which already contains some images. This feature also allows to use ClickPoints as an image viewing tool.

ClickPoints can be opened with

-  an **image**, then ClickPoints loads all images in the folder of this
   image.
-  a **video** file, then ClickPoints loads only this video.
-  a **folder**, then ClickPoints loads all image and video files of the
   folder and its sub folders, which are concatenated to one single
   image stream.
-  a previously saved ``.cdb`` **ClickPoints Project** file.

``Esc`` closes ClickPoints. If you want to process the data afterwards, you can refere to the `API <api.html>`_ for a
python interface to read the ``.cdb`` ClickPoints Project files.

.. attention::
    If no project has been specified (once saved as a ``.cdb`` file), all changes are lost! If a project was specified,
    the changes will always be saved.

Zooming, Panning, Rotating
--------------------------

ClickPoints opens with a display of the current image fit to the window. The display can be zoomed using the mouse wheel
and panned holding down the right mouse button. To fit the image to the view again press ``F``.
The display can be set to full screen pressing ``W``. The image can be rotated using ``R``.

.. note::
    How much the image is rotated at the beginning or how much to rotate with each press of ``R`` can be defined in the
    ``ConfigClickPoints.txt`` with the entries ``rotation =`` and ``rotation_steps =``.

Jumping frames
--------------

Changing frames is a key element of ClickPoints and therefore various possibilities exists to change the current frame.

- The keys ``Left`` and ``Right`` go to the previous or next frame.
- The keys ``Home`` and ``End`` jump to the first or last frame.

Key pairs on the numpad allow for jumps of

- ``Numpad 2``, ``Numpad 3``:  -/+ 1
- ``Numpad 5``, ``Numpad 6``:  -/+ 10
- ``Numpad 8``, ``Numpad 9``:  -/+ 100
- ``Numpad /``, ``Numpad *``:  -/+ 1000

Be sure to have the numpad activated, or the keys won't work.

For continuous playback of frames see `timeline <timeline.html>`_.

.. note::
    If other jumps are required, the entry ``jumps =`` in the ``ConfigClickPoints.txt`` can redefine
    these jumps, by giving a list of a new definition of these 8 jumps.

Interfaces
----------

The interfaces for Marker, Mask and GammaCorretion can be shown/hidden
pressing ``F2``. Marker and Masks are saved by pressing ``S`` or
changing the current frame.


.. |the save button| image:: images/IconSave.png
.. |the folder button| image:: images/IconFolder.png

