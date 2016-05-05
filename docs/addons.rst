Addons
======

Addons are helpful scripts which are not part of the main ClickPoints program, but can be loaded on demand to do some evaluation task.


A list of different scripts can be specified in the
ConfigClickPoints.txt ``launch_scripts =`` entry. These scripts can
contain evaluation tools which access the data e.g. tracking or plotting
script. These scripts get as command line parameter the current path of
the image in ClickPoints as well es the frame number:

::

    folder = sys.argv[1]
    index = sys.argv[2]

The scripts can be started using the keys ``F12`` to ``F9``, where
``F12`` starts the first script and ``F9`` would start the fourth script
if the list contains that many entries.


-  ``launch_scripts =`` specify a list of scripts which can be started
   by pressing ``F12`` to ``F9``


-  F12: Launch


.. toctree::
   :maxdepth: 2
   
   track
   driftcorrection