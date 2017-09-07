Opening Files and Folders
=========================

ClickPoints was designed with multiple usage keys in mind, and therefore provides multiple ways to open files.

.. attention::
    Opening a set of files for the first time can take some time to extract time and meta information
    from the filename, TIFF or EXIF header. For large collections of files it is recommended to save the collection
    as a project and use the ``.cdb`` file for starting ClickPoints. Saving time as no file system search is necessary
    and all meta information is already stored in the ``.cdb``

via Interface
-------------
ClickPoints can be started empty by using a desktop link or calling ``ClickPoints.bat`` from CMD (Windows),
or respectively ``ClickPoints`` from a terminal (Linux).

Images can be added by using |the folder button|.

.. |the folder button| image:: images/IconFolder.png

via Context Menu
----------------
A fast and comfortable way to open files and folders with ClickPoints is the context menu.

ClickPoints can be opened with various files as target:

-  an **image**, loading all images in the folder of the target image.
-  a **video** file, loading only this video.
-  a **folder**, loading all image and video files of the folder and its sub folders, which are concatenated to one single image stream.
-  a previously saved ``.cdb`` **ClickPoints Project** file, loading the project as it was saved.


via Commandline Parameter
-------------------------
ClickPoints can be run directly from the commandline, e.g. to open the files in the current or a specific folder


.. code-block:: python

   ClickPoints "C:\Images"

or

.. code-block:: python

   python ClickPoints.py -srcfile="C:\Images"

.. note::

    To use the short version of calling ClickPoints without the path, you have to add ClickPoints base path to
    the systems or users ``PATH`` variable (Windows) or create an alias (Linux).

via .txt File
-------------
Furthermore it is possible to supply a text file where each line contains the path to an image or video file.
This is useful e.g. to open a fixed set of files, a list of files extract by another application or a database interface.

.. code-block:: python

    ClickPoints "sample.txt"

.. code-block:: python
   :caption: sample.txt
   :name: sample.txt
   :linenos:

     20120919_colonydensity.gif   								# relativ path (to txt file)
     C:\Users\Desktop\images\20160601-141408_GE4000.jpg  		# absolut path
     \\192.168.0.99\2014\20140323\03\20140323-030151_31n2.JPG 	# network path

.. note::

    It is possible to open files over the network e.g. via samba shares.
    On Linux systems it is necessary do mount the network drive first!
