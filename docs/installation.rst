Installation
============

ClickPoints can be installed in different ways, you can choose the one which is the most comfortable for you and the
operating system you are using.

If you are already familiar with python, you can choose one of the following ways:

- If you are in a conda env: ``conda install -c rgerum clickpoints``
- If you have pip: ``pip install clickpoints``
- Or with ``python setup.py install``

Windows
-------

Installer
~~~~~~~~~

We provide an installer for ClickPoints on Windows 64bit platforms.

`Download: ClickPoints Installer <https://bitbucket.org/fabry_biophysics/clickpoints/downloads/ClickPoints.exe>`_

This will install the miniconda environment, if it is not already installed and download the clickpoints conda package.

.. note::
    ClickPoints will be by default installed in a new conda environment called `_app_own_environment_clickpoints`.


Cutting Edge Version (Mercurial)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you prefer to have the latest version with the latest features and bugfixes, you can grab the tip version from our
mercurial repository. To do so, you need to install `Mercurial <https://www.mercurial-scm.org/>`_. Then you can open a command
line in the folder where you want to install ClickPoints and run the following command:

    ``hg clone https://bitbucket.org/fabry_biophysics/clickpoints``

Then execute the file ``install.bat`` in the installed directory. This will register the `clickpoints` package and add
clickpoints to the right click menu in the file explorer.

.. warning::
    If you don't use our provided Python installation, you need to install the required packages. Missing packages will
    throw an ImportError, e.g. ``ImportError: No module named peewee``. This means this package is missing and has to be
    installed. While most packages can be easily installed using pip, unfortunately some packages don't install out of
    the box with ``pip install PACKAGENAME`` but wheel files for these packages be obtained for Windows from Christoph Gohlke's
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


