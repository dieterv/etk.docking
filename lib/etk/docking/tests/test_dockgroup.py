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

from etk.docking import DockGroup


class TestDockGroup(unittest.TestCase):
    def test_prop_group_id(self):
        global notify_called

        def _on_notify(gobject, pspec):
            global notify_called
            notify_called = True

        dockgroup = DockGroup()
        dockgroup.connect('notify::group-id', _on_notify)

        notify_called = False
        dockgroup.set_group_id(1)
        self.assertEquals(dockgroup.get_group_id(), 1,
                          msg='get_group_id method did not return expected value')
        self.assertTrue(notify_called,
                        msg='group-id property change notification failed when using set_group_id method')

        notify_called = False
        dockgroup.set_property('group-id', 2)
        self.assertEquals(dockgroup.get_property('group-id'), 2,
                          msg='get_property method did not return expected value')
        self.assertTrue(notify_called,
                        msg='group-id property change notification failed when using set_property method')

        notify_called = False
        dockgroup.props.group_id = 3
        self.assertEquals(dockgroup.props.group_id, 3,
                          msg='.props attribute did not return expected value')
        self.assertTrue(notify_called,
                        msg='group-id property change notification failed when using .props attribute')
