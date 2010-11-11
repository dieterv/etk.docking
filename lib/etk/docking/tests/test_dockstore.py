# vim:sw=4:et:ai
import unittest
import gtk
from etk.docking import DockLayout, DockFrame, DockPaned, DockGroup, DockItem
from etk.docking.dockstore import serialize, deserialize, get_main_frames, finish


class ItemFactory(object):

    def __call__(self, label):
        return gtk.Button(label)

class LoadingTestCase(unittest.TestCase):

    def test_serialize(self):
        win = gtk.Window(gtk.WINDOW_TOPLEVEL)
        layout = DockLayout()
        frame = DockFrame()
        win.add(frame)
        layout.add(frame)
        paned = DockPaned()
        frame.add(paned)
        group = DockGroup()
        paned.add(group)
        item = DockItem('icon', 't', 'xx')
        item.set_name('fillme')
        group.add(item)

        s = serialize(layout)
        assert '<layout><dockframe height="1" width="1">'\
        '<dockpaned orientation="horizontal">'\
        '<dockgroup expand="true" weight="100">'\
        '<dockitem icon="icon" title="t" tooltip="xx" />'\
        '</dockgroup></dockpaned></dockframe></layout>' == s, s


    def test_deserialize(self):
        xml = '''
        <layout>
          <dockframe height="120" width="200">
            <dockpaned orientation="horizontal">
              <dockgroup expand="true" weight="100">
                <dockitem icon="icon" title="t" tooltip="xx">
                  <widget name="fillme" />
                </dockitem>
              </dockgroup>
            </dockpaned>
          </dockframe>
        </layout>
        '''

        layout = deserialize(xml, ItemFactory())
        assert 1, len(layout.frames)
        frame = iter(layout.frames).next()
        assert frame.child
        paned = frame.child
        assert paned.get_n_items()
        group = paned.get_nth_item(0)
        assert isinstance(group, DockGroup), group
        assert group.get_n_items()
        item = group.get_nth_item(0)
        assert isinstance(item, DockItem)
        button = item.child
        assert isinstance(button, gtk.Button)
        assert "fillme" == button.get_label(), button.get_label()
        win = gtk.Window(gtk.WINDOW_TOPLEVEL)
        win.add(frame)
        win.show()
        while gtk.events_pending():
            gtk.main_iteration()

        #assert frame.allocation.width == 200, frame.allocation.width
        #assert frame.allocation.height == 120, frame.allocation.height

    def test_deserialize_floating_windows(self):
        xml = """
        <layout>
          <dockframe height="100" width="492">
            <dockpaned orientation="horizontal">
              <dockgroup expand="true" weight="45">
                <dockitem icon="file-manager" title="New 3" tooltip="Hi!"/>
              </dockgroup>
              <dockgroup expand="true" weight="55">
                <dockitem icon="web-browser" title="New 1" tooltip="browser"/>
                <dockitem icon="web-browser" title="New 4" tooltip="browser"/>
              </dockgroup>
            </dockpaned>
          </dockframe>
          <dockframe floating="true" x="12" y="23" height="100" width="330">
            <dockgroup>
              <dockitem icon="style" title="New 2" tooltip="abc"/>
            </dockgroup>
          </dockframe>
        </layout>
        """

        layout = deserialize(xml, ItemFactory())
        assert layout
        assert len(layout.frames) == 2, layout.frames
        frames = list(get_main_frames(layout))
        assert len(frames) == 1, frames
        win = gtk.Window()
        win.add(frames[0])
        finish(layout, frames[0])


        main_frames = list(layout.get_main_frames())
        floating_frames = list(layout.get_floating_frames())
        assert len(main_frames) == 1
        assert len(floating_frames) == 1

        assert floating_frames[0].get_toplevel().get_transient_for() is win

        self.assertEquals(0.45, main_frames[0].get_children()[0]._items[0].weight_request)

        win.show_all()

        self.assertEquals(0.45, main_frames[0].get_children()[0]._items[0].weight)



