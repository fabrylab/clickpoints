GammaCorrection
===============

A slider box in the right bottom corner which allows to change the
brightness and gamma of the currently displayed image.

Basics
------

.. figure:: images/ModulesGamma.png
   :alt: Gamma Example

   Gamma Example

The gamma correction can be opened by clicking on |the adjust icon|.

A box in the bottom right corner shows the current gamma and brightness
adjustment. Moving a slider changes the display of the currently
selected region in the images. The background of the box displays a
histogram of brightness values of the current image region and a red
line denoting the histogram transform given by the gamma and brightness
adjustment. Pressing ``G`` sets the currently visible region of the
image as the active region for the adjustment. Especially for large
images it increases performance significantly if only a portion of the
image is adjusted. A right click on the box resets gamma and brightness
adjustments.

Gamma
-----

.. figure:: images/ModulesGammaGamma.png
   :alt: Gamma Change

   Gamma Change

The gamma value changes how bright and dark regions of the images are
treated. A low gamma value (<1) brightens the dark regions up while
leaving the bright regions as they are. A high gamma value (>1) darkens
the dark regions of the image while leaving the bright regions as they
are.

Brightness
----------

.. figure:: images/ModulesGammaBrightness.png
   :alt: Brightness Change

   Brightness Change

The brightness can be adjusted by selecting the Max and Min values.
Increasing the Min value darkens the image by setting the Min value (and
everything below) to zero intensity. Decreasing the Max value brightens
the image by setting the Max value (and everything above) to maximum
intensity.

Config Parameter
----------------

Keys
----

-  G: update rect

.. |the adjust icon| image:: images/IconAdjust.png

