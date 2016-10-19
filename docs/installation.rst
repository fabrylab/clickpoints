Installation
============

ClickPoints can be installed in different ways, you can choose the one which is the most comfortable for you and the
operating system you are using.

Windows
-------

Installer
~~~~~~~~~

We provide an installer for the windows platform including python and all the packages which are needed. It is the simplest and most
comfortable installation.

`Download Installer with Python 175MB <https://bitbucket.org/fabry_biophysics/clickpoints/downloads/ClickPoints_latest.exe>`_

.. note::
    We recommend that you install ClickPoints to ``C:\Software\ClickPoints``, as the ``Program files`` folder requires
    to always provide admin privileges when modifying any files.

Installer (without python)
~~~~~~~~~~~~~~~~~~~~~~~~~~

If you already have python installed and don't want two different versions of python on your computer, we provide an
installer which doesn't include python.

`Download Installer without Python 1MB <https://bitbucket.org/fabry_biophysics/clickpoints/downloads/ClickPoints_latest_no_python.exe>`_

Zip Package
~~~~~~~~~~~

If you prefer to install all required packages yourself, you can download ClickPoints in a zip archive. Some packages
don't install out of the box with `pip` but wheel files for these packages be obtained from Christoph Gohlke.

`Download Zip Package 1MB <https://bitbucket.org/fabry_biophysics/clickpoints/downloads/clickpoints_latest.zip>`_

For adding clickpoints to the right click menu in the file explorer, execute the ``install_bat.py`` in the install folder.

To register clickpoints as an importable package, go to your clickpoints folder in the subfolder package and execute
``python setup.py install``.


Cutting Edge Version (Mercurial)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you prefer to have the latest version with the latest features and bugs, you can grab the tip version from our
mercurial repository.

    ``hg clone https://bitbucket.org/fabry_biophysics/clickpoints``

Linux
-----

Download the `Zip Package`_. or `Cutting Edge Version`_ and run the ``install_bat.py``, which will create a command line
command ``clickpoints`` and add ClickPoints to the menu for right clicking on folders/images in the file browser (e.g.
nautilus or dolphin).

Mac
---

Not yet supported. ClickPoints hasn't been tried on Mac yet and ClickPoints won't be added to the Finder right click menu
yet. If you have python already installed, you can refer to the installation from `Zip Package`_ to try to get it working
yourself.


