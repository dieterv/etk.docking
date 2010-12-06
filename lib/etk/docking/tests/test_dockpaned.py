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
import gtk.gdk as gdk

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
    def test_child_prop_weight(self):
        global child_notify_called

        def _on_child_notify(gobject, pspec):
            global child_notify_called
            child_notify_called = True

        dockpaned = DockPaned()
        dockgroup = DockGroup()
        dockgroup.connect('child-notify::weight', _on_child_notify)
        dockpaned.add(dockgroup)

        child_notify_called = False
        dockpaned.child_set_property(dockgroup, 'weight', 0.3)
        self.assertTrue(child_notify_called,
                        msg='weight child property change notification failed')

        dockgroup.destroy()
        dockpaned.destroy()

    ############################################################################
    # Test signals
    ############################################################################
    def test_add_signal(self):
        add_events = []

        def on_add(self, widget):
            add_events.append(widget)

        dockgroup = DockGroup()
        dockpaned = DockPaned()
        dockpaned.connect('add', on_add)
        dockpaned.add(dockgroup)

        self.assertTrue(dockgroup in add_events)

        dockgroup.destroy()
        dockpaned.destroy()

    def test_remove_signal(self):
        remove_events = []
        item_removed_events = []

        def on_remove(self, widget):
            remove_events.append(widget)

        def on_item_removed(dockpaned, child):
            item_removed_events.append(child)

        dockgroup = DockGroup()
        dockpaned = DockPaned()
        dockpaned.connect('remove', on_remove)
        dockpaned.connect('item-removed', on_item_removed)
        dockpaned.add(dockgroup)
        dockpaned.remove(dockgroup)

        self.assertTrue(dockgroup in remove_events)
        self.assertTrue(dockgroup in item_removed_events)

        dockgroup.destroy()
        dockpaned.destroy()

    def test_item_added_signal(self):
        add_events = []
        item_added_events = []

        def on_add(self, widget):
            add_events.append(widget)

        def on_item_added(dockpaned, child):
            item_added_events.append(child)

        dockgroup1 = DockGroup()
        dockgroup2 = DockGroup()
        dockpaned = DockPaned()
        dockpaned.connect('add', on_add)
        dockpaned.connect('item-added', on_item_added)
        dockpaned.add(dockgroup1)
        dockpaned.insert_item(dockgroup2)

        self.assertTrue(dockgroup1 in item_added_events)
        self.assertTrue(dockgroup1 in add_events)
        self.assertTrue(dockgroup2 in item_added_events)
        self.assertFalse(dockgroup2 in add_events)

        dockgroup2.destroy()
        dockgroup1.destroy()
        dockpaned.destroy()

    def test_item_removed_signal(self):
        remove_events = []
        item_removed_events = []

        def on_remove(self, widget):
            remove_events.append(widget)

        def on_item_removed(dockpaned, child):
            item_removed_events.append(child)

        dockgroup1 = DockGroup()
        dockgroup2 = DockGroup()
        dockpaned = DockPaned()
        dockpaned.connect('remove', on_remove)
        dockpaned.connect('item-removed', on_item_removed)
        dockpaned.add(dockgroup1)
        dockpaned.add(dockgroup2)
        dockpaned.remove(dockgroup1)
        dockpaned.remove_item(0)

        self.assertTrue(dockgroup1 in item_removed_events)
        self.assertTrue(dockgroup1 in remove_events)
        self.assertTrue(dockgroup2 in item_removed_events)
        self.assertFalse(dockgroup2 in remove_events)

        dockgroup1.destroy()
        dockgroup2.destroy()
        dockpaned.destroy()

    ############################################################################
    # Test protected api
    ############################################################################

    def test_redistribute_weight(self):
        dockpaned = DockPaned()
        dockgroup1 = DockGroup()
        dockgroup2 = DockGroup()

        dockpaned.insert_item(dockgroup1)
        dockpaned._items[0].min_size = 20

        self.assertEquals(1, len(dockpaned._items))
        self.assertEquals(1.0, dockpaned._items[0].weight)
        self.assertEquals(None, dockpaned._items[0].weight_request)

        dockpaned._redistribute_weight(100)

        self.assertEquals(1.0, dockpaned._items[0].weight)
        self.assertEquals(None, dockpaned._items[0].weight_request)

        dockpaned.insert_item(dockgroup2, weight=0.5)
        dockpaned._items[1].min_size = 20

        self.assertTrue(0.5, dockpaned._items[1].weight_request)

        dockpaned._redistribute_weight(100)

        self.assertAlmostEquals(0.5, dockpaned._items[0].weight, 4)
        self.assertAlmostEquals(0.5, dockpaned._items[1].weight, 4)

    def test_redistribute_weight_resize(self):
        dockpaned = DockPaned()
        dockgroup1 = DockGroup()
        dockgroup2 = DockGroup()

        dockpaned.insert_item(dockgroup1, weight=0.5)
        dockpaned._items[0].min_size = 20

        self.assertEquals(1, len(dockpaned._items))
        self.assertEquals(None, dockpaned._items[0].weight)
        self.assertEquals(0.5, dockpaned._items[0].weight_request)

        dockpaned._redistribute_weight(100)

        self.assertEquals(1.0, dockpaned._items[0].weight)
        self.assertEquals(None, dockpaned._items[0].weight_request)

        dockpaned.insert_item(dockgroup2, weight=0.5)
        dockpaned._items[1].min_size = 20

        self.assertTrue(0.5, dockpaned._items[1].weight_request)

        dockpaned._redistribute_weight(100)

        self.assertAlmostEquals(0.5, dockpaned._items[0].weight, 4)
        self.assertAlmostEquals(0.5, dockpaned._items[1].weight, 4)


    ############################################################################
    # Test public api
    ############################################################################
    def test_add(self):
        dockgroup = DockGroup()
        dockpaned = DockPaned()
        dockpaned.add(dockgroup)

        self.assertTrue(dockgroup in dockpaned)

        dockgroup.destroy()
        dockpaned.destroy()

    def test_remove(self):
        dockgroup = DockGroup()
        dockpaned = DockPaned()
        dockpaned.add(dockgroup)
        dockpaned.remove(dockgroup)

        self.assertTrue(dockgroup not in dockpaned)

        dockgroup.destroy()
        dockpaned.destroy()

    def test_delitem(self):
        dg = DockGroup()
        dockpaned = DockPaned()
        dockpaned.add(DockGroup())
        dockpaned.add(dg)
        dockpaned.add(DockGroup())
        
        assert dg in dockpaned
        assert len(dockpaned) == 3
        assert dg is dockpaned[1]
        del dockpaned[1]
        assert len(dockpaned) == 2
        assert dg not in dockpaned

        dg.destroy()
        dockpaned.destroy()

    def test_append_item(self):
        dockgroup1 = DockGroup()
        dockgroup2 = DockGroup()
        dockpaned = DockPaned()
        item_num1 = dockpaned.append_item(dockgroup1)
        item_num2 = dockpaned.append_item(dockgroup2)

        self.assertTrue(item_num1 == 0)
        self.assertTrue(dockpaned.get_nth_item(0) is dockgroup1)
        self.assertTrue(item_num2 == 1)
        self.assertTrue(dockpaned.get_nth_item(1) is dockgroup2)

        dockgroup2.destroy()
        dockgroup1.destroy()
        dockpaned.destroy()

    def test_prepend_item(self):
        dockgroup1 = DockGroup()
        dockgroup2 = DockGroup()
        dockpaned = DockPaned()
        item_num1 = dockpaned.prepend_item(dockgroup1)
        self.assertTrue(item_num1 == 0)
        item_num2 = dockpaned.prepend_item(dockgroup2)
        self.assertTrue(item_num2 == 0)

        self.assertTrue(dockpaned.get_nth_item(0) is dockgroup2)
        self.assertTrue(dockpaned.get_nth_item(1) is dockgroup1)

        dockgroup2.destroy()
        dockgroup1.destroy()
        dockpaned.destroy()

    def test_insert_item(self):
        dockgroup1 = DockGroup()
        dockgroup2 = DockGroup()
        dockgroup3 = DockGroup()
        dockpaned = DockPaned()
        item_num1 = dockpaned.insert_item(dockgroup1, position=None)
        self.assertTrue(item_num1 == 0)
        item_num2 = dockpaned.insert_item(dockgroup2, position=-1)
        self.assertTrue(item_num2 == 1)
        item_num3 = dockpaned.insert_item(dockgroup3, position=1, weight=0.5)
        self.assertTrue(item_num3 == 1)

        self.assertTrue(dockpaned.get_nth_item(0) is dockgroup1)
        self.assertTrue(dockpaned.get_nth_item(1) is dockgroup3)
        self.assertTrue(dockpaned.get_nth_item(2) is dockgroup2)

        dockgroup3.destroy()
        dockgroup2.destroy()
        dockgroup1.destroy()
        dockpaned.destroy()

    def test_remove_item(self):
        dockgroup1 = DockGroup()
        dockgroup2 = DockGroup()
        dockgroup3 = DockGroup()
        dockpaned = DockPaned()
        dockpaned.add(dockgroup1)
        dockpaned.add(dockgroup2)
        dockpaned.add(dockgroup3)
        dockpaned.remove_item(None)
        dockpaned.remove_item(0)
        dockpaned.remove_item(-1)

        self.assertTrue(dockgroup1 not in dockpaned)
        self.assertTrue(dockgroup2 not in dockpaned)

        dockgroup2.destroy()
        dockgroup1.destroy()
        dockpaned.destroy()

    def test_item_num(self):
        dockgroup1 = DockGroup()
        dockgroup2 = DockGroup()
        dockpaned = DockPaned()
        dockpaned.add(dockgroup1)
        dockpaned.add(dockgroup2)

        self.assertTrue(dockpaned.item_num(dockgroup1) == 0)
        self.assertTrue(dockpaned.item_num(dockgroup2) == 1)

        dockgroup2.destroy()
        dockgroup1.destroy()
        dockpaned.destroy()

    def test_len(self):
        dockgroup1 = DockGroup()
        dockgroup2 = DockGroup()
        dockpaned = DockPaned()
        dockpaned.add(dockgroup1)
        dockpaned.add(dockgroup2)

        self.assertTrue(len(dockpaned) == 2)

        dockgroup2.destroy()
        dockgroup1.destroy()
        dockpaned.destroy()

    def test_get_n_handles(self):
        dockgroup1 = DockGroup()
        dockgroup2 = DockGroup()
        dockpaned = DockPaned()
        dockpaned.add(dockgroup1)
        dockpaned.add(dockgroup2)

        self.assertTrue(dockpaned._get_n_handles() == 1)

        dockgroup2.destroy()
        dockgroup1.destroy()
        dockpaned.destroy()

    def test_get_nth_item(self):
        dockgroup1 = DockGroup()
        dockgroup2 = DockGroup()
        dockpaned = DockPaned()
        dockpaned.add(dockgroup1)
        dockpaned.add(dockgroup2)

        self.assertTrue(dockpaned.get_nth_item(0) == dockgroup1)
        self.assertTrue(dockpaned.get_nth_item(1) == dockgroup2)

        dockgroup2.destroy()
        dockgroup1.destroy()
        dockpaned.destroy()

    def test_get_item_at_pos(self):
        dockgroup1 = DockGroup()
        dockgroup2 = DockGroup()
        dockpaned = DockPaned()
        dockpaned.add(dockgroup1)
        dockpaned.add(dockgroup2)
        window = gtk.Window()
        window.add(dockpaned)
        window.show_all()

        child1 = dockpaned.get_item_at_pos(dockgroup1.allocation.x + 1,
                                           dockgroup1.allocation.y + 1)

        child2 = dockpaned.get_item_at_pos(dockgroup2.allocation.x + 1,
                                           dockgroup2.allocation.y + 1)

        self.assertTrue(child1 is dockgroup1)
        self.assertTrue(child2 is dockgroup2)

        dockgroup2.destroy()
        dockgroup1.destroy()
        dockpaned.destroy()
        window.destroy()

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

        dockgroup3.destroy()
        dockgroup2.destroy()
        dockgroup1.destroy()
        dockpaned.destroy()

    ############################################################################
    # Test parent/child interaction
    ############################################################################
    def test_child_destroy(self):
        dockgroup = DockGroup()
        dockpaned = DockPaned()
        dockpaned.add(dockgroup)

        self.assertTrue(len(dockpaned) == len(dockpaned._items) == 1)

        dockgroup.destroy()

        self.assertTrue(len(dockpaned) == len(dockpaned._items) == 0)

        dockgroup.destroy()
        dockpaned.destroy()
