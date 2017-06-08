Add-ons
=======

Add-ons are helpful scripts which are not part of the main ClickPoints program, but can be loaded on demand to do some evaluation task.

They can be loaded by clicking on |the script icon| and selecting the add-on from the list. ClickPoints already comes
with a couple of add-ons, but it is easy to add your own or extend existing ones.

Each add-on will be assigned to a key from ``F12`` downwards (``F12``, ``F11``, ``F10`` and so on) and a button will
appear for each add-on next to |the script icon|. Hitting the key or pressing the button will start the ``run`` function
of the add-on in a separate thread, or tell the thread to stop if it is already running.

To configure ClickPoints to already have scripts loaded on startup, you can define them in the ``ConfigClickPoints.txt``
file as ``launch_scripts =``.

For writing your own add-ons please refer to the `add-on api <api_addon.html>`_.

.. toctree::
    :caption: List of Addons
    :maxdepth: 2
   
    addon_track
    addon_driftcorrection
    addon_celldetector
    addon_grabplotdata

.. |the script icon| image:: images/IconCode.png