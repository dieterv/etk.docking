# -*- coding: utf-8 -*-
# vim:sw=4:et:ai

# Copyright © 2010 etk.docking Contributors
#
# This file is part of etk.docking.
#
# etk.docking is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# etk.docking is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with etk.docking. If not, see <http://www.gnu.org/licenses/>.


import unittest

import gtk
from etk.docking import DockLayout, DockFrame, DockPaned, DockGroup, DockItem
from etk.docking.dockgroup import DockGroup, DRAG_TARGET_ITEM_LIST
from etk.docking.dnd import DockDragContext

class TestDockLayout(unittest.TestCase):

    def test_construction(self):
        win = gtk.Window(gtk.WINDOW_TOPLEVEL)
        frame = DockFrame()
        paned = DockPaned()
        group = DockGroup()
        item = DockItem()

        win.add(frame)
        frame.add(paned)
        paned.add(group)
        group.add(item)

        layout = DockLayout()

        layout.add(frame)

        assert frame in layout.frames
        print layout._signal_handlers
        self.assertEquals(4, len(layout._signal_handlers))
        self.assertEquals(8, len(layout._signal_handlers[frame]))

        layout.remove(frame)

        assert not layout._signal_handlers, layout._signal_handlers
        assert frame not in layout.frames

    def test_construction_after_setting_layout(self):
        win = gtk.Window(gtk.WINDOW_TOPLEVEL)
        frame = DockFrame()
        paned = DockPaned()
        group = DockGroup()
        item = DockItem()

        layout = DockLayout()

        layout.add(frame)

        win.add(frame)
        frame.add(paned)
        paned.add(group)
        group.add(item)

        assert frame in layout.frames
        self.assertEquals(4, len(layout._signal_handlers))
        self.assertEquals(8, len(layout._signal_handlers[frame]))

        paned.remove(group)

        self.assertEquals(2, len(layout._signal_handlers), layout._signal_handlers)
        assert frame in layout._signal_handlers.keys(), layout._signal_handlers
        assert paned in layout._signal_handlers.keys(), layout._signal_handlers
        assert group not in layout._signal_handlers.keys(), layout._signal_handlers
        assert item not in layout._signal_handlers.keys(), layout._signal_handlers
        assert frame in layout.frames



class StubContext(object):
    def __init__(self, source_widget, tabs):
        self.targets = [ DRAG_TARGET_ITEM_LIST[0] ]
        self.source_widget = source_widget
        # Set up dragcontext (nornally done in motion_notify event)
        if tabs:
            self.source_widget.dragcontext = dragcontext = DockDragContext()
            dragcontext.dragged_object = tabs

    def get_source_widget(self):
        return self.source_widget

    def finish(self, success, delete, timestamp):
        self.finished = (success, delete)

class StubSelectionData(object):
    def set(self, atom, bytes, data):
        print 'StubSelectionData.set(%s, %s, %s)' % (atom, bytes, data)


class TestDockLayoutDnD(unittest.TestCase):

    def setUp(self):

        self.layout = DockLayout()

        def drag_get_data(widget, context, target, timestamp):
            selection_data = StubSelectionData()
            context.source_widget.do_drag_data_get(context, selection_data, None, timestamp)
            self.layout.on_widget_drag_data_received(widget, context, 20, 20, selection_data, None, timestamp)

        DockGroup.drag_get_data = drag_get_data
        DockPaned.drag_get_data = drag_get_data
        DockFrame.drag_get_data = drag_get_data

    def tearDown(self):
        del self.layout
        del DockGroup.drag_get_data
        del DockPaned.drag_get_data
        del DockFrame.drag_get_data

    def test_drag_drop_on_group(self):
        win = gtk.Window(gtk.WINDOW_TOPLEVEL)
        frame = DockFrame()
        paned = DockPaned()
        group = DockGroup()
        item = DockItem()

        layout = self.layout

        layout.add(frame)

        win.add(frame)
        frame.add(paned)
        paned.add(group)
        group.add(item)

        win.set_default_size(200, 200)
        win.show_all()

        while gtk.events_pending():
            gtk.main_iteration()

        x, y = 30, 30
        context = StubContext(group, [group.tabs[0]])
        layout.on_widget_drag_motion(group, context, x, y, 0)

        assert layout._drag_data
        assert layout._drag_data.drop_widget is group

        layout.on_widget_drag_drop(group, context, x, y, 0)

    def test_drag_drop_on_paned(self):
        win = gtk.Window(gtk.WINDOW_TOPLEVEL)
        frame = DockFrame()
        paned = DockPaned()
        groups = (DockGroup(), DockGroup())
        item = DockItem()

        layout = self.layout

        layout.add(frame)

        win.add(frame)
        frame.add(paned)
        map(paned.add, groups)
        groups[0].add(item)

        win.set_default_size(200, 200)
        win.show_all()


        x, y = 10, 10
        context = StubContext(groups[0], [groups[0].tabs[0]])
        layout.on_widget_drag_motion(paned, context, x, y, 0)

        assert layout._drag_data
        assert layout._drag_data.drop_widget is paned

    def test_remove_empty_groups_recursively(self):
        win = gtk.Window(gtk.WINDOW_TOPLEVEL)
        frame = DockFrame()
        paneds = (DockPaned(), DockPaned(), DockPaned())
        group = DockGroup()
        item = DockItem()

        layout = self.layout

        layout.add(frame)

        win.add(frame)
        frame.add(paneds[0])
        paneds[0].add(paneds[1])
        paneds[1].add(paneds[2])
        paneds[2].add(group)

        win.set_default_size(200, 200)
        win.show_all()

        layout.on_widget_drag_end(group, None) # omit Context

        # TODO: check is paned[0]
        assert not paneds[0].get_parent()
