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

import gtk
import gtk.gdk as gdk


class DockFrame(gtk.Bin):
    '''
    The etk.DockFrame widget is a gtk.Bin that acts as the toplevel widget
    for a dock layout hierarchy.
    '''
    __gtype_name__ = 'EtkDockFrame'

    def __init__(self):
        gtk.Bin.__init__(self)

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

        if self.child and self.child.flags() & gtk.VISIBLE:
            (requisition.width, requisition.height) = self.child.size_request()
            requisition.width += self.border_width * 2
            requisition.height += self.border_width * 2

    def do_size_allocate(self, allocation):
        self.allocation = allocation

        if self.child and self.child.flags() & gtk.VISIBLE:
            child_allocation = gdk.Rectangle()
            child_allocation.x = allocation.x + self.border_width
            child_allocation.y = allocation.y + self.border_width
            child_allocation.width = allocation.width - (2 * self.border_width)
            child_allocation.height = allocation.height - (2 * self.border_width)
            self.child.size_allocate(child_allocation)

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
