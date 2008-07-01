from threading import Thread
from enthought.pyface.api import SplitApplicationWindow, GUI
from enthought.traits.api import HasTraits, Float, Instance, String
from enthought.traits.ui.api import View, Item, Group
from mplwidget import MPLWidget
import scipy
import sys

from distortion import NonlinearDistortionParameters, CaltechNonlinearDistortionParameters

class DistortionThread(Thread):
    def run(self):
        im,ll,ur = self.distortion_instance.remove_distortion(self.image_data)

        self.mplwidget.axes.images=[]
        self.mplwidget.axes.imshow(im,
                                   origin='lower',
                                   extent=(ll[0],ur[0],ll[1],ur[1]),
                                   aspect='equal')
        GUI.invoke_later(self.mplwidget.figure.canvas.draw)

class NonlinearDistortionControlPanel(HasTraits):
    params = Instance(NonlinearDistortionParameters)
    mplwidget = Instance(MPLWidget)
    filename = String()
    traits_view = View(Group(Item('filename'),
                             Item('params')))

    def __init__(self,*args,**kw):
        super(NonlinearDistortionControlPanel,self).__init__(*args,**kw)
        self.params.on_trait_change(self._show_undistorted_image)

    def _filename_fired(self, event ):
        self.image_data = scipy.misc.pilutil.imread(self.filename)
        h,w = self.image_data.shape[:2]
        cc1 = w/2.0
        cc2 = h/2.0
        self.params = CaltechNonlinearDistortionParameters(cc1=cc1,cc2=cc2)
        self._show_undistorted_image()

    def _show_undistorted_image(self):
        if self.params is None:
            return
        try:
            if self.processing_job.isAlive():
                self.display("Processing too slow")
                return
        except AttributeError:
            pass
        self.processing_job = DistortionThread()
        self.processing_job.mplwidget = self.mplwidget
        self.processing_job.distortion_instance = self.params
        self.processing_job.image_data = self.image_data
        self.processing_job.start()

class MainWindow(SplitApplicationWindow):
    """ The main window, here go the instructions to create and destroy
        the application.
    """
    mplwidget = Instance(MPLWidget)
    panel = Instance(NonlinearDistortionControlPanel)
    ratio = Float(0.7)
    filename = String()
    title = 'pinpoint - camera distortion GUI'

    def _create_lhs(self, parent):
        self.mplwidget = MPLWidget(parent)
        return self.mplwidget.control

    def _create_rhs(self, parent):
        self.panel = NonlinearDistortionControlPanel(mplwidget=self.mplwidget,
                                                     filename=self.filename)
        return self.panel.edit_traits(parent = parent, kind="subpanel").control

    def _on_close(self, event):
        self.close()

if __name__ == '__main__':
    filename = sys.argv[1]

    gui = GUI()
    window = MainWindow(filename=filename)
    window.size = (700, 400)
    window.open()

    gui.start_event_loop()
