# vim:sw=4:et:ai
import unittest
import gtk
from etk.docking import DockLayout, DockFrame, DockPaned, DockGroup, DockItem
from etk.docking.dockstore import serialize

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
    '<dockpaned height="1" orientation="horizontal" width="1">'\
    '<dockgroup height="1" width="1">'\
    '<dockitem icon-name="icon" name="fillme" title="t" title-tooltip-text="xx" />'\
    '</dockgroup></dockpaned></dockframe></layout>' == s, s
