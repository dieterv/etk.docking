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


from __future__ import absolute_import, division
from logging import getLogger
from math import floor

import gobject
import gtk
import gtk.gdk as gdk

from .util import rect_contains, rect_overlaps


class _DockPanedHandle(object):
    '''
    Convenience class storing information about a handle.
    '''
    __slots__ = ['item_before', # item before this handle (_DockPanedItem)
                 'item_after',  # item after this handle (_DockPanedItem)
                 'area']        # area, used for hit testing (gdk.Rectangle)


class _DockPanedItem(object):
    '''
    Convenience class storing information about a child.
    '''
    __slots__ = ['item',                # child widget
                 'area',                # area, used to calculate allocation (gdk.Rectangle)
                 'size']                # percentual size used by this item (float)


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
        self._handles = []
        self._handle_size = 4
        self._orientation = gtk.ORIENTATION_HORIZONTAL
        self._first_allocation = True
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

        # Reset item sizes
        n_items = self.get_n_items()

        if n_items == 1:
            self._children[0].size = 1.0
        elif n_items > 1:
            for child in self._children:
                child.size = 1.0 / n_items

        # Queue resize event
        self._first_allocation = True

        for child in self._children:
            child.item.queue_resize()

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
                w, h = child.item.size_request()
                width += w
                height = max(height, h)

            width += (self.get_n_items() - 1) * self._handle_size
        elif self._orientation == gtk.ORIENTATION_VERTICAL:
            for child in self._children:
                w, h = child.item.size_request()
                width = max(width, w)
                height += h

            height += (self.get_n_items() - 1) * self._handle_size

        requisition.width = width
        requisition.height = height

    def do_size_allocate(self, allocation):
        if self._first_allocation:
            width_delta = 0
            height_delta = 0
            self._first_allocation = False
        else:
            width_delta = allocation.width - self.allocation.width
            height_delta = allocation.height - self.allocation.height

        self.allocation = allocation

        # Reset handles
        self._handles = []

        if self._orientation == gtk.ORIENTATION_HORIZONTAL:
            # Don't shrink our children's allocated width below their requested width
            if width_delta < 0:
                width_delta = abs(width_delta)

                # List children we can shrink
                for child in reversed(self._children):
                    if child.item.allocation.width > child.item.get_child_requisition()[0]:
                        if width_delta > 0:
                            shrinkable_width = child.item.allocation.width - child.item.get_child_requisition()[0]
                            if shrinkable_width >= width_delta:
                                shrinkable_width = width_delta
                                child.size -= shrinkable_width / (allocation.width - (len(self._children) - 1) * self._handle_size)
                                width_delta -= shrinkable_width
                    else:
                        child.size = child.item.get_child_requisition()[0] / (allocation.width - (len(self._children) - 1) * self._handle_size)

            # Allocate size and create handles
            cx = cy = 0

            for child in self._children:
                size = floor((allocation.width - (len(self._children) - 1) * self._handle_size) * child.size)

                child.area.x = cx
                child.area.y = cy
                child.area.width = size
                child.area.height = allocation.height
                cx += child.area.width

                if child is self._children[-1:][0]:
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
                handle.item_before = self._children[index]
                handle.item_after = self._children[index + 1]
        elif self._orientation == gtk.ORIENTATION_VERTICAL:
            # Don't shrink our children's allocated height below their requested height
            if height_delta < 0:
                height_delta = abs(height_delta)

                # List children we can shrink
                for child in reversed(self._children):
                    if child.item.allocation.height > child.item.get_child_requisition()[1]:
                        if height_delta > 0:
                            shrinkable_height = child.item.allocation.height - child.item.get_child_requisition()[1]
                            if shrinkable_height >= height_delta:
                                shrinkable_height = height_delta
                                child.size -= shrinkable_height / (allocation.height - (len(self._children) - 1) * self._handle_size)
                                height_delta -= shrinkable_height
                    else:
                        child.size = child.item.get_child_requisition()[1] / (allocation.height - (len(self._children) - 1) * self._handle_size)

            # Allocate size and create handles
            cx = cy = 0

            for child in self._children:
                size = floor((allocation.height - (len(self._children) - 1) * self._handle_size) * child.size)

                child.area.x = cx
                child.area.y = cy
                child.area.width = allocation.width
                child.area.height = size
                cy += child.area.height

                if child is self._children[-1:][0]:
                    child.area.height = allocation.height - child.area.y
                else:
                    handle = _DockPanedHandle()
                    handle.area = gdk.Rectangle()
                    handle.area.x = cx
                    handle.area.y = cy
                    handle.area.width = allocation.width
                    handle.area.height = self._handle_size
                    self._handles.append(handle)
                    cy += self._handle_size

                child.item.size_allocate(child.area)

            # Attach items to handles
            for index, handle in enumerate(self._handles):
                handle.item_before = self._children[index]
                handle.item_after = self._children[index + 1]

        if self.flags() & gtk.REALIZED:
            self.window.move_resize(*allocation)

    def do_expose_event(self, event):
        for child in self._children:
            self.propagate_expose(child.item, event)

        return False

    def do_button_press_event(self, event):
        self._dragging = False
        self._drag_handle = None
        self._drag_pos = None

        for handle in self._handles:
            if rect_overlaps(handle.area, event.x, event.y):
                self._dragging = True
                self._drag_handle = handle
                self._drag_pos = (event.x, event.y)

    def do_button_release_event(self, event):
        if self._dragging:
            self._dragging = False
            self._drag_handle = None
            self._drag_pos = None
            self.window.set_cursor(None)

    def do_motion_notify_event(self, event):
        if self._dragging:
            if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                width_delta = self.get_pointer()[0] - self._drag_pos[0]
                size_delta = width_delta / self.allocation.width

                if width_delta < 0:
                    ia = self._drag_handle.item_after
                    items = reversed(self._children[:self._children.index(self._drag_handle.item_after)])

                    for item in items:
                        if ia.area.width - width_delta >= ia.item.get_child_requisition()[0] and item.area.width + width_delta >= item.item.get_child_requisition()[0]:
                            item.size += size_delta
                            ia.size -= size_delta
                            break
                elif width_delta > 0:
                    ib = self._drag_handle.item_before
                    items = self._children[self._children.index(self._drag_handle.item_before) + 1:]

                    for item in items:
                        if ib.area.width + width_delta >= ib.item.get_child_requisition()[0] and item.area.width - width_delta >= item.item.get_child_requisition()[0]:
                            item.size -= size_delta
                            ib.size += size_delta
                            break
            elif self._orientation == gtk.ORIENTATION_VERTICAL:
                height_delta = self.get_pointer()[1] - self._drag_pos[1]
                size_delta = height_delta / self.allocation.height

                if height_delta < 0:
                    ia = self._drag_handle.item_after
                    items = reversed(self._children[:self._children.index(self._drag_handle.item_after)])

                    for item in items:
                        if ia.area.height - height_delta >= ia.item.get_child_requisition()[1] and item.area.height + height_delta >= item.item.get_child_requisition()[1]:
                            item.size += size_delta
                            ia.size -= size_delta
                            break
                elif height_delta > 0:
                    ib = self._drag_handle.item_before
                    items = self._children[self._children.index(self._drag_handle.item_before) + 1:]

                    for item in items:
                        if ib.area.height + height_delta >= ib.item.get_child_requisition()[1] and item.area.height - height_delta >= item.item.get_child_requisition()[1]:
                            item.size -= size_delta
                            ib.size += size_delta
                            break

            # Update drag position
            self._drag_pos = (event.x, event.y)

            self.queue_resize()
        else:
            for handle in self._handles:
                if rect_overlaps(handle.area, event.x, event.y):
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
        self._children.append(child)

        if self.flags() & gtk.REALIZED:
            child.item.set_parent_window(self.window)

        # Recalculate sizes for all children
        n_items = self.get_n_items()
        size_ok = []
        size_nok = []

        for child in self._children:
            if child.size is None:
                size_nok.append(child)
            else:
                size_ok.append(child)

        for child in size_nok:
            if n_items > 1:
                # Set a default size
                child.size = 1.0 / n_items
                delta = child.size / (n_items - 1)

                # And the rest has to shrink...
                for child in size_ok:
                    child.size -= delta
            else:
                child.size = 1.0

        self.queue_resize()

    def do_remove(self, widget):
        # Get the _DockPanedItem associated with widget
        for child in self._children:
            if child.item is widget:
                # Remove child from the list
                child.item.unparent()
                self._children.remove(child)

                # Distribute the freed size over the other children
                n_items = self.get_n_items()

                if n_items > 1:
                    delta = child.size / n_items

                    for child in self._children:
                        child.size += delta
                elif n_items == 1:
                    self._children[0].size = 1.0

                break

        self.queue_resize()

    ############################################################################
    # EtkDockGroup
    ############################################################################
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

    #TODO: def item_num(self, item):
    #TODO: def set_current_item(self, item_num):
    #TODO: def next_item()
    #TODO: def prev_item()
    #TODO: def reorder_item(item, position)
