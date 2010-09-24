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

from etk.docking import DockPaned, DockGroup


class TestDockPaned(unittest.TestCase):
    ############################################################################
    # Test properties
    ############################################################################
    def test_prop_handle_size(self):
        global notify_called

        def _on_notify(gobject, pspec):
            global notify_called
            notify_called = True

        dockpaned = DockPaned()
        dockpaned.connect('notify::handle-size', _on_notify)

        notify_called = False
        dockpaned.set_handle_size(1)
        self.assertEquals(dockpaned.get_handle_size(), 1,
                          msg='get_handle_size method did not return expected value')
        self.assertTrue(notify_called,
                        msg='handle-size property change notification failed when using set_handle_size method')

        notify_called = False
        dockpaned.set_property('handle-size', 2)
        self.assertEquals(dockpaned.get_property('handle-size'), 2,
                          msg='get_property method did not return expected value')
        self.assertTrue(notify_called,
                        msg='handle-size property change notification failed when using set_property method')

        notify_called = False
        dockpaned.props.handle_size = 3
        self.assertEquals(dockpaned.props.handle_size, 3,
                          msg='.props attribute did not return expected value')
        self.assertTrue(notify_called,
                        msg='handle-size property change notification failed when using .props attribute')

        dockpaned.destroy()

    def test_prop_orientation(self):
        global notify_called

        def _on_notify(gobject, pspec):
            global notify_called
            notify_called = True

        dockpaned = DockPaned()
        dockpaned.connect('notify::orientation', _on_notify)

        notify_called = False
        dockpaned.set_orientation(gtk.ORIENTATION_VERTICAL)
        self.assertEquals(dockpaned.get_orientation(), gtk.ORIENTATION_VERTICAL,
                          msg='get_orientation method did not return expected value')
        self.assertTrue(notify_called,
                        msg='orientation property change notification failed when using set_orientation method')

        notify_called = False
        dockpaned.set_property('orientation', gtk.ORIENTATION_HORIZONTAL)
        self.assertEquals(dockpaned.get_property('orientation'), gtk.ORIENTATION_HORIZONTAL,
                          msg='get_property method did not return expected value')
        self.assertTrue(notify_called,
                        msg='orientation property change notification failed when using set_property method')

        notify_called = False
        dockpaned.props.orientation = gtk.ORIENTATION_VERTICAL
        self.assertEquals(dockpaned.props.orientation, gtk.ORIENTATION_VERTICAL,
                          msg='.props attribute did not return expected value')
        self.assertTrue(notify_called,
                        msg='orientation property change notification failed when using .props attribute')

        dockpaned.destroy()

    ############################################################################
    # Test child properties
    ############################################################################
    def test_child_prop_expand(self):
        global child_notify_called

        def _on_child_notify(gobject, pspec):
            global child_notify_called
            child_notify_called = True

        dockpaned = DockPaned()
        dockgroup = DockGroup()
        dockgroup.connect('child-notify::expand', _on_child_notify)
        dockpaned.add(dockgroup)

        child_notify_called = False
        dockpaned.child_set_property(dockgroup, 'expand', True)
        self.assertTrue(child_notify_called,
                        msg='expand child property change notification failed')

        dockgroup.destroy()
        dockpaned.destroy()

    ############################################################################
    # Test child/parent interaction
    ############################################################################
    def test_child_destroy(self):
        paned = DockPaned()
        group = DockGroup()
        paned.add(group)

        assert paned.get_n_items() == len(paned._items) == 1

        group.destroy()

        assert paned.get_n_items() == len(paned._items) == 0

    ############################################################################
    # Test public api
    ############################################################################
    def test_insert_item(self):
        events = []

        def add_handler(self, widget):
            print 'added widget', widget
            events.append(widget)

        dockpaned = DockPaned()
        dockpaned.connect('add', add_handler)

        dg1 = DockGroup()
        dockpaned.add(dg1)

        assert dg1 in events, events

        dg2 = DockGroup()
        dockpaned.insert_item(dg2)

        assert dg2 in events, events

    def test_reorder_item(self):
        dockgroup1 = DockGroup()
        dockgroup2 = DockGroup()
        dockgroup3 = DockGroup()
        dockpaned = DockPaned()
        dockpaned.add(dockgroup1)
        dockpaned.add(dockgroup2)
        dockpaned.add(dockgroup3)
        dockpaned.reorder_item(dockgroup3, 0)
        dockpaned.reorder_item(dockgroup1, 2)

        self.assertTrue(dockpaned.item_num(dockgroup1) == 2)
        self.assertTrue(dockpaned.item_num(dockgroup2) == 1)
        self.assertTrue(dockpaned.item_num(dockgroup3) == 0)

        dockgroup1.destroy()
        dockgroup2.destroy()
        dockgroup3.destroy()
        dockpaned.destroy()
