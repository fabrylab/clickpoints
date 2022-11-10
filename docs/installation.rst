Installation
============

ClickPoints can be installed in different ways, you can choose the one which is the most comfortable for you and the
operating system you are using.

Python Packages
~~~~~~~~~~~~~~~

You can install the latest release version of clickpoints with pip:

    ``pip install clickpoints``

We recommend the pip installation, as this should always be the newest version of ClickPoints.

Run ClickPoints via executing

    ``clickpoints``

If you want to register clickpoints for the typical file extensions, e.g. add it to the right click menu, execute

    ``clickpoints register``

If you want to remove it again, call

    ``clickpoints unregister``
    
Update
~~~~~~

ClickPoints can be updated like any other python package with:

    ``pip install clickpoints --upgrade``
    
You can see the current version number when you open ClickPoints and click on the cog wheels icon to open the options dialog. In the top right corner you will see the current version number.

Developer Version
~~~~~~~~~~~~~~~~~

If you just want to get the very latest features you can install with pip the latest revision:

    ``pip install git+https://github.com/fabrylab/clickpoints``

If you want to actively work on the ClickPoints code, you should clone the repository. First of all you need to have git installed (`Git <https://git-scm.com/>`_ or directly a git client e.g. `GitHub Desktop <https://desktop.github.com/>`_).
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
