Database API
============

ClickPoints comes with a powerful API which enables access from within python to ClickPoints Projects which are stored in a ``.cdb`` ClickPoints SQLite database.

To get started reading and writing to a database use:

.. code-block:: python
    :linenos:

    import clickpoints
    db = clickpoints.DataFile("project.cdb")

This will open an existing project file called ``project.cdb``.

.. note::
    The `Examples <examples.html>`_ section demonstrates the use of the API with various examples and provides a good
    starting point to write custom evaluations.

.. attention::
    To be able to use the API, the clickpoints package has to be installed!
    If a ``ImportError: No module named clickpoints`` error is raised, you have to install the package first. Go to clickpoints\package in your clickpoints directory and execute ``python setup.py develop`` there.


Database Models
---------------

The ``.cdb`` file consists of multiple SQL tables in which it stores its information. Each table is represented in the API
as a peewee model. Users which are not familiar can use the API without any knowledge of peewee, as the API provides
all functions necessary to access the data. For each table a ``get`` (retrieve entries), ``set`` (add and change entries)
and ``delete`` (remove entries) function is provided. Functions with a plural name always work on multiple entries at once
and all arguments can be provided as single values or arrays if multiple entries should be affected.

The tables are: :py:class:`Meta`, :py:class:`Path`, :py:class:`Image`, :py:class:`Offset`, :py:class:`Track`, :py:class:`MarkerType`,
:py:class:`Marker`, :py:class:`Line`, :py:class:`Rectangle`, :py:class:`Mask`, :py:class:`MaskType`, :py:class:`Annotation`,
:py:class:`Tag`, :py:class:`TagAssociation`.

.. py:class:: Meta()

    Stores key value pairs containing meta information for the ClickPoints project.

    Attributes:
        - **key** *(str, unique)* - the key
        - **value** *(str)* - the value for the key

.. py:class:: Path()

    Stores a path. Referenced by each image entry.

    See also: :py:meth:`~.DataFile.getPath`, :py:meth:`~.DataFile.getPaths`, :py:meth:`~.DataFile.setPath`,
    :py:meth:`~.DataFile.deletePaths`.

    Attributes:
        - **path** *(str, unique)* - the path
        - **images** *(list of* :py:class:`Image` *)* - the images with this path.

.. py:class:: Image()

    Stores an image.

    See also: :py:meth:`~.DataFile.getImage`, :py:meth:`~.DataFile.getImages`, :py:meth:`~.DataFile.getImageIterator`,
    :py:meth:`~.DataFile.setImage`, :py:meth:`~.DataFile.deleteImages`.

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
        - **offset** *(* :py:class:`Offset` *)* - the linked offset entry containing the offsets stored for this image.
        - **markers** *(list of* :py:class:`Marker` *)* - a list of marker entries for this image.
        - **lines** *(list of* :py:class:`Line` *)* - a list of line entries for this image.
        - **rectangles** *(list of* :py:class:`Rectangle` *)* - a list of rectangle entries for this image.
        - **mask** *(* :py:class:`Mask` *)* - the mask entry associated with the image.
        - **data** *(array)* - the image data as a numpy array. Data will be loaded on demand and cached.
        - **data8** *(array, uint8)* - the image data converted to unsigned 8 bit integers.
        - **getShape()** *(list)* - a list containing height and width of the image. If they are not stored in the database yet, the image data has to be loaded.

.. py:class:: Offset()

    Offsets associated with an image.

    Attributes:
        - **image** *(* :py:class:`Image` *)* - the associated image entry.
        - **x** *(int)* - the x offset
        - **y** *(int)* - the y offset

