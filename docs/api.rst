API
===

ClickPoints comes with a powerful API which enables access from within python to ClickPoints Projects which are stored in a ``.cdb`` ClickPoints SQLite database.

To get started reading and writing to a database use:

>>> import clickpoints
>>> db = clickpoints.DataFile("project.cdb")

This will open an existing project file called ``project.cdb``.

If you intend to use your python script also as an addon script, you should start with:

>>> import clickpoints
>>> start_frame, database, port = clickpoints.GetCommandLineArgs()
>>> db = clickpoints.DataFile(database)
>>> com = clickpoints.Commands(port, catch_terminate_signal=True)

This will retrieve ``start_frame``, ``database`` and ``port`` from the command line arguments the script was started with. When executing the script through the addon interface, ClickPoints will provide these values. These can then be used to open the ClickPoints project file and establish a connection to the ClickPoints instance.

.. note::
    Please refere to the `Examples <examples.html>`_ and `Addons <addons.html>`_ section to see how this can be used.

.. attention::
    To be able to use the API, the clickpoints package has to be installed!
    If a ``ImportError: No module named clickpoints`` error is raised, you have to install the package first. Go to clickpoints\package in your clickpoints directory and execute ``python setup.py develop`` there.

GetCommandLineArgs
------------------

.. autofunction:: clickpoints.GetCommandLineArgs

DataFile
--------

.. autoclass:: clickpoints.DataFile
   :members:
   
Commands
--------   
   
.. autoclass:: clickpoints.Commands
   :members: