"""models of non-linear camera distortion"""
import numpy as np
import scipy
import scipy.ndimage

from enthought.pyface.api import SplitApplicationWindow, GUI
from enthought.traits.api import HasTraits, Float, Instance, String, File, Enum

from enthought.traits.ui.api import View, Item, Group, Handler
from enthought.traits.ui.menu import Action

import pinpoint._caltech_distortion as _cd
import pinpoint.util as util

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

class HasFilename(HasTraits):
    filename = File

class CaltechNonlinearDistortionHandler(Handler):
    def do_save_rad_file(self, info):
        fileobj = HasFilename()
        ui  = fileobj.edit_traits( kind = 'livemodal' )
        if ui.result:
            info.object.save_to_rad_file(fileobj.filename)

    def do_load_rad_file(self, info):
        creator = info.object
        raise NotImplementedError('')

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

    SaveRadFileAction = Action(name = "Save .rad file", action = "do_save_rad_file")
    LoadRadFileAction = Action(name = "Load .rad file", action = "do_load_rad_file")

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
                       resizable = True,
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
                       buttons=[SaveRadFileAction],
                       handler=CaltechNonlinearDistortionHandler(),
                       title   = 'Caltech Distortion Model - parameters',
                       #label = 'Edit distortion parameters',
                       resizable = True,
                       )

    def _anytrait_changed(self,event):
        self.helper = _cd.CaltechDistortion( self.fc1, self.fc2,
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

    def save_to_rad_file( self, fd, comments=None ):
        """save distortion parameters to .rad file

        .rad files are compatible with Bouget's camera calibration
        toolbox and the Multi-Camera Self Calibration Toolbox.

        """

        # http://www.vision.caltech.edu/bouguetj/calib_doc/htmls/parameters.html
        rad_fd,close_file = util.open_file(fd,mode='w')

        # See
        # http://www.vision.caltech.edu/bouguetj/calib_doc/htmls/parameters.html
        K = np.array((( self.fc1, self.alpha_c*self.fc1, self.cc1),
                      ( 0,        self.fc2,              self.cc2),
                      ( 0,        0,                     1       )))

        rad_fd.write('K11 = %s;\n'%repr(K[0,0]))
        rad_fd.write('K12 = %s;\n'%repr(K[0,1]))
        rad_fd.write('K13 = %s;\n'%repr(K[0,2]))
        rad_fd.write('K21 = %s;\n'%repr(K[1,0]))
        rad_fd.write('K22 = %s;\n'%repr(K[1,1]))
        rad_fd.write('K23 = %s;\n'%repr(K[1,2]))
        rad_fd.write('K31 = %s;\n'%repr(K[2,0]))
        rad_fd.write('K32 = %s;\n'%repr(K[2,1]))
        rad_fd.write('K33 = %s;\n'%repr(K[2,2]))
        rad_fd.write('\n')
        rad_fd.write('kc1 = %s;\n'%repr(self.k1))
        rad_fd.write('kc2 = %s;\n'%repr(self.k2))
        rad_fd.write('kc3 = %s;\n'%repr(self.p1))
        rad_fd.write('kc4 = %s;\n'%repr(self.p2))
        rad_fd.write('\n')
        if comments is not None:
            comments = str(comments)
        rad_fd.write("comments = '%s';\n"%comments)
        rad_fd.write('\n')
        if close_file:
            rad_fd.close()

def read_rad_file(filename):
    """load distortion parameters from a .rad file"""
    params = {}
    execfile(filename,params)
    kwargs = dict(fc1=params['K11'],
                  fc2=params['K22'],
                  cc1=params['K13'],
                  cc2=params['K23'],
                  k1= params['kc1'],
                  k2= params['kc2'],
                  p1= params['kc3'],
                  p2= params['kc4'],
                  alpha_c=(params['K12']/params['K11']),
                  )
    return CaltechNonlinearDistortionParameters(**kwargs)
