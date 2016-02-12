from setuptools import setup

import os
os.chdir(os.path.dirname(__file__))  # for call from the installer

try:
    with open("../version.txt") as fp:
        version = fp.read().strip()
except IOError:
    version = "unknown"

setup(name='clickpoints',
      version=version,
      description='The clickpoints package enables communicating with the clickpoints software and to save and load clickpoints files.',
      url='https://bitbucket.org/fabry_biophysics/clickpointsproject/wiki/Home',
      author='FabryLab',
      author_email='richard.gerum@fau.de',
      license='MIT',
      packages=['clickpoints'],
      install_requires=[
          'pyqt4',
          'numpy',
          'scipy',
          'pillow',
          'qimage2ndarray',
          'peewee',
          'pymysql',
          'natsort',
          'tifffile',
          'imageio',
          'sortedcontainers',
          'matplotlib'
      ],
      zip_safe=False)
