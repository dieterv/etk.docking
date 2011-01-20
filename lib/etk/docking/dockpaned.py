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

import gobject
import gtk
import gtk.gdk as gdk

from .dnd import DockDragContext
from .util import rect_overlaps
from .docksettings import settings


# The weight we allocate to a newly added item if we can't come up with anything else
FALLBACK_WEIGHT = 0.2


class _DockPanedHandle(object):
    '''
    Private object storing information about a handle.
    '''
    __slots__ = ['area']       # area, used for hit testing (gdk.Rectangle)

    def __init__(self):
        self.area = gdk.Rectangle()

    def __contains__(self, pos):
        return rect_overlaps(self.area, *pos)


class _DockPanedItem(object):
    '''
    Private object storing information about a child widget.
    '''
    __slots__ = ['child',      # child widget
                 'weight',     # relative weight [0..1]
                 'weight_request', # requested weight, processed in size_allocate()
                 'min_size'] # minimum relative weight

    def __init__(self):
        self.child = None
        self.weight = None
        self.weight_request = None
        self.min_size = None

    def __contains__(self, pos):
        return rect_overlaps(self.child.allocation, *pos)


class DockPaned(gtk.Container):
    '''
    The :class:`etk.DockPaned` widget is a container widget with multiple panes
    arranged either horizontally or vertically, depending on the value of the
    orientation property. Child widgets are added to the panes of the widget
    with the :meth:`append_item`, :meth:`prepend_item` or :meth:`insert_item`
    methods.

    A dockpaned widget draws a separator between it's child widgets and a small
    handle that the user can drag to adjust the division. It does not draw any
    relief around the children or around the separator.
    '''
    __gtype_name__ = 'EtkDockPaned'
    __gproperties__ = \
        {'handle-size':
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
    __gchild_properties__ = \
         {'weight':
             (gobject.TYPE_FLOAT,
              'item weight',
              'item weight',
              0, # min
              1, # max
              .2, # default
              gobject.PARAM_READWRITE)}
    __gsignals__ = {'item-added':
                        (gobject.SIGNAL_RUN_LAST,
                         gobject.TYPE_NONE,
                         (gobject.TYPE_OBJECT,)),
                    'item-removed':
                        (gobject.SIGNAL_RUN_LAST,
                         gobject.TYPE_NONE,
                         (gobject.TYPE_OBJECT,))}

    def __init__(self):
        gtk.Container.__init__(self)

        # Initialize logging
        self.log = getLogger('%s.%s' % (self.__gtype_name__, hex(id(self))))

        # Initialize attributes
        self._items = []
        self._handles = []
        self._hcursor = None
        self._vcursor = None

        # Initialize handle dragging (not to be confused with DnD...)
        self._dragcontext = DockDragContext()

        # Initialize properties
        self.set_handle_size(4)
        self.set_orientation(gtk.ORIENTATION_HORIZONTAL)

    ############################################################################
    # Private
    ############################################################################
    def _children(self):
        '''
        :returns: an iterator that returns the items and handles in the dockpaned.

        The :meth:`_children` method returns an iterator that returns the items
        and handles in the dockpaned in the order they are drawn. This
        corresponds to ``[_items[0], _handles[0], _items[1], _handles[1],
        _items[2], ...]``
        '''
        index = 0
        switch = True

        for x in range(len(self._items) + len(self._handles)):
            if switch:
                yield self._items[index]
                switch = False
            else:
                yield self._handles[index]
                switch = True
                index += 1

    def _insert_item(self, child, position=None, weight=None):
        '''
        :param child: a :class:`gtk.Widget` to use as the contents of the item.
        :param position: the index (starting at 0) at which to insert the
                         item, negative or :const:`None` to append the item
                         after all other items.
        :param weight: The relative amount of space the child should get. No guarantees.
        :returns: the index number of the item in the dockpaned.

        The :meth:`_insert_item` method is the private implementation behind
        the :meth:`add`, :meth:`insert_item`, :meth:`append_item` and
        :meth:`prepend_item` methods.
        '''
        assert isinstance(child, gtk.Widget)
        assert self.item_num(child) is None
        assert not child.get_parent()

        if position is None or position < 0:
            position = len(self)

        # Create new _DockPanedItem
        item = _DockPanedItem()
        item.child = child
        item.child.set_parent(self)

        if self.flags() & gtk.REALIZED:
            item.child.set_parent_window(self.window)

        self._items.insert(position, item)

        # Create a _DockPanedHandle if needed
        if len(self) > 1:
            self._insert_handle(position - 1)

        assert len(self._items) == len(self._handles) + 1

        if weight:
            assert 0.0 <= weight <= 1.0
            item.weight_request = weight
        elif len(self._items) == 1:
            # First item always gets 100% allocated
            item.weight = 1.0
        elif self.allocation and child.allocation:
            size = self._effective_size(self.allocation) - self._handle_size
            if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                child_size = child.size_request()[0]
            else:
                child_size = child.size_request()[1]

            if size > 0 and child_size > 0:
                item.weight_request = float(child_size) / size
            else:
                item.weight_request = FALLBACK_WEIGHT
        else:
            item.weight_request = FALLBACK_WEIGHT

        self.queue_resize()
        self.emit('item-added', child)
        return self.item_num(child)

    def _remove_item(self, child):
        '''
        :param child: a :class:`gtk.Widget` to use as the contents of the item.

        The :meth:`_remove_item` method is the private implementation behind
        the :meth:`remove` and :meth:`remove_item` methods.
        '''
        item_num = self.item_num(child)
        assert item_num is not None

        # Remove the DockPanedItem from the list
        child.unparent()
        del self._items[item_num]

        # If there are still items/handles in the list, we'd like to
        # remove a handle...
        if self._items:
            self._remove_handle(item_num)

        assert len(self._items) == len(self._handles) + 1 or \
               len(self._items) == len(self._handles) == 0

        self.queue_resize()
        self.emit('item-removed', child)

    def _insert_handle(self, position):
        '''
        :param position: the index (starting at 0) at which to insert a handle.

        The :meth:`_insert_handle` inserts a handle at the index specified by
        `position`.
        '''
        handle = _DockPanedHandle()
        self._handles.insert(position, handle)

    def _remove_handle(self, position):
        '''
        :param position: the index (starting at 0) at which to remove a handle.

        The :meth:`_remove_handle` removes a handle at the index specified by
        `position`.
        '''
        try:
            # Remove the DockPanedHandle that used to be located after
            # the DockPanedItem we just removed
            del self._handles[position]
        except IndexError:
            # Well, seems we removed the last DockPanedItem from the
            # list, so we'll remove the DockPanedHandle that used to
            # be located before the DockPanedItem we just removed
            del self._handles[position - 1]

    def _get_n_handles(self):
        '''
        :returns: the number of handles in the dockpaned.

        The :meth:`_get_n_handles` method returns the number of handles in the
        dockpaned.
        '''
        return len(self._handles)

    def _get_handle_at_pos(self, x, y):
        '''
        :param x: the x coordinate of the position.
        :param y: the y coordinate of the position.
        :returns: the handle at the position specified by x and y or :const:`None`.

        The :meth:`_get_handle_at_pos` method returns the handle whose area
        contains the position specified by `x` and `y` or :const:`None` if no
        handle is at that position.
        '''
        for handle in self._handles:
            if (x, y) in handle:
                return handle
        else:
            return None

    def _item_for_child(self, child):
        for item in self._items:
            if item.child is child:
                return item
        raise ValueError('child widget %s not in paned' % child)

    def _size(self, allocation):
        '''
        Get the size (width or height) required in calculations, depending on the
        Paned's orientation.
        '''
        if self._orientation == gtk.ORIENTATION_HORIZONTAL:
            return allocation.width
        else:
            return allocation.height

    def _effective_size(self, allocation):
        '''
        Find the size we can actually spend on items.
        '''
        return self._size(allocation) - self._get_n_handles() * self._handle_size

    def _redistribute_size(self, delta_size, enlarge, shrink):
        '''
        :param delta_size: the size we want to add the item specified by
                           `enlarge`.
        :param enlarge: the `_DockPanedItem` we want to add size to.
        :param shrink: a list of `_DockPanedItem`'s where the size requested
                       by `delta_size` will be removed.

        The :meth:`_redistribute_size` method subtracts size from the items
        specified by `shrink` and adds the freed size to the item specified by
        `enlarge`. This is done until `delta_size` reaches 0, or there's no
        more items left in `shrink`.
        '''
        # Distribute delta_size amongst the items in shrink
        size = self._effective_size(self.allocation)
        enlarge_alloc = enlarge.child.allocation

        for item in shrink:

            available_size = self._size(item.child.allocation) - item.min_size

            # Check if we can shrink (respecting the child's size_request)
            if available_size > 0:
                a = item.child.allocation

                # Can we adjust the whole delta or not?
                if delta_size > available_size:
                    adjustment = available_size
                else:
                    adjustment = delta_size

                enlarge.weight_request = float(self._size(enlarge_alloc) + adjustment) / size
                item.weight_request = float(self._size(a) - adjustment) / size

                delta_size -= adjustment

            if delta_size == 0:
                break

        self.queue_resize()

    def _redistribute_weight(self, size):
        '''
        Divide the space available over the items. Items that have explicitly been
        assigned a weight should get it assigned, as long as the max weight (1.0) is not
        exeeded.

        The general scheme is as follows:

        * figure out which items requested a new weight
        * ensure sum(min_sizes) fits in the allocated size
        * ensure the requested weights do not make items go smaller than min_size
        * divide remaining space over other items.
        '''
        items = self._items
        size = float(size)

        # Scale non-expandable items, so their size does not change effectively
        if self.allocation:
            f = self._effective_size(self.allocation) / size
            for i in self._items:
                #if i.weight and not i.expand and not i.weight_request:
                if i.weight and not settings[i.child].expand and not i.weight_request:
                    i.weight_request = i.weight * f

        requested_items = [ i for i in items if i.weight_request ]
        other_items = [ i for i in items if not i.weight_request ]

        # Ensure the min_sizes do not exceed the overall size
        min_size = sum(i.min_size for i in items)

        if min_size > size:
            sf = size / min_size
            self.log.warn('Size scaling required (factor=%f)' % sf)
        else:
            sf = 1.0

        # First ensure all remaining items can be placed
        for i, w in zip(other_items,
                        fair_scale(1.0 - sum(i.weight_request for i in requested_items), \
                                   [(i.weight, sf * i.min_size / size) for i in other_items])):
            i.weight = w

        # Divide what's left over the requesting items
        for i, w in zip(requested_items,
                        fair_scale(1.0 - sum(i.weight for i in other_items), \
                                   [(i.weight_request, sf * i.min_size / size) for i in requested_items])):
            i.weight = w
            i.weight_request = None


    ############################################################################

    def __getitem__(self, index):
        return self._items[index].child

    def __delitem__(self, index):
        child = self[index]
        self._remove_item(child)

    def __len__(self):
        return len(self._items)

    def __contains__(self, child):
        for i in self._items:
            if i.child is child:
                return True
        return False

    def __iter__(self):
        for i in self._items:
            yield i.child

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
                                               gdk.LEAVE_NOTIFY_MASK |
                                               gdk.BUTTON_PRESS_MASK |
                                               gdk.BUTTON_RELEASE_MASK |
                                               gdk.POINTER_MOTION_MASK))
        self.window.set_user_data(self)
        self.style.attach(self.window)
        self.style.set_background(self.window, gtk.STATE_NORMAL)

        # Set parent window on all child widgets
        for item in self._items:
            item.child.set_parent_window(self.window)

        # Initialize cursors
        self._hcursor = gdk.Cursor(self.get_display(), gdk.SB_H_DOUBLE_ARROW)
        self._vcursor = gdk.Cursor(self.get_display(), gdk.SB_V_DOUBLE_ARROW)

    def do_unrealize(self):
        self._hcursor = None
        self._vcursor = None
        self.window.set_user_data(None)
        self.window.destroy()
        gtk.Container.do_unrealize(self)

    def do_map(self):
        self.window.show()
        gtk.Container.do_map(self)

    def do_unmap(self):
        self.window.hide()
        gtk.Container.do_unmap(self)

    def do_size_request(self, requisition):
        # Start with nothing
        width = height = 0

        # Add child widgets
        for item in self._items:
            w, h = item.child.size_request()

            if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                width += w
                height = max(height, h)
                # Store the minimum weight for usage in do_size_allocate
                item.min_size = w
            else:
                width = max(width, w)
                height += h
                # Store the minimum weight for usage in do_size_allocate
                item.min_size = h

        # Add handles
        if self._orientation == gtk.ORIENTATION_HORIZONTAL:
            width += self._get_n_handles() * self._handle_size
        else:
            height += self._get_n_handles() * self._handle_size

        # Done
        requisition.width = width
        requisition.height = height

    def do_size_allocate(self, allocation):
        ####################################################################
        # DockPaned resizing explained
        #
        # When a widget is resized (ie when the parent window is resized by
        # the user), the do_size_request & do_size_allocate dance is
        # typically executed multiple times with small changes (1 or 2 pixels,
        # sometimes more depending on the gdk backend used), instead of one
        # pass with the complete delta. Distributing those small values
        # evenly across multiple child widgets simply doesn't work very well.
        # To overcome this problem, we assign a weight (can be translated to
        # "factor") to each child.
        #
        ####################################################################

        if self._items:
            size = self._effective_size(allocation)

            self._redistribute_weight(size)

            cx = cy = 0  # current x and y counters
            handle_size = self._handle_size

            # Allocate child widgets: both items and handles, so we can simply increment
            for child in self._children():
                rect = gdk.Rectangle()
                rect.x = cx
                rect.y = cy

                if isinstance(child, _DockPanedItem):
                    s = round(child.weight * size)

                    if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                        rect.height = allocation.height
                        rect.width = s
                        cx += s

                        if child is self._items[-1]:
                            rect.width += allocation.width - cx
                    else:
                        rect.height = s
                        rect.width = allocation.width
                        cy += s

                        if child is self._items[-1]:
                            rect.height += allocation.height - cy

                    child.child.size_allocate(rect)

                elif isinstance(child, _DockPanedHandle):
                    if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                        rect.height = allocation.height
                        rect.width = handle_size
                        cx += handle_size
                    else:
                        rect.height = handle_size
                        rect.width = allocation.width
                        cy += handle_size

                    child.area = rect

        # Accept new allocation
        self.allocation = allocation

        # Move/Resize our GdkWindow
        if self.flags() & gtk.REALIZED:
            self.window.move_resize(*allocation)

    def do_expose_event(self, event):
        for item in self._items:
            self.propagate_expose(item.child, event)

        for handle in self._handles:
            #TODO: render themed handle if not using compact layout
            pass

        return False

    def do_leave_notify_event(self, event):
        # Reset cursor
        self.window.set_cursor(None)

    def do_button_press_event(self, event):
        # We might be starting a drag operation, or we could simply be starting
        # a click somewhere. Store information from this event in self._dragcontext
        # and decide in do_motion_notify_event if we're actually starting a
        # drag operation or not.
        if event.window is self.window and event.button == 1:
            handle = self._get_handle_at_pos(event.x, event.y)

            if handle:
                self._dragcontext.dragging = True
                self._dragcontext.dragged_object = handle
                self._dragcontext.source_button = event.button
                self._dragcontext.offset_x = event.x - handle.area.x
                self._dragcontext.offset_y = event.y - handle.area.y
                return True

        return False

    def do_button_release_event(self, event):
        # Reset drag context
        if event.button == self._dragcontext.source_button:
            self._dragcontext.reset()
            self.window.set_cursor(None)
            return True

        return False

    def do_motion_notify_event(self, event):
        cursor = None

        # Set an appropriate cursor when the pointer is over a handle
        if self._get_handle_at_pos(event.x, event.y):
            if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                cursor = self._hcursor
            else:
                cursor = self._vcursor

        # Drag a handle
        if self._dragcontext.dragging:
            if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                cursor = self._hcursor
                delta_size = int(event.x -
                                 self._dragcontext.dragged_object.area.x -
                                 self._dragcontext.offset_x)
            else:
                cursor = self._vcursor
                delta_size = int(event.y -
                                 self._dragcontext.dragged_object.area.y -
                                 self._dragcontext.offset_y)

            handle_index = self._handles.index(self._dragcontext.dragged_object)
            item_after = self._items[handle_index + 1]

            if delta_size < 0:
                # Enlarge the item after and shrink the items before the handle
                delta_size = abs(delta_size)
                enlarge = item_after
                shrink = reversed(self._items[:self._items.index(item_after)])
                self._redistribute_size(delta_size, enlarge, shrink)
            elif delta_size > 0:
                # Enlarge the item before and shrink the items after the handle
                enlarge = self._items[handle_index]
                shrink = self._items[self._items.index(item_after):]
                self._redistribute_size(delta_size, enlarge, shrink)
            else:
                enlarge = None
                shrink = []

            self.queue_resize()

        # Set the cursor we decided upon above...
        if cursor:
            self.window.set_cursor(cursor)

    ############################################################################
    # GtkContainer
    ############################################################################
    def do_add(self, widget):
        self._insert_item(widget)

    def do_remove(self, widget):
        self._remove_item(widget)

    def do_forall(self, internals, callback, data):
        try:
            for item in self._items:
                callback(item.child, data)
        except AttributeError:
            pass

    def do_get_child_property(self, child, property_id, pspec):
        item = self._item_for_child(child)

        if pspec.name == 'weight':
            return item.weight_request or item.weight

    def do_set_child_property(self, child, property_id, value, pspec):
        item = self._item_for_child(child)

        if pspec.name == 'weight':
            item.weight_request = value
            child.child_notify('weight')

    ############################################################################
    # EtkDockPaned
    ############################################################################
    def get_handle_size(self):
        '''
        :return: the size of the handles in the dockpaned.

        Retrieves the size of the handles in the dockpaned.
        '''
        return self._handle_size

    def set_handle_size(self, handle_size):
        '''
        :param handle_size: the new size for the handles in the dockpaned.

        Sets the size for the handles in the dockpaned.
        '''
        self._handle_size = handle_size
        self.notify('handle-size')
        self.queue_resize()

    def get_orientation(self):
        '''
        :return: the orientation of the dockpaned.

        Retrieves the orientation of the dockpaned.
        '''
        return self._orientation

    def set_orientation(self, orientation):
        '''
        :param orientation: the dockpaned's new orientation.

        Sets the orientation of the dockpaned.
        '''
        self._orientation = orientation
        self.notify('orientation')
        self.queue_resize()

    def append_item(self, child):
        '''
        :param child: the :class:`gtk.Widget` to use as the contents of the item.
        :returns: the index number of the item in the dockpaned.

        The :meth:`append_item` method prepends an item to the dockpaned.
        '''
        return self._insert_item(child)

    def prepend_item(self, child):
        '''
        :param child: the :class:`gtk.Widget` to use as the contents of the item.
        :returns: the index number of the item in the dockpaned.

        The :meth:`prepend_item` method prepends an item to the dockpaned.
        '''
        return self._insert_item(child, 0)

    def insert_item(self, child, position=None, weight=None):
        '''
        :param child: a :class:`gtk.Widget`` to use as the contents of the item.
        :param position: the index (starting at 0) at which to insert the item,
                         negative or :const:`None` to append the item after all
                         other items.
        :param weight: The relative amount of space the child should get. No guarantees.
        :returns: the index number of the item in the dockpaned.

        The :meth:`insert_item` method inserts an item into the dockpaned at the
        location specified by `position` (0 is the first item). `child` is the
        widget to use as the contents of the item. If position is negative or
        :const:`None` the item is appended to the dockpaned.
        '''
        return self._insert_item(child, position, weight)

    def remove_item(self, item_num):
        '''
        :param item_num: the index (starting from 0) of the item to remove. If
                         :const:`None` or negative, the last item will be removed.

        The :meth:`remove_item` method removes the item at the location
        specified by `item_num`. The value of `item_num` starts from 0. If
        `item_num` is negative or :const:`None` the last item of the dockpaned
        will be removed.
        '''
        if item_num is None or item_num < 0:
            child = self.get_nth_item(len(self) - 1)
        else:
            child = self.get_nth_item(item_num)

        self._remove_item(child)

    def item_num(self, child):
        '''
        :param child: a :class:`gtk.Widget`.
        :returns: the index of the item containing `child`, or :const:`None` if
                  `child` is not in the dockpaned.

        The :meth:`item_num()` method returns the index of the item which
        contains the widget specified by `child` or :const:`None` if no item
        contains `child`.
        '''
        try:
            return self.get_children().index(child)
        except ValueError:
            pass

    def get_nth_item(self, item_num):
        '''
        :param item_num: the index of an item in the dockpaned.
        :returns: the child widget, or :const:`None` if `item_num` is out of
                  bounds.

        The :meth:`get_nth_item‘ method returns the child widget contained at
        the index specified by `item_num`. If `item_num` is out of bounds for
        the item range of the dockpaned this method returns :const:`None`.
        '''
        if item_num >= 0 and item_num <= len(self) - 1:
            return self._items[item_num].child
        else:
            return None

    def get_item_at_pos(self, x, y):
        '''
        :param x: the x coordinate of the position.
        :param y: the y coordinate of the position.
        :returns: the child widget at the position specified by x and y or
                  :const:`None`.

        The :meth:`get_item_at_pos` method returns the child widget whose
        allocation contains the position specified by `x` and `y` or
        :const:`None` if no child widget is at that position.
        '''
        for item in self._items:
            if (x, y) in item:
                return item.child
        else:
            return None

    def reorder_item(self, child, position):
        '''
        :param child: the child widget to move.
        :param position: the index that `child` is to move to, or :const:`None` to
                         move to the end.

        The :meth:`reorder_item` method reorders the dockpaned child widgets so
        that `child` appears in the location specified by `position`. If
        `position` is greater than or equal to the number of children in the
        list or negative or :const:`None`, `child` will be moved to the end of
        the list.
        '''
        item_num = self.item_num(child)
        assert item_num is not None

        if position is None or position < 0 or position > len(self) - 1:
            position = len(self)

        item = self._items[item_num]
        self._items.remove(item)
        self._items.insert(position, item)
        self.queue_resize()

