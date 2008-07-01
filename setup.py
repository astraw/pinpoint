from distutils.core import setup
from distutils.core import Extension
from Cython.Distutils import build_ext

ext_modules = []

ext_modules.append(Extension(name='pinpoint.caltech_distortion',
                             sources=['src/caltech_distortion.pyx']))

setup(name='pinpoint',
      version='0.0.1',
      author='pinpoint developers',
      author_email='strawman@astraw.com', # until the Launchpad pinpoint-team mailing list is running
      license='BSD',
      url='http://launchpad.net/pinpoint',
      packages = ['pinpoint'],
      ext_modules= ext_modules,
      cmdclass = {'build_ext': build_ext},
      )
