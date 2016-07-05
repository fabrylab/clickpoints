Addons
======

Addons are helpful scripts which are not part of the main ClickPoints program, but can be loaded on demand to do some evaluation task.

They can be loaded by clicking on |the script icon| and loading a the ``.py`` of the addon. ClickPoints already comes
with a couple of addons, but it is easy to add your own or extend existing ones.

Each addon will be assigned to a key from ``F12`` downwards (``F12``, ``F11``, ``F10`` and so on). Hitting this key
will start the addon with access to the current project database and the current ClickPoints instances. Hitting this key
again will stop the addon again.

To configure ClickPoints to already have scripts loaded on startup, you can define them in the ``ConfigClickPoints.txt``
file as ``launch_scripts =``.

.. attention::
    Addons can only access the project data when the project has already been saved. Starting addons to work on an
    unsaved project doesn't work.

.. toctree::
    :caption: List of Addons
    :maxdepth: 2
   
    addon_track
    addon_driftcorrection
    addon_celldetector

.. |the script icon| image:: images/IconCode.png