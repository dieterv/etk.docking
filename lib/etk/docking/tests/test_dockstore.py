# vim:sw=4:et:ai
import unittest
from gi.repository import Gtk
from etk.docking import DockLayout, DockFrame, DockPaned, DockGroup, DockItem
from etk.docking.dockstore import serialize, deserialize, get_main_frames, finish


class ItemFactory(object):

    def __call__(self, label):
        return Gtk.Button(label)

class LoadingTestCase(unittest.TestCase):

    def test_serialize(self):
        win = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        layout = DockLayout()
        frame = DockFrame()
        win.add(frame)
        layout.add(frame)
        paned = DockPaned()
        frame.add(paned)
        group = DockGroup()
        paned.add(group)
        item = DockItem(title='t', title_tooltip_text='xx', icon_name='icon', stock_id="")
        item.set_name('fillme')
        group.add(item)

        s = serialize(layout)
        assert '<layout><dockframe height="1" width="1">'\
        '<dockpaned orientation="horizontal">'\
        '<dockgroup weight="100">'\
        '<dockitem icon_name="icon" title="t" tooltip="xx" />'\
        '</dockgroup></dockpaned></dockframe></layout>' == s, s

    def test_deserialize(self):
        xml = '''
        <layout>
          <dockframe height="120" width="200">
            <dockpaned orientation="horizontal">
              <dockgroup weight="100">
                <dockitem title="t" tooltip="xx" icon_name="icon" stock_id="">
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
        assert frame.get_child()
        paned = frame.get_child()
        assert len(paned)
        group = paned.get_nth_item(0)
        assert isinstance(group, DockGroup), group
        assert len(group)
        item = group.get_nth_item(0)
        assert isinstance(item, DockItem)
        button = item.get_child()
        assert isinstance(button, Gtk.Button)
        assert "fillme" == button.get_label(), button.get_label()
        win = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        win.add(frame)
        win.show()
        while Gtk.events_pending():
            Gtk.main_iteration()

        #assert frame.allocation.width == 200, frame.allocation.width
        #assert frame.allocation.height == 120, frame.allocation.height

    def test_deserialize_floating_windows(self):
        xml = """
        <layout>
          <dockframe height="100" width="492">
            <dockpaned orientation="horizontal">
              <dockgroup weight="45">
                <dockitem title="New 3" tooltip="Hi!" icon_name="file-manager" stock_id=""/>
              </dockgroup>
              <dockgroup weight="55">
                <dockitem title="New 1" tooltip="browser" icon_name="web-browser" stock_id=""/>
                <dockitem title="New 4" tooltip="browser" icon_name="web-browser" stock_id=""/>
              </dockgroup>
            </dockpaned>
          </dockframe>
          <dockframe floating="true" x="12" y="23" height="100" width="330">
            <dockgroup>
              <dockitem title="New 2" tooltip="abc" icon_name="style" stock_id=""/>
            </dockgroup>
          </dockframe>
        </layout>
        """

        layout = deserialize(xml, ItemFactory())
        assert layout
        assert len(layout.frames) == 2, layout.frames
        frames = list(get_main_frames(layout))
        assert len(frames) == 1, frames
        win = Gtk.Window()
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



