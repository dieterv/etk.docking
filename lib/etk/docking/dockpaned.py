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
from .util import rect_contains, rect_overlaps


class _DockPanedHandle(object):
    '''
    Convenience class storing information about a handle.
    '''
    __slots__ = ['area']       # area, used for hit testing (gdk.Rectangle)

    def __init__(self):
        self.area = gdk.Rectangle()

    def __contains__(self, pos):
        return rect_overlaps(self.area, *pos)


class _DockPanedItem(object):
    '''
    Convenience class storing information about a child.
    '''
    __slots__ = ['child',      # child widget
                 'min_weight', # minimum relative weight
                 'weight',     # relative weight, used to calculate width/height
                 'area',       # area, used to calculate allocation (gdk.Rectangle)
                 'expand']     # used to store the 'expand' child property

    def __init__(self):
        self.child = None
        self.min_weight = None
        self.weight = None
        self.area = gdk.Rectangle()

    def __contains__(self, pos):
        return rect_contains(self.area, *pos)


class DockPaned(gtk.Container):
    '''
    The etk.DockPaned class groups it's children in panes, either
    horizontally or vertically.
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
        self.set_redraw_on_allocate(False)

        # Initialize logging
        self.log = getLogger('%s.%s' % (self.__gtype_name__, hex(id(self))))
        self.log.debug('')

        # Initialize properties
        self.set_orientation(gtk.ORIENTATION_HORIZONTAL)
        self.set_handle_size(4)

        # Initialize attributes
        self._children = [] # Note: list contains both items and handles.
        self._reset_weights = True
        self._hcursor = None
        self._vcursor = None

        # Initialize handle dragging (this is not DnD!)
        self.dragcontext = DockDragContext()

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
        self._reset_weights = True
        self.queue_resize()
        self.notify('orientation')

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
                                               gdk.LEAVE_NOTIFY_MASK |
                                               gdk.BUTTON_PRESS_MASK |
                                               gdk.BUTTON_RELEASE_MASK |
                                               gdk.POINTER_MOTION_MASK))
        self.window.set_user_data(self)
        self.style.attach(self.window)
        self.style.set_background(self.window, gtk.STATE_NORMAL)

        # Set parent window on all child widgets
        for item in self._children:
            if isinstance(item, _DockPanedItem):
                item.child.set_parent_window(self.window)

        # Initialize cursors
        self._hcursor = gtk.gdk.Cursor(self.get_display(), gdk.SB_H_DOUBLE_ARROW)
        self._vcursor = gtk.gdk.Cursor(self.get_display(), gdk.SB_V_DOUBLE_ARROW)

    def do_unrealize(self):
        self.log.debug('')
        self._hcursor = None
        self._vcursor = None
        self.window.set_user_data(None)
        self.window.destroy()
        gtk.Container.do_unrealize(self)

    def do_map(self):
        self.log.debug('')

        gtk.Container.do_map(self)
        self.window.show()

    def do_unmap(self):
        self.log.debug('')

        self.window.hide()
        gtk.Container.do_unmap(self)

    def do_size_request(self, requisition):
        self.log.debug('%s' % requisition)

        # Compute total size request
        width = height = 0

        for item in self._children:
            if isinstance(item, _DockPanedItem):
                w, h = item.child.size_request()

                if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                    item.min_weight = ((w << 16) + 999) / 1000
                    width += w
                    height = max(height, h)
                else:
                    item.min_weight = ((h << 16) + 999) / 1000
                    width = max(width, w)
                    height += h
            else:
                if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                    width += self._handle_size
                else:
                    height += self._handle_size

        requisition.width = width
        requisition.height = height

    def do_size_allocate(self, allocation):
        self.log.debug('%s' % allocation)

        # Compute old and new total weight
        if self._orientation == gtk.ORIENTATION_HORIZONTAL:
            old_weight = (((self.allocation.width - (self._get_n_handles() * self._handle_size)) << 16) + 999) / 1000
            new_weight = (((allocation.width - (self._get_n_handles() * self._handle_size)) << 16) + 999) / 1000
        else:
            old_weight = (((self.allocation.height - (self._get_n_handles() * self._handle_size)) << 16) + 999) / 1000
            new_weight = (((allocation.height - (self._get_n_handles() * self._handle_size)) << 16) + 999) / 1000

        # Compute delta if we have been resized
        if self._reset_weights:
            self._reset_weights = False
            requested_weights = 0

            for item in self._children[::2]:
                item.weight = item.min_weight
                requested_weights += item.min_weight

            delta_size = new_weight - requested_weights
        else:
            delta_size = new_weight - old_weight

        # Accept new allocation
        self.allocation = allocation

        # Move/Resize our GdkWindow
        if self.flags() & gtk.REALIZED:
            self.window.move_resize(*allocation)

        if self._children:
            # Adjust weights if we have been resized
            if delta_size:
                d = delta_size / self.get_n_items()

                for item in self._children[::2]:
                    if item.weight + d <= item.min_weight:
                        item.weight = item.min_weight
                    else:
                        item.weight += d

            # Compute allocation for our children
            cx = cy = 0  # current x and y counters

            for item in self._children:
                if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                    item.area.x = cx
                    item.area.y = cy
                    item.area.height = allocation.height

                    if isinstance(item, _DockPanedItem):
                        item.area.width = item.weight * 1000 >> 16
                    else:
                        item.area.width = self._handle_size

                    cx += item.area.width
                else:
                    item.area.x = cx
                    item.area.y = cy
                    item.area.width = allocation.width

                    if isinstance(item, _DockPanedItem):
                        item.area.height = item.weight * 1000 >> 16
                    else:
                        item.area.height = self._handle_size

                    cy += item.area.height

            # Give any extra space left to the last item in the list
            if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                self._children[-1].area.width += allocation.width - cx
            else:
                self._children[-1].area.height += allocation.height - cy

            # Allocate child sizes
            for item in self._children:
                if isinstance(item, _DockPanedItem):
                    item.child.size_allocate(item.area)

    def do_expose_event(self, event):
        self.log.debug('%s' % event)

        for item in self._children[1::2]:
            #TODO: render themed handle if not using compact layout
            pass

        return False

    def do_leave_notify_event(self, event):
        self.log.debug('%s' % event)

        # Reset cursor
        self.window.set_cursor(None)

    def do_button_press_event(self, event):
        '''
        :param event: the event that triggered the signal
        :returns : True to stop other handlers from being invoked for the event.
                   False to propagate the event further.

        The do_button_press_event() signal handler is executed when a mouse
        button is pressed.
        '''
        self.log.debug('%s' % event)

        # We might start a drag operation, or we could simply be starting
        # a click somewhere. Store information from this event in self.dragcontext
        # and decide in do_motion_notify_event if we're actually starting a
        # drag operation.
        if event.window is self.window and event.button == 1:
            for item in self._children[1::2]:
                if (event.x, event.y) in item:
                    self.dragcontext.dragging = True
                    self.dragcontext.dragged_object = item
                    self.dragcontext.source_x = event.x
                    self.dragcontext.source_y = event.y
                    self.dragcontext.source_button = event.button
                    break

    def do_button_release_event(self, event):
        '''
        :param event: the event that triggered the signal
        :returns : True to stop other handlers from being invoked for the event.
                   False to propagate the event further.

        The do_button_release_event() signal handler is executed when a mouse
        button is released.
        '''
        self.log.debug('%s' % event)

        # Reset drag context
        if event.button == self.dragcontext.source_button:
            self.dragcontext.reset()

    def do_motion_notify_event(self, event):
        '''
        :param event: the event that triggered the signal
        :returns : True to stop other handlers from being invoked for the event.
                   False to propagate the event further.

        The do_motion-notify-event() signal handler is executed when the mouse
        pointer moves while over this widget.
        '''
        self.log.debug('%s' % event)

        cursor = None

        # Set an appropriate cursor when the pointer is over a handle
        if event.window is self.window:
            for item in self._children[1::2]:
                if (event.x, event.y) in item:
                    if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                        cursor = self._hcursor
                    elif self._orientation == gtk.ORIENTATION_VERTICAL:
                        cursor = self._vcursor

                    break

        # Drag a handle
        if self.dragcontext.dragging:
            children = self._children[::2]
            handle_index = self._children.index(self.dragcontext.dragged_object)
            item_before = self._children[handle_index - 1]
            item_after = self._children[handle_index + 1]

            if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                cursor = self._hcursor
                delta_size = int(self.get_pointer()[0] - self.dragcontext.source_x)
            else:
                cursor = self._vcursor
                delta_size = int(self.get_pointer()[1] - self.dragcontext.source_y)

            delta_weight = ((delta_size << 16) + 999) / 1000

            if delta_weight < 0:
                # Enlarge the item after and shrink the items before the handle
                delta_weight = abs(delta_weight)
                enlarge = item_after
                shrink = reversed(children[:children.index(item_after)])
            elif delta_weight > 0:
                # Enlarge the item before and shrink the items after the handle
                enlarge = item_before
                shrink = children[children.index(item_after):]
            else:
                enlarge = None
                shrink = []

            self._redistribute_weight(delta_weight, enlarge, shrink)

            # Store current drag position
            self.dragcontext.source_x = event.x
            self.dragcontext.source_y = event.y

            self.queue_resize()

        # Set the cursor we decided above...
        if cursor:
            self.window.set_cursor(cursor)

    ############################################################################
    # GtkContainer
    ############################################################################
    def do_get_child_property(self, child, pspec):
        if pspec.name == 'expand':
            self.log.debug('%s, %s' % child, pspec)

    def do_set_child_property(self, child, value, pspec):
        if pspec.name == 'expand':
            self.log.debug('%s, %s, %s' % child, pspec, value)
            self.child_notify('expand')

    def do_forall(self, internals, callback, data):
        try:
            for item in self._children:
                if isinstance(item, _DockPanedItem):
                    callback(item.child, data)
        except AttributeError:
            pass

    def do_add(self, widget):
        if widget not in (item.child for item in self.items):
            self._insert_child(widget, expand=True)

    def do_remove(self, widget):
        # Get the _DockPanedItem associated with widget
        self.log.debug('')
        for item in self._children:
            if isinstance(item, _DockPanedItem) and item.child is widget:
                item.child.unparent()
                index = self._children.index(item)
                # Remove the DockPanedItem from the list
                del self._children[index]

                # If there are still items/handles in the list, we'd like to
                # remove a handle...
                if self._children:
                    try:
                        # Remove the DockPanedHandle that used to be located after
                        # the DockPanedItem we just removed
                        del self._children[index]
                    except IndexError:
                        # Well, seems we removed the last DockPanedItem from the
                        # list, so we'll remove the DockPanedHandle that used to
                        # be located before the DockPanedItem we just removed
                        del self._children[index - 1]

                break

        #TODO: this is a hack! remove it!
        self._reset_weights = True
        self.queue_resize()

    ############################################################################
    # EtkDockPaned
    ############################################################################
    def _redistribute_weight(self, delta_weight, enlarge, shrink):
        '''
        The _redistribute_weight method subtracts weight from the items
        specified by shrink and adds the freed weight to the item
        specified by enlarge. This is done until delta_weight reaches 0,
        or there's no more items left in shrink.
        '''
        # Distribute delta_size amongst the children marked as shrinkable
        for item in shrink:
            available_weight = item.weight - item.min_weight

            # Check if we can shrink (respecting the child's size_request)
            if available_weight > 0:
                # Can we adjust the whole delta or not?
                if delta_weight > available_weight:
                    adjustment = available_weight
                else:
                    adjustment = delta_weight

                enlarge.weight += adjustment
                item.weight -= adjustment
                delta_weight -= adjustment

            if delta_weight == 0:
                break

    def insert_child(self, widget, position=-1, expand=True):
        self._insert_child(widget, position, expand)
        self.emit('add', widget)

    def _insert_child(self, widget, position=-1, expand=True):
        '''
        Private logic, shared between public interface and add event handler.
        '''
        #TODO: implement 'expand' child property...
        handle = _DockPanedHandle()
        item = _DockPanedItem()
        item.expand = expand
        item.child = widget
        item.child.set_parent(self)
        item.child.child_notify('expand')

        if position == -1:
            if len(self._children) >= 1:
                self._children.append(handle)

            self._children.append(item)

        else:
            if len(self._children) >= 1:
                self._children.insert(position * 2, handle)

            self._children.insert(position * 2, item)

        if self.flags() & gtk.REALIZED:
            item.child.set_parent_window(self.window)

        #TODO: this is a hack! remove it!
        self._reset_weights = True
        self.queue_resize()

    #TODO: def append_item(self, item):
    #TODO: def prepend_item(item, tab_label=None)
    #TODO: def insert_item(item, tab_label=None, position=-1)
    #TODO: def remove_item(self, item_num):
    #TODO: def get_current_item(self):
    #TODO: def get_nth_item(self, item_num):

    handles = property(lambda s: s._children[1::2])

    items = property(lambda s: s._children[::2])

    def _get_n_handles(self):
        '''
        The _get_n_handles() method returns the number of handles in the DockPaned.
        '''
        return int(len(self.handles))

    def get_n_items(self):
        '''
        The get_n_items() method returns the number of items in the DockPaned.
        '''
        return int(len(self.items))

    def get_handle_at_pos(self, x, y):
        '''
        :param x: the x coordinate of the position
        :param y: the y coordinate of the position
        :returns: the handle at the position specified by x and y or None

        The get_handle_at_pos() method returns the _DockPanedHandle whose area
        contains the position specified by x and y or None if no handle is at
        that position.
        '''
        for h in self.handles:
            if (x, y) in h:
                return h
        else:
            return None

    def get_item_at_pos(self, x, y):
        '''
        :param x: the x coordinate of the position
        :param y: the y coordinate of the position
        :returns: the item at the position specified by x and y or None
        '''
        for i in self.items:
            if (x, y) in i:
                return i
        else:
            return None

    #TODO: def item_num(self, item):
    #TODO: def set_current_item(self, item_num):
    #TODO: def next_item()
    #TODO: def prev_item()
    #TODO: def reorder_item(item, position)

############################################################################
# Install child properties
############################################################################
for index, (name, pspec) in enumerate(DockPaned.__gchild_properties__.iteritems()):
    pspec = list(pspec)
    pspec.insert(0, name)
    DockPaned.install_child_property(index + 1, tuple(pspec))
