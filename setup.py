from setuptools import setup
from distutils.core import Extension

ext_modules = []

ext_modules.append(Extension(name='pinpoint._caltech_distortion',
                             sources=['src/_caltech_distortion.c']))

setup(name='pinpoint',
      description='a Python library for N-view camera calibration',
      version='0.0.4',
      author='pinpoint developers',
      author_email='strawman@astraw.com',
      license='BSD',
      url='http://github.com/astraw/pinpoint',
      packages = ['pinpoint'],
      ext_modules= ext_modules,
      entry_points = {
    'gui_scripts': ['pinpoint_distortion_gui = pinpoint.distortion_gui:main',
                    ],
    },
      )
