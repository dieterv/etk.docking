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
from collections import namedtuple
from logging import getLogger

from simplegeneric import generic

import gobject
import gtk
import gtk.gdk as gdk
import itertools
from weakref import WeakKeyDictionary

from .dnd import DRAG_TARGET_ITEM_LIST, Placeholder
from .dockframe import DockFrame
from .dockpaned import DockPaned
from .dockgroup import DockGroup
from .dockitem import DockItem
from .docksettings import settings
from .util import flatten


MAGIC_BORDER_SIZE = 10
DragData = namedtuple('DragData', 'drop_widget leave received')


class DockLayout(gobject.GObject):
    """
    Manage a dock layout.

    For this to work the toplevel widget in the layout hierarchy should be a
    DockFrame. The DockFrame is registered with the DockLayout. After that
    sophisticated drag-and-drop functionality is present.

    NB. When items are closed, the item-closed signal is emitted. The item is *not*
    destroyed, though.
    """

    __gtype_name__ = 'EtkDockLayout'
    __gsignals__ = {
        'item-closed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                      (gobject.TYPE_OBJECT, gobject.TYPE_OBJECT)),
        'item-selected': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                      (gobject.TYPE_OBJECT, gobject.TYPE_OBJECT)),
    }

    def __init__(self):
        gobject.GObject.__init__(self)

        # Initialize logging
        self.log = getLogger('%s.%s' % (self.__gtype_name__, hex(id(self))))

        self.frames = set()
        self._signal_handlers = {} # Map widget -> set([signals, ...])

        self._focused_item = None
        self._focused_group = None
        self._focus_data = WeakKeyDictionary() # Map item -> last focused widget

        self._drag_data = None

    def add(self, frame):
        assert isinstance(frame, DockFrame)
        self.frames.add(frame)
        self.add_signal_handlers(frame)

    def remove(self, frame):
        self.remove_signal_handlers(frame)
        self.frames.remove(frame)

    def get_main_frames(self):
        """
        Get the frames that are non-floating (the main frames).
        """
        return (f for f in self.frames \
                if not (isinstance(f.get_parent(), gtk.Window) \
                    and f.get_parent().get_transient_for()) )

    def get_floating_frames(self):
        """
        Get the floating frames. Floating frames have a gtk.Window as parent that is
        transient for some other window.
        """
        return (f for f in self.frames \
                if isinstance(f.get_parent(), gtk.Window) \
                    and f.get_parent().get_transient_for() )

    def get_widgets(self, name):
        """
        Get a set of widgets based on their name.
        """
        return filter(lambda w: w.get_name() == name,
                      itertools.chain.from_iterable(flatten(frame) for frame in self.frames))

    def _get_signals(self, widget):
        """
        Get a list of signals to be registered for a specific widget.
        """
        if isinstance(widget, DockPaned):
            signals = (('item-added', self.on_widget_add),
                       ('item-removed', self.on_widget_remove))
        elif isinstance(widget, DockGroup):
            signals = (('item-added', self.on_widget_add),
                       ('item-removed', self.on_widget_remove),
                       ('item-selected', self.on_dockgroup_item_selected))
        elif isinstance(widget, DockItem):
            signals = (('close', self.on_dockitem_close),)
        elif isinstance(widget, gtk.Container):
            signals = (('add', self.on_widget_add),
                       ('remove', self.on_widget_remove))
        else:
            signals = ()


        return signals + (('drag-motion', self.on_widget_drag_motion),
                          ('drag-leave', self.on_widget_drag_leave),
                          ('drag-drop', self.on_widget_drag_drop),
                          ('drag-data-received', self.on_widget_drag_data_received),
                          ('drag-end', self.on_widget_drag_end),
                          ('drag-failed', self.on_widget_drag_failed),
                          ('notify::is-focus', self.on_widget_is_focus))

    def add_signal_handlers(self, widget):
        """
        Set up signal handlers for layout and child widgets
        """
        if self._signal_handlers.get(widget):
            return

        signals = set()
        drag_dest = widget.drag_dest_get_target_list()

        if not drag_dest:
            widget.drag_dest_set(gtk.DEST_DEFAULT_MOTION, [DRAG_TARGET_ITEM_LIST],
                                 gdk.ACTION_MOVE)
        elif DRAG_TARGET_ITEM_LIST not in drag_dest:
            widget.drag_dest_set_target_list(drag_dest + [DRAG_TARGET_ITEM_LIST])

        # Use instance methods here, so layout can do additional bookkeeping
        for name, callback in self._get_signals(widget):
            try:
                signals.add(widget.connect(name, callback))
            except TypeError, e:
                self.log.debug(e)

        self._signal_handlers[widget] = signals

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

            # TODO: widget.drag_dest_set_target_list(drag_dest - [DRAG_TARGET_ITEM_LIST])??

            if isinstance(widget, gtk.Container):
                widget.foreach(self.remove_signal_handlers)

    def update_floating_window_title(self, widget):
        frame = widget.get_ancestor(DockFrame)

        if frame in self.get_floating_frames():
            frame.get_toplevel().set_title(
                ', '.join(
                    map(lambda w: w.title,
                        filter(lambda w: isinstance(w, DockItem),
                            flatten(frame)))))

    def do_item_closed(self, group, item):
        """
        If an item is closed, perform maintenance cleanup.
        """
        if settings[item].auto_remove:
            cleanup(group, self)

    def do_item_selected(self, group, item):
        # Use this callback to grey out the selection on all but the active selection?
        self._focused_item = item

        if not (group is self._focused_group and group.get_tab_state() != gtk.STATE_PRELIGHT):
            if self._focused_group:
                self._focused_group.set_tab_state(gtk.STATE_PRELIGHT)

            self._focused_group = group
            group.set_tab_state(gtk.STATE_SELECTED)

    def on_widget_add(self, container, widget):
        """
        Deal with new elements being added to the layout or it's children.
        """
        if isinstance(widget, gtk.Container):
            self.add_signal_handlers(widget)

        self.update_floating_window_title(container)

    def on_widget_remove(self, container, widget):
        """
        Remove signals from containers and subcontainers.
        """
        if isinstance(widget, gtk.Container):
            self.remove_signal_handlers(widget)

        self.update_floating_window_title(container)

    def on_widget_drag_motion(self, widget, context, x, y, timestamp):
        if DRAG_TARGET_ITEM_LIST[0] in context.targets:
            context.docklayout = self
            drag_data = drag_motion(widget, context, x, y, timestamp)

            old_drop_widget = self._drag_data and self._drag_data.drop_widget
            new_drop_widget = drag_data and drag_data.drop_widget

            if new_drop_widget is not old_drop_widget:
                self.on_widget_drag_leave(widget, context, timestamp)
                self._drag_data = drag_data

    def on_widget_drag_leave(self, widget, context, timestamp):
        # Note: when dropping, drag-leave is invoked before drag-drop
        if DRAG_TARGET_ITEM_LIST[0] in context.targets:
            drag_data = self._drag_data

            if drag_data and drag_data.leave:
                self.log.debug('on widget drag leave %s' % drag_data.leave)
                drag_data.leave(drag_data.drop_widget)

    def on_widget_drag_drop(self, widget, context, x, y, timestamp):
        self.log.debug('drag_drop %s %s %s %s', context, x, y, timestamp)

        if DRAG_TARGET_ITEM_LIST[0] in context.targets:
            drag_data = self._drag_data

            if drag_data and drag_data.drop_widget:
                target = gdk.atom_intern(DRAG_TARGET_ITEM_LIST[0])
                drag_data.drop_widget.drag_get_data(context, target, timestamp)
                return True

            # act as if drag failed:
            source = context.get_source_widget()
            source.emit('drag-failed', context, 1)
            cleanup(source, self)

        return False


    def on_widget_drag_data_received(self, widget, context, x, y, selection_data, info, timestamp):
        '''
        Execute the received handler using the received handler retrieved in the
        drag_drop event handler.
        '''
        self.log.debug('drag_data_received %s, %s, %s, %s, %s, %s' % (context, x, y, selection_data, info, timestamp))

        if DRAG_TARGET_ITEM_LIST[0] in context.targets:
            drag_data = self._drag_data
            assert drag_data.received

            try:
                drag_data.received(selection_data, info)
            finally:
                self._drag_data = None

    def on_widget_drag_end(self, widget, context):
        if DRAG_TARGET_ITEM_LIST[0] in context.targets:
            context.docklayout = self
            return drag_end(widget, context)

    def on_widget_drag_failed(self, widget, context, result):
        if DRAG_TARGET_ITEM_LIST[0] in context.targets:
            context.docklayout = self
            return drag_failed(widget, context, result)

    def on_widget_is_focus(self, widget, pspec):
        """
        The input focus moved to another widget.
        """
        if isinstance(widget, DockItem):
            item = widget
        else:
            item = widget.get_ancestor(DockItem)

        if item:
            self._focus_data[item] = widget

            if item is not self._focused_item:
                group = item.get_parent()
                self.emit('item-selected', group, item)

    def on_dockitem_close(self, item):
        group = item.get_parent()
        self.emit('item-closed', group, item)
        cleanup(group, self)

    def on_dockgroup_item_selected(self, group, item):
        """
        An item is selected by clicking on a tab.
        """
        focus_child = self._focus_data.get(item)

        if focus_child:
            # item-selected is emited by is-focus handler
            focus_child.set_property('has-focus', True)

        self.emit('item-selected', group, item)

################################################################################
# Placement
################################################################################

def add_new_group_left(widget, new_group):
    add_new_group_before(widget, new_group, gtk.ORIENTATION_HORIZONTAL)

def add_new_group_right(widget, new_group):
    add_new_group_after(widget, new_group, gtk.ORIENTATION_HORIZONTAL)

def add_new_group_above(widget, new_group):
    add_new_group_before(widget, new_group, gtk.ORIENTATION_VERTICAL)

def add_new_group_below(widget, new_group):
    add_new_group_after(widget, new_group, gtk.ORIENTATION_VERTICAL)

def add_new_group_before(widget, new_group, orientation):
    """
    Create a new DockGroup and place it before `widget`. The DockPaned that will hold
    both groups will have the defined orientation.
    """
    position = widget.get_parent().get_children().index(widget)
    add_new_group(widget, new_group, orientation, position)
    return new_group

def add_new_group_after(widget, new_group, orientation):
    """
    Create a new DockGroup and place it after `widget`. The DockPaned that will hold
    both groups will have the defined orientation.
    """
    position = widget.get_parent().get_children().index(widget) + 1
    add_new_group(widget, new_group, orientation, position)
    return new_group

def add_new_group(widget, new_group, orientation, position):
    """
    Place a `new_group` next to `widget` in a
    """
    # Parameters: orientation, position (left/top: None, right/bottom: 1),
    # current_child, (paned) current_position, (paned) weight

    parent = widget.get_parent()
    assert parent

    try:
        current_position = parent.item_num(widget)
        weight = parent.child_get_property(widget, 'weight')
    except AttributeError:
        current_position = None

    if isinstance(parent, DockPaned) and orientation == parent.get_orientation():
        new_paned = parent
    else:
        new_paned = new(DockPaned)
        new_paned.set_orientation(orientation)

        # Current_child will always be a DockGroup or DockPaned with opposite orientation
        parent.remove(widget)

        if current_position is not None:
            # used for DockPaned
            parent.insert_item(new_paned, position=current_position, weight=weight)
        else:
            # Used for DockFrame
            parent.add(new_paned)

        new_paned.insert_item(widget, weight=0.5)
        widget.queue_resize()

    #new_group = new(DockGroup, source, context.docklayout)
    new_paned.insert_item(new_group, position, weight=0.5)

    new_paned.show()
    new_group.show()

    return new_group

def _window_delete_handler(window, event):
    map(lambda i: i.close(),
        filter(lambda i: isinstance(i, DockItem), flatten(window)))
    return False

def add_new_group_floating(new_group, layout, size=None, pos=None):
    window = gtk.Window(gtk.WINDOW_TOPLEVEL)

    if pos:
        window.move(*pos)

    window.set_resizable(True)
    window.set_skip_taskbar_hint(True)
    window.set_type_hint(gdk.WINDOW_TYPE_HINT_UTILITY)
    window.set_transient_for(layout.get_main_frames().next().get_toplevel())

    if size:
        window.set_size_request(*size)

    window.connect('delete-event', _window_delete_handler)
    frame = new(DockFrame)
    window.add(frame)
    frame.add(new_group)
    window.show()
    frame.show()
    new_group.show()
    layout.add(frame)

    return frame

################################################################################
# Drag and Drop behaviour
################################################################################

def _propagate_to_parent(func, widget, context, x, y, timestamp):
    '''
    Common function to propagate calls to a parent widget.
    '''
    parent = widget.get_parent()

    if parent:
        # Should not use get_pointer as it's not testable.
        px, py = widget.translate_coordinates(parent, x, y)
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
    :returns: DragData if the parent widget handled the event

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
    return _propagate_to_parent(drag_motion, widget, context, x, y, timestamp)

@generic
def cleanup(widget, layout):
    '''
    :param widget: widget that may require cleanup.

    Perform cleanup action for a widget. For example after a drag-and-drop
    operation or when a dock-item is closed.
    '''
    parent = widget.get_parent()
    return parent and cleanup(parent, layout)

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
################################################################################

def new(class_, old=None, layout=None):
    '''
    Create a new Widget. Set the group name if required.
    '''
    new = class_()

    if old and settings[old].inherit_settings:
        new.set_name(old.get_name())
    return new

def dock_group_expose_highlight(self, event):
    try:
        tab = self._visible_tabs[self._drop_tab_index]
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
    self.queue_draw()

def dock_unhighlight(self):
    self.queue_draw()

    try:
        self.disconnect(self._expose_event_id)
        del self._expose_event_id
    except AttributeError, e:
        self.log.error(e, exc_info=True)

@drag_motion.when_type(DockGroup)
@with_magic_borders
def dock_group_drag_motion(self, context, x, y, timestamp):
    self.log.debug('dock_group_drag_motion: %s, %s, %s, %s' % (context, x, y, timestamp))

    # Insert the dragged tab before the tab under (x, y)
    drop_tab = self.get_tab_at_pos(x, y)
    self.log.debug('drop tab at (%d, %d) is %s', x, y, drop_tab)

    if drop_tab:
        self._drop_tab_index = self._visible_tabs.index(drop_tab)
    elif self._tabs:
        self._drop_tab_index = self._visible_tabs.index(self._current_tab)
    else:
        self._drop_tab_index = None

    dock_group_highlight(self)

    def dock_group_drag_data_received(selection_data, info):
        self.log.debug('%s, %s, %s, %s, %s, %s' % (context, x, y, selection_data, info, timestamp))
        source = context.get_source_widget()
        assert source
        self.log.debug('Recieving item %s' % source.dragcontext.dragged_object)

        for item in reversed(source.dragcontext.dragged_object):
            self.insert_item(item, visible_position=self._drop_tab_index)

        context.finish(True, True, timestamp) # success, delete, time

    return DragData(self, dock_unhighlight, dock_group_drag_data_received)

@cleanup.when_type(DockGroup)
def dock_group_cleanup(self, layout):
    if not self.items and settings[self].auto_remove:
        parent = self.get_parent()
        self.log.debug('removing empty group')
        self.destroy()
        return parent and cleanup(parent, layout)

# Attached to drag *source*
@drag_end.when_type(DockGroup)
def dock_group_drag_end(self, context):
    cleanup(self, context.docklayout)

# Attached to drag *source*
@drag_failed.when_type(DockGroup)
def dock_group_drag_failed(self, context, result):
    global settings
    self.log.debug('%s, %s' % (context, result))
    if result == 1 and settings[self].can_float: #gtk.DRAG_RESULT_NO_TARGET
        if reduce(lambda a, b: a or b,
                  map(lambda i: settings[i].float_retain_size,
                      self.dragcontext.dragged_object)):
            size = (self.allocation.width, self.allocation.height)
        else:
            size = None

        layout = context.docklayout
        new_group = new(DockGroup, context.get_source_widget(), layout)
        add_new_group_floating(new_group, layout, size, self.get_pointer())

        for item in self.dragcontext.dragged_object:
            new_group.append_item(item)

    else:
        for item in self.dragcontext.dragged_object:
            self.insert_item(item, position=self._dragged_tab_index)
    return True

################################################################################
# DockPaned
################################################################################
def dock_paned_expose_highlight(self, event):
    try:
        handle = self._handles[self._drop_handle_index]
    except (AttributeError, IndexError, TypeError), e:
        self.log.error(e, exc_info=True)
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
    self.queue_draw()

@drag_motion.when_type(DockPaned)
@with_magic_borders
def dock_paned_drag_motion(self, context, x, y, timestamp):
    self.log.debug('dock_paned_drag_motion: %s, %s, %s, %s' % (context, x, y, timestamp))

    handle = self._get_handle_at_pos(x, y)
    self.log.debug('handle at pos (%d, %d) is %s', x, y, handle)

    if handle:
        self._drop_handle_index = self._handles.index(handle)
    else:
        self._drop_handle_index = None

    dock_paned_highlight(self)

    def dock_paned_drag_data_received(selection_data, info):
        self.log.debug('%s, %s, %s, %s, %s, %s' % (context, x, y, selection_data, info, timestamp))

        source = context.get_source_widget()

        self.log.debug('Recieving item %s' % source.dragcontext.dragged_object)
        # If on handle: create new DockGroup and add items
        new_group = new(DockGroup, source, context.docklayout)
        self.insert_item(new_group, self._drop_handle_index + 1)
        new_group.show()

        for item in source.dragcontext.dragged_object:
            new_group.insert_item(item)

        context.finish(True, True, timestamp) # success, delete, time

    return DragData(self, dock_unhighlight, dock_paned_drag_data_received)

@cleanup.when_type(DockPaned)
def dock_paned_cleanup(self, layout):
    if not len(self):
        parent = self.get_parent()
        self.log.debug('removing empty paned')
        self.destroy()
        return parent and cleanup(parent, layout)

    if len(self) == 1:
        parent = self.get_parent()
        child = self[0]

        if isinstance(parent, DockPaned):
            position = [c for c in parent].index(self)
            weight = parent.child_get_property(self, 'weight')
            self.remove(child)
            parent.remove(self)
            parent.insert_item(child, position=position, weight=weight)
            assert child.get_parent() is parent, (child.get_parent(), parent)
        else:
            #does not work: child.unparent()
            self.remove(child)
            parent.remove(self)
            parent.add(child)

        self.log.debug('removing empty paned - moved child to parent first')
        self.destroy()

# Attached to drag *source*
@drag_end.when_type(DockPaned)
def dock_paned_drag_end(self, context):
    cleanup(self, context.docklayout)

def dock_paned_magic_borders_leave(self):
    self.get_ancestor(DockFrame).set_placeholder(None)

@magic_borders.when_type(DockPaned)
def dock_paned_magic_borders(self, context, x, y, timestamp):

    a = self.allocation

    def create_received(create):
        current_group = self.get_item_at_pos(x, y)
        assert current_group

        ca = current_group.allocation

        if x < MAGIC_BORDER_SIZE:
            allocation = (ca.x, ca.y, MAGIC_BORDER_SIZE, ca.height)
        elif a.width - x < MAGIC_BORDER_SIZE:
            allocation = (a.width - MAGIC_BORDER_SIZE, ca.y, MAGIC_BORDER_SIZE, ca.height)
        elif y < MAGIC_BORDER_SIZE:
            allocation = (ca.x, ca.y, ca.width, MAGIC_BORDER_SIZE)
        elif a.height - y < MAGIC_BORDER_SIZE:
            allocation = (ca.x, a.height - MAGIC_BORDER_SIZE, ca.width, MAGIC_BORDER_SIZE)

        frame = self.get_ancestor(DockFrame)
        fx, fy = self.translate_coordinates(frame, allocation[0], allocation[1])
        fa = frame.allocation
        allocation = (fa.x + fx, fa.y + fy, allocation[2], allocation[3])

        placeholder = Placeholder()
        frame.set_placeholder(placeholder)
        placeholder.size_allocate(allocation)
        placeholder.show()

        if create:
            if self.get_orientation() == gtk.ORIENTATION_HORIZONTAL:
                orientation = gtk.ORIENTATION_VERTICAL
            else:
                orientation = gtk.ORIENTATION_HORIZONTAL

            weight = self.child_get_property(current_group, 'weight')

            if min(x, y) < MAGIC_BORDER_SIZE:
                position = 0
            else:
                position = None

            def new_paned_and_group_receiver(selection_data, info):
                source = context.get_source_widget()
                assert source

                new_group = new(DockGroup, source, context.docklayout)
                add_new_group(current_group, new_group, orientation, position)

                self.log.debug('Recieving item %s' % source.dragcontext.dragged_object)

                for item in source.dragcontext.dragged_object:
                    new_group.append_item(item)

                context.finish(True, True, timestamp) # success, delete, time

            return new_paned_and_group_receiver

        else:
            def add_group_receiver(selection_data, info):
                source = context.get_source_widget()
                assert source
                new_group = new(DockGroup, source, context.docklayout)
                if min(x, y) < MAGIC_BORDER_SIZE:
                    position = 0
                else:
                    position = None
                self.insert_item(new_group, position)
                new_group.show()
                for item in source.dragcontext.dragged_object:
                    new_group.append_item(item)

                context.finish(True, True, timestamp) # success, delete, time

            return add_group_receiver

    if abs(min(y, a.height - y)) < MAGIC_BORDER_SIZE:
        received = create_received(self.get_orientation() == gtk.ORIENTATION_HORIZONTAL)
        return DragData(self, dock_paned_magic_borders_leave, received)
    elif abs(min(x, a.width - x)) < MAGIC_BORDER_SIZE:
        received = create_received(self.get_orientation() == gtk.ORIENTATION_VERTICAL)
        return DragData(self, dock_paned_magic_borders_leave, received)

    return None

################################################################################
# DockFrame
################################################################################
@cleanup.when_type(DockFrame)
def dock_frame_cleanup(self, layout):
    if not self.get_children():
        parent = self.get_parent()
        layout.remove(self)
        self.destroy()
        try:
            if parent.get_transient_for():
                parent.destroy()
        except AttributeError:
            self.log.error(' Not a transient top level widget')

@drag_end.when_type(DockFrame)
def dock_frame_drag_end(self, context):
    cleanup(self, context.docklayout)

def dock_frame_magic_borders_leave(self):
    self.set_placeholder(None)

@drag_motion.when_type(DockFrame)
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
    border = self.border_width

    if x - border < MAGIC_BORDER_SIZE:
        orientation = gtk.ORIENTATION_HORIZONTAL
        allocation = (a.x + border, a.y + border, MAGIC_BORDER_SIZE, a.height - border*2)
    elif a.width - x - border < MAGIC_BORDER_SIZE:
        orientation = gtk.ORIENTATION_HORIZONTAL
        allocation = (a.x + a.width - MAGIC_BORDER_SIZE - border, a.y + border, MAGIC_BORDER_SIZE, a.height - border*2)
    elif y - border < MAGIC_BORDER_SIZE:
        orientation = gtk.ORIENTATION_VERTICAL
        allocation = (a.x + border, a.y + border, a.width - border*2, MAGIC_BORDER_SIZE)
    elif a.height - y - border < MAGIC_BORDER_SIZE:
        orientation = gtk.ORIENTATION_VERTICAL
        allocation = (a.x + border, a.y + a.height - MAGIC_BORDER_SIZE - border, a.width - border*2, MAGIC_BORDER_SIZE)
    else:
        return None

    placeholder = Placeholder()

    self.set_placeholder(placeholder)
    placeholder.size_allocate(allocation)
    placeholder.show()

    current_child = self.get_children()[0]
    assert current_child

    if min(x - border, y - border) < MAGIC_BORDER_SIZE:
        position = 0
    else:
        position = None

    def new_paned_and_group_receiver(selection_data, info):
        source = context.get_source_widget()
        assert source

        new_group = new(DockGroup, source, context.docklayout)
        add_new_group(current_child, new_group, orientation, position)

        self.log.debug('Recieving item %s' % source.dragcontext.dragged_object)

        for item in source.dragcontext.dragged_object:
            new_group.append_item(item)

        context.finish(True, True, timestamp) # success, delete, time

    return DragData(self, dock_frame_magic_borders_leave, new_paned_and_group_receiver)
