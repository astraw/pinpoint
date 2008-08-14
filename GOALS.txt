.. This document is in reStructuredText format.

This is a document stating the goals for the `pinpoint
project`_. Currently, this document and the project are in a very
early and unfinished form, and everything should be regarded as a
pre-alpha sketch. Please join the fun if you're so inclined.

.. _pinpoint project: https://edge.launchpad.net/pinpoint

Ultimately, we would like pinpoint to be an open-source Python library
suitable for multi-camera calibration used in 3D machine vision
tasks. Multi-camera setups are now common, and we would like to allow
the calibration of these to be as easy as possible. Although this is
still an active area of academic research, there are a number of
published algorithms which are useful to the practitioner. Some of
these are already available as open source software, such as sba_. We
would like to bring together, under one unified API, everything
necessary to perform multi-camera calibrations. Another inspiration is
the `Multi Camera Self Calibration Toolbox`_ by Svoboda et al.

.. _sba: http://www.ics.forth.gr/~lourakis/sba/
.. _Multi Camera Self Calibration Toolbox: http://cmp.felk.cvut.cz/%7Esvoboda/SelfCal/index.html

One initial use case for the pinpoint project are the flydra_ systems
by Andrew Straw and Michael Dickinson at Caltech. The specific needs
for this setup are:

.. _flydra: http://dickinson.caltech.edu/Research/MultiTrack

1. Quantitative characterization of radial distortion (and possibly
   other distortion) allowing imaging systems to be treated as a
   non-linear 2D image distortion stage and a pinhole camera
   model. This is a relatively well-understood problem. We have
   implemented the `Line-Based Correction of Radial Lens Distortion`_
   (GMIP 1997) algorithm by Prescott and McLean in the
   pinpoint/distortion_estimate.py module.

2. Factorization of (strongly) perspective-distorted images of 3D
   points in which some views of the points are occluded. This is the
   domain of the `Sturm & Triggs`_ (1996) algorithms and subsequent
   work, for example, `Oliensis & Hartley`_'s (2008) recent CIESTA
   algorithm.

3. Bundle adjustment of the output of the factorization step. This
   also a relatively well understood problem, as described in Chapter
   18 of `Hartley & Zisserman`_.

.. _Line-Based Correction of Radial Lens Distortion: http://dx.doi.org/10.1006/gmip.1996.0407
.. _Hartley & Zisserman: http://www.robots.ox.ac.uk/~vgg/hzbook/hzbook1.html
.. _Oliensis & Hartley: http://dx.doi.org/10.1109/TPAMI.2007.1132
.. _Sturm & Triggs: http://citeseer.ist.psu.edu/sturm96factorization.html

Straw and Dickinson will provide test data sets for the pinpoint
project to gauge progress towards these goals.