############################################################################
# Install child properties
############################################################################
for index, (name, pspec) in enumerate(DockPaned.__gchild_properties__.iteritems()):
    pspec = list(pspec)
    pspec.insert(0, name)
    DockPaned.install_child_property(index + 1, tuple(pspec))

def fair_scale(weight, wmpairs):
    """
    Fair scaling algorithm.
    A weight and a list of (weight, min_weight) pairs is provided. The result is a list
    of calculated weights that add up to weight, but are no smaller than their specified
    min_weight's.

    >>> fair_scale(.7, ((.3, .2), (.5, .1)))
    [0.26249999999999996, 0.43749999999999994]
    >>> fair_scale(.5, ((.3, .2), (.5, .1)))
    [0.20000000000000001, 0.29999999999999999]
    >>> fair_scale(.4, ((.3, .2), (.5, .1)))
    [0.20000000000000001, 0.20000000000000001]
    """
    # List of new weights
    n = [0] * len(wmpairs)
    # Values that have been assigned their min_weight end up in this list:
    skip = [False] * len(wmpairs)
    while True:
        try:
            f = weight / sum(a[0] for a, s in zip(wmpairs, skip) if not s)
        except ZeroDivisionError:
            f = 0
        for i, (w, m) in enumerate(wmpairs):
            if skip[i]:
                continue
            n[i] = w * f
            if n[i] < m:
                n[i] = m
                weight -= m
                skip[i] = True
                break
        else:
            break # quit while loop
    return n

