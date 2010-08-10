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
from collections import namedtuple

import gtk
import gtk.gdk as gdk

from simplegeneric import generic

from .dockframe import DockFrame
from .dockgroup import DockGroup, DRAG_TARGET_ITEM_LIST
from .dockpaned import DockPaned

MAGIC_BORDER_SIZE = 10

DragData = namedtuple('DragData', 'drop_widget leave received')

class DockLayout(object):

    def __init__(self):

        # Initialize logging
        self.log = getLogger('%s.%s' % (self.__class__.__name__, hex(id(self))))
        self.log.debug('')

        self.frames = set()
        # Map widget -> set([signals, ...])
        self._signal_handlers = {}

        self._drag_data = None

    def add(self, frame):
        assert isinstance(frame, DockFrame)
        self.frames.add(frame)
        self.add_signal_handlers(frame)

    def remove(self, frame):
        self.remove_signal_handlers(frame)
        self.frames.remove(frame)

    def add_signal_handlers(self, widget):
        """
        Set up signal handlers for layout and child widgets
        """
        if self._signal_handlers.get(widget):
            return
    
        self.log.debug('Adding signal handlers for widget %s' % widget)

        signals = set()
        widget.drag_dest_set(gtk.DEST_DEFAULT_MOTION,
                             [DRAG_TARGET_ITEM_LIST],
                             gdk.ACTION_MOVE)

        # TODO: Deal with gtk.Container subclasses that do not issue add/remove
        #       events on child addition/removal.
        # Use instance methods here, so layout can do additional bookkeeping
        for name, callback in (('add', self.on_widget_add),
                               ('remove', self.on_widget_remove),
                               ('drag_motion', self.on_widget_drag_motion),
                               ('drag-leave', self.on_widget_drag_leave),
                               ('drag-drop', self.on_widget_drag_drop),
                               ('drag-data-received', self.on_widget_drag_data_received),
                               ('drag-end', self.on_widget_drag_end),
                               ('drag-failed', self.on_widget_drag_failed)):
            signals.add(widget.connect(name, callback))
        self._signal_handlers[widget] = signals

        # TODO: Should we limit this to only Dock* instances?
        if isinstance(widget, gtk.Container):
            widget.foreach(self.add_signal_handlers)

    def remove_signal_handlers(self, widget):
        """
        Remove signal handlers.
        """
        try:
            signals = self._signal_handlers[widget]
        except KeyError:
            pass # No signals
        else:
            self.log.debug('Removing signals for widget %s' % widget)
            for s in signals:
                widget.disconnect(s)
            del self._signal_handlers[widget]
            if isinstance(widget, gtk.Container):
                widget.foreach(self.remove_signal_handlers)

    def on_widget_add(self, container, widget):
        """
        Deal with new elements being added to the layout or it's children.
        """
        if isinstance(widget, gtk.Container):
            self.add_signal_handlers(widget)

    def on_widget_remove(self, container, widget):
        """
        Remove signals from containers and subcontainers.
        """
        if isinstance(widget, gtk.Container):
            self.remove_signal_handlers(widget)

    def on_widget_drag_motion(self, widget, context, x, y, timestamp):
        self.log.debug('on widget drag motion %s: %s %s', widget, x, y)

        drag_data = drag_motion(widget, context, x, y, timestamp)
        old_drop_widget = self._drag_data and self._drag_data.drop_widget
        new_drop_widget = drag_data and drag_data.drop_widget
        if new_drop_widget is not old_drop_widget:
            self.on_widget_drag_leave(widget, context, timestamp)
            self._drag_data = drag_data


    def on_widget_drag_leave(self, widget, context, timestamp):
        # Note: when dropping, drag-leave is invoked before drag-drop
        drag_data = self._drag_data
        if drag_data and drag_data.leave:
            self.log.debug('on widget drag leave %s' % drag_data.leave)
            drag_data.leave(drag_data.drop_widget)

    def on_widget_drag_drop(self, widget, context, x, y, timestamp):
        self.log.debug('%s %s %s %s', context, x, y, timestamp)

        if DRAG_TARGET_ITEM_LIST[0] in context.targets:
            drag_data = self._drag_data
        else:
            drag_data = None

        if drag_data and drag_data.drop_widget:
            target = gdk.atom_intern(DRAG_TARGET_ITEM_LIST[0])
            drag_data.drop_widget.drag_get_data(context, target, timestamp)
        return drag_data and drag_data.received

    def on_widget_drag_data_received(self, widget, context, x, y, selection_data, info, timestamp):
        '''
        Execute the received handler using the received handler retrieved in the
        drag_drop event handler.
        '''
        self.log.debug('%s, %s, %s, %s, %s, %s' % (context, x, y, selection_data, info, timestamp))
        drag_data = self._drag_data
        assert drag_data.received
        try:
            drag_data.received(selection_data, info)
        finally:
            self._drag_data = None

    def on_widget_drag_end(self, widget, context):
        return drag_end(widget, context)

    def on_widget_drag_failed(self, widget, context, result):
        return drag_failed(widget, context, result)


