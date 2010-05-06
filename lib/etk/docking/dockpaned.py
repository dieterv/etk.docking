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


from __future__ import absolute_import, division
from logging import getLogger
from math import floor

import gobject
import gtk
import gtk.gdk as gdk

from .util import _rect_overlaps


class _DockPanedHandle(object):
    '''
    Convenience class storing information about a handle.
    '''
    __slots__ = ['left',    # item on the left side of this handle (_DockPanedItem)
                 'right',   # item on the left side of this handle (_DockPanedItem)
                 'area']    # area, used for hit testing (gdk.Rectangle)


class _DockPanedItem(object):
    '''
    Convenience class storing information about a child.
    '''
    __slots__ = ['item',                # child widget
                 'area',                # area, used to calculate allocation (gdk.Rectangle)
                 'size',                # percentual size used by this item (float)
                 'handler_id_visible']  # handler id for visible property notification signal


class DockPaned(gtk.Container):
    '''
    The etk.DockPaned class groups it's children in panes, either
    horizontally or vertically.
    '''
    __gtype_name__ = 'EtkDockPaned'
    __gproperties__ = {'handle-size': (gobject.TYPE_UINT,
                                       'handle size',
                                       'handle size',
                                       0,
                                       gobject.G_MAXINT,
                                       4,
                                       gobject.PARAM_READWRITE),
                       'orientation': (gobject.TYPE_UINT,
                                       'handle size',
                                       'handle size',
                                       0,
                                       1,
                                       0,
                                       gobject.PARAM_READWRITE)}

    def __init__(self):
        gtk.Container.__init__(self)

        # Initialize logging
        self.log = getLogger('<%s object at %s>' % (self.__gtype_name__, hex(id(self))))

        # Internal housekeeping
        self._children = []
        self._visible_children = []
        self._handles = []
        self._handle_size = 4
        self._orientation = gtk.ORIENTATION_HORIZONTAL
        self._dragging = False
        self._drag_pos = None
        self._drag_handle = None

    ############################################################################
    # GObject
    ############################################################################
    def do_get_property(self, pspec):
        if pspec.name == 'handle-size':
            return self.get_handle_size()
        elif pspec.name == 'orientation':
            return self.get_orientation()

    def do_set_property(self, pspec, value):
        if pspec.name == 'handle-size':
            self.set_handle_size(value)
        elif pspec.name == 'orientation':
            self.set_orientation(value)

    def get_handle_size(self):
        return self._handle_size

    def set_handle_size(self, value):
        self._handle_size = value
        self.notify('handle-size')

    def get_orientation(self):
        return self._orientation

    def set_orientation(self, value):
        self._orientation = value
        self.queue_resize()
        self.notify('orientation')

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
        for child in self._children:
            child.item.set_parent_window(self.window)

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

        if self._orientation == gtk.ORIENTATION_HORIZONTAL:
            for child in self._children:
                if child.item.flags() & gtk.VISIBLE:
                    w, h = child.item.size_request()
                    width += w
                    height = max(height, h)

            width += (self._get_n_visible_items() - 1) * self._handle_size
        elif self._orientation == gtk.ORIENTATION_VERTICAL:
            for child in self._children:
                if child.item.flags() & gtk.VISIBLE:
                    w, h = child.item.size_request()
                    width = max(width, w)
                    height += h

            height += (self._get_n_visible_items() - 1) * self._handle_size

        requisition.width = width
        requisition.height = height

    def do_size_allocate(self, allocation):
        self.allocation = allocation

        if self._orientation == gtk.ORIENTATION_HORIZONTAL:
            # Keep track of these
            self._visible_children = []
            self._handles = []

            # List visible children
            for child in self._children:
                if child.item.flags() & gtk.VISIBLE:
                    self._visible_children.append(child)

            # Allocate size and create handles
            cx = cy = 0
            for child in self._visible_children:
                size = floor((allocation.width - (len(self._visible_children) - 1) * self._handle_size) * child.size)

                child.area.x = cx
                child.area.y = cy
                child.area.width = size
                child.area.height = allocation.height
                cx += child.area.width

                if child is self._visible_children[-1:][0]:
                    child.area.width = allocation.width - child.area.x
                else:
                    handle = _DockPanedHandle()
                    handle.area = gdk.Rectangle()
                    handle.area.x = cx
                    handle.area.y = cy
                    handle.area.width = self._handle_size
                    handle.area.height = allocation.height
                    self._handles.append(handle)
                    cx += self._handle_size

                child.item.size_allocate(child.area)

            # Attach items to handles
            for index, handle in enumerate(self._handles):
                handle.left = self._visible_children[index]
                handle.right = self._visible_children[index + 1]

        elif self._orientation == gtk.ORIENTATION_VERTICAL:
            #TODO: implement this
            pass

        if self.flags() & gtk.REALIZED:
            self.window.move_resize(*allocation)

    def do_expose_event(self, event):
        for child in self._children:
            if child.item.flags() & gtk.VISIBLE:
                self.propagate_expose(child.item, event)

        return False

    def do_button_press_event(self, event):
        self._dragging = False
        self._drag_handle = None
        self._drag_pos = None

        for handle in self._handles:
            if _rect_overlaps(handle.area, event.x, event.y):
                self._dragging = True
                self._drag_handle = handle

                if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                    self._drag_pos = event.x
                elif self._orientation == gtk.ORIENTATION_VERTICAL:
                    self._drag_pos = event.y

    def do_button_release_event(self, event):
        if self._dragging:
            self._dragging = False
            self._drag_pos = None
            self._drag_handle = None

    def do_motion_notify_event(self, event):
        if self._dragging:
            if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                width_delta = self.get_pointer()[0] - self._drag_pos
                size_delta = width_delta / self.allocation.width

                ri = self._drag_handle.right
                li = self._drag_handle.left

                if width_delta < 0 and ri.area.width - width_delta >= ri.item.size_request()[0]:
                    li.size += size_delta
                    ri.size -= size_delta
                elif width_delta > 0 and li.area.width + width_delta >= li.item.size_request()[0]:
                    li.size += size_delta
                    ri.size -= size_delta

                self.queue_resize()
            elif self._orientation == gtk.ORIENTATION_VERTICAL:
                #TODO: implement this
                pass

            # Update drag position
            if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                self._drag_pos = event.x
            elif self._orientation == gtk.ORIENTATION_VERTICAL:
                self._drag_pos = event.y
        else:
            for handle in self._handles:
                if _rect_overlaps(handle.area, event.x, event.y):
                    if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                        cursor = gtk.gdk.Cursor(self.get_display(), gdk.SB_H_DOUBLE_ARROW)
                    elif self._orientation == gtk.ORIENTATION_VERTICAL:
                        cursor = gtk.gdk.Cursor(self.get_display(), gdk.SB_V_DOUBLE_ARROW)

                    break
            else:
                cursor = None

            self.window.set_cursor(cursor)

    ############################################################################
    # GtkContainer
    ############################################################################
    def do_forall(self, internals, callback, data):
        for child in self._children:
            callback(child.item, data)

    def do_add(self, widget):
        # _DockPanedItem
        child = _DockPanedItem()
        child.item = widget
        child.item.set_parent(self)
        child.area = gdk.Rectangle()
        child.size = None
        child.handler_id_visible = child.item.connect('notify::visible', self._on_child_visibility_changed)
        self._children.append(child)

        if self.flags() & gtk.REALIZED:
            child.item.set_parent_window(self.window)

        if child.item.flags() & gtk.VISIBLE:
            self._add_visible_item(child)

        self.queue_resize()

    def do_remove(self, widget):
        # Get the _DockPanedItem associated with widget
        for child in self._children:
            if child.item is widget:
                child.item.disconnect(child.handler_id_visible)
                child.item.unparent()
                self._children.remove(child)

                if child.item.flags() & gtk.VISIBLE:
                    self._remove_visible_item(child)

                self.queue_resize()
                break

    ############################################################################
    # EtkDockGroup
    ############################################################################
    def _on_child_visibility_changed(self, gobject, pspec):
        # Get the _DockPanedItem associated with gobject
        for child in self._children:
            if child.item is gobject:
                if child.item.flags() & gtk.VISIBLE:
                    self._add_visible_item(child)
                else:
                    self._remove_visible_item(child)

                break

        self.queue_resize()

    def _add_visible_item(self, item):
        n_visible_items = self._get_n_visible_items()

        if item.size is None:
            size_ok = []
            size_nok = []

            for child in self._children:
                if child.item.flags() & gtk.VISIBLE:
                    if child.size is None:
                        size_nok.append(child)
                    else:
                        size_ok.append(child)

            for child in size_nok:
                if n_visible_items > 1:
                    # Set a default size
                    child.size = 1.0 / n_visible_items
                    delta = child.size / (n_visible_items - 1)

                    # And the rest has to shrink...
                    for child in size_ok:
                        child.size -= delta
                else:
                    child.size = 1.0
        else:
            if n_visible_items > 1:
                delta = item.size / (n_visible_items - 1)

                for child in self._children:
                    if child.item.flags() & gtk.VISIBLE and not item is child:
                        child.size -= delta
            else:
                item.size = 1.0

    def _remove_visible_item(self, child):
        n_visible_items = self._get_n_visible_items()

        if n_visible_items > 1:
            delta = child.size / n_visible_items
            for child in self._children:
                if child.item.flags() & gtk.VISIBLE:
                    child.size += delta
        elif n_visible_items == 1:
            for child in self._children:
                if child.item.flags() & gtk.VISIBLE:
                    child.size = 1.0
                    break

    #TODO: def append_item(self, item):
    #TODO: def prepend_item(item, tab_label=None)
    #TODO: def insert_item(item, tab_label=None, position=-1)
    #TODO: def remove_item(self, item_num):
    #TODO: def get_current_item(self):
    #TODO: def get_nth_item(self, item_num):

    def get_n_items(self):
        '''
        The get_n_items() method returns the number of items in the DockPaned.
        '''
        return len(self._children)

    def _get_n_visible_items(self):
        '''
        The _get_n_visible_items() method returns the number of visible items
        in the DockPaned. This method is used when self._visible_children has
        not been calculated.
        '''
        n_items = 0

        for child in self._children:
            if child.item.flags() & gtk.VISIBLE:
                n_items += 1

        return n_items

    def get_n_visible_items(self):
        '''
        The get_n_visible_items() method returns the number of visible items in
        the DockPaned.
        '''
        return len(self._visible_children)

    #TODO: def item_num(self, item):
    #TODO: def set_current_item(self, item_num):
    #TODO: def next_item()
    #TODO: def prev_item()
    #TODO: def reorder_item(item, position)
