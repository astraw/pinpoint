"""interactive GUI app for exploring non-linear distortion of images"""
from threading import Thread
from enthought.pyface.api import SplitApplicationWindow, GUI

from enthought.traits.api import HasTraits, Float, Instance, String, File, Button, Array
import enthought.traits.api as traits
from enthought.traits.ui.api import View, Item, Group

from enthought.pyface.api import Widget
from enthought.pyface.expandable_panel import ExpandablePanel

from mplwidget import MPLWidget

import scipy
import sys
import wx

from distortion import NonlinearDistortionParameters, CaltechNonlinearDistortionParameters

class RightSidePanel(HasTraits):
    # right or bottom panel depending on direction of split
    button = Button # add new filename
    distortion_instance = Instance(NonlinearDistortionParameters)

    traits_view = View( 'button',
                        'distortion_instance')

class DistortionWorkThread(Thread):
    def run(self):
        im,ll,ur = self.distortion_instance.remove_distortion(self.image_data)

        self.mplwidget.axes.images=[]
        self.mplwidget.axes.imshow(im,
                                   origin='lower',
                                   extent=(ll[0],ur[0],ll[1],ur[1]),
                                   aspect='equal')
        GUI.invoke_later(self.mplwidget.figure.canvas.draw)

class DistortedImageWidget(Widget):
    distortion_instance = Instance(NonlinearDistortionParameters)
    param_holder = Instance(RightSidePanel)
    list_of_lines = traits.List
    mplwidget = Instance(MPLWidget)
    distorted_image = Array
    processing_job = Instance(DistortionWorkThread)

    def __init__(self, parent, distorted_image, distortion_instance, **kwargs):
        self.distorted_image = distorted_image
        self.distortion_instance = distortion_instance
        super(DistortedImageWidget,self).__init__(**kwargs)
        self.control = self._create_control(parent)
        self.distortion_instance.on_trait_change(self._show_undistorted_image)
        self._show_undistorted_image()

    def _create_control(self, parent):
        """ Create the toolkit-specific control that represents the widget. """
        # The panel lets us add additional controls.
        self._panel = wx.Panel(parent, -1, style=wx.CLIP_CHILDREN)
        self.mplwidget = MPLWidget(self._panel)
        return self._panel

    def _show_undistorted_image(self):
        if self.distortion_instance is None:
            return
        try:
            if self.processing_job.isAlive():
                # previous call still running too slow
                return
        except AttributeError:
            pass
        self.processing_job = DistortionWorkThread()
        self.processing_job.mplwidget = self.mplwidget
        self.processing_job.distortion_instance = self.distortion_instance
        self.processing_job.image_data = self.distorted_image
        self.processing_job.start()

FIX1 = False

class MainWindow(SplitApplicationWindow):
    """ The main window, here go the instructions to create and destroy
        the application.
    """
    _expandable = Instance(ExpandablePanel) # FIX1 = False
    #_expandable = Instance(wx.Panel) # FIX1 = True

    rspanel = Instance(RightSidePanel)
    ratio = Float(0.8)
    title = 'pinpoint - camera distortion GUI'
    dis = traits.List

    direction = String('horizontal')

    def __init__(self,*args,**kwargs):
        super(MainWindow,self).__init__(*args,**kwargs)
        self.dis = []

    def on_add_filename(self, filename):
        image_data = scipy.misc.pilutil.imread(filename)
        h,w = image_data.shape[:2]
        cc1 = w/2.0
        cc2 = h/2.0

        if self.rspanel.distortion_instance is None:
            # the first time an image is loaded, the parameters are initialized
            self.rspanel.distortion_instance = CaltechNonlinearDistortionParameters(cc1=cc1,cc2=cc2)

        parent = self._expandable.control
        if FIX1:
            parent_sizer = parent.GetSizer()
            panel = wx.Panel(parent, -1, style=wx.CLIP_CHILDREN)
            parent_sizer.Add(panel, 1, wx.EXPAND)
            parent_sizer.Layout()
            parent = panel
        di = DistortedImageWidget(parent,
                                  distorted_image=image_data,
                                  distortion_instance=self.rspanel.distortion_instance,
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