def _propagate_to_parent(func, widget, context, x, y, timestamp):
    '''
    Common function to propagate calls to a parent widget.
    '''
    parent = widget.get_parent()
    if parent:
        px, py = parent.get_pointer()
        return func(parent, context, px, py, timestamp)
    else:
        return None


def with_magic_borders(func):
    '''
    decorator for handlers that have sensitive borders, as items may be dropped
    on the parent item as well.
    '''
    def func_with_magic_borders(widget, context, x, y, timestamp):
        # Always ensure we check the parent class:
        handled = _propagate_to_parent(magic_borders, widget, context, x, y, timestamp)
        return handled or func(widget, context, x, y, timestamp)

    func_with_magic_borders.__doc__ = func.__doc__
    return func_with_magic_borders

@generic
def magic_borders(widget, context, x, y, timestamp):
    '''
    :returns: True if the parent widget handled the event

    This method is used to find out if (in case an item is dragged on the border of
    a widget, the parent is eager to take that event instead. This, for example,
    can be used to place items above or below each other in not-yet existing paned
    sections.
    '''
    pass

@generic
def drag_motion(widget, context, x, y, timestamp):
    '''
    :param context: the gdk.DragContext
    :param x: the X position of the drop
    :param y: the Y position of the drop
    :param timestamp: the time of the drag event
    :returns: a tuple (widget, callback) to be called when leaving the
    item (drag_leave event) if the cursor is in a drop zone.

    The do_drag_motion() signal handler is executed when the drag operation
    moves over a drop target widget. The handler must determine if the
    cursor position is in a drop zone or not. If it is not in a drop zone,
    it should return False and no further processing is necessary. Otherwise,
    the handler should return True. In this case, the handler is responsible
    for providing the necessary information for displaying feedback to the
    user, by calling the gdk.DragContext.drag_status() method. If the
    decision to accept or reject the drop can't be made based solely on
    the cursor position and the type of the data, the handler may inspect
    the dragged data by calling the drag_get_data() method and defer the
    gdk.DragContext.drag_status() method call to the do_drag_data_received()
    signal handler.

    Note::
        There is no do_drag_enter() signal handler. The drag receiver has
        to keep track of any do_drag_motion() signals received since the
        last do_drag_leave() signal. The first do_drag_motion() signal
        received after a do_drag_leave() signal should be treated as an
        "enter" signal. Upon an "enter", the handler will typically
        highlight the drop site with the drag_highlight() method.

    drag_data_received(widget, context, x, y, selection_data, info, timestamp):

    The do_drag_data_received() signal handler is executed when the drag
    destination receives the data from the drag operation. If the data was
    received in order to determine whether the drop will be accepted, the
    handler is expected to call the gdk.DragContext.drag_status() method
    and not finish the drag. If the data was received in response to a
    do_drag_drop() signal (and this is the last target to be received),
    the handler for this signal is expected to process the received data
    and then call the gdk.DragContext.finish() method, setting the success
    parameter to True if the data was processed successfully.
    '''
    print 'drag_motion'
    return _propagate_to_parent(drag_motion, widget, context, x, y, timestamp)

