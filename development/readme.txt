Make Release
============

WARNING: make sure that you have an updated repository before making a release.

Making a release consists of three parts:

- raising the version number and committing the new version number (RaiseVersion.py -r -v 1.6.0)
- bundling the package and load it to PyPi (UploadPyPi.py, optionally with --username and --password)
- bundling the conda package and loading it to the Anaconda cloud (UploadAnaconda.py, optionally with --username and --password)

For raising the version number you need to have write access to the Repository, e.g. use your Bitbucket account.

For uploading to PyPi you need a PyPi account and write access to the ClickPoints project. You can either provide your
username and password as parameters to the script or you will be prompted to enter them.
WARNING: on PyPi every version can only be uploaded once and even if it is deleted, you have to upload it with a new
version number.

For uploading to Anaconda you need an anaconda account. Here the username and password will be cached by conda, so you
only need to provide them once, and it will raise a warning if you try to login again.
Anaconda packages are per OS system, so you need to call this from Windows and from Linux to keep all OS versions updated.

The following explanations provide some details on what the scripts do, if you use the provided scripts as described
above, you do not need the following paragraphs.


Updating a version
==================

Raise version number in
    
    - setup.py
    - meta.yaml
    - docs/conf.py
    - clickpoints/__init__.py

Upload to PiPy
==============

ensure that twine is installed

    pip install twine

build the package and upload it

    python setup.py sdist
    twine upload dist/clickpoints-VERSION.tar.gz

Upload to Conda
===============
install anaconda-client and conda-build

    conda install anaconda-client conda-build -y
   
update those two packages

    conda update -n root conda-build
    conda update -n root anaconda-client
    
specify the login

    anaconda login --username rgerum --password *****
    
set autoupload to "yes"

    conda config --set anaconda_upload yes
    
build the package

    conda-build . -c conda-forge
