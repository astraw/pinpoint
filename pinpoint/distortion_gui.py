"""interactive GUI app for exploring non-linear distortion of images"""
from threading import Thread
from enthought.pyface.api import SplitApplicationWindow, GUI

from enthought.traits.api import HasTraits, Float, Instance, String, File, \
     Button, Array
import enthought.traits.api as traits
from enthought.traits.ui.api import View, Item, Group, Spring

from enthought.pyface.api import Widget
from enthought.pyface.expandable_panel import ExpandablePanel

from mplwidget import MPLWidget
import matplotlib.cm as cm

import numpy as np
import scipy
import sys
from optparse import OptionParser
import wx

from distortion import NonlinearDistortionModel, CaltechNonlinearDistortionModel
import distortion_estimate

def draw_lines_on_ax(ax,lines,func=None,display_transform=None):
    ax.lines=[] # remove old line(s) that may already be plotted

    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    for line in lines:
        if not len(line):
            continue
        tmp = np.array( line )
        x = tmp[:,0]
        y = tmp[:,1]
        if func is not None:
            ux,uy = func(x,y)
        else:
            ux,uy = x,y
        if display_transform in ['rotate 90','rotate 270']:
            ux,uy=uy,ux
        ax.plot(ux,uy,'bx-')
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)

class RightSidePanel(HasTraits):
    # right or bottom panel depending on direction of split
#    add_image_file = Button()
    automatically_estimate_distortion = Button()
    nonlinear_distortion_model = Instance(NonlinearDistortionModel)
    distorted_image_widgets = traits.Trait([],list)

    ## def _add_image_file_changed ( self ):
    ##     # need to figure out how to open a dialog with traits to ask for filename

    def _automatically_estimate_distortion_changed ( self ):
        print 'estimating'
        # gather lines
        all_lines = []
        heightwidth = None
        for diw in self.distorted_image_widgets:
            all_lines.extend( diw.list_of_lines )
            if heightwidth is None:
                heightwidth = diw.distorted_image.shape[:2]
            else:
                assert np.allclose(heightwidth, diw.distorted_image.shape[:2])
        all_lines = [np.array(xys) for xys in all_lines if len(xys) ] # numpify
        h,w = heightwidth
        obj = distortion_estimate.Objective(all_lines,
                                            distortion_center_guess=(w/2.,h/2.),
                                            # fixme: give menu option
                                            # fixme: allow non-unity aspect
                                            #        ratio (focal length x !=
                                            #               focal length y)
                                            )

        p0 = obj.get_default_p0(self.nonlinear_distortion_model)
        initial_err = obj.sumsq_err(p0)
        print 'initial_err',initial_err
        print 'estimating... please wait'
        pfinal, cov_x, infodict, mesg, ier = scipy.optimize.minpack.leastsq(
            obj.lm_err_func,
            np.array(p0,copy=True), # workaround bug (scipy ticket 637)
            #epsfcn=options.epsfcn,
            #ftol=options.tol,
            #xtol=options.tol,
            maxfev=int(1e6),
            full_output=True,
            )
        final_err=obj.sumsq_err( pfinal )
        print 'final_err',final_err
        model = obj.get_distortion_model_for_params(pfinal)
        self.nonlinear_distortion_model = model

    traits_view = View( Group(#Item(name='add_image_file',),
                              Item(name='automatically_estimate_distortion',),
                              Item(name='nonlinear_distortion_model'),
                              label='control',
                              show_border=True,
                              show_labels=False,
                              orientation = 'horizontal',
                              ),
                        )

class DisplayWorkThread(Thread):
    def run(self):
        if ((not hasattr(self,'nonlinear_distortion_model')) or
            (self.nonlinear_distortion_model is None)):
            do_undistortion = False
        else:
            do_undistortion = True

        if do_undistortion:
            im,ll,ur = self.nonlinear_distortion_model.remove_distortion(
                self.image_data)
        else:
            im = self.image_data
            ll = 0,0
            ur = im.shape[:2][::-1]-np.array([1,1])

        ax = self.mplwidget.axes
        ax.images=[]
        ax.lines=[]
        kwargs = {}

        if self.display_transform == 'flip y':
            display_im = im
            kwargs['origin']='lower'
            kwargs['extent']=(ll[0],ur[0],ll[1],ur[1])
        elif self.display_transform == 'identity':
            display_im = im
            kwargs['extent']=(ll[0],ur[0],ur[1],ll[1])
        elif self.display_transform == 'rotate 180':
            display_im = np.rot90(np.rot90(im))
            kwargs['extent']=(ur[0],ll[0],ll[1],ur[1])#(ll[0],ur[0],ur[1],ll[1])
        elif self.display_transform == 'rotate 90':
            display_im = np.rot90(im)
            kwargs['extent']=(ll[1],ur[1],ll[0],ur[0])
        elif self.display_transform == 'rotate 270':
            display_im = np.rot90(np.rot90(np.rot90(im)))
            kwargs['extent']=(ur[1],ll[1],ur[0],ll[0])
        else:
            raise ValueError("unknown transform '%s'"%self.display_transform)

        ax.imshow(display_im,
                  aspect='equal',
                  cmap=cm.pink,
                  **kwargs)

        if hasattr(self,'lines'):
            if do_undistortion:
                func = self.nonlinear_distortion_model.undistort
            else:
                func = None
            draw_lines_on_ax(ax,self.lines,func=func,
                             display_transform=self.display_transform)

        GUI.invoke_later(self.mplwidget.figure.canvas.draw)