@generic
def drag_end(widget, context):
    '''
    :param context: the gdk.DragContext

    The do_drag_end() signal handler is executed when the drag operation is
    completed. A typical reason to use this signal handler is to undo things
    done in the do_drag_begin() handler.
    '''
    parent = widget.get_parent()
    return parent and drag_end(parent, context)
 
@generic
def drag_failed(widget, context, result):
    '''
    :param context: the gdk.DragContext
    :param result: the result of the drag operation
    :returns: True if the failed drag operation has been already handled.

    The do_drag_failed() signal handler is executed on the drag source when
    a drag has failed. The handler may hook custom code to handle a failed
    DND operation based on the type of error. It returns True if the
    failure has been already handled (not showing the default
    "drag operation failed" animation), otherwise it returns False.
    '''
    parent = widget.get_parent()
    return parent and drag_failed(parent, context, result)

################################################################################
# DockGroup
#
# TODO: If cursor is near the border, propagate event to the parent
################################################################################

def dock_group_expose_highlight(self, event):
    try:
        tab = self.visible_tabs[self._drop_tab_index]
    except TypeError:
        a = event.area
    else:
        if tab is self._current_tab:
            a = event.area
        else:
            a = tab.area

    cr = self.window.cairo_create()
    cr.set_source_rgb(0, 0, 0)
    cr.set_line_width(1.0)
    cr.rectangle(a.x + 0.5, a.y + 0.5, a.width - 1, a.height - 1)
    cr.stroke()

def dock_group_highlight(self):
    if not hasattr(self, '_expose_event_id'):
        self.log.debug('attaching expose event')
        self._expose_event_id = self.connect_after('expose-event',
                                                   dock_group_expose_highlight)
    self.queue_resize()

def dock_unhighlight(self):
    self.queue_resize()
    try:
        self.disconnect(self._expose_event_id)
        del self._expose_event_id
    except AttributeError, e:
        self.log.error(e)
    
@drag_motion.when_type(DockGroup)
@with_magic_borders
def dock_group_drag_motion(self, context, x, y, timestamp):
    self.log.debug('%s, %s, %s, %s' % (context, x, y, timestamp))

    # Insert the dragged tab before the tab under (x, y)
    drop_tab = self.get_tab_at_pos(x, y)

    if drop_tab:
        self._drop_tab_index = self.visible_tabs.index(drop_tab)
    elif self._tabs:
        self._drop_tab_index = self.visible_tabs.index(self._current_tab)
    else:
        self._drop_tab_index = None

    dock_group_highlight(self)

    def dock_group_drag_data_received(selection_data, info):
        self.log.debug('%s, %s, %s, %s, %s, %s' % (context, x, y, selection_data, info, timestamp))

        source = context.get_source_widget()
        assert source

        self.log.debug('Recieving item %s' % source.dragcontext.dragged_object)
        for tab in reversed(source.dragcontext.dragged_object):
            self.insert_item(tab.item, visible_position=self._drop_tab_index)
        context.finish(True, True, timestamp) # success, delete, time

    return DragData(self, dock_unhighlight, dock_group_drag_data_received)

# Attached to drag *source*
@drag_end.when_type(DockGroup)
def dock_group_drag_end(self, context):
    self.log.debug('checking for removal')
    if not self.tabs:
        parent = self.get_parent()
        self.log.debug('removing empty group')
        self.destroy()
        #drag_end.default(self, context)
        return parent and drag_end(parent, context)


# Attached to drag *source*
@drag_failed.when_type(DockGroup)
def dock_group_drag_failed(self, context, result):
    self.log.debug('%s, %s' % (context, result))
    for tab in self.dragcontext.dragged_object:
        if not tab.item.get_parent():
            self.insert_item(tab.item, position=self._dragged_tab_index)
    #context.drop_finish(False, 0)
    return True

################################################################################
# DockPaned
################################################################################

def dock_paned_expose_highlight(self, event):
    try:
        handle = self.handles[self._drop_handle_index]
    except (AttributeError, IndexError, TypeError), e:
        print e
        return
    else:
        a = handle.area

    cr = self.window.cairo_create()
    cr.set_source_rgb(0, 0, 0)
    cr.set_line_width(1.0)
    cr.rectangle(a.x + 0.5, a.y + 0.5, a.width - 1, a.height - 1)
    cr.stroke()

def dock_paned_highlight(self):
    if not hasattr(self, '_expose_event_id'):
        self.log.debug('attaching expose event')
        self._expose_event_id = self.connect_after('expose-event',
                                                   dock_paned_expose_highlight)
    self.queue_resize()

@drag_motion.when_type(DockPaned)
@with_magic_borders
def dock_paned_drag_motion(self, context, x, y, timestamp):
    self.log.debug('%s, %s, %s, %s' % (context, x, y, timestamp))


    handle = self.get_handle_at_pos(x, y)
    if handle:
        self._drop_handle_index = self.handles.index(self.get_handle_at_pos(x, y))
    else:
        self._drop_handle_index = None
    
    dock_paned_highlight(self)

    def dock_paned_drag_data_received(selection_data, info):
        self.log.debug('%s, %s, %s, %s, %s, %s' % (context, x, y, selection_data, info, timestamp))

        source = context.get_source_widget()

        self.log.debug('Recieving item %s' % source.dragcontext.dragged_object)
        # If on handle: create new DockGroup and add items
        dock_group = DockGroup()
        self.insert_child(dock_group, self._drop_handle_index + 1)
        dock_group.show()
        for tab in source.dragcontext.dragged_object:
            dock_group.insert_item(tab.item)
        context.finish(True, True, timestamp) # success, delete, time

    return DragData(self, dock_unhighlight, dock_paned_drag_data_received)

# Attached to drag *source*
@drag_end.when_type(DockPaned)
def dock_paned_drag_end(self, context):
    self.log.debug('checking for removal')
    print 'Context:', dir(context)
    if not self.items:
        parent = self.get_parent()
        self.log.debug('removing empty paned')
        self.destroy()
        return parent and drag_end(parent, context)

def dock_paned_magic_borders_leave(self):
    pass

@magic_borders.when_type(DockPaned)
def dock_paned_magic_borders(self, context, x, y, timestamp):
    def handle(create):
        if create:
            print 'Add new DockPaned and add DockGroup'
        elif min(x, y) < MAGIC_BORDER_SIZE:
            print 'Prepend group'
        else:
            print 'Append group'
    a = self.allocation
    print 'MAGIC happens here', self, a, x, y, (map(abs, (a.x - x, a.y - y, a.x + a.width - x, a.y + a.height - y)))
    if abs(min(y, a.height - y)) < MAGIC_BORDER_SIZE:
        print 'HORIZONTAL', y, a.height, min(y, a.height - y) 
        handle(self.get_orientation() == gtk.ORIENTATION_HORIZONTAL)
        return DragData(self, dock_paned_magic_borders_leave, None)
    elif abs(min(x, a.width - x)) < MAGIC_BORDER_SIZE:
        print 'VERTICAL'
        handle(self.get_orientation() == gtk.ORIENTATION_VERTICAL)
        return DragData(self, dock_paned_magic_borders_leave, None)
    return None


################################################################################
# DockFrame
################################################################################


@magic_borders.when_type(DockFrame)
def dock_frame_magic_borders(self, context, x, y, timestamp):
    '''
    Deal with drop events that are not accepted by any Paned. Provided the
    outermost n pixels are not used by the item itself, but propagate the event
    to the parent widget. This means that sometimes the event ends up in the
    "catch-all", the DockFrame.  The Frame should make sure a new DockPaned is
    created with the proper orientation and whatever's needed.
    '''
    a = self.allocation
    print 'LAYOUT MAGIC happens here', self, a, x, y, (map(abs, (a.x - x, a.y - y, a.x + a.width - x, a.y + a.height - y)))
    # Find out if child is a DockPaned. If so, determine orientation
    # Based on position add Dockgroup with opposite orientation
    # If it's a DockGroup, add based on side.
    if x < MAGIC_BORDER_SIZE:
        pass
    elif a.width - x < MAGIC_BORDER_SIZE:
        pass
    elif y < MAGIC_BORDER_SIZE:
        pass
    elif a.height - y < MAGIC_BORDER_SIZE:
        pass
    return None
