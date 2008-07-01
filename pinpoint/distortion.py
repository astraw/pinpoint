"""models of non-linear camera distortion"""
import numpy as np
import scipy
import scipy.ndimage

from enthought.pyface.api import SplitApplicationWindow, GUI
from enthought.traits.api import HasTraits, Float, Instance, String
from enthought.traits.ui.api import View, Item, Group

import pinpoint.caltech_distortion as cd

class NonlinearDistortionParameters(HasTraits):
    def distort(self, x, y):
        raise NotImplementedError('this is an abstract base class method - please override')

    def undistort(self, x, y):
        raise NotImplementedError('this is an abstract base class method - please override')

    def _stackcopy(self,a,b):
        """a[:,:,0] = a[:,:,1] = ... = b"""
        if a.ndim == 3:
            a.transpose().swapaxes(1,2)[:] = b
        else:
            a[:] = b

    def remove_distortion(self,img,reshape=True):
        img = np.atleast_3d(img)
        height, width = img.shape[:2]

        oshape = np.array(img.shape)
        if reshape:
            lowerleft_corner = np.array(self.distort(0.,0.))
            upperright_corner = np.array(self.distort(width-1,height-1))
            oshape[:2][::-1] = upperright_corner - lowerleft_corner

        y,x = np.mgrid[0:oshape[0],0:oshape[1]]

        # center offset
        if reshape:
            x += lowerleft_corner[0]
            y += lowerleft_corner[1]

        # Calculate reverse coordinates
        x,y = self.undistort(x,y)

        coords = np.empty(np.r_[3,oshape],dtype=float)

        # y mapping
        self._stackcopy(coords[0,...],y)

        # x mapping
        self._stackcopy(coords[1,...],x)

        # colour band mapping
        coords[2,...] = range(img.shape[2])

        restored_img = scipy.ndimage.map_coordinates(img,coords,order=1,prefilter=False).squeeze()
        return restored_img, lowerleft_corner, upperright_corner

class CaltechNonlinearDistortionParameters(NonlinearDistortionParameters):
    fc1 = Float(1000.0, label="fc1", desc="focal length (x)")
    fc2 = Float(1000.0, label="fc2", desc="focal length (y)")
    cc1 = Float(label="cc1", desc="distortion center (x)")
    cc2 = Float(label="cc2", desc="distortion center (y)")
    k1 = Float(0.0, label="k1", desc="1st radial disortion term (for r^2)")
    k2 = Float(0.0, label="k2", desc="2nd radial disortion term (for r^4)")
    p1 = Float(0.0, label="p1", desc="1st tangential disortion term")
    p2 = Float(0.0, label="p2", desc="2nd tangential disortion term")
    alpha_c = Float(0.0, label="alpha_c", desc="pixel skew" )

    simple_view = View(Group(Group(Item('cc1'),
                                   Item('cc2'),
                                   label='image center',
                                   show_border=True,
                                   ),
                             Group(Item('k1'),
                                   Item('k2'),
                                   label='radial distortion coefficients',
                                   show_border=True,
                                   )),
                       title   = 'Caltech Distortion Model - parameters',
                       )

    traits_view = View(Group(Group(Item('fc1'),
                                   Item('fc2'),
                                   label='focal length',
                                   show_border=True,
                                   ),
                             Group(Item('cc1'),
                                   Item('cc2'),
                                   label='image center',
                                   show_border=True,
                                   ),
                             Group(Item('k1'),
                                   Item('k2'),
                                   label='radial distortion coefficients',
                                   show_border=True,
                                   ),
                             Group(Item('p1'),
                                   Item('p2'),
                                   label='tangential distortion coefficients',
                                   show_border=True,
                                ),
                             Group(Item('alpha_c'),
                                   #label='pixel skew coefficient',
                                   #show_border=True,
                                   )),
                       title   = 'Caltech Distortion Model - parameters',
                       )

    def _anytrait_changed(self,event):
        self.helper = cd.CaltechDistortion( self.fc1, self.fc2,
                                            self.cc1, self.cc2,
                                            self.k1, self.k2,
                                            self.p1, self.p2,
                                            alpha_c=self.alpha_c )

    def distort(self, x, y):
        # TODO: use numpy arrays natively
        vfunc = np.vectorize( self.helper.distort )
        return vfunc(x,y)

    def undistort(self, x, y):
        # TODO: use numpy arrays natively
        vfunc = np.vectorize( self.helper.undistort )
        return vfunc(x,y)