class DistortedImageWidget(Widget):
    parent_w_model = Instance(RightSidePanel)
    list_of_lines = traits.Trait([],list)
    # fixme: need to allow user to change the display_transform within
    # the GUI.
    display_transform = traits.Trait('identity','flip y','rotate 90',
                                     'rotate 180', 'rotate 270')

    distorted_mplwidget   = Instance(MPLWidget) # original image
    undistorted_mplwidget = Instance(MPLWidget) # the undistorted version

    distorted_image = Array
    distortion_display_thread   = Instance(DisplayWorkThread)
    undistortion_display_thread = Instance(DisplayWorkThread)
    current_line = traits.Trait([],list)

    def __init__(self, parent, distorted_image,
                 parent_w_model, **kwargs):
        self.distorted_image = distorted_image
        self.parent_w_model = parent_w_model
        super(DistortedImageWidget,self).__init__(**kwargs)
        self.control = self._create_control(parent)
        self.parent_w_model.on_trait_change(
            self._register_model, name='nonlinear_distortion_model')
        self._register_model()

        self._show_distorted_image()
        self._show_undistorted_image()

        self.current_line = [] # create new line
        self.list_of_lines.append( self.current_line ) # keep it

    def _register_model(self):
        self.parent_w_model.nonlinear_distortion_model.on_trait_change(
            self._show_undistorted_image)
        self._show_undistorted_image()

    def _create_control(self, parent):
        """ Create the toolkit-specific control that represents the widget. """
        # The panel lets us add additional controls.
        self._panel = wx.Panel(parent, -1, style=wx.CLIP_CHILDREN)
        if 1:
            sizer = wx.BoxSizer(wx.HORIZONTAL)
            self._panel.SetSizer(sizer)

            distorted_panel = wx.Panel(self._panel, -1, style=wx.CLIP_CHILDREN)
            sizer.Add( distorted_panel, 1, wx.EXPAND)

            undistorted_panel = wx.Panel(self._panel, -1,
                                         style=wx.CLIP_CHILDREN)
            sizer.Add( undistorted_panel, 1, wx.EXPAND)
            sizer.Layout()

            self.distorted_mplwidget = MPLWidget(distorted_panel,
                                           on_key_press=self.on_mpl_key_press)
            self.distorted_mplwidget.axes.set_title('original, distorted image')

            self.undistorted_mplwidget = MPLWidget(undistorted_panel)
            self.undistorted_mplwidget.axes.set_title('undistorted image')
        else:
            # only 1 mpl widget - the undistorted image
            self.undistorted_mplwidget = MPLWidget(self._panel,
                                            on_key_press=self.on_mpl_key_press)
        return self._panel

    def _list_of_lines_changed(self):
        # Note: this doesn't get called on append() or other list operations
        print 'self.list_of_lines','-'*20
        for line in self.list_of_lines:
            print '  + line '
            for xy_tuple in line:
                print '  |   (%.1f, %.1f)'%xy_tuple
        print

    def _current_line_changed(self):
        # Note: this doesn't get called on append() or other list operations
        print 'current line','-'*20
        line = self.current_line
        if 1:
            print '  + line '
            for xy_tuple in line:
                print '  |   (%.1f, %.1f)'%xy_tuple
        print


    def _update_lines(self):
        ax = self.distorted_mplwidget.axes
        if 1:
            draw_lines_on_ax(ax,self.list_of_lines,
                             display_transform=self.display_transform)

            self.distorted_mplwidget.figure.canvas.draw()

            if 1:
                # draw undistorted version
                ax = self.undistorted_mplwidget.axes
                draw_lines_on_ax(ax,self.list_of_lines,
                                 func=self.parent_w_model.nonlinear_distortion_model.undistort,
                                 display_transform=self.display_transform)

                self.undistorted_mplwidget.figure.canvas.draw()

    def on_mpl_key_press(self,event):
        if event.key=='p':
            # The plot is in undistorted coordinates given the current
            # distortion model. But we need to save the distorted
            # coordinates so that we can undistort according to
            # whichever distortion model we choose.

            ax = event.inaxes  # the axes instance
            ## # distorted coordinates
            dx, dy = event.xdata,event.ydata
            print 'dx, dy',dx, dy
            if self.display_transform in ['rotate 90','rotate 270']:
                # flip coordinate axes
                dx,dy = dy, dx
            self.current_line.append( (dx,dy) )
            self._update_lines()

        elif event.key=='n':
            # new line
            self.current_line = [] # create a new one
            self.list_of_lines.append( self.current_line ) # keep it
            self._update_lines()

        elif event.key=='c':
            # clear all lines
            del self.list_of_lines[:]
            del self.current_line[:]

            self.current_line = [] # create a new one
            self.list_of_lines.append( self.current_line ) # keep it
            self._update_lines()

        self._list_of_lines_changed()

    def _show_undistorted_image(self):
        try:
            if self.undistortion_display_thread.isAlive():
                # previous call still running. too slow.
                return
        except AttributeError:
            pass
        self.undistortion_display_thread = DisplayWorkThread()
        self.undistortion_display_thread.display_transform = self.display_transform
        self.undistortion_display_thread.lines = self.list_of_lines
        self.undistortion_display_thread.mplwidget = self.undistorted_mplwidget
        self.undistortion_display_thread.nonlinear_distortion_model = \
                                         self.parent_w_model.nonlinear_distortion_model
        self.undistortion_display_thread.image_data = self.distorted_image
        self.undistortion_display_thread.start()

    def _show_distorted_image(self):
        try:
            if self.distortion_display_thread.isAlive():
                # previous call still running. too slow.
                return
        except AttributeError:
            pass
        self.distortion_display_thread = DisplayWorkThread()
        self.distortion_display_thread.display_transform = self.display_transform
        self.distortion_display_thread.mplwidget = self.distorted_mplwidget
        self.distortion_display_thread.image_data = self.distorted_image
        self.distortion_display_thread.start()

FIX1 = False

class MainWindow(SplitApplicationWindow):
    """ The main window, here go the instructions to create and destroy
        the application.
    """
    _expandable = Instance(ExpandablePanel) # FIX1 = False
    #_expandable = Instance(wx.Panel) # FIX1 = True

    rspanel = Instance(RightSidePanel)
    ratio = Float(1.0)
    title = 'pinpoint - camera distortion GUI'
    #dis = traits.Trait([],list)

    direction = String('horizontal')

    def __init__(self,*args,**kwargs):
        super(MainWindow,self).__init__(*args,**kwargs)
        #self.dis = []

    def add_filename(self, filename):
        image_data = scipy.misc.pilutil.imread(filename)
        h,w = image_data.shape[:2]
        cc1 = w/2.0
        cc2 = h/2.0

        if self.rspanel.nonlinear_distortion_model is None:
            # the first time an image is loaded, the parameters are initialized
            self.rspanel.nonlinear_distortion_model = \
                 CaltechNonlinearDistortionModel(cc1=cc1,cc2=cc2)

        parent = self._expandable.control
        if FIX1:
            parent_sizer = parent.GetSizer()
            panel = wx.Panel(parent, -1, style=wx.CLIP_CHILDREN)
            sizer = wx.BoxSizer(wx.HORIZONTAL)
            panel.SetSizer(sizer)
            panel.SetBackgroundColour((255,0,0)) # set bg color as debug tool
            parent_sizer.Add(panel, 1, wx.EXPAND)
            parent_sizer.Layout()
            parent = panel
        di = DistortedImageWidget(
            parent,
            distorted_image=image_data,
            parent_w_model=self.rspanel,
            )
        self.rspanel.distorted_image_widgets.append(di)
        if FIX1:
            pass
        else:
            self._expandable.add_panel(filename, di.control)
            #self._expandable.show_layer(filename) # this is mentioned in expandable_panel.py source, but doesn't exist

    def _create_lhs(self, parent):
        if FIX1:
            self._expandable = panel = wx.Panel(parent, -1,
                                                style=wx.CLIP_CHILDREN)
            self._expandable.control = panel
            sizer = wx.BoxSizer(wx.VERTICAL)
            panel.SetSizer(sizer)
            panel.SetBackgroundColour((0,255,0))  # set bg color as debug tool
        else:
            self._expandable = ExpandablePanel(parent)

        return self._expandable.control

    def _create_rhs(self, parent):
        self.rspanel = RightSidePanel()
        return self.rspanel.edit_traits(parent = parent,
                                        kind="subpanel").control

    def _on_close(self, event):
        self.close()

def main():
    usage = '%prog IMAGE_FILE [IMAGE_FILE] [...]'
    parser = OptionParser(usage)
    (options, args) = parser.parse_args()

    if len(args)<1:
        # Currently at least one IMAGE_FILE is required because the
        # add_image button is broken.
        parser.print_help()
        return

    gui = GUI()
    window = MainWindow()

    window.size = (700, 400)
    window.open()

    for filename in args:
        window.add_filename( filename )

    gui.start_event_loop()

if __name__ == '__main__':
    main()
