Installation
============

ClickPoints can be installed in different ways, you can choose the one which is the most comfortable for you and the
operating system you are using.

Windows
-------

Installer
~~~~~~~~~

We provide an installer for ClickPoints on Windows 64bit platforms.

`Download: ClickPoints Installer <https://bitbucket.org/fabry_biophysics/clickpoints/downloads/ClickPoints_latest.exe>`_

Additionally, you need an installation of Python with the packaged needed by ClickPoints. For convenience we provide a
WinPython installation with all the packages already installed. We recommend to used ClickPoints with this Python installation.

`Download: WinPython for ClickPoints Installer <https://bitbucket.org/fabry_biophysics/clickpoints/downloads/WinPython_ClickPoints.exe>`_

.. note::
    We recommend that you install ClickPoints to ``C:\Software\ClickPoints``, as the ``Program files`` folder requires
    to always provide admin privileges when modifying any files.


Cutting Edge Version (Mercurial)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you prefer to have the latest version with the latest features and bugfixes, you can grab the tip version from our
mercurial repository.

    ``hg clone https://bitbucket.org/fabry_biophysics/clickpoints``

For adding clickpoints to the right click menu in the file explorer, execute the ``install_clickpoints.bat`` in the installation folder.

.. warning::
    If you don't use our provided Python installation, you need to install the required packages. Missing packages will
    throw an ImportError, e.g. ``ImportError: No module named peewee``. This means this package is missing and has to be
    installed. While most packages can be easily installed using pip, unfortunately some packages don't install out of
    the box with `pip` but wheel files for these packages be obtained for Windows from Christoph Gohlke's
    `Unofficial Windows Binaries <http://www.lfd.uci.edu/~gohlke/pythonlibs/>`_ or if you are on Linux from your
     distributions package repositories, e.g. using ``sudo apt install python-PACKAGENAME``

Linux
-----

Download the `Cutting Edge Version (Mercurial)`_ and run the ``install_bat.py``, which will create a command line
command ``clickpoints`` and add ClickPoints to the menu for right clicking on folders/images in the file browser (e.g.
nautilus or dolphin).

Mac
---

Not yet supported. ClickPoints hasn't been tried on Mac yet and ClickPoints won't be added to the Finder right click menu
yet. If you have python already installed, you can refer to the installation from `Cutting Edge Version (Mercurial)`_ to try to get it working
yourself.