.. py:class:: Track()

    A track containing multiple markers.

    See also: :py:meth:`~.DataFile.getTrack`, :py:meth:`~.DataFile.getTracks`, :py:meth:`~.DataFile.setTrack`, :py:meth:`~.DataFile.deleteTracks`.

    Attributes:
        - **style** *(str)* - the style for this track.
        - **text** *(str)* - an additional text associated with this track. It is displayed next to the markers of this track in ClickPoints.
        - **hidden** *(bool)* - whether the track should be displayed in ClickPoints.
        - **points** *(array)* - an Nx2 array containing the x and y coordinates of the associated markers.
        - **points_corrected** *(array)* - an Nx2 array containing the x and y coordinates of the associated markers corrected by the offsets of the images.
        - **markers** *(list of* :py:class:`Marker` *)* - a list containing all the associated markers.
        - **times** *(list of datetime)* - a list containing the timestamps for the images of the associated markers.
        - **frames** *(list of int)* - a list containing all the frame numbers for the images of the associated markers.
        - **image_ids** *(list of int)* - a list containing all the ids for the images of the associated markers.

.. py:class:: MarkerType()

    A marker type.

    See also: :py:meth:`~.DataFile.getMarkerTypes`, :py:meth:`~.DataFile.getMarkerType`, :py:meth:`~.DataFile.setMarkerType`, :py:meth:`~.DataFile.deleteMarkerTypes`.

    Attributes:
        - **name** *(str, unique)* - the name of the marker type.
        - **color** *(str)* - the color of the marker in HTML format, e.g. #FF0000 (red).
        - **mode** *(int)* - the mode, hast to be either: TYPE_Normal, TYPE_Rect, TYPE_Line or TYPE_Track
        - **style** *(str)* - the style of the marker type.
        - **text** *(str)* - an additional text associated with the marker type. It is displayed next to the markers of this type in ClickPoints.
        - **hidden** *(bool)* - whether the markers of this type should be displayed in ClickPoints.
        - **markers** *(list of* :py:class:`Marker` *)* - a list containing all markers of this type. Only for TYPE_Normal and TYPE_Track.
        - **lines** *(list of* :py:class:`Line` *)* - a list containing all lines of this type. Only for TYPE_Line.
        - **markers** *(list of* :py:class:`Rectangle` *)* - a list containing all rectangles of this type. Only for TYPE_Rect.

.. py:class:: Marker()

    A marker.

    See also: :py:meth:`~.DataFile.getMarker`, :py:meth:`~.DataFile.getMarkers`, :py:meth:`~.DataFile.setMarker`,
    :py:meth:`~.DataFile.setMarkers`, :py:meth:`~.DataFile.deleteMarkers`.

    Attributes:
        - **image** *(* :py:class:`Image` *)* - the image entry associated with this marker.
        - **x** *(int)* - the x coordinate of the marker.
        - **y** *(int)* - the y coordinate of the marker.
        - **type** *(* :py:class:`MarkerType` *)* - the marker type.
        - **processed** *(bool)* - a flag that is set to 0 if the marker is manually moved in ClickPoints, it can be set from an add-on if the add-on has already processed this marker.
        - **style** *(str)* - the style definition of the marker.
        - **text** *(str)* - an additional text associated with the marker. It is displayed next to the marker in ClickPoints.
        - **track** *(* :py:class:`Track` *)* - the track entry the marker belongs to. Only for TYPE_Track.
        - **correctedXY()** *(array)* - the marker position corrected by the offset of the image.
        - **pos()** *(array)* - an array containing the coordinates of the marker: [x, y].

.. py:class:: Line()

    A line.

    See also: :py:meth:`~.DataFile.getLine`, :py:meth:`~.DataFile.getLines`, :py:meth:`~.DataFile.setLine`,
    :py:meth:`~.DataFile.setLines`, :py:meth:`~.DataFile.deleteLines`.

    Attributes:
        - **image** *(* :py:class:`Image` *)* - the image entry associated with this line.
        - **x1** *(int)* - the first x coordinate of the line.
        - **y1** *(int)* - the first y coordinate of the line.
        - **x2** *(int)* - the second x coordinate of the line.
        - **y2** *(int)* - the second y coordinate of the line.
        - **type** *(* :py:class:`MarkerType` *)* - the marker type.
        - **processed** *(bool)* - a flag that is set to 0 if the line is manually moved in ClickPoints, it can be set from an add-on if the add-on has already processed this line.
        - **style** *(str)* - the style definition of the line.
        - **text** *(str)* - an additional text associated with the line. It is displayed next to the line in ClickPoints.
        - **correctedXY()** *(array)* - the line positions corrected by the offset of the image.
        - **pos()** *(array)* - an array containing the coordinates of the line: [x, y].
        - **length** *(float)* - the length of the line in pixel.

