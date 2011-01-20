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

"""
Configuration settings for elements in a Etk.Docking configuration.

The configuration can be set for every element in the hierarchy. By default the class
name can be used.
"""


import gtk


class DockSettings(object):
    '''
    Container for group specific settings.
    The following settings can be set:

    * auto_remove: group is removed if if empty.
    * can_float: Group can be a floating group.
    * expand: A group can expand/shrink on resize.
    * inherit_settings: new groups constructed from items dragged from a group should
    get the same group name.
    '''
    __slots__ = [ 'auto_remove',
                  'can_float',
                  'float_retain_size',
                  'expand',
                  'inherit_settings' ]

    def __init__(self, auto_remove=True, can_float=True,
                 float_retain_size=False, expand=True, inherit_settings=True):
        self.auto_remove = auto_remove
        self.can_float = can_float
        self.float_retain_size = float_retain_size
        self.expand = expand
        self.inherit_settings = inherit_settings


class DockSettingsDict(object):
    '''
    Settings container. Adheres partly to the dict protocol, only get() and setitem are
    supported.

    Settings can deal with widget names as well as widgets itself (in which case the
    name is requested). By overriding ``widget_name()`` it is possible to customize
    the behaviour for settings.
    '''

    def __init__(self):
        self._settings = {} # Map group-id -> layout settings

    def get(self, target):
        return self[target]

    def widget_name(self, target):
        if isinstance(target, gtk.Widget):
            return target.get_name()
        return str(target)

    def __getitem__(self, target):
        target = self.widget_name(target)
        settings = self._settings.get(target)
        if not settings:
            settings = self._settings[target] = DockSettings()
        return settings

    def __setitem__(self, target, settings):
        self._settings[self.widget_name(target)] = settings


settings = DockSettingsDict()
