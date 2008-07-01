from distutils.core import setup
from distutils.core import Extension

ext_modules = []

ext_modules.append(Extension(name='pinpoint.caltech_distortion',
                             sources=['src/caltech_distortion.c']))

setup(name='pinpoint',
      version='0.0.1',
      author='pinpoint developers',
      author_email='strawman@astraw.com', # until the Launchpad pinpoint-team mailing list is running
      license='BSD',
      url='http://launchpad.net/pinpoint',
      packages = ['pinpoint'],
      ext_modules= ext_modules,
      )