.. py:class:: Rectangle()

    A rectangle.

    See also: :py:meth:`~.DataFile.getRectangle`, :py:meth:`~.DataFile.getRectangles`, :py:meth:`~.DataFile.setRectangle`,
    :py:meth:`~.DataFile.setRectangles`, :py:meth:`~.DataFile.deleteRectangles`.

    Attributes:
        - **image** *(* :py:class:`Image` *)* - the image entry associated with this rectangle.
        - **x** *(int)* - the x coordinate of the rectangle.
        - **y** *(int)* - the y coordinate of the rectangle.
        - **width** *(int)* - the width of the rectangle.
        - **height** *(int)* - the height of the rectangle.
        - **type** *(* :py:class:`MarkerType` *)* - the marker type.
        - **processed** *(bool)* - a flag that is set to 0 if the rectangle is manually moved in ClickPoints, it can be set from an add-on if the add-on has already processed this line.
        - **style** *(str)* - the style definition of the rectangle.
        - **text** *(str)* - an additional text associated with the rectangle. It is displayed next to the rectangle in ClickPoints.
        - **correctedXY()** *(array)* - the rectangle positions corrected by the offset of the image.
        - **pos()** *(array)* - an array containing the coordinates of the rectangle: [x, y].
        - **slice_x()** *(slice*) - a slice object to use the rectangle to cut out a region of an image
        - **slice_y()** *(slice)* - a slice object to use the rectangle to cut out a region of an image
        - **area()** *(float)* - the area of the rectangle

.. py:class:: Mask()

    A mask entry.

    See also: :py:meth:`~.DataFile.getMask`, :py:meth:`~.DataFile.getMasks`, :py:meth:`~.DataFile.setMask`, :py:meth:`~.DataFile.deleteMasks`.

    Attributes:
        - **image** *(* :py:class:`Image` *)* - the image entry associated with this marker.
        - **data** *(array)* - the mask image as a numpy array. Mask types are stored by their index value.


.. py:class:: MaskType()

    A mask type.

    See also: :py:meth:`~.DataFile.getMaskType`, :py:meth:`~.DataFile.getMaskTypes`, :py:meth:`~.DataFile.setMaskType`,
    :py:meth:`~.DataFile.deleteMaskTypes`.

    Attributes:
        - **name** *(str)* - the name of the mask type.
        - **color** *(str)* - the color of the mask type in HTML format, e.g. #FF0000 (red).
        - **index** *(int)* - the integer value used to represent this type in the mask.


.. py:class:: Annotation()

    An annotation.

    See also: :py:meth:`~.DataFile.getAnnotation`, :py:meth:`~.DataFile.getAnnotations`, :py:meth:`~.DataFile.setAnnotation`, :py:meth:`~.DataFile.deleteAnnotations`.

    Attributes:
        - **image** *(* :py:class:`Image` *)* - the image entry associated with this annotation.
        - **timestamp** *(datetime)* - the timestamp of the image linked to the annotation.
        - **comment** *(str)* - the text of the comment.
        - **rating** *(int)* - the value added to the annotation as rating.
        - **tags** *(list of* :py:class:`Tag` *)* - the tags associated with this annotation.


.. py:class:: Tag()

    A tag for an :py:class:`Annotation`.

    See also: :py:meth:`~.DataFile.getTag`, :py:meth:`~.DataFile.getTags`, :py:meth:`~.DataFile.setTag`, :py:meth:`~.DataFile.deleteTags`.

    Attributes:
        - **name** *(str)* - the name of the tag.
        - **annotations** *(list of* :py:class:`Annotation` *)* - the annotations associated with this tag.


.. py:class:: TagAssociation()

   A link between a :py:class:`Tag` and an :py:class:`Annotation`

   Attributes:
        - **annotation** *(* :py:class:`Annotation` *)* - the linked annotation.
        - **tag** *(* :py:class:`Tag` *)* - the linked tag.


DataFile
--------

.. autoclass:: clickpoints.DataFile
   :members:
