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


DRAG_TARGET_ITEM_LIST = ('x-etk-docking/item-list', gtk.TARGET_SAME_APP, 0)


class DockDragContext(object):
    '''
    As we can't reliably use drag_source_set to initiate a drag operation
    (there's just to much information locked away in C structs - GtkDragSourceSite,
    GtkDragSourceInfo, GtkDragDestSite, GtkDragDestInfo, ... - that are not
    exposed to Python), we are sadly forced to mimic some of that default behavior.

    This class can also be used to store extra information about a drag operation
    in progress.
    '''
    __slots__ = ['dragging',        # are we dragging or not (bool)
                 'source_x',        # x coordinate starting a potential drag
                 'source_y',        # y coordinate starting a potential drag
                 'source_button',   # the button the user pressed to start the drag
                 'dragged_object']  # object being dragged

    def __init__(self):
        self.reset()

    def reset(self):
        self.dragging = False
        self.source_x = None
        self.source_y = None
        self.source_button = None
        self.dragged_object = None


class Placeholder(gtk.DrawingArea):
    __gtype_name__ = 'EtkDockPlaceholder'

    def do_expose_event(self, expose):
        a = self.allocation
        c = self.window.cairo_create()
        c.set_source_rgb(0, 0, 0)
        c.set_line_width(1.0)
        c.rectangle(0.5, 0.5, a.width - 1, a.height - 1)
        #c.set_source_rgba(0, 0, 0, 0)
        #c.fill()
        c.stroke()


class HighlightWindow(gtk.Window):
    '''
    The etk.dnd.HighlightWindow widget is a gtk.Window that can highlight an
    area on screen. This is used by the drag and drop implementation to mark
    a valid destination for the drag and drop operation while dragging.
    '''
    __gtype_name__ = 'EtkHighlightWindow'

    def __init__(self, dockgroup):
        gtk.Window.__init__(self, gtk.WINDOW_POPUP)
        self.set_skip_taskbar_hint(True)
        self.set_decorated(False)
        self.set_transient_for(dockgroup.get_toplevel())
        self.set_type_hint(gdk.WINDOW_TYPE_HINT_UTILITY)

        # Initialize logging
        self.log = getLogger('%s.%s' % (self.__gtype_name__, hex(id(self))))
        self.log.debug('%s' % dockgroup)

        # Internal housekeeping
        self._gc = dockgroup.style.bg_gc[gtk.STATE_SELECTED]

        self.realize()

    def _create_shape(self, width, height):
        black = gdk.Color(0, 0, 0)
        black.pixel = 1
        white = gdk.Color(255, 255, 255)
        white.pixel = 0

        pm = gdk.Pixmap(self.window, width, height, 1)
        gc = gdk.GC(pm)
        gc.set_background(white)
        gc.set_foreground(white)
        pm.draw_rectangle(gc, True, 0, 0, width, height)

        gc.set_foreground(black)
        pm.draw_rectangle(gc, False, 0, 0, width - 1, height - 1)
        pm.draw_rectangle(gc, False, 1, 1, width - 3, height - 3)

        self.shape_combine_mask(pm, 0, 0)

    def do_size_allocate(self, allocation):
        self.log.debug('%s' % allocation)
        gtk.Window.do_size_allocate(self, allocation)

        self._create_shape(allocation.width, allocation.height)

    def do_expose_event(self, event):
        self.log.debug('%s' % event)
        gtk.Window.do_expose_event(self, event)

        width, height = self.get_size()
        self.window.draw_rectangle(self._gc, False, 0, 0, width-1, height-1)
        self.window.draw_rectangle(self._gc, False, 1, 1, width-3, height-3)
        return True

    def move_resize(self, x, y, width, height):
        self.log.debug('%s, %s, %s, %s' % (x, y, width, height))

        self.move(x, y)
        self.resize(width, height)
