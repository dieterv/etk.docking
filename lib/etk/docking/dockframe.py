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


from __future__ import absolute_import
from logging import getLogger

from gi.repository import GObject, Gtk, Gdk, cairo


class DockFrame(Gtk.Bin):
    '''
    The etk.DockFrame widget is a Gtk.Bin that acts as the toplevel widget
    for a dock layout hierarchy.
    '''
    __gtype_name__ = 'EtkDockFrame'

    def __init__(self):
        GObject.GObject.__init__(self)

        # Initialize logging
        self.log = getLogger('%s.%s' % (self.__gtype_name__, hex(id(self))))

        # Internal housekeeping
        self._placeholder = None

    ############################################################################
    # GtkWidget
    ############################################################################
    def do_size_request(self, requisition):
        requisition.width = 0
        requisition.height = 0

        if self.get_child() and self.get_child().is_visible():
            (requisition.width, requisition.height) = self.get_child().size_request()
            requisition.width += self.props.border_width * 2
            requisition.height += self.props.border_width * 2

    def do_size_allocate(self, allocation):
        self.set_allocation(allocation)

        if self.get_child() and self.get_child().is_visible():
            child_allocation = cairo.RectangleInt()
            child_allocation.x = allocation.x + self.props.border_width
            child_allocation.y = allocation.y + self.props.border_width
            child_allocation.width = allocation.width - (2 * self.props.border_width)
            child_allocation.height = allocation.height - (2 * self.props.border_width)
            self.get_child().size_allocate(child_allocation)

    ############################################################################
    # EtkDockFrame
    ############################################################################
    def set_placeholder(self, placeholder):
        """
        Set a new placeholder widget on the frame. The placeholder is drawn on top
        of the dock items.

        If a new placeholder is set, an existing placeholder is destroyed.
        """
        if self._placeholder:
            self._placeholder.unparent()
            self._placeholder.destroy()
            self._placeholder = None

        if placeholder:
            self._placeholder = placeholder
            self._placeholder.set_parent(self)
