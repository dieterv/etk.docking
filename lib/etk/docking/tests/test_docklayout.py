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


class TestDockLayoutDnD(unittest.TestCase):
    def setUp(self):
        def drag_get_data(self, context, target, timestamp):
            self.emit('drag-data-received', self, context, 0, 0, None, None, timestamp)

        DockGroup.drag_get_data = drag_get_data
        DockPaned.drag_get_data = drag_get_data
        DockFrame.drag_get_data = drag_get_data

    def tearDown(self):
        del DockGroup.drag_get_data
        del DockPaned.drag_get_data
        del DockFrame.drag_get_data

    def test_drag_drop_on_group(self):
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

        win.set_default_size(200, 200)
        win.show_all()


        group.emit('drag-motion', None, 130, 130, 0)

        assert layout._drag_data
        assert layout._drag_data.drop_widget is group

    def test_drag_drop_on_paned(self):
        win = gtk.Window(gtk.WINDOW_TOPLEVEL)
        frame = DockFrame()
        paned = DockPaned()
        groups = (DockGroup(), DockGroup())
        item = DockItem()

        layout = DockLayout()

        layout.add(frame)

        win.add(frame)
        frame.add(paned)
        paned.add(groups[0])
        paned.add(groups[1])
        groups[0].add(item)

        win.set_default_size(200, 200)
        win.show_all()


        paned.emit('drag-motion', None, 10, 10, 0)

        assert layout._drag_data
        assert layout._drag_data.drop_widget is paned
