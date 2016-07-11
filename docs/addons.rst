Add-ons
======

Add-ons are helpful scripts which are not part of the main ClickPoints program, but can be loaded on demand to do some evaluation task.

They can be loaded by clicking on |the script icon| and loading a the ``.py`` of the add-on. ClickPoints already comes
with a couple of add-ons, but it is easy to add your own or extend existing ones.

Each addon will be assigned to a key from ``F12`` downwards (``F12``, ``F11``, ``F10`` and so on). Hitting this key
will start the addon with access to the current project database and the current ClickPoints instances. Hitting this key
again will stop the addon again.

To configure ClickPoints to already have scripts loaded on startup, you can define them in the ``ConfigClickPoints.txt``
file as ``launch_scripts =``.

.. toctree::
    :caption: List of Addons
    :maxdepth: 2
   
    addon_track
    addon_driftcorrection
    addon_celldetector
    addon_grabplotdata

.. |the script icon| image:: images/IconCode.png