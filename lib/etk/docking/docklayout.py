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

from simplegeneric import generic

from .dockframe import DockFrame
from .dockgroup import DockGroup, DRAG_TARGET_ITEM_LIST
from .dockpaned import DockPaned


class DockLayout(object):

    def __init__(self):

        # Initialize logging
        self.log = getLogger('%s.%s' % (self.__class__.__name__, hex(id(self))))
        self.log.debug('')

        self.frames = set()
        # Map widget -> set([signals, ...])
        self._signal_handlers = {}

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
        signals = set()
        # TODO: Remove Highlight flag. Create it ourselves.
        widget.drag_dest_set(gtk.DEST_DEFAULT_MOTION,
                             [DRAG_TARGET_ITEM_LIST],
                             gdk.ACTION_MOVE)

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
        # TODO: Maybe find the ite we live in there and create a new context
        # (based on the widget) if it does not exist yes (using a dict).
        # This way we can create all motion/leave/drop/data_received stuff
        # in one simple class. Clear the dict in leave events.
        # Condition is it should be simpler to find the actual item to find the 
        # context to work in. For example it may be simpler if 
        self.log.debug('on widget drag motion %s: %s %s', widget, x, y)
        return drag_motion(widget, context, x, y, timestamp)

    def on_widget_drag_leave(self, widget, context, timestamp):
        self.log.debug('on widget drag leave')
        return drag_leave(widget, context, timestamp)

    def on_widget_drag_drop(self, widget, context, x, y, timestamp):
        self.log.debug('on widget drag drop: %s %s', x, y)
        return drag_drop(widget, context, x, y, timestamp)

    def on_widget_drag_data_received(self, widget, context, x, y, selection_data, info, timestamp):
        self.log.debug('on widget drag data recieved, %s, %s, %s, %s, %s, %s' % (context, x, y, selection_data, info, timestamp))
        return drag_data_received(widget, context, x, y, selection_data, info, timestamp)

    def on_widget_drag_end(self, widget, context):
        return drag_end(widget, context)

    def on_widget_drag_failed(self, widget, context, result):
        return drag_failed(widget, context, result)


def get_parent_info(widget):
    '''
    :param widget: the gtk.Widget to obtain parent info from
    :returns: Tuple (parent widget, px, py), where px/py is the parent item offset
    '''
    parent = widget.get_parent()

    # We can use gtk.Widget.get_window(widget) instead of special casing
    # gtk.TextView.get_window (mapped to gtk_text_view_get_window in pygtk
    # whereas get_window for other widgets is mapped to gtk_widget_get_window).
    if isinstance(widget, gtk.Widget):
        w = gtk.Widget.get_window(widget)

    px, py = w.get_position()
    return parent, px, py

@generic
def drag_motion(widget, context, x, y, timestamp):
    '''
    :param context: the gdk.DragContext
    :param x: the X position of the drop
    :param y: the Y position of the drop
    :param timestamp: the time of the drag event
    :returns: True if the cursor is in a drop zone

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
    '''
    parent, px, py = get_parent_info(widget)
    return parent and drag_motion(parent, context, px + x, px + y, timestamp)

@generic
def drag_leave(widget, context, timestamp):
    '''
    :param context: the gdk.DragContext
    :param timestamp: the time of the drag event

    The do_drag_leave() signal handler is executed when the drag operation
    moves off of a drop target widget. A typical reason to use this signal
    handler is to undo things done in the do_drag_motion() handler, e.g. undo
    highlighting with the drag_unhighlight() method.
    '''
    parent = widget.get_parent()
    if parent:
        drag_leave(parent, context, timestamp)

@generic
def drag_drop(widget, context, x, y, timestamp):
    '''
    :param context: the gdk.DragContext
    :param x: the X position of the drop
    :param y: the Y position of the drop
    :param timestamp: the time of the drag event
    :returns: True if the cursor is in a drop zone

    The do_drag_drop() signal handler is executed when the drag initiates a
    drop operation on the destination widget. The signal handler must
    determine whether the cursor position is in a drop zone or not. If it is
    not in a drop zone, it returns False and no further processing is
    necessary. Otherwise, the handler returns True. In this case, the handler
    must ensure that the gdk.DragContext.finish() method is called to let
    the source know that the drop is done. The call to the
    gdk.DragContext.finish() method can be done either directly or in the
    do_drag_data_received() handler that gets triggered by calling the
    drag_get_data() method to receive the data for one or more of the
    supported targets.
    '''
    parent, px, py = get_parent_info(widget)
    return parent and drag_drop(parent, context, px + x, px + y, timestamp)

@generic
def drag_data_received(widget, context, x, y, selection_data, info, timestamp):
    '''
    :param context: the gdk.DragContext
    :param x: the X position of the drop
    :param y: the Y position of the drop
    :param selection_data: a gtk.SelectionData object
    :param info: an integer ID for the drag
    :param timestamp: the time of the drag event

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
    parent, px, py = get_parent_info(widget)
    if parent:
        drag_data_received(parent, context, px + x, px + y, selection_data, info, timestamp)

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
# TODO: Put all methods in a generic "role" class. This instance should be used
#       in motion, leave, etc. cases. Investigate.
# TODO: Deal with drag_end in order to clear destroy groups.
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
    target = self.drag_dest_find_target(context, ());

    dock_group_highlight(self)

    return True

@drag_leave.when_type(DockGroup)
def dock_group_drag_leave(self, context, timestamp):
    dock_unhighlight(self)

@drag_drop.when_type(DockGroup)
def dock_group_drag_drop(self, context, x, y, timestamp):
    self.log.debug('%s, %s, %s, %s' % (context, x, y, timestamp))

    target = self.drag_dest_find_target(context, [DRAG_TARGET_ITEM_LIST])
    item_target = gdk.atom_intern(DRAG_TARGET_ITEM_LIST[0])

    if target == item_target:
        # Register location where to drop
        self.log.debug('Dropping item/group at index %s with target %s' % (self._drop_tab_index, target))
        self.drag_get_data(context, target, timestamp)
        return True

    return False

@drag_data_received.when_type(DockGroup)
def dock_group_drag_data_received(self, context, x, y, selection_data, info, timestamp):
    self.log.debug('%s, %s, %s, %s, %s, %s' % (context, x, y, selection_data, info, timestamp))

    source = context.get_source_widget()
    assert source

    if selection_data.target == gdk.atom_intern(DRAG_TARGET_ITEM_LIST[0]):
        self.log.debug('Recieving item %s' % source.dragcontext.dragged_object)
        for tab in reversed(source.dragcontext.dragged_object):
            self.insert_item(tab.item, visible_position=self._drop_tab_index)
        context.finish(True, True, timestamp) # success, delete, time
    else:
        context.finish(False, False, timestamp) # success, delete, time

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
    except (AttributeError, IndexError), e:
        pass
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
def dock_paned_drag_motion(self, context, x, y, timestamp):
    self.log.debug('%s, %s, %s, %s' % (context, x, y, timestamp))

    dock_paned_highlight(self)

    handle = self.get_handle_at_pos(x, y)
    if handle:
        self._drop_handle_index = self.handles.index(self.get_handle_at_pos(x, y))
    else:
        self._drop_handle_index = None
    
    return True

@drag_leave.when_type(DockPaned)
def dock_paned_drag_leave(self, context, timestamp):
    dock_unhighlight(self)

@drag_drop.when_type(DockPaned)
def dock_paned_drag_drop(self, context, x, y, timestamp):
    self.log.debug('%s, %s, %s, %s' % (context, x, y, timestamp))

    target = self.drag_dest_find_target(context, [DRAG_TARGET_ITEM_LIST])
    item_target = gdk.atom_intern(DRAG_TARGET_ITEM_LIST[0])

    if target == item_target:
        # Register location where to drop
        self.log.debug('Dropping item-list with target %s' % (target,))
        self.drag_get_data(context, target, timestamp)
        return True

    return False

@drag_data_received.when_type(DockPaned)
def dock_paned_drag_data_received(self, context, x, y, selection_data, info, timestamp):
    self.log.debug('%s, %s, %s, %s, %s, %s' % (context, x, y, selection_data, info, timestamp))

    source = context.get_source_widget()

    if selection_data.target == gdk.atom_intern(DRAG_TARGET_ITEM_LIST[0]):
        self.log.debug('Recieving item %s' % source.dragcontext.dragged_object)
        if self._drop_handle_index is not None:
            # If on handle: create new DockGroup and add items
            dock_group = DockGroup()
            self.insert_child(dock_group, self._drop_handle_index + 1)
            dock_group.show()
            for tab in source.dragcontext.dragged_object:
                dock_group.insert_item(tab.item)
            context.finish(True, True, timestamp) # success, delete, time
        elif False:
            # If on side: add new DockGroup and add items
            pass
        else:
            context.finish(False, False, timestamp) # success, delete, time
    else:
        context.finish(False, False, timestamp) # success, delete, time

# Attached to drag *source*
@drag_end.when_type(DockPaned)
def dock_group_drag_end(self, context):
    self.log.debug('checking for removal')
    if not self.items:
        parent = self.get_parent()
        self.log.debug('removing empty paned')
        self.destroy()
        return parent and drag_end(parent, context)




################################################################################
# DockFrame
################################################################################

# TODO: Deal with drop events that are not accepted by any Paned. Provided the
# outermost n pixels are not used by the item itself, but propagate the event
# to the parent widget. This means that sometimes the event ends up in the
# "catch-all", the DockFrame.  The Frame should make sure a new DockPaned is
# created with the proper orientation and whatever's needed.
