# vim:sw=4:et:ai
import unittest
import gtk
from etk.docking import DockLayout, DockFrame, DockPaned, DockGroup, DockItem
from etk.docking.dockstore import serialize, deserialize

def test_serialize():
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
    '<dockgroup>'\
    '<dockitem icon="icon" name="fillme" title="t" tooltip="xx" />'\
    '</dockgroup></dockpaned></dockframe></layout>' == s, s

class ItemFactory(object):

    def __call__(self, label):
        return gtk.Button(label)

def test_deserialize():

    xml = '<layout><dockframe height="120" width="200">'\
    '<dockpaned orientation="horizontal">'\
    '<dockgroup>'\
    '<dockitem icon="icon" name="fillme" title="t" tooltip="xx" />'\
    '</dockgroup></dockpaned></dockframe></layout>'

    layout = deserialize(xml, ItemFactory())
    assert 1, len(layout.frames)
    frame = iter(layout.frames).next()
    assert frame.child
    paned = frame.child
    assert paned.items
    group = paned.items[0].child
    assert isinstance(group, DockGroup), group
    assert group.items, group.items
    item = group.items[0]
    assert isinstance(item, DockItem)
    button = item.children()[0]
    assert isinstance(button, gtk.Button)
    assert "fillme" == button.get_label()
    win = gtk.Window(gtk.WINDOW_TOPLEVEL)
    win.add(frame)
    win.show()
    assert frame.allocation.width == 200, frame.allocation.width
    assert frame.allocation.height == 120

