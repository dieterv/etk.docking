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
from gtk import gdk


class DockFrame(gtk.Container):
    """
    Top level widget for a dock layout hierarchy.
    """
    __gtype_name__ = 'EtkDockFrame'

    def __init__(self):
        gtk.Container.__init__(self)

        # Initialize logging
        self.log = getLogger('%s.%s' % (self.__gtype_name__, hex(id(self))))
        self.log.debug('')
        self.child = None
        self.placeholder = None

    ############################################################################
    # GtkWidget
    ############################################################################
    def do_realize(self):
        self.log.debug('')

        # Internal housekeeping
        self.set_flags(self.flags() | gtk.REALIZED)
        self.window = gdk.Window(self.get_parent_window(),
                                 x = self.allocation.x,
                                 y = self.allocation.y,
                                 width = self.allocation.width,
                                 height = self.allocation.height,
                                 window_type = gdk.WINDOW_CHILD,
                                 wclass = gdk.INPUT_OUTPUT,
                                 event_mask = (gdk.EXPOSURE_MASK |
                                               gdk.POINTER_MOTION_MASK |
                                               gdk.BUTTON_PRESS_MASK |
                                               gdk.BUTTON_RELEASE_MASK))
        self.window.set_user_data(self)

        if self.child:
            self.child.set_parent_window(self.window)

    def do_unrealize(self):
        self.log.debug('')
        self.window.destroy()
        gtk.Container.do_unrealize(self)

    def do_size_request(self, requisition):
        self.log.debug('%s' % requisition)

        # Compute total size request
        width = height = 0
        if self.child:
            width, height = self.child.size_request()

        requisition.width = width
        requisition.height = height

    def do_size_allocate(self, allocation):
        self.log.debug('%s' % allocation)

        self.allocation = allocation
        if self.flags() & gtk.REALIZED:
            self.window.move_resize(*allocation)

        if self.child:
            bw = self.props.border_width
            self.child.size_allocate((0, 0,
                    allocation.width - 2*bw, allocation.height - 2*bw))
        #if self.placeholder:
        #    self.placeholder.size_allocate((0, 0, 200, 200))

    def do_forall(self, internals, callback, data):
        # Is also called for map and expose events.
        if self.child:
            callback(self.child, data)

        if internals and self.placeholder:
            callback(self.placeholder, data)

    def do_add(self, widget):
        self.log.debug('')
        assert not self.child
        widget.set_parent(self)
        self.child = widget

    def do_remove(self, widget):
        self.log.debug('')
        assert self.child
        self.child.unparent()
        self.child = None

    def set_placeholder(self, placeholder):
        if self.placeholder:
            self.placeholder.unparent()
            self.placeholder = None
        if placeholder:
            self.placeholder = placeholder
            self.placeholder.set_parent(self)

