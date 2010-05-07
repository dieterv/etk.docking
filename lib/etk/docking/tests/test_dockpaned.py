# -*- coding: utf-8 -*-
#
# Copyright © 2010 Dieter Verfaillie <dieterv@optionexplicit.be>
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

from etk.docking import DockPaned


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
    # Test public api
    ############################################################################
