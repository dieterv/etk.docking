# -*- coding: utf-8 -*-
# vim:sw=4:et:ai
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

from .util import rect_overlaps


class _DockPanedHandle(object):
    '''
    Convenience class storing information about a handle.
    '''
    __slots__ = ['item_before', # item before this handle (_DockPanedItem)
                 'item_after',  # item after this handle (_DockPanedItem)
                 'area']        # area, used for hit testing (gdk.Rectangle)

    def __contains__(self, pos):
        return rect_overlaps(self.area, pos[0], pos[1])


class _DockPanedItem(object):
    '''
    Convenience class storing information about a child.
    '''
    __slots__ = ['child',               # child widget
                 'area',                # area, used to calculate allocation (gdk.Rectangle)
                 'size']                # percentual size used by this item (float)


DRAG_TARGET_GROUP = ('x-etk-docking/group', gtk.TARGET_SAME_APP, 0)
DRAG_TARGET_ITEM = ('x-etk-docking/item', gtk.TARGET_SAME_APP, 1)
DRAG_TARGETS = [DRAG_TARGET_GROUP, DRAG_TARGET_ITEM]

class DockPaned(gtk.Container):
    '''
    The etk.DockPaned class groups it's children in panes, either
    horizontally or vertically.
    '''
    __gtype_name__ = 'EtkDockPaned'
    __gproperties__ = {'handle-size':
                           (gobject.TYPE_UINT,
                            'handle size',
                            'handle size',
                            0,
                            gobject.G_MAXINT,
                            4,
                            gobject.PARAM_READWRITE),
                       'orientation':
                           (gobject.TYPE_UINT,
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
        self._items = []
        self._handles = []
        self._handle_size = 4
        self._orientation = gtk.ORIENTATION_HORIZONTAL
        self._first_allocation = True
        self._dragging = False
        self._drag_pos = None
        self._drag_handle = None

        self.drag_dest_set(gtk.DEST_DEFAULT_ALL,
                           DRAG_TARGETS,
                           gdk.ACTION_MOVE)

        self._drop_handle = None


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

#        # Reset item sizes
#        n_items = self.get_n_items()
#
#        if n_items == 1:
#            self._items[0].size = 1.0
#        elif n_items > 1:
#            for item in self._items:
#                items.size = 1.0 / n_items

        # Queue resize event
        self._first_allocation = True

        for item in self._items:
            item.child.queue_resize()

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
        for item in self._items:
            item.child.set_parent_window(self.window)

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
            for item in self._items:
                w, h = item.child.size_request()
                width += w
                height = max(height, h)

            width += (self.get_n_items() - 1) * self._handle_size
        elif self._orientation == gtk.ORIENTATION_VERTICAL:
            for item in self._items:
                w, h = item.child.size_request()
                width = max(width, w)
                height += h

            height += (self.get_n_items() - 1) * self._handle_size

        requisition.width = width
        requisition.height = height

    def do_size_allocate(self, allocation):
#        if self._orientation == gtk.ORIENTATION_HORIZONTAL:
#            counter = 0.0
#            for item in self._items:
#                print item.size,
#                counter += item.size
#            print
#            print counter
#            print

        if self._first_allocation:
            delta_w = 0
            delta_h = 0
            self._first_allocation = False
        else:
            delta_w = allocation.width - self.allocation.width
            delta_h = allocation.height - self.allocation.height

        self.allocation = allocation

        # Reset handles
        self._handles = []

        n_handles = len(self._items) - 1
        cx = cy = 0

        if self._orientation == gtk.ORIENTATION_HORIZONTAL:
            # Don't shrink our children's allocated width below their requested width
            if delta_w < 0:
                delta_w = abs(delta_w)

                for item in reversed(self._items):
                    if item.child.allocation.width > item.child.get_child_requisition()[0]:
                        if delta_w > 0:
                            shrinkable_width = item.child.allocation.width - item.child.get_child_requisition()[0]
                            if shrinkable_width >= delta_w:
                                shrinkable_width = delta_w
                                item.size -= shrinkable_width / (allocation.width - n_handles * self._handle_size)
                                delta_w -= shrinkable_width
                    else:
                        item.size = item.child.get_child_requisition()[0] / (allocation.width - n_handles * self._handle_size)

            # Allocate size
            for item in self._items:
                item.area.x = cx
                item.area.y = cy
                item.area.width = floor((allocation.width - n_handles * self._handle_size) * item.size)
                item.area.height = allocation.height
                cx += item.area.width + self._handle_size

                item.child.size_allocate(item.area)

        elif self._orientation == gtk.ORIENTATION_VERTICAL:
            # Don't shrink our children's allocated height below their requested height
            if delta_h < 0:
                delta_h = abs(delta_h)

                for item in reversed(self._items):
                    if item.child.allocation.height > item.child.get_child_requisition()[1]:
                        if delta_h > 0:
                            shrinkable_height = item.child.allocation.height - item.child.get_child_requisition()[1]
                            if shrinkable_height >= delta_h:
                                shrinkable_height = delta_h
                                item.size -= shrinkable_height / (allocation.height - n_handles * self._handle_size)
                                delta_h -= shrinkable_height
                    else:
                        item.size = item.child.get_child_requisition()[1] / (allocation.height - n_handles * self._handle_size)

            # Allocate size
            for item in self._items:
                item.area.x = cx
                item.area.y = cy
                item.area.width = allocation.width
                item.area.height = floor((allocation.height - n_handles * self._handle_size) * item.size)
                cy += item.area.height + self._handle_size

                item.child.size_allocate(item.area)

        self._update_handles()

        if self.flags() & gtk.REALIZED:
            self.window.move_resize(*allocation)


    def do_expose_event(self, event):
        for item in self._items:
            self.propagate_expose(item.child, event)

        return False

    def do_button_press_event(self, event):
        self._dragging = False
        self._drag_handle = None
        self._drag_pos = None

        for handle in self._handles:
            if (event.x, event.y) in handle:
                self._dragging = True
                self._drag_handle = handle
                self._drag_pos = (event.x, event.y)
                break

    def do_button_release_event(self, event):
        if self._dragging:
            self._dragging = False
            self._drag_handle = None
            self._drag_pos = None
            self.window.set_cursor(None)

    def do_motion_notify_event(self, event):
        if self._dragging:
            if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                delta_w = self.get_pointer()[0] - self._drag_pos[0]

                # Don't shrink our children's allocated width below their requested width
                if delta_w < 0:
                    # Enlarge the item after and shrink the items before the handle
                    delta_w = abs(delta_w)
                    enlarge = self._drag_handle.item_after
                    shrink = reversed(self._items[:self._items.index(enlarge)])
                elif delta_w > 0:
                    # Enlarge the item before and shrink the items after the handle
                    enlarge = self._drag_handle.item_before
                    shrink = self._items[self._items.index(enlarge) + 1:]
                elif delta_w == 0:
                    return

                # Distribute delta_w amongst the children marked as shrinkable
                for item in shrink:
                    if item.child.allocation.width > item.child.get_child_requisition()[0]:
                        if delta_w > 0:
                            shrinkable_width = item.child.allocation.width - item.child.get_child_requisition()[0]

                            if shrinkable_width >= delta_w:
                                shrinkable_width = delta_w

                                enlarge.size += shrinkable_width / (self.allocation.width - len(self._handles) * self._handle_size)
                                item.size -= shrinkable_width / (self.allocation.width - len(self._handles) * self._handle_size)
                                delta_w -= shrinkable_width
                    else:
                        item.size = item.child.get_child_requisition()[0] / (self.allocation.width - len(self._handles) * self._handle_size)
#            elif self._orientation == gtk.ORIENTATION_VERTICAL:
#                delta_h = self.get_pointer()[1] - self._drag_pos[1]
#
#                if delta_h < 0:
#                    # Don't shrink our children's allocated height below their requested height
#                    delta_w = abs(delta_w)
#                    ia = self._drag_handle.item_after
#
#                    for child in reversed(self._items[:self._items.index(ia)]):
#                        if child.item.allocation.width > child.item.get_child_requisition()[0]:
#                            if delta_w > 0:
#                                shrinkable_width = child.item.allocation.width - child.item.get_child_requisition()[0]
#                                if shrinkable_width >= delta_w:
#                                    shrinkable_width = delta_w
#                                    ia.size += shrinkable_width
#                                    child.size -= shrinkable_width / (self.allocation.width - len(self._handles) * self._handle_size)
#                                    delta_w -= shrinkable_width
#                        else:
#                            child.size = child.item.get_child_requisition()[0] / (self.allocation.width - len(self._handles) * self._handle_size)
#
##                    ia = self._drag_handle.item_after
##                    items = reversed(self._items[:self._items.index(self._drag_handle.item_after)])
##
##                    for item in items:
##                        if ia.area.height - delta_h >= ia.item.get_child_requisition()[1] and item.area.height + delta_h >= item.item.get_child_requisition()[1]:
##                            item.size += size_delta
##                            ia.size -= size_delta
##                            break
#                elif delta_h > 0:
#                    ib = self._drag_handle.item_before
#                    items = self._items[self._items.index(self._drag_handle.item_before) + 1:]
#
#                    for item in items:
#                        if ib.area.height + delta_h >= ib.item.get_child_requisition()[1] and item.area.height - delta_h >= item.item.get_child_requisition()[1]:
#                            item.size -= size_delta
#                            ib.size += size_delta
#                            break

            # Update drag position
            self._drag_pos = (event.x, event.y)

            self.queue_resize()
        else:
            if event.window is self.window:
                for handle in self._handles:
                    if (event.x, event.y) in handle:
                        if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                            cursor = gtk.gdk.Cursor(self.get_display(), gdk.SB_H_DOUBLE_ARROW)
                        elif self._orientation == gtk.ORIENTATION_VERTICAL:
                            cursor = gtk.gdk.Cursor(self.get_display(), gdk.SB_V_DOUBLE_ARROW)

                        break
                else:
                    cursor = None
            else:
                cursor = None

            self.window.set_cursor(cursor)

    # drop destination
    def xx_do_drag_motion(self, context, x, y, timestamp):
        self.log.debug('Paned motion: %s, %s, %s' % (context, x, y))
        self._drop_handle = None
        pos = (x, y)
        for handle in self._handles:
            if pos in handle:
                self._drop_handle = handle
                print '*** drop handle:', self._drop_handle
                return True
        return False

    def xx_do_drag_data_received(self, context, x, y, selection_data, info, timestamp):
        source = context.get_source_widget()
        assert source
        assert self._drop_handle
        self.log.debug('Paned received data %s', selection_data.target)
        if selection_data.target == gdk.atom_intern(DRAG_TARGET_ITEM[0]):
            self.log.debug('... will create group for item %s', source._dragged_tab)
#            self.log.debug('Recieving item %s' % source._dragged_tab)
#            self.insert_item(source._dragged_tab.item, self._drop_tab_index)
        if selection_data.target == gdk.atom_intern(DRAG_TARGET_GROUP[0]):
            self.log.debug('... will add group %s', source)
#            self.log.debug('Recieving group from %s' % source)
#            self.merge_group(source, self._drop_tab_index)
#        else:
#            context.finish(False, False, timestamp) # success, delete, time
#            return
#
#        source._dragged_tab = None
        context.finish(True, False, timestamp) # success, delete, time

    ############################################################################
    # GtkContainer
    ############################################################################
    def do_forall(self, internals, callback, data):
        for item in self._items:
            callback(item.child, data)

    def do_add(self, widget):
        self.insert_child(widget)

    def _recalculate_sizes(self):
        """
        Recalculate sizes (%) for all children.
        """
        n_items = self.get_n_items()
        size_ok = []
        size_nok = []

        for item in self._items:
            if item.size is None:
                size_nok.append(item)
            else:
                size_ok.append(item)

        for item in size_nok:
            if n_items > 1:
                # Set a default size
                item.size = 1.0 / n_items
                delta = item.size / (n_items - 1)

                # And the rest has to shrink...
                for item in size_ok:
                    item.size -= delta
            else:
                item.size = 1.0

        self.queue_resize()

    def do_remove(self, widget):
        # Get the _DockPanedItem associated with widget
        for item in self._items:
            if item.child is widget:
                # Remove child from the list
                item.child.unparent()
                self._items.remove(item)

                # Distribute the freed size over the other children
                n_items = self.get_n_items()

                if n_items > 1:
                    delta = item.size / n_items

                    for item in self._items:
                        item.size += delta
                elif n_items == 1:
                    self._items[0].size = 1.0

                break

        self.queue_resize()

    ############################################################################
    # EtkDockPaned
    ############################################################################

    def _update_handles(self):
        """
        Update the _handles list.
        """
        allocation = self.allocation
        cx = cy = 0
        if self._orientation == gtk.ORIENTATION_HORIZONTAL:
            width = self._handle_size
            height = allocation.height
        elif self._orientation == gtk.ORIENTATION_VERTICAL:
            width = allocation.width
            height = self._handle_size
        items = self._items
        for before, after in zip(items, items[1:]):
            handle = _DockPanedHandle()
            handle.area = gdk.Rectangle()
            if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                cx += before.area.width
                handle.area.x = cx
                cx += self._handle_size
            elif self._orientation == gtk.ORIENTATION_VERTICAL:
                cy = before.area.height
                handle.area.y = cy
                cy += self._handle_size
            handle.area.width = width
            handle.area.height = height

            handle.item_before = before
            handle.item_after = after
            self._handles.append(handle)


    def insert_child(self, widget, position=-1):
        item = _DockPanedItem()
        item.child = widget
        item.child.set_parent(self)
        item.area = gdk.Rectangle()
        item.size = None
        if position == -1:
            self._items.append(item)
        else:
            self._items.insert(position, item)

        if self.flags() & gtk.REALIZED:
            item.child.set_parent_window(self.window)

        self._recalculate_sizes()


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
        return len(self._items)

    #TODO: def item_num(self, item):
    #TODO: def set_current_item(self, item_num):
    #TODO: def next_item()
    #TODO: def prev_item()
    #TODO: def reorder_item(item, position)
