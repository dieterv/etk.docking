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
                 'weight',     # relative weight
                 'min_weight', # minimum relative weight
                 'expand']     # used to store the 'expand' child property

    def __init__(self):
        self.child = None
        self.weight = None
        self.min_weight = None
        self.expand = True

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

    Each child has an expand option that can be set. If resize is :const:`True`,
    when the dockpaned is resized, that child will expand or shrink along
    with the dockpaned widget. If multiple child widgets have the resize
    property set to :const:`True`, all of them will expand of shrink evenly.
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
        {'expand':
             (gobject.TYPE_BOOLEAN,
              'expand',
              'expand',
              True,
              gobject.PARAM_READWRITE)}

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

    def _insert_item(self, child, position=None, expand=True):
        '''
        :param child: a :class:`gtk.Widget` to use as the contents of the item.
        :param position: the index (starting at 0) at which to insert the
                         item, negative or :const:`None` to append the item
                         after all other items.
        :param expand: :const:`True` if `child` is to be given extra space
                       allocated to dockpaned. The extra space will be divided
                       evenly between all children of the dockpaned that use
                       this option.
        :returns: the index number of the item in the dockpaned.

        The :meth:`_insert_item` method is the private implementation behind
        the :meth:`add`, :meth:`insert_item`, :meth:`append_item` and
        :meth:`prepend_item` methods.
        '''

        assert not isinstance(child, _DockPanedItem)
        assert not isinstance(child, _DockPanedHandle)
        assert isinstance(child, gtk.Widget)
        assert not child.get_parent()

        if self.item_num(child):
            #TODO: improve this message...
            raise ValueError('Inserted widget is already in the dockpaned')

        if position is None or position < 0:
            position = self.get_n_items()

        # Create new _DockPanedItem
        item = _DockPanedItem()
        item.child = child
        self._items.insert(position, item)

        # Set parent/parent_window on child
        child.set_parent(self)

        if self.flags() & gtk.REALIZED:
            child.set_parent_window(self.window)

        # Set child properties
        self.child_set_property(child, 'expand', expand)

        # And a _DockPanedHandle if needed
        if len(self._items) > 1:
            self._handles.insert(position - 1, _DockPanedHandle())

        # Refresh ourselves
        self._orientation_changed = True #TODO: fix this hack...
        self.queue_resize()

        print len(self._items), len(self._handles) + 1
        assert len(self._items) == len(self._handles) + 1
        return self.item_num(child)

    def _remove_item(self, child):
        '''
        :param child: a :class:`gtk.Widget` to use as the contents of the item.

        The :meth:`_remove_item` method is the private implementation behind
        the :meth:`remove` and :meth:`remove_item` methods.
        '''

        item_num = self.item_num(child)

        if item_num is not None:
            # Unparent the widget
            child.unparent()
            assert not child.get_parent()

            # Remove the DockPanedItem from the list
            del self._items[item_num]

            # If there are still items/handles in the list, we'd like to
            # remove a handle...
            if self._items:
                try:
                    # Remove the DockPanedHandle that used to be located after
                    # the DockPanedItem we just removed
                    del self._handles[item_num]
                except IndexError:
                    # Well, seems we removed the last DockPanedItem from the
                    # list, so we'll remove the DockPanedHandle that used to
                    # be located before the DockPanedItem we just removed
                    del self._handles[item_num - 1]

            self.queue_resize()
        else:
            raise ValueError('Error removing child "%s"' % child)

        assert len(self._items) == len(self._handles) + 1

    def _get_expandable_items(self):
        for item in self._items:
            if item.expand:
                yield item

    def _get_n_expandable_items(self):
        return len(list(self._get_expandable_items()))

    def _s2w(self, size):
        '''
        :param size: an integer size value corresponding to a child's width
                     if the orientation property is gtk.ORIENTATION_HORIZONTAL,
                     otherwise the child's height.
        :returns: the weight value.
        '''

        return ((size << 16) + 999) / 1000

    def _w2s(self, weight):
        '''
        :param size: a weight value
        :returns: the integer size value corresponding to a child's width
                  if the orientation property is gtk.ORIENTATION_HORIZONTAL,
                  otherwise the child's height.
        '''

        return (weight  * 1000) >> 16

    def _redistribute_size(self, delta_size, enlarge, shrink):
        '''
        :param delta_size:

        The :meth:`_redistribute_size` method subtracts size from the items
        specified by `shrink` and adds the freed size to the item specified by
        `enlarge`. This is done until `delta_size` reaches 0, or there's no
        more items left in `shrink`.
        '''

        # Distribute delta_size amongst the items in shrink
        for item in shrink:
            if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                available_size = item.child.allocation.width - item.child.size_request()[0]
            else:
                available_size = item.child.allocation.height - item.child.size_request()[1]

            # Check if we can shrink (respecting the child's size_request)
            if available_size > 0:
                enlarge_rect = enlarge.child.allocation.copy()
                item_rect = item.child.allocation.copy()

                # Can we adjust the whole delta or not?
                if delta_size > available_size:
                    adjustment = available_size
                else:
                    adjustment = delta_size

                if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                    enlarge_rect.width += adjustment
                    item_rect.width -= adjustment
                else:
                    enlarge_rect.height += adjustment
                    item_rect.height -= adjustment

                delta_size -= adjustment

                enlarge.child.size_allocate(enlarge_rect)
                item.child.size_allocate(item_rect)

            if delta_size == 0:
                break

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
        self._orientation_changed = True
        self.notify('orientation')
        self.queue_resize()

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
        gtk.Container.do_map(self)
        self.window.show()

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
                item.min_weight = self._s2w(w)
            else:
                width = max(width, w)
                height += h
                # Store the minimum weight for usage in do_size_allocate
                item.min_weight = self._s2w(h)

        # Add handles
        if self._orientation == gtk.ORIENTATION_HORIZONTAL:
            width += self._get_n_handles() * self._handle_size
        else:
            height += self._get_n_handles() * self._handle_size

        # Done
        requisition.width = width
        requisition.height = height

    def do_size_allocate(self, allocation):
        if self._items:
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
            # "huge value") to each child.
            # You can look at the _s2w and _w2s methods to discover how the
            # weight value is calculated.
            #
            # !!! WARNING !!!
            #
            # Outside of the do_size_request/do_size_allocate dance, the
            # weight values associated with each child widget have absolutely
            # no meaning whatsoever. Therefore, you should not use them for any
            # other purpose!
            ####################################################################

            # Compute weight for child widgets
            for item in self._items:
                if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                    if not item.weight or self._orientation_changed:
                        item.weight = item.min_weight
                    else:
                        item.weight = self._s2w(item.child.allocation.width)
                else:
                    if not item.weight or self._orientation_changed:
                        item.weight = item.min_weight
                    else:
                        item.weight = self._s2w(item.child.allocation.height)

            # Compute old and new total weight
            handle_sizes = self._get_n_handles() * self._handle_size

            if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                old_weight = self._s2w(self.allocation.width - handle_sizes)
                new_weight = self._s2w(allocation.width - handle_sizes)
            else:
                old_weight = self._s2w(self.allocation.height - handle_sizes)
                new_weight = self._s2w(allocation.height - handle_sizes)

            # Compute delta (have we been resized?)
            if old_weight < 0:
                # This is the first time we get allocated...
                delta_weight = 0
            else:
                delta_weight = new_weight - old_weight

            # Adjust child widget weights (if we have been resized)
            if delta_weight and not self._orientation_changed:
                n_expandable_items = self._get_n_expandable_items()

                if n_expandable_items:
                    d = delta_weight / n_expandable_items


                    for item in self._get_expandable_items():
                        if item.weight + d <= item.min_weight:
                            item.weight = item.min_weight
                        else:
                            item.weight += d
                else:
                    d = delta_weight / self.get_n_items()

                    for item in self._items:
                        if item.weight + d <= item.min_weight:
                            item.weight = item.min_weight
                        else:
                            item.weight += d

            ####################################################################
            # And now we continue the regular child widget allocation fun
            ####################################################################
            cx = cy = 0  # current x and y counters

            # Allocate child widgets
            for child in self._children():
                rect = gdk.Rectangle()
                rect.x = cx
                rect.y = cy

                if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                    rect.height = allocation.height
                else:
                    rect.width = allocation.width

                if isinstance(child, _DockPanedItem):
                    if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                        size = self._w2s(child.weight)
                        rect.width = size
                        cx += size
                    else:
                        size = self._w2s(child.weight)
                        rect.height = size
                        cy += size

                    # Allocate child sizes
                    if child is self._items[-1]:
                        # Give any extra space left to the last item in the list
                        if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                            rect.width += allocation.width - cx
                        else:
                            rect.height += allocation.height - cy

                    child.child.size_allocate(rect)
                elif isinstance(child, _DockPanedHandle):
                    if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                        rect.width = self._handle_size
                        cx += self._handle_size
                    else:
                        rect.height = self._handle_size
                        cy += self._handle_size

                    child.area = rect

        # Accept new allocation
        self.allocation = allocation

        # Move/Resize our GdkWindow
        if self.flags() & gtk.REALIZED:
            self.window.move_resize(*allocation)

        self._orientation_changed = False

    def do_expose_event(self, event):
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
            else:
                return False

    def do_button_release_event(self, event):
        # Reset drag context
        if event.button == self._dragcontext.source_button:
            self._dragcontext.reset()
            return True

        return False

    def do_motion_notify_event(self, event):
        cursor = None

        # Set an appropriate cursor when the pointer is over a handle
        if self._get_handle_at_pos(event.x, event.y):
            if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                cursor = self._hcursor
            elif self._orientation == gtk.ORIENTATION_VERTICAL:
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
            elif delta_size > 0:
                # Enlarge the item before and shrink the items after the handle
                enlarge = self._items[handle_index]
                shrink = self._items[self._items.index(item_after):]
            else:
                enlarge = None
                shrink = []

            self._redistribute_size(delta_size, enlarge, shrink)
            self.queue_resize()

        # Set the cursor we decided upon above...
        if cursor:
            self.window.set_cursor(cursor)

    ############################################################################
    # GtkContainer
    ############################################################################
    def do_get_child_property(self, child, property_id, pspec):
        if pspec.name == 'expand':
            for item in self._items:
                if item.child is child:
                    return item.expand
                    break
            else:
                #TODO: improve this message...
                raise ValueError('Widget specified by child is not a child of ours...')

    def do_set_child_property(self, child, property_id, value, pspec):
        if pspec.name == 'expand':
            for item in self._items:
                if item.child is child:
                    item.expand = value
                    item.child.child_notify('expand')
                    break
            else:
                #TODO: improve this message...
                raise ValueError('Widget specified by child is not a child of ours...')

    def do_forall(self, internals, callback, data):
        try:
            for item in self._items:
                callback(item.child, data)
        except AttributeError:
            pass

    def do_add(self, widget):
        if widget not in (item.child for item in self._items):
            self._insert_item(widget, expand=True)

    def do_remove(self, widget):
        self._remove_item(widget)

    ############################################################################
    # EtkDockPaned
    ############################################################################
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

    def insert_item(self, child, position=None, expand=True):
        '''
        :param child: a :class:`gtk.Widget`` to use as the contents of the item.
        :param position: the index (starting at 0) at which to insert the item,
                         negative or :const:`None` to append the item after all
                         other items.
        :param expand: :const:`True` if `child` is to be given extra space
                       allocated to dockpaned. The extra space will be divided
                       evenly between all children of the dockpaned that use
                       this option.
        :returns: the index number of the item in the dockpaned.

        The :meth:`insert_item` method inserts an item into the dockpaned at the
        location specified by `position` (0 is the first item). `child` is the
        widget to use as the contents of the item. If position is negative or
        :const:`None` the item is appended to the dockpaned.
        '''

        item_num = self._insert_item(child, position, expand)
        self.emit('add', child)
        return item_num

    def remove_item(self, item_num):
        '''
        :param item_num: the index of an item, starting from 0. If :const:`None`
                         or negative, the last item will be removed.

        The :meth:`remove_item` method removes the item at the location
        specified by `item_num`. The value of `item_num` starts from 0. If
        `item_num` is negative or :const:`None` the last item of the dockpaned
        will be removed.
        '''

        if item_num is None or item_num < 0:
            item = self.get_nth_item(self.get_n_items())
        else:
            item = self.get_nth_item(item_num)

        self._remove_item(item.child)

    def item_num(self, child):
        '''
        :param child: a :class:`gtk.Widget`.
        :returns: the index of the item containing `child`, or :const:`None` if
                  `child` is not in the dockpaned.

        The :meth:`item_num()` method returns the index of the item which
        contains the widget specified by `child` or :const:`None` if no item
        contains `child`.
        '''

        for item in self._items:
            if item.child is child:
                return self._items.index(item)
        else:
            return None

    def _get_n_handles(self):
        '''
        :returns: the number of handles in the dockpaned.

        The :meth:`_get_n_handles‘ method returns the number of handles in the
        dockpaned.
        '''

        return len(self._handles)

    def get_n_items(self):
        '''
        :returns: the number of child widgets in the dockpaned.

        The :meth:`get_n_items‘ method returns the number of child widgets in
        the dockpaned.
        '''

        return len(self._items)

    def get_nth_item(self, item_num):
        '''
        :param item_num: the index of an item in the dockpaned.
        :returns: the child widget, or :const:`None` if `item_num` is out of
                  bounds.

        The :meth:`get_nth_item‘ method returns the child widget contained at
        the index specified by `item_num`. If `item_num` is out of bounds for
        the item range of the dockpaned this method returns :const:`None`.
        '''

        if item_num >= 0 and item_num <= self.get_n_items() - 1:
            return self._items[item_num]
        else:
            return None

    def _get_handle_at_pos(self, x, y):
        '''
        :param x: the x coordinate of the position
        :param y: the y coordinate of the position
        :returns: the handle at the position specified by x and y or :const:`None`

        The :meth:`_get_handle_at_pos` method returns the handle whose area
        contains the position specified by `x` and `y` or :const:`None` if no
        handle is at that position.
        '''

        for handle in self._handles:
            if (x, y) in handle:
                return handle
        else:
            return None

    def get_item_at_pos(self, x, y):
        '''
        :param x: the x coordinate of the position
        :param y: the y coordinate of the position
        :returns: the item at the position specified by x and y or :const:`None`

        The :meth:`get_item_at_pos` method returns the child widget whose allocation
        contains the position specified by `x` and `y` or :const:`None` if no
        child widget is at that position.
        '''

        for item in self._items:
            if (x, y) in item:
                return item
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

        if not item_num:
            #TODO: improve this message...
            raise ValueError('widget is not a child of this DockPaned')
        else:
            if position is None or position < 0 or position > self.get_n_items() - 1:
                position = self.get_n_items()

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
