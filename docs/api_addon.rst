Add-on API
==========

ClickPoints allows to easily write add-on scripts.

.. note::
    The `Addons <addons.html>`_ section demonstrates how the add-ons can be used and may serve as a good starting point
    to write custom add-ons.

The add-on consists of at least two files. A meta data file with ``.txt`` ending which contains basic information on the add-on and a script file
providing an overloaded class of ``clickpoints.Addon`` as shown above.

Meta Data File
--------------

The file has to start with ``[addon]`` followed by lines with key and value pairs:
A typical meta file looks like this:


.. code-block:: python
    :linenos:

    [addon]
    name=My new Add-on
    file=Addon.py
    icon=fa.flask
    description=This add-on makes cool new things.


-  **name** - ``name=My new Add-on``
      Defines the name of the add-on. This name is displayed in ClickPoints in the add-on list.

-  **file** - ``file=Addon.py``
      Defines the filename of the python file that contains the add-on class.

-  **icon** - ``icon=fa.flask``
      Defines the icon of the add-on. It can be either a filename or ``fa.`` followed by the name of a font awesome icon
      see the `font awesome iconlist <http://fontawesome.io/icons/>`_.

-  **description** - ``description=This add-on makes cool new things.``
      Defines a short description for the add-on. If a longer description is desired, a file called ``Desc.html`` next to the
      ``*.txt`` file can be used. This file supports rich text with an html subset defined by `Qt Html Subset <http://doc.qt.io/qt-4.8/richtext-html-subset.html>`_.

Script File
-----------

The script file has to contain a class called ``Addon`` which is derived
from a prototype Add-on class:

.. code-block:: python
    :linenos:

    import clickpoints

    class Addon(clickpoints.Addon):
        def __init__(self, *args, **kwargs):
            clickpoints.Addon.__init__(self, *args, **kwargs)

            print("I am initialized with the database", self.db)
            print("and the ClickPoints interface", self.cp)

        def run(self, *args, **kwargs):
            print("The user wants to run me")

This class will allow you to overload the ``init`` function were your add-on can set up its configuration, e.g. add some
new marker types to ClickPoints.

To process data, you can overload the ``run`` function. Here the add-on can do it's heavy work. Some caution has to be
taken when executing interface actions, as ``run`` is called in a second thread to not block ClickPoints during its
execution. For a good example of an add-on that uses the ``run`` function, refer to the `Track Add-on <addon_track.html>`_.

But add-ons can also provide passive features that are not executed by a call of the ``run`` method, but rely on callbacks.
Here a good example is the `Measure Tool Add-on <addon_measure_tool.html>`_, which just reacts on the ``MarkerMoved`` callback.

The add-on class has two main member variables: ``self.db`` and ``self.cp``.

- ``self.db`` is a `DataFile <api.html#datafile>`_ instance which gives access to the ClickPoints database. For details on the interface see `Database API <api.html>`_.

- ``self.cp`` is a `Commands <#id1>`_ instance which allows for communication with the ClickPoints interface.

.. attention::
    To be able to use the API, the clickpoints package has to be installed!
    If a ``ImportError: No module named clickpoints`` error is raised, you have to install the package first. Go to clickpoints\package in your clickpoints directory and execute ``python setup.py develop`` there.

Defining Options
----------------

Add-ons can define their own options that are saved in the database along the ClickPoints options. They are also included
in the ClickPoints options menu and the export of options.

New options should be defined in the ``__init__`` function of the add-on. Therefore the add-on class has some methods to
add, get and set options:

.. py:function:: addOption(key, default, value_type="string", values=None, display_name="", hidden=False, tooltip="", min_value=None, max_value=None, value_count=1)

   Define a new option value for the add-on.

   Parameters:
        - **key** *(str)* - the name of the option.
        - **default** *(str, int, float, list)* - the default value for the option.
        - **value_type** *(str)* - the type of the value, can be *string*, *int*, *float*, *bool*, *choice*
        - **values** *(list)* - allowed values if the type is *choice*.
        - **display_name** *(str)* - the name to display in the option menu.
        - **hidden** *(bool)* - weather the option should be displayed in the option menu.
        - **tooltip** *(str)* - the tooltip of the option in the option menu.
        - **min_value** *(number)* - the minimal value for a *int* or *float* option.
        - **max_value** *(number)* - the maximum value for a *int* or *float* option.
        - **value_count** *(int)* - it the option should accept a list of values. Only for *int* values.

.. py:function:: getOption(key)

   Return the current value of an option.

   Parameters:
        - **key** *(str)* - the name of the option.

.. py:function:: setOption(key, value)

   Set the current value of an option.

   Parameters:
        - **key** *(str)* - the name of the option.
        - **value** *(str, int, float, list)* - the new value of the option.

.. py:function:: getOptions()

   Return a list of all options of this add-on. The list contains option objects with the following properties:

   Properties:
        - **key** *(str)* - the name of the option.
        - **value** *(str, int, float, list)* - the current value of the option.
        - **default** *(str, int, float, list)* - the default value for the option.
        - **value_type** *(str)* - the type of the value, can be *string*, *int*, *float*, *bool*, *choice*
        - **values** *(list)* - allowed values if the type is *choice*.
        - **display_name** *(str)* - the name to display in the option menu.
        - **hidden** *(bool)* - weather the option should be displayed in the option menu.
        - **tooltip** *(str)* - the tooltip of the option in the option menu.
        - **min_value** *(number)* - the minimal value for a *int* or *float* option.
        - **max_value** *(number)* - the maximum value for a *int* or *float* option.
        - **value_count** *(int)* - it the option should accept a list of values. Only for *int* values.

Commands
--------

Add-ons have some basic functions to communicate with the main ClickPoints window. This interface is accessible through
the ``self.cp`` class variable in the add-on class.
   
.. autoclass:: clickpoints.Addon.Command
    :members:
