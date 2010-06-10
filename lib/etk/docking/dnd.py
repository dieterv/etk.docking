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
import gtk.gdk as gdk


class HighlightWindow(gtk.Window):
    '''
    The etk.dnd.HighlightWindow widget is a gtk.Window that can highlight an
    area on screen. This is used by the drag and drop implementation to mark
    a valid destination for the drag and drop operation while dragging.
    '''
    __gtype_name__ = 'EtkHighlightWindow'

    def __init__(self, dockgroup):
        gtk.Window.__init__(self, gtk.WINDOW_POPUP)

        # Initialize logging
        self.log = getLogger('%s.%s' % (self.__gtype_name__, hex(id(self))))

        # Internal housekeeping
        self._gc = dockgroup.style.bg_gc[gtk.STATE_SELECTED]

        self.set_skip_taskbar_hint(True)
        self.set_decorated(False)
        self.set_transient_for(dockgroup.get_toplevel())
        self.set_type_hint(gdk.WINDOW_TYPE_HINT_UTILITY)

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
