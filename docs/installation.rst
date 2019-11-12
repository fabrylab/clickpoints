Installation
============

ClickPoints can be installed in different ways, you can choose the one which is the most comfortable for you and the
operating system you are using.

Windows Installer
~~~~~~~~~~~~~~~~~

If you have no Python installation and just want to get started, our installer is the best option for you. Just download
and execute the following installer:

`Download: ClickPoints Installer <https://bitbucket.org/fabry_biophysics/clickpoints/downloads/ClickPoints.exe>`_

This will install the miniconda environment, if it is not already installed and download the clickpoints conda package.

.. note::
    ClickPoints will be by default installed in a new conda environment called `_app_own_environment_clickpoints`.

Python Packages
~~~~~~~~~~~~~~~

If you are already familiar with python and have a python installation, you can choose one of the following ways:

- If you have pip: ``pip install clickpoints`` (recomended)
- If you are in a conda env: ``conda install -c conda-forge -c rgerum clickpoints``
- Or with ``python setup.py install`` (to use this command download the package and call the command in the main folder)

We recommend the conda installation, as this should always be the newest version of ClickPoints.

If you want to register clickpoints for the typical file extensions, e.g. add it to the right click menu, execute

    ``clickpoints register``

If you want to remove it again, call

    ``clickpoints unregister``

Developer Version
~~~~~~~~~~~~~~~~~

If you want to have ClickPoints installed from the repository and be able to update to the newest changesets, you can
follow this guide. First of all you need to have git installed (`Git <https://git-scm.com/>`_ or directly a git client e.g. `GitHub Desktop<https://desktop.github.com/>`_).
Then you can open a command line in the folder where you want to install ClickPoints (e.g. C:\Software) and run the following command:

    ``git clone https://github.com/fabrylab/clickpoints.git``

To install the package with all dependencies, go to the folder where ClickPoints has been downloaded (e.g. C:\Software\clickpoints) and execute:

    ``pip install -e .``

in the downloaded repository directory. Then execute the command

    ``clickpoints register``

which will add clickpoints to the right click menu in the file explorer.

Possible Errors
~~~~~~~~~~~~~~~

Here is a short list of possible error messages after installation and how they can be fixed.

    ``This application failed to start because it could not find or load the Qt platform plugin "windows" in "".``

reinstall pyqt5 with ``pip install pyqt5``.
