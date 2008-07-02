import numpy as np
import scipy
import scipy.optimize

import distortion

class Objective(object):

    # TODO: fixme: implement alternative distortion models. Currently
    # only CaltechNonlinearDistortionModel is used.

    def __init__(self,
                 list_of_lines,
                 distortion_center_guess=None,
                 focal_length_x=1000.0,
                 focal_length_y=1000.0,
                 ):
        """
        list_of_lines - sequence of ( Nx2 sequences )
            Lists of distorted image coordinates which should form straight lines.
        distortion_center_guess - sequence of length 2
            Coordinates (in distorted image) from which to penalize estimates of disortion center proportional to distance from this point
        focal_length_x - float
            Focal length of X dimension
        focal_length_y - float
            Focal length of Y dimension ( focal_length_y = focal_length_x * aspect_ratio )
        """
        self._xys = list_of_lines
        self._focal_length_x = focal_length_x
        self._focal_length_y = focal_length_y
        if distortion_center_guess is not None:
            assert len(distortion_center_guess)==2
        self._distortion_center_guess = distortion_center_guess

    def get_default_p0(self,distortion_model=None):
        """create initial estimate of parameter vector"""
        # K13 and K23 may be None in dict, thus default value in config.get() won't work.
        assert isinstance(distortion_model,distortion.CaltechNonlinearDistortionModel)

        x0 = distortion_model.cc1
        y0 = distortion_model.cc2
        r1 = distortion_model.k1 # 1st radial term
        r2 = distortion_model.k1 # 2st radial term

        params = [x0, y0, r1, r2]

        for orig_xys in self._xys:
            line_params = self._fit_line( orig_xys )
            params.extend( line_params )

        return np.array(params,dtype=np.float64)

    def get_distortion_model_for_params(self,params):
        x0, y0, r1, r2 = params[:4]
        distortion_model = distortion.CaltechNonlinearDistortionModel( fc1=self._focal_length_x,
                                                                       fc2=self._focal_length_y,
                                                                       cc1=x0,
                                                                       cc2=y0,
                                                                       k1=r1,
                                                                       k2=r2,
                                                                       )
        return distortion_model

    def lm_err_func(self, params):
        results = self.lm_err4(params)
        if self._distortion_center_guess is not None:
            # add penalty for straying too far from center
            x0_guess, y0_guess = self._distortion_center_guess

            alpha = 1.0 # penalty coefficient

            distortion_model = self.get_distortion_model_for_params( params )
            x0 = distortion_model.cc1
            y0 = distortion_model.cc2
            dist2 = np.sqrt((x0-x0_guess)**2 + (y0-y0_guess)**2)
            results = list(results) + [alpha*dist2]
        return results

    def sumsq_err(self, params):
        results = self.lm_err4(params)
        results = np.sum( results**2 )
        return results

    def lm_err4(self, params):
        """

        This was implemented after 'Line-Based Correction of Radial
        Lens Distortion' (GMIP 1997) by Prescott and McLean.

        Also, as decribed in 'Correcting Radial Distortion by Circle
        Fitting' (BMVC 2005) by Rickard Strand and Eric Hayman, this
        algorithm seems to more-or-less called 'DF' (after F. Devernay
        and O.D. Faugeras. Straight lines have to be straight. MVA,
        2001). (I have not read the DF paper, however.)

        Note that the Strand and Hayman paper (see above) suggests
        what might be a better way to estimate radial distortion and
        gives test on synthetic data regarding the performance of
        various algorithms.

        Finally, 'A new algorithm to correct fish-eye and strong
        wide-angle lens-distortion from single images' (2001) by
        Brauer-Burchardt, C.; Voss, K 10.1109/ICIP.2001.958994 gives
        an algorithm that seems very similar to Strand and Hayman.

        """
        distortion_model = self.get_distortion_model_for_params( params )

        results = []
        for i,orig_xys in enumerate(self._xys):
            # each set of xys should form a line after undistortion
            new_xys = np.array([distortion_model.undistort( ox, oy ) for (ox,oy) in orig_xys])
            line_params = params[4+i*2:4+(i+1)*2]
            d = self._get_dist_from_line( line_params, new_xys )
            results.extend( list(d) )
        results = np.array(results)
        return results

    def _get_dist_from_line( self, line_params, xys ):
        theta, dist = line_params
        # point coordinates
        x0 = xys[:,0]
        y0 = xys[:,1]

        return (x0*np.cos( theta ) + y0*np.sin( theta ) - dist)

    def _fit_line( self, xys ):
        #XXX TODO: directly fit line rather than this crazy NL leastsq operation

        def residuals( line_params, xys ):
            d = self._get_dist_from_line( line_params, xys )
            return d

        p0 = np.ones((2,))
        pfinal, ier = scipy.optimize.leastsq( residuals, p0,
                                              args=( xys, ),
                                              )
        if ier not in (1,2,3,4):
            raise RuntimeError('could not fit line')
        theta, dist = pfinal

        return theta, dist

def test():
    model = distortion.CaltechNonlinearDistortionModel(cc1=321,
                                                       cc2=242,
                                                       k1=0.9)
    distorted_lines = []

    # a couple sample points
    slopes = [0.2, 1.3]
    y_offsets = [2.1, -200]

    for slope,y_offset in zip(slopes,y_offsets):
        # calculate undistorted coordinates
        x = np.linspace(-300,300,10)
        y = slope*x + y_offset

        # now distort them
        dx, dy = model.distort(x,y)
        print 'dx'
        print dx
        print 'dy'
        print dy
        xys = np.hstack( (dx[:,np.newaxis], dy[:,np.newaxis]) )
        print 'xys'
        print xys
        print
        distorted_lines.append(  xys )

    obj = Objective(distorted_lines,
                    distortion_center_guess=(320,240),
                    )
    p0 = obj.get_default_p0(model)
    initial_err = obj.sumsq_err(p0)
    print 'initial_err',initial_err
    pfinal, cov_x, infodict, mesg, ier = scipy.optimize.minpack.leastsq(
        obj.lm_err_func,
        np.array(p0,copy=True), # workaround bug (scipy ticket 637)
        epsfcn=1e-6,
        ftol=1e-5,
        xtol=1e-5,
        maxfev=int(1e6),
        full_output=True,
        )
    final_err=obj.sumsq_err( pfinal )
    print 'final_err',final_err

    model = obj.get_distortion_model_for_params(pfinal)
    print 'model.fc1, model.fc2, model.cc1, model.cc2, model.k1, model.k2'
    print model.fc1, model.fc2, model.cc1, model.cc2, model.k1, model.k2

if __name__=='__main__':
    test()
