#emacs, this is -*-Python-*- mode
def make_CaltechDistortion(*args,**kw):
    return CaltechDistortion(*args,**kw)

cdef class CaltechDistortion:
    cdef readonly double fc1, fc2, cc1, cc2
    cdef readonly double k1, k2, p1, p2
    cdef readonly double alpha_c

    def __init__(self, fc1, fc2, cc1, cc2, k1, k2, p1, p2, alpha_c=0 ):
        """create instance of CaltechDistortion

        CaltechDistortion(fc1, fc2, cc1, cc2, k1, k2, p1, p2 )
        where:
        fc - focal length
        cc - camera center
        k - radial distortion parameters (non-linear)
        p - tangential distortion parameters (non-linear)
        alpha_c - skew between X and Y pixel axes
        """
        self.fc1 = fc1
        self.fc2 = fc2
        self.cc1 = cc1
        self.cc2 = cc2
        self.k1 = k1
        self.k2 = k2
        self.p1 = p1
        self.p2 = p2
        self.alpha_c = alpha_c

    def __reduce__(self):
        """this allows CaltechDistortion to be pickled"""
        args = (self.fc1, self.fc2, self.cc1, self.cc2,
                self.k1, self.k2, self.p1, self.p2, self.alpha_c)
        return (make_CaltechDistortion, args)

    def undistort(self, double x_kk, double y_kk):
        """undistort 2D coordinate pair

        Iteratively performs an undistortion using camera intrinsic
        parameters.

        Implementation translated from CalTechCal.

        See also the OpenCV reference manual, which has the equation
        used.
        """

        cdef double xl, yl

        cdef double xd, yd, x, y
        cdef double r_2, k_radial, delta_x, delta_y
        cdef int i

        # undoradial.m / CalTechCal/normalize.m

        xd = ( x_kk - self.cc1 ) / self.fc1
        yd = ( y_kk - self.cc2 ) / self.fc2

        xd = xd - self.alpha_c * yd

        # comp_distortion_oulu.m

        # initial guess
        x = xd
        y = yd

        for i from 0<=i<20:
            r_2 = x*x + y*y
            k_radial = 1.0 + (self.k1) * r_2 + (self.k2) * r_2*r_2
            delta_x = 2.0 * (self.p1)*x*y + (self.p2)*(r_2 + 2.0*x*x)
            delta_y = (self.p1) * (r_2 + 2.0*y*y)+2.0*(self.p2)*x*y
            x = (xd-delta_x)/k_radial
            y = (yd-delta_y)/k_radial

        # undoradial.m

        xl = (self.fc1)*x + (self.fc1*self.alpha_c)*y + (self.cc1)
        yl = (self.fc2)*y + (self.cc2)
        return (xl, yl)

    def distort(self, double xl, double yl):
        """distort 2D coordinate pair"""

        cdef double x, y, r_2, term1, xd, yd

        x = ( xl - self.cc1 ) / self.fc1
        y = ( yl - self.cc2 ) / self.fc2

        r_2 = x*x + y*y
        r_4 = r_2**2
        term1 = self.k1*r_2 + self.k2*r_4

        # OpenCV manual (chaper 6, "3D reconstruction", "camera
        # calibration" section) seems to disagree with
        # http://www.vision.caltech.edu/bouguetj/calib_doc/htmls/parameters.html

        # Furthermore, implementations in cvundistort.cpp seem still
        # unrelated.  Finally, project_points2.m in Bouguet's code is
        # consistent with his webpage and this below.

        xd = x + x*term1 + (2*self.p1*x*y + self.p2*(r_2+2*x**2))
        yd = y + y*term1 + (self.p1*(r_2+2*y**2) + 2*self.p2*x*y)

        xd = (self.fc1)*xd + (self.cc1)
        yd = (self.fc2)*yd + (self.cc2)

        return (xd, yd)
