Drift Correction
================

This addon takes a region in the image and tries to find it in every image. The offset saved for every image to correct
for drift in the video.

To use it, open a ClickPoints session and add the addon ``DriftCorrection.py`` by clicking on |the script icon|.

When you first start the script a marker type named ``drift_rect`` is created. Use this type to select a region in the
image which remains stable over the course of the video. Start the drift correction script by using ``F12`` (or the key
the script is connected to). The drift correction can be stopped and restarted at any time using the key again.

.. |the script icon| image:: images/IconCode.png