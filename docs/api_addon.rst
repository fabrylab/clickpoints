Add-on API
==========

ClickPoints allows to easily write add-on scripts. The are called form ClickPoints with command line arguments
specifiying which database to use, at which frame to start and how to communicate with ClikcPoints.

The add-on script should start as follows:

.. code-block:: python
    :linenos:

    import clickpoints
    start_frame, database, port = clickpoints.GetCommandLineArgs()
    db = clickpoints.DataFile(database)
    com = clickpoints.Commands(port, catch_terminate_signal=True)

This will retrieve ``start_frame``, ``database`` and ``port`` from the command line arguments the script was started
with. When executing the script through the add-on interface, ClickPoints will provide these values. These can then be used to open the ClickPoints project file and establish a connection to the ClickPoints instance.

.. note::
    The `Addons <addons.html>`_ section demonstrates how the add-ons can be used and may serve as a good starting point
    to write custom add-ons.

.. attention::
    To be able to use the API, the clickpoints package has to be installed!
    If a ``ImportError: No module named clickpoints`` error is raised, you have to install the package first. Go to clickpoints\package in your clickpoints directory and execute ``python setup.py develop`` there.

GetCommandLineArgs
------------------

.. autofunction:: clickpoints.GetCommandLineArgs


Commands
--------   
   
.. autoclass:: clickpoints.Commands
    :members: