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

    This class is also used to store extra information about a drag operation
    in progress not available in the C structs mentioned above.
    '''
    __slots__ = ['dragging',        # are we dragging or not (bool)
                 'dragged_object',  # object being dragged
                 'source_x',        # x coordinate starting a potential drag
                 'source_y',        # y coordinate starting a potential drag
                 'source_button',   # the button the user pressed to start the drag
                 'offset_x',        # cursor x offset relative to dragged object source_x
                 'offset_y']        # cursor y offset relative to dragged object source_y

    def __init__(self):
        self.reset()

    def reset(self):
        self.dragging = False
        self.dragged_object = None
        self.source_x = None
        self.source_y = None
        self.source_button = None
        self.offset_x = None
        self.offset_y = None


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


class PlaceHolderWindow(gtk.Window):
    '''
    The etk.dnd.PlaceHolderWindow is a gtk.Window that can highlight an area
    on screen. When a PlaceHolderWindow has no child widget an undecorated
    utility popup is shown drawing a transparent highlighting rectangle around
    the desired area. The location and size of the highlight rectangle can
    easily be updated with the move_resize method. The show and hide methods
    do as they suggest.

    When you add a child widget to the PlaceHolderWindow the utility popup is
    automatically decorated (get's a title bar) and removes it's transparency.

    This is used by the drag and drop implementation to mark a valid destination
    for the drag and drop operation while dragging and as the container window
    for teared off floating items.
    '''
    __gtype_name__ = 'EtkDockPlaceHolderWindow'

    def __init__(self):
        gtk.Window.__init__(self, gtk.WINDOW_POPUP)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_type_hint(gdk.WINDOW_TYPE_HINT_UTILITY)
        #TODO: self.set_transient_for(???.get_toplevel())

        # Initialize logging
        self.log = getLogger('%s.%s' % (self.__gtype_name__, hex(id(self))))

        # Internal housekeeping
        self._gc = None

    def _create_shape(self, width, height):
        black = gdk.Color(red=0, green=0, blue=0, pixel=1)
        white = gdk.Color(red=255, green=255, blue=255, pixel=0)

        pm = gdk.Pixmap(self.window, width, height, 1)
        gc = gdk.GC(pm)
        gc.set_background(white)
        gc.set_foreground(white)
        pm.draw_rectangle(gc, True, 0, 0, width, height)

        gc.set_foreground(black)
        pm.draw_rectangle(gc, False, 0, 0, width - 1, height - 1)
        pm.draw_rectangle(gc, False, 1, 1, width - 3, height - 3)

        self.shape_combine_mask(pm, 0, 0)

    ############################################################################
    # GtkWidget
    ############################################################################
    def do_realize(self):
        gtk.Window.do_realize(self)
        self._gc = self.style.bg_gc[gtk.STATE_SELECTED]

    def do_unrealize(self):
        self._gc = None
        gtk.Window.do_unrealize(self)

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

    ############################################################################
    # GtkContainer
    ############################################################################
    def do_add(self, widget):
        self.set_decorated(True)
        self.reset_shapes()
        gtk.Window.add(self, widget)

    ############################################################################
    # EtkPlaceHolderWindow
    ############################################################################
    def move_resize(self, x, y, width, height):
        self.log.debug('%s, %s, %s, %s' % (x, y, width, height))

        self.move(x, y)
        self.resize(width, height)
