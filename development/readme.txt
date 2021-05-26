Make Release
============

WARNING: make sure that you have an updated repository before making a release.

Making a release consists of three parts:

- raising the version number and committing the new version number (RaiseVersion.py -r -v 1.6.0)
- bundling the package and load it to PyPi via github ("draft new release") make sure to use the new version number as a tag.
- bundling the conda package and loading it to the Anaconda cloud (UploadAnaconda.py, optionally with --username and --password)