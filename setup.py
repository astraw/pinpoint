from setuptools import setup
from distutils.core import Extension

ext_modules = []

ext_modules.append(Extension(name='pinpoint._caltech_distortion',
                             sources=['src/_caltech_distortion.c']))

setup(name='pinpoint',
      description='a Python library for N-view camera calibration',
      version='0.0.2+git',
      author='pinpoint developers',
      author_email='pinpoint-team@lists.launchpad.net',
      license='BSD',
      url='http://launchpad.net/pinpoint',
      packages = ['pinpoint'],
      ext_modules= ext_modules,
      entry_points = {
    'gui_scripts': ['pinpoint_distortion_gui = pinpoint.distortion_gui:main',
                    ],
    },
      )
