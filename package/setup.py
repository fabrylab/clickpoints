from setuptools import setup

import os
if os.path.dirname(__file__) != "":
    os.chdir(os.path.dirname(__file__))  # for call from the installer

try:
    with open("../version.txt") as fp:
        version = fp.read().strip()
except IOError:
    version = "unknown"

setup(name='clickpoints',
      version=version,
      description='The clickpoints package enables communicating with the clickpoints software and to save and load clickpoints files.',
      url='https://bitbucket.org/fabry_biophysics/clickpoints',
      author='FabryLab',
      author_email='richard.gerum@fau.de',
      license='MIT',
      packages=['clickpoints'],
      zip_safe=False)
