# -*- coding: utf-8 -*-
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


from __future__ import absolute_import
from logging import getLogger

import gtk


class DockLayout(gtk.Container):
    __gtype_name__ = 'EtkDockLayout'

    def __init__(self):
        gtk.Container.__init__(self)

        # Initialize logging
        self.log = getLogger('<%s object at %s>' % (self.__gtype_name__, hex(id(self))))

        # Child containers:
        self._child = None
        self._floating_windows = []

    ############################################################################
    # GtkWidget
    ############################################################################
    def do_realize(self):
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
        self.style.attach(self.window)
        self.style.set_background(self.window, gtk.STATE_NORMAL)

        # Set parent window on all child widgets
        if self._child:
            self._child.set_parent_window(self.window)

    def do_unrealize(self):
        self.window.destroy()
        gtk.Container.do_unrealize(self)

    def do_map(self):
        gtk.Container.do_map(self)
        self.window.show()

    def do_unmap(self):
        self.window.hide()
        gtk.Container.do_unmap(self)

    def do_size_request(self, requisition):
        # Calculate total size request
        width = height = 0

        if self._child:
            width, height = self._child.size_request()

        requisition.width = width
        requisition.height = height

    def do_expose_event(self, event):
        if self._child:
            self.propagate_expose(self._child, event)

        return False


    ############################################################################
    # GtkWidget drag destination
    ############################################################################

    def do_drag_motion(self, context, x, y, timestamp):
        print 'Layout drag motion', x, y

    ############################################################################
    # GtkContainer
    ############################################################################

    def do_forall(self, internals, callback, data):
        # Internal widgets
        if internals:
            if self._child:
                callback(self._child, data)

        # Floating windows
        for w in self._floating_windows:
            callback(w, data)

    def do_add(self, widget):
        if not self._child:
            self._child = widget
            widget.set_parent(self)
            if self.flags() & gtk.REALIZED:
                self._child.set_parent_window(self.window)
        else:
            raise ValueError, 'Child widget is already set'

    def do_remove(self, widget):
        self.remove_item(self.item_num(widget))
        
