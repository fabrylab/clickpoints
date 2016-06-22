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

Database Models
---------------

The database contains some tables represented in the ClickPoints api as peewee models.

.. py:class:: Meta()

   Stores key value pairs containing meta information for the ClickPoints project.

   Attributes:
        - **key** *(str, unique)* - the key
        - **value** *(str)* - the value for the key

.. py:class:: Path()

   Stores a path. Referenced by each image entry.

   Attributes:
        - **path** *(str, unique)* - the path

.. py:class:: Image()

    Stores an image.

    Attributes:
        - **filename** *(str, unique)* - the name of the file.
        - **ext** *(str)* - the extension of the file.
        - **frame** *(int)* - the frame of the file (0 for images, >= 0 for images from videos).
        - **external_id** *(int)* - the id of the file entry of a corresponding external database. Only used when ClickPoints is started from an external database.
        - **timestamp** *(datetime)* - the timestamp associated to the image.
        - **sort_index** *(int, unique)* - the index of the image. The number shown in ClickPoints next to the time line.
        - **width** *(int)* - None if it has not be set, otherwise the width of the image.
        - **height** *(int)* - None if it has not be set, otherwise the height of the image.
        - **path** *(* :py:class:`Path` *)* - the linked path entry containing the path to the image.
        - **mask** *(* :py:class:`Mask` *)* - the mask entry associated with the image.
        - **data** *(array)* - the image data as a numpy array. Data will be loaded on demand and cached.
        - **data8** *(array, uint8)* - the image data converted to unsigned 8 bit integers.

.. py:class:: Offset()

   Offsets asociated with an image.

   Attributes:
        - **image** *(* :py:class:`Image` *)* - the associated image entry.
        - **x** *(int)* - the x offset
        - **y** *(int)* - the y offset

.. py:class:: Track()

   A track containing multiple markers.

   Attributes:
        - **style** *(str)* - the style for this track.
        - **points()** *(array)* - an Nx2 array containing the x and y coordinates of the associated markers.
        - **marker()** *(list of* :py:class:`Marker` *)*)* - a list containing all the associated markers.
        - **times()** *(list of datetime)* - a list containing the timestamps for the images of the associated markers.
        - **frames()** *(list of int)* - a list containing all the frame numbers for the images of the associated markers.

.. py:class:: MarkerType()

   A Marker type.

   Attributes:
        - **name** *(str, unique)* - the name of the marker type.
        - **color** *(str)* - the color of the marker in HTML format, e.g. #FF0000 (red).
        - **mode** *(int)* - the mode, hast to be either: TYPE_Normal, TYPE_Rect, TYPE_Line or TYPE_Track
        - **style** *(str)* - the style of the marker.

.. py:class:: Marker()

   A Marker.

   Attributes:
        - **image** *(* :py:class:`Image` *)* - the image entry associated with this marker.
        - **x** *(int)* - the x coordinate of the marker.
        - **y** *(int)* - the y coordinate of the marker.
        - **type** *(* :py:class:`MarkerType` *)* - the marker type.
        - **processed** *(bool)* - a flag that is set to 0 if the marker is manually moved in ClickPoints, it can be set from an addon if the addon has already processed this marker.
        - **partner** *(* :py:class:`Marker` *)* - a partner marker with is associated with this marker. Only for TYPE_Line or TYPE_Rect markers.
        - **style** *(str)* - the style definition of the marker.
        - **text** *(str)* - an aditional text associated with the marker. It is displayed next to the marker in ClickPoints.
        - **track** *(* :py:class:`Track` *)* - the track entry the marker belongs to. Only for TYPE_Track.
        - **correctedXY()** *(array)* - the marker position corrected by the offset of the image.
        - **pos()** *(array)* - an array containing the coordinates of the marker: [x, y].

.. py:class:: Mask()

   A mask entry.

   Attributes:
        - **image** *(* :py:class:`Image` *)* - the image entry associated with this marker.
        - **filename** *(str)* - the filename where the mask is stored.
        - **data** *(array)* - the mask image as a numpy array. Mask types are stored by their index value.


.. py:class:: MaskType()

   A mask type.

   Attributes:
        - **name** *(str)* - the name of the mask type.
        - **color** *(str)* - the color of the mask type in HTML format, e.g. #FF0000 (red).
        - **index** *(int)* - the integer value used to represent this type in the mask.
   
Commands
--------   
   
.. autoclass:: clickpoints.Commands
   :members: