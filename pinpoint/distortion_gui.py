"""interactive GUI app for exploring non-linear distortion of images"""
from threading import Thread
from enthought.pyface.api import SplitApplicationWindow, GUI

from enthought.traits.api import HasTraits, Float, Instance, String, File, Button, Array
import enthought.traits.api as traits
from enthought.traits.ui.api import View, Item, Group, Spring

from enthought.pyface.api import Widget
from enthought.pyface.expandable_panel import ExpandablePanel

from mplwidget import MPLWidget

import numpy as np
import scipy
import sys
import wx

from distortion import NonlinearDistortionParameters, CaltechNonlinearDistortionParameters

class RightSidePanel(HasTraits):
    # right or bottom panel depending on direction of split
    add_image_file = Button()#
    automatically_estimate_distortion = Button()
    nonlinear_distortion_parameters = Instance(NonlinearDistortionParameters)

    traits_view = View( Group(Item(name='add_image_file',),
                              Item(name='automatically_estimate_distortion',),
                              Item(name='nonlinear_distortion_parameters'),
                              label='control',
                              show_border=True,
                              show_labels=False,
                              orientation = 'horizontal',
                              ),
                        )

class DisplayWorkThread(Thread):
    def run(self):
        if ((not hasattr(self,'nonlinear_distortion_parameters')) or
            (self.nonlinear_distortion_parameters is None)):
            do_undistortion = False
        else:
            do_undistortion = True

        if do_undistortion:
            im,ll,ur = self.nonlinear_distortion_parameters.remove_distortion(self.image_data)
        else:
            im = self.image_data
            ll = 0,0
            ur = im.shape[:2][::-1]-np.array([1,1])

        ax = self.mplwidget.axes
        ax.images=[]
        ax.lines=[]
        ax.imshow(im,
                  origin='lower',
                  extent=(ll[0],ur[0],ll[1],ur[1]),
                  aspect='equal')
        if hasattr(self,'lines'):
            for line in self.lines:
                if not len(line):
                    # empty line
                    continue
                line = np.array(line)
                x = line[:,0]
                y = line[:,1]
                if do_undistortion:
                    x,y = self.nonlinear_distortion_parameters.undistort(x,y)
                ax.plot(x,y,'x-')
        GUI.invoke_later(self.mplwidget.figure.canvas.draw)

class DistortedImageWidget(Widget):
    nonlinear_distortion_parameters = Instance(NonlinearDistortionParameters)
    param_holder = Instance(RightSidePanel)
    list_of_lines = traits.Trait([],list)

    distorted_mplwidget   = Instance(MPLWidget) # original image
    undistorted_mplwidget = Instance(MPLWidget) # the undistorted version

    distorted_image = Array
    distortion_display_thread   = Instance(DisplayWorkThread)
    undistortion_display_thread = Instance(DisplayWorkThread)
    current_line = traits.Trait([],list)

    def __init__(self, parent, distorted_image, nonlinear_distortion_parameters, **kwargs):
        self.distorted_image = distorted_image
        self.nonlinear_distortion_parameters = nonlinear_distortion_parameters
        super(DistortedImageWidget,self).__init__(**kwargs)
        self.control = self._create_control(parent)
        self.nonlinear_distortion_parameters.on_trait_change(self._show_undistorted_image)

        self._show_distorted_image()
        self._show_undistorted_image()

        self.current_line = [] # create new line
        self.list_of_lines.append( self.current_line ) # keep it

    def _create_control(self, parent):
        """ Create the toolkit-specific control that represents the widget. """
        # The panel lets us add additional controls.
        self._panel = wx.Panel(parent, -1, style=wx.CLIP_CHILDREN)
        if 1:
            sizer = wx.BoxSizer(wx.HORIZONTAL)
            self._panel.SetSizer(sizer)

            distorted_panel = wx.Panel(self._panel, -1, style=wx.CLIP_CHILDREN)
            sizer.Add( distorted_panel, 1, wx.EXPAND)

            undistorted_panel = wx.Panel(self._panel, -1, style=wx.CLIP_CHILDREN)
            sizer.Add( undistorted_panel, 1, wx.EXPAND)
            sizer.Layout()

            self.distorted_mplwidget = MPLWidget(distorted_panel,on_key_press=self.on_mpl_key_press)
            self.distorted_mplwidget.axes.set_title('original, distorted image')

            self.undistorted_mplwidget = MPLWidget(undistorted_panel)
            self.undistorted_mplwidget.axes.set_title('undistorted image')
        else:
            # only 1 mpl widget - the undistorted image
            self.undistorted_mplwidget = MPLWidget(self._panel,on_key_press=self.on_mpl_key_press)
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
            self.current_line.append( (dx,dy) )

            xlim = ax.get_xlim().copy()
            ylim = ax.get_ylim().copy()
            ax.lines=[] # remove old line(s) that may already be plotted

            # plot all lines
            for line in self.list_of_lines:
                if not len(line):
                    continue
                tmp = np.array( self.current_line )
                x = tmp[:,0]
                y = tmp[:,1]
                ax.plot(x,y,'bx-')
            ax.set_xlim(xlim)
            ax.set_ylim(ylim)
            self.distorted_mplwidget.figure.canvas.draw()

            if 1:
                # draw undistorted version
                ax = self.undistorted_mplwidget.axes
                ax.lines=[] # remove old line(s) that may already be plotted

                xlim = ax.get_xlim().copy()
                ylim = ax.get_ylim().copy()
                for line in self.list_of_lines:
                    if not len(line):
                        continue
                    tmp = np.array( self.current_line )
                    x = tmp[:,0]
                    y = tmp[:,1]
                    ux,uy = self.nonlinear_distortion_parameters.undistort(x,y)
                    ax.plot(ux,uy,'bx-')
                ax.set_xlim(xlim)
                ax.set_ylim(ylim)
                self.undistorted_mplwidget.figure.canvas.draw()

        elif event.key=='n':
            self.current_line = [] # create a new one
            self.list_of_lines.append( self.current_line ) # keep it
        elif event.key=='c':
            # clear all
            del self.list_of_lines[:]
            del self.current_line[:]
        self._list_of_lines_changed()

    def _show_undistorted_image(self):
        try:
            if self.undistortion_display_thread.isAlive():
                # previous call still running. too slow.
                return
        except AttributeError:
            pass
        self.undistortion_display_thread = DisplayWorkThread()
        self.undistortion_display_thread.lines = self.list_of_lines
        self.undistortion_display_thread.mplwidget = self.undistorted_mplwidget
        self.undistortion_display_thread.nonlinear_distortion_parameters = self.nonlinear_distortion_parameters
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
    dis = traits.Trait([],list)

    direction = String('horizontal')

    def __init__(self,*args,**kwargs):
        super(MainWindow,self).__init__(*args,**kwargs)
        self.dis = []

    def on_add_filename(self, filename):
        image_data = scipy.misc.pilutil.imread(filename)
        h,w = image_data.shape[:2]
        cc1 = w/2.0
        cc2 = h/2.0

        if self.rspanel.nonlinear_distortion_parameters is None:
            # the first time an image is loaded, the parameters are initialized
            self.rspanel.nonlinear_distortion_parameters = CaltechNonlinearDistortionParameters(cc1=cc1,cc2=cc2)

        parent = self._expandable.control
        if FIX1:
            parent_sizer = parent.GetSizer()
            panel = wx.Panel(parent, -1, style=wx.CLIP_CHILDREN)
            parent_sizer.Add(panel, 1, wx.EXPAND)
            parent_sizer.Layout()
            parent = panel
        di = DistortedImageWidget(parent,
                                  distorted_image=image_data,
                                  nonlinear_distortion_parameters=self.rspanel.nonlinear_distortion_parameters,
                                  )
        self.dis.append( di )
        if FIX1:
            pass
        else:
            self._expandable.add_panel(filename, di.control)
            #self._expandable.show_layer(filename) # this is mentioned in expandable_panel.py source, but doesn't exist

    def _create_lhs(self, parent):

        if FIX1:
            self._expandable = panel = wx.Panel(parent, -1, style=wx.CLIP_CHILDREN)
            self._expandable.control = panel
            sizer = wx.BoxSizer(wx.VERTICAL)
            panel.SetSizer(sizer)
        else:
            self._expandable = ExpandablePanel(parent)

        return self._expandable.control

    def _create_rhs(self, parent):
        self.rspanel = RightSidePanel()
        return self.rspanel.edit_traits(parent = parent, kind="subpanel").control

    def _on_close(self, event):
        self.close()

if __name__ == '__main__':

    gui = GUI()
    window = MainWindow()

    window.size = (700, 400)
    window.open()

    if 1:
        filenames = sys.argv[1:]
        for filename in filenames:
            window.on_add_filename( filename )

    gui.start_event_loop()
