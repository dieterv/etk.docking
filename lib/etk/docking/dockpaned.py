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


from __future__ import absolute_import, division
from logging import getLogger

import gobject
import gtk
import gtk.gdk as gdk

from .dnd import DockDragContext
from .util import rect_overlaps


class _DockPanedHandle(object):
    '''
    Convenience class storing information about a handle.
    '''
    __slots__ = ['area']    # area, used for hit testing (gdk.Rectangle)

    def __init__(self):
        self.area = gdk.Rectangle()

    def __contains__(self, pos):
        return rect_overlaps(self.area, pos[0], pos[1])


class _DockPanedItem(object):
    '''
    Convenience class storing information about a child.
    '''
    __slots__ = ['child',   # child widget
                 'area']    # area, used to calculate allocation (gdk.Rectangle)

    def __init__(self):
        self.child = None
        self.area = gdk.Rectangle()


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
        self.log = getLogger('%s.%s' % (self.__gtype_name__, hex(id(self))))

        # Initialize properties
        self.set_orientation(gtk.ORIENTATION_HORIZONTAL)
        self.set_handle_size(4)

        # Initialize attributes
        self._children = []

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
            if isinstance(item, gtk.Widget):
                item.child.set_parent_window(self.window)

    def do_unrealize(self):
        self.log.debug('')

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
                    width += w
                    height = max(height, h)
                else:
                    width = max(width, w)
                    height += h
            elif isinstance(item, _DockPanedHandle):
                if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                    width += self._handle_size
                else:
                    height += self._handle_size

        requisition.width = width
        requisition.height = height

    def do_size_allocate(self, allocation):
        self.log.debug('%s' % allocation)

        self.allocation = allocation

        if self.flags() & gtk.REALIZED:
            self.window.move_resize(*allocation)

        cx = cy = 0  # current x and y counters
        min_size = 0 # minimum required width/height

        # Calculate minimum size
        for item in self._children:
            if isinstance(item, _DockPanedItem):
                if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                    requested_size = item.child.get_child_requisition()[0]
                    item.area.width = requested_size
                else:
                    requested_size = item.child.get_child_requisition()[1]
                    item.area.height = requested_size

                min_size += requested_size
            elif isinstance(item, _DockPanedHandle):
                min_size += self._handle_size

        # Calculate extra_size
        if self._orientation == gtk.ORIENTATION_HORIZONTAL:
            extra_size = allocation.width - min_size
        else:
            extra_size = allocation.height - min_size

        quotient, remainder = divmod(extra_size, self.get_n_items())

        # Give items their requested minimum size + extra size
        for item in self._children:
            if isinstance(item, _DockPanedItem):
                item.area.x = cx
                item.area.y = cy
                if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                    item.area.width += quotient
                    item.area.height = allocation.height
                    cx += item.area.width
                else:
                    item.area.width = allocation.width
                    item.area.height += quotient
                    cy += item.area.height
            elif isinstance(item, _DockPanedHandle):
                item.area.x = cx
                item.area.y = cy
                if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                    item.area.width = self._handle_size
                    item.area.height = allocation.height
                    cx += self._handle_size
                else:
                    item.area.width = allocation.width
                    item.area.height = self._handle_size
                    cy += self._handle_size

        # Give the remainder size to the last item in the list
        if self._orientation == gtk.ORIENTATION_HORIZONTAL:
            self._children[-1].area.width += remainder
        elif self._orientation == gtk.ORIENTATION_VERTICAL:
            self._children[-1].area.height += remainder

        # Allocate child sizes
        for item in self._children:
            if isinstance(item, _DockPanedItem):
                item.child.size_allocate(item.area)

    def do_expose_event(self, event):
        self.log.debug('%s' % event)

        for item in self._children:
            if isinstance(item, _DockPanedItem):
                self.propagate_expose(item.child, event)
            elif isinstance(item, _DockPanedHandle):
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
            for item in self._children:
                if isinstance(item, _DockPanedHandle) and (event.x, event.y) in item:
                    self.dragcontext.dragging = False
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
            self.dragcontext.dragging = False
            self.dragcontext.dragged_object = None
            self.dragcontext.source_x = None
            self.dragcontext.source_y = None
            self.dragcontext.source_button = None

    def do_motion_notify_event(self, event):
        '''
        :param event: the event that triggered the signal
        :returns : True to stop other handlers from being invoked for the event.
                   False to propagate the event further.

        The do_motion-notify-event() signal handler is executed when the mouse
        pointer moves while over this widget.
        '''
        self.log.debug('%s' % event)

        # Check if we are actually starting a DnD operation
        if not self.dragcontext.dragging and self.dragcontext.dragged_object:
            if event.state & gdk.BUTTON1_MASK and self.dragcontext.source_button == 1:
                if self.drag_check_threshold(self.dragcontext.source_x, self.dragcontext.source_y, event.x, event.y):
                    self.log.debug('begin dragging handle %s' % self.dragcontext.dragged_object)
                    self.dragcontext.dragging = True

        # Set an appropriate cursor
        cursor = None

        if event.window is self.window:
            for item in self._children:
                if isinstance(item, _DockPanedHandle) and (event.x, event.y) in item:
                    if self._orientation == gtk.ORIENTATION_HORIZONTAL:
                        cursor = gtk.gdk.Cursor(self.get_display(), gdk.SB_H_DOUBLE_ARROW)
                    elif self._orientation == gtk.ORIENTATION_VERTICAL:
                        cursor = gtk.gdk.Cursor(self.get_display(), gdk.SB_V_DOUBLE_ARROW)

                    break

        if cursor:
            self.window.set_cursor(cursor)

    ############################################################################
    # GtkContainer
    ############################################################################
    def do_forall(self, internals, callback, data):
        for item in self._children:
            if isinstance(item, _DockPanedItem):
                callback(item.child, data)

    def do_add(self, widget):
        self.insert_child(widget)

    def do_remove(self, widget):
        # Get the _DockPanedItem associated with widget
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

        self.queue_resize()

    ############################################################################
    # EtkDockPaned
    ############################################################################
    def insert_child(self, widget, position=-1):
        handle = _DockPanedHandle()
        item = _DockPanedItem()
        item.child = widget
        item.child.set_parent(self)

        if position == -1:
            if len(self._children) >= 1:
                self._children.append(handle)

            self._children.append(item)

        else:
            if len(self._children) >= 1:
                self._children.append(position * 2, handle)

            self._children.insert(position * 2, item)

        if self.flags() & gtk.REALIZED:
            item.child.set_parent_window(self.window)

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
        return int(len(self._children) / 2) + 1

    #TODO: def item_num(self, item):
    #TODO: def set_current_item(self, item_num):
    #TODO: def next_item()
    #TODO: def prev_item()
    #TODO: def reorder_item(item, position)
