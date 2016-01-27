from setuptools import setup

setup(name='clickpoints',
      version='0.1.5',
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
