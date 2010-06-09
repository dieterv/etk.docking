# -*- coding: utf-8 -*-
# vim:sw=4:et:ai
#
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


class TestDockGroup(unittest.TestCase):

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
        self.assertEquals(4, len(layout._signal_handlers))
        self.assertEquals(2, len(layout._signal_handlers[frame]))

        layout.remove(frame)

        assert not layout._signal_handlers, layout._signal_handlers
        assert frame not in layout.frames


