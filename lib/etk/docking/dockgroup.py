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


from __future__ import absolute_import
from math import pi
from logging import getLogger
from operator import attrgetter
from time import time

import cairo
import gobject
import gtk
import gtk.gdk as gdk

from . import _
from .compactbutton import CompactButton
from .dockitem import DockItem
from .util import rect_contains


DRAG_TARGET_ITEM_LIST = ('x-etk-docking/item-list', gtk.TARGET_SAME_APP, 0)


class _DockGroupTab(object):
    '''
    Convenience class storing information about a tab.
    '''
    __slots__ = ['item',                # DockItem associated with this tab
                 'item_title_handler',  # item title property notification signal handler id
                 'item_title_tooltip_text_handler', # item title-tooltip-text property notification signal handler id
                 'image',               # icon (gtk.Image)
                 'label',               # title (gtk.Label)
                 'button',              # close button (etk.docking.CompactButton)
                 'menu_item',           # menu item (gtk.ImageMenuItem)
                 'state',               # state (one of the GTK State Type Constants)
                 'area',                # area, used for hit testing (gdk.Rectangle)
                 'last_focused']        # timestamp set last time a tab was focused

    def __contains__(self, pos):
        return rect_contains(self.area, *pos)

    def __str__(self):
        return "<%s object at 0x%x with label '%s' on %s>" % (self.__class__.__name__, id(self), self.label.get_text(), self.area)


class DockGroup(gtk.Container):
    '''
    The etk.DockGroup widget is a gtk.Container that groups its children in a
    tabbed interface.

    You can reorder tabs by dragging them to the desired location within the
    same or another etk.DockGroup having the same group-id. You can also drag
    a complete etk.DockGroup onto another etk.DockGroup having the same group-id
    to merge all etk.DockItems from the source into the destination
    etk.DockGroup.
    '''
    __gtype_name__ = 'EtkDockGroup'
    __gproperties__ = {'group-id': (gobject.TYPE_UINT,
                                    'group id',
                                    'group id',
                                    0,
                                    gobject.G_MAXUINT,
                                    0,
                                    gobject.PARAM_READWRITE)}

    def __init__(self):
        gtk.Container.__init__(self)

        # Initialize logging
        self.log = getLogger('<%s object at %s>' % (self.__gtype_name__, hex(id(self))))

        # Internal housekeeping
        self.set_border_width(2)
        self._group_id = 0
        self._frame_width = 1
        self._spacing = 3
        self._current_tab = None

        # Decoration area
        self._decoration_area = gdk.Rectangle()
        self._tabs = []
        self._visible_tabs = []

        gtk.widget_push_composite_child()
        self._tab_menu = gtk.Menu()
        self._tab_menu.attach_to_widget(self, None)
        self._list_button = CompactButton('compact-list')
        self._list_button.set_tooltip_text(_('Show list'))
        self._list_button.connect('clicked', self._on_list_button_clicked)
        self._list_button.set_parent(self)
        self._list_menu = gtk.Menu()
        self._list_menu.attach_to_widget(self._list_button, None)
        self._min_button = CompactButton('compact-minimize')
        self._min_button.set_tooltip_text(_('Minimize'))
        self._min_button.connect('clicked', self._on_min_button_clicked)
        self._min_button.set_parent(self)
        self._max_button = CompactButton('compact-maximize')
        self._max_button.set_tooltip_text(_('Maximize'))
        self._max_button.connect('clicked', self._on_max_button_clicked)
        self._max_button.set_parent(self)
        gtk.widget_pop_composite_child()

        # Configure drag/drop
        self.drag_dest_set(gtk.DEST_DEFAULT_MOTION | gtk.DEST_DEFAULT_HIGHLIGHT,
                           [DRAG_TARGET_ITEM_LIST],
                           gdk.ACTION_MOVE)
        # There doesn't seem to be a do_drag_failed virtual method that handles
        # the drag-failed event, so we specifically connect to it...
        self.connect('drag-failed', DockGroup._do_drag_failed)

        self._drag_target = None
        self._dragged_tabs = []
        self._drop_tab_index = None


    ############################################################################
    # GObject
    ############################################################################
    def do_get_property(self, pspec):
        if pspec.name == 'group-id':
            return self.get_group_id()

    def do_set_property(self, pspec, value):
        if pspec.name == 'group-id':
            self.set_group_id(value)

    def get_group_id(self):
        return self._group_id

    def set_group_id(self, value):
        self._group_id = value
        self.notify('group-id')

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
        for tab in self._tabs:
            tab.image.set_parent_window(self.window)
            tab.label.set_parent_window(self.window)
            tab.button.set_parent_window(self.window)
            tab.item.set_parent_window(self.window)

        self._list_button.set_parent_window(self.window)
        self._min_button.set_parent_window(self.window)
        self._max_button.set_parent_window(self.window)

    def do_unrealize(self):
        self.window.set_user_data(None)
        self.window.destroy()
        gtk.Container.do_unrealize(self)

    def do_map(self):
        gtk.Container.do_map(self)
        self._list_button.show()
        self._min_button.show()
        self._max_button.show()
        self.window.show()

    def do_unmap(self):
        self._list_button.hide()
        self._min_button.hide()
        self._max_button.hide()
        self.window.hide()
        gtk.Container.do_unmap(self)

    def do_size_request(self, requisition):
        # Start with a zero sized decoration area
        dw = dh = 0

        # Precalculate width and height for each tab, but only add
        # current item tab size to the decoration area requisition as
        # the other tabs can be hidden when we don't get enough room
        # in the allocation fase.
        for tab in self._tabs:
            (iw, ih) = tab.image.size_request()
            (lw, lh) = tab.label.size_request()
            (bw, bh) = tab.button.size_request()

            tab.area.width = (self._frame_width + self._spacing +
                              iw + self._spacing + lw + self._spacing +
                              bw + self._spacing + self._frame_width)
            tab.area.height = (self._frame_width + self._spacing +
                               max(ih, lh, bh) +
                               self._spacing + self._frame_width)

            if tab == self._current_tab:
                dw = tab.area.width - lw

            dh = max(dh, tab.area.height)

        # Add decoration button sizes to the decoration area
        (list_w, list_h) = self._list_button.size_request()
        (min_w, min_h) = self._min_button.size_request()
        (max_w, max_h) = self._max_button.size_request()

        dw += (self._spacing + list_w + min_w + max_w +
               self._spacing + self._frame_width)
        dh = max(dh,
                 (self._spacing + list_h + self._spacing),
                 (self._spacing + min_h + self._spacing),
                 (self._spacing + max_h + self._spacing))

        self._decoration_area.width = dw
        self._decoration_area.height = dh

        # Current item
        if self._current_tab:
            (iw, ih) = self._current_tab.item.size_request()
        else:
            iw = ih = 0

        iw += 2 * self._frame_width + 2 * self.border_width
        ih += self._frame_width + 2 * self.border_width

        # Calculate total size requisition
        requisition.width = max(dw, iw)
        requisition.height = dh + ih

    def do_size_allocate(self, allocation):
        self.allocation = allocation

        # Allocate space for decoration buttons
        max_w, max_h = self._max_button.get_child_requisition()
        min_w, min_h = self._min_button.get_child_requisition()
        list_w, list_h = self._list_button.get_child_requisition()
        bh = max(list_h, min_h, max_h)
        by = self._frame_width + self._spacing
        self._max_button.size_allocate(gdk.Rectangle(allocation.width - self._frame_width - self._spacing - max_w, by, max_w, bh))
        self._min_button.size_allocate(gdk.Rectangle(allocation.width - self._frame_width - self._spacing - max_w - min_w, by, min_w, bh))
        self._list_button.size_allocate(gdk.Rectangle(allocation.width - self._frame_width - self._spacing - max_w - min_w - list_w, by, list_w, bh))

        # Check what tabs we can show with the space we have been allocated.
        # Tabs on the far right of the current item tab get hidden first,
        # then tabs on the far left.
        if not self._tabs:
            del self._visible_tabs[:]
        else:
            current_tab_index = self._tabs.index(self._current_tab)

            # Calculate available tab area width
            available_width = (allocation.width - self._frame_width - self._spacing -
                               max_w - min_w - list_w - self._spacing -
                               self._current_tab.area.width)

            # TODO: get previous tab position, use that to insert _current_tab
            if self._current_tab and self._current_tab not in self._visible_tabs:
                self._visible_tabs.append(self._current_tab)

            #if not set(self._visible_tabs) <= set(self._tabs):
            for tab in self._visible_tabs:
                if tab not in self._tabs:
                    self._visible_tabs.remove(tab)

            calculated_width = 0
            for tab in self._visible_tabs:
                calculated_width += tab.area.width

            if calculated_width > available_width:
                tab_age = sorted(self._visible_tabs, key=attrgetter('last_focused'))
                while len(tab_age) > 1 and calculated_width > available_width + tab_age[0].area.width:
                    calculated_width -= tab_age[0].area.width
                    self._visible_tabs.remove(tab_age[0])
                    del tab_age[0]
            elif calculated_width < available_width \
                    and len(self._visible_tabs) < len(self._tabs):
                tab_age = sorted(self._tabs, key=attrgetter('last_focused'), reverse=True)
                while tab_age and calculated_width < available_width + tab_age[0].area.width:
                    if tab_age[0] not in self._visible_tabs:
                        calculated_width += tab_age[0].area.width
                        self._visible_tabs.append(tab_age[0])
                    del tab_age[0]

            # If the current item's tab is the only visible tab,
            # we need to recalculate its tab.area.width
            if len(self._visible_tabs) == 1:
                (iw, ih) = self._current_tab.image.get_child_requisition()
                (lw, lh) = self._current_tab.label.get_child_requisition()
                (bh, bw) = self._current_tab.button.get_child_requisition()

                normal = (self._frame_width + self._spacing + iw +
                          self._spacing + lw + self._spacing + bw +
                          self._spacing + self._frame_width)

                width = (allocation.width - self._frame_width - self._spacing -
                         max_w - min_w - list_w - self._spacing)

                if width <= normal:
                    self._current_tab.area.width = width
                else:
                    self._current_tab.area.width = normal

            # Update visibility on dockitems and composite children used
            # by tabs.
            for tab in self._tabs:
                if tab is self._current_tab:
                    tab.item.show()
                    tab.image.show()
                    tab.label.show()
                    tab.button.show()
                elif tab in self._visible_tabs:
                    tab.item.hide()
                    tab.image.show()
                    if tab.state == gtk.STATE_PRELIGHT:
                        tab.button.show()
                    else:
                        tab.button.hide()
                    tab.label.show()
                else:
                    if tab.item.flags() & gtk.VISIBLE:
                        tab.item.hide()
                        tab.image.hide()
                        tab.button.hide()
                        tab.label.hide()

        # Only show the list button when needed
        if len(self._tabs) > len(self._visible_tabs):
            self._list_button.show()
        else:
            self._list_button.hide()

        # Precalculate x an y for each visible tab and allocate space for
        # the tab's composite children.
        cx = cy = 0
        for tab in self._visible_tabs:
            tab.area.x = cx
            tab.area.y = cy

            (iw, ih) = tab.image.get_child_requisition()
            (lw, lh) = tab.label.get_child_requisition()
            (bh, bw) = tab.button.get_child_requisition()

            ix = cx + self._frame_width + self._spacing
            iy = (tab.area.height - ih) / 2 + 1
            tab.image.size_allocate(gdk.Rectangle(ix, iy, iw, ih))

            if len(self._visible_tabs) == 1:
                lw = tab.area.width - (self._frame_width + self._spacing + iw +
                                       self._spacing + self._spacing + bw +
                                       self._spacing + self._frame_width)
                lw = max(lw, 0) # Prevent negative width

            lx = cx + self._frame_width + self._spacing + iw + self._spacing
            ly = (tab.area.height - lh) / 2 + 1
            tab.label.size_allocate(gdk.Rectangle(lx, ly, lw, lh))

            bx = (cx + self._frame_width + self._spacing + iw +
                  self._spacing + lw + self._spacing)
            by = (tab.area.height - bh) / 2 + 1
            tab.button.size_allocate(gdk.Rectangle(bx, by, bw, bh))

            cx += tab.area.width

        # Allocate space for the current *item*
        if self._current_tab:
            ix = self._frame_width + self.border_width
            iy = self._decoration_area.height + self.border_width
            iw = max(allocation.width - (2 * self._frame_width) - (2 * self.border_width), 0)
            ih = max(allocation.height - (2 * self._frame_width) - (2 * self.border_width) - 23, 0)
            self._current_tab.item.size_allocate(gdk.Rectangle(ix, iy, iw, ih))

        if self.flags() & gtk.REALIZED:
            self.window.move_resize(*allocation)

    def do_expose_event(self, event):
        # Prepare colors
        bg = self.style.bg[self.state]
        bg = (bg.red_float, bg.green_float, bg.blue_float)
        dark = self.style.dark[self.state]
        dark = (dark.red_float, dark.green_float, dark.blue_float)

        # Create cairo context
        c = self.window.cairo_create()
        c.set_line_width(self._frame_width)
        # Restrict context to the exposed area, avoid extra work
        c.rectangle(event.area.x, event.area.y, event.area.width, event.area.height)
        c.clip_preserve()
        # Draw background
        c.set_source_rgb(*bg)
        c.fill()

        # Decoration area height
        dh = 0
        for tab in self._tabs:
            dh = max(dh, tab.area.height)

        dh = max(dh, (self._spacing + self._list_button.allocation.height + self._spacing),
                     (self._spacing + self._min_button.allocation.height + self._spacing),
                     (self._spacing + self._max_button.allocation.height + self._spacing))

        # Draw DockGroup frame
        c.move_to(0.5, 0.5)
        c.line_to(self.allocation.width - 0.5, 0.5)
        c.line_to(self.allocation.width - 0.5, self.allocation.height - 0.5)
        c.line_to(0.5, self.allocation.height - 0.5)
        c.line_to(0.5, 0.5)
        c.set_source_rgb(*dark)
        c.stroke()
        c.move_to(0.5, dh - 0.5)
        c.line_to(self.allocation.width + 0.5, dh - 0.5)
        c.set_source_rgb(*dark)
        c.stroke()

        # Draw tabs
        if self._visible_tabs:
            visible_index = self._visible_tabs.index(self._current_tab)

            for index, tab in enumerate(self._visible_tabs):
                tx = tab.area.x
                ty = tab.area.y
                tw = tab.area.width
                th = tab.area.height

                if index < visible_index and index != 0:
                    c.move_to(tx + 0.5, ty + th)
                    c.line_to(tx + 0.5, ty + 8.5)
                    c.arc(tx + 8.5, 8.5, 8, 180 * (pi / 180), 270 * (pi / 180))
                    c.set_source_rgb(*dark)
                    c.stroke()
                elif index > visible_index:
                    c.arc(tx + tw - 8.5, 8.5, 8, 270 * (pi / 180), 360 * (pi / 180))
                    c.line_to(tx + tw - 0.5, ty + th)
                    c.set_source_rgb(*dark)
                    c.stroke()
                elif index == visible_index:
                    if visible_index == 0:
                        c.move_to(tx + 0.5, ty + th)
                        c.line_to(tx + 0.5, ty + 0.5)
                        c.line_to(tx + tw - 8.5, ty + 0.5)
                        c.arc(tx + tw - 8.5, 8.5, 8, 270 * (pi / 180), 360 * (pi / 180))
                        c.line_to(tx + tw - 0.5, ty + th)
                        linear = cairo.LinearGradient(0.5, 0.5, 0.5, th)
                        linear.add_color_stop_rgb(0, 0.87843137254901960784313725490196, 0.91764705882352941176470588235294, 0.98431372549019607843137254901961)
                        linear.add_color_stop_rgb(1, 0.6, 0.72941176470588235294117647058824, 0.95294117647058823529411764705882)
                        c.set_source(linear)
                        c.fill_preserve()
                        c.set_source_rgb(*dark)
                        c.stroke()
                    else:
                        c.move_to(tx + 0.5, ty + th)
                        c.line_to(tx + 0.5, ty + 8.5)
                        c.arc(tx + 8.5, 8.5, 8, 180 * (pi / 180), 270 * (pi / 180))
                        c.line_to(tx + tw - 8.5, ty + 0.5)
                        c.arc(tx + tw - 8.5, 8.5, 8, 270 * (pi / 180), 360 * (pi / 180))
                        c.line_to(tx + tw - 0.5, ty + th)
                        linear = cairo.LinearGradient(0.5, 0.5, 0.5, th)
                        linear.add_color_stop_rgb(0, 0.87843137254901960784313725490196, 0.91764705882352941176470588235294, 0.98431372549019607843137254901961)
                        linear.add_color_stop_rgb(1, 0.6, 0.72941176470588235294117647058824, 0.95294117647058823529411764705882)
                        c.set_source(linear)
                        c.fill_preserve()
                        c.set_source_rgb(*dark)
                        c.stroke()

                self.propagate_expose(tab.image, event)
                self.propagate_expose(tab.label, event)
                self.propagate_expose(tab.button, event)

        self.propagate_expose(self._list_button, event)
        self.propagate_expose(self._min_button, event)
        self.propagate_expose(self._max_button, event)

        # Draw DockItem border
        if self._current_tab:
            c.rectangle(self._frame_width, dh, self.allocation.width - 2*self._frame_width, self.allocation.height - dh - self._frame_width)
            c.set_source_rgb(0.6, 0.72941176470588235294117647058824, 0.95294117647058823529411764705882)
            c.fill()

        return False

    def do_motion_notify_event(self, event):
        # Reset tooltip text
        self.set_tooltip_text(None)

        # We should not react to motion_notify_events originating from the
        # current tab's child widget
        if event.window is self.window:
            if event.state & gdk.BUTTON1_MASK:
                tab = self._get_tab_at_pos(event.x, event.y)
                if tab:
                    self._dragged_tabs = [tab]
                else:
                    self._dragged_tabs = list(self._tabs)
                self.drag_begin([DRAG_TARGET_ITEM_LIST], gdk.ACTION_MOVE, 1, event)

            for tab in self._visible_tabs:
                if (event.x, event.y) in tab:
                    # Update tooltip for tab under the cursor
                    self.set_tooltip_text(tab.item.get_title_tooltip_text())

                    if tab.state == gtk.STATE_NORMAL:
                        tab.state = gtk.STATE_PRELIGHT
                        self.queue_resize()
                # Doing this as an elif above might seem tempting, but this way
                # reduces flicker on the close button...
                else:
                    tab.state = gtk.STATE_NORMAL
                    self.queue_resize()

    def do_button_release_event(self, event):
        for tab in self._visible_tabs:
            if (event.x, event.y) in tab:
                if event.button == 1:
                    self.set_current_item(self._tabs.index(tab))
                elif event.button == 3:
                    def _menu_position(menu):
                        wx, wy = self.window.get_origin()
                        x = wx + event.x
                        y = wy + event.y
                        return (x, y, True)

                    self._tab_menu.show_all()
                    self._tab_menu.popup(parent_menu_shell=None, parent_menu_item=None,
                                          func=_menu_position, button=3,
                                          activate_time=0)

                break

        return True

    ############################################################################
    # GtkWidget drag source
    ############################################################################
    def do_drag_begin(self, context):
        '''
        :param context: the gdk.DragContext

        The do_drag_begin() signal handler is executed on the drag source when
        the user initiates a drag operation. A typical reason to use this signal
        handler is to set up a custom drag icon with the drag_source_set_icon()
        method.
        '''
        self.log.debug('do_drag_begin: %s' % context)

        #TODO: Set drag icon to be empty
        #TODO: Set drag cursor -> will most likely not (only) happen here...
        # Can be any of the following, depending on the selected drag destination:
        #   - gdk.DIAMOND_CROSS    "stacking" a dockitem into a dockgroup
        #   - gdk.SB_UP_ARROW      "splitting" a dockitem into a new dockgroup above the source dockgroup (needs docklayout)
        #   - gdk.SB_DOWN_ARROW    "splitting" a dockitem into a new dockgroup below the source dockgroup (needs docklayout)
        #   - gdk.SB_LEFT_ARROW    "splitting" a dockitem into a new dockgroup on the left of the source dockgroup (needs docklayout)
        #   - gdk.SB_RIGHT_ARROW   "splitting" a dockitem into a new dockgroup on the right of the source dockgroup (needs docklayout)

        #dnd_window = gtk.Window(gtk.WINDOW_POPUP)
        #dnd_window.set_screen(self.get_screen())
        #dnd_window.add(tab.item)
        #dnd_window.set_size_request(tab.item.allocation.width,
        #                            tab.item.allocation.height)
        #dnd_window.show_all()
        #context.set_icon_widget(dnd_window, -2, -2)
        #context.set_icon_pixmap(tab.image.get_pixmap(), -2, -2)

    def do_drag_data_get(self, context, selection_data, info, timestamp):
        '''
        :param context: the gdk.DragContext
        :param selection_data: a gtk.SelectionData object
        :param info: an integer ID for the drag
        :param timestamp: the time of the drag event

        The do_drag_data_get() signal handler is executed when a drag operation
        completes that copies data or when a drag drop occurs using the
        gtk.gdk.DRAG_PROTO_ROOTWIN protocol. The drag source executes this
        handler when the drag destination requests the data using the
        drag_get_data() method. This handler needs to fill selection_data
        with the data in the format specified by the target associated with
        info.

        For tab movement, here the tab is removed from the group. If the
        drop fails, the tab is restored in do_drag_failed().

        For group movement, no special action is taken.
        '''
        #TODO: Fill selection_data with the right data (set() or set_text())
        self.log.debug('do_drag_data_get: %s, %s, %s' % (context, selection_data, info))

        # Free the item for transport.
        for tab in self._dragged_tabs:
            self._dragged_tab_index = self._tabs.index(tab)
            self.remove_item(self._dragged_tab_index, retain_item=True)

        # Set some data, so DnD process continues
        selection_data.set(gdk.atom_intern(DRAG_TARGET_ITEM_LIST[0]), 8,
                            '%d tabs' % len(self._dragged_tabs))


    def do_drag_data_delete(self, context):
        '''
        :param context: the gdk.DragContext

        The do_drag_data_delete() signal handler is executed when the drag
        completes a move operation and requires the source data to be deleted.
        The handler is responsible for deleting the data that has been dropped.

        For groups, the group is deleted, for tabs the group is destroyed
        of there are no more tabs left (see do_drag_data_get()).
        '''
        self.log.debug('do_drag_data_delete: %s' % context)
        # Let this be handled by the DockLayout

    def do_drag_failed(self, context, result):
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
        self.log.debug('do_drag_failed: %s, %s' % (context, result))
        # Put back the item removed in do_drag_data_get()
        #context.drop_finish(False, 0)
        return True

    def do_drag_end(self, context):
        '''
        :param context: the gdk.DragContext

        The do_drag_end() signal handler is executed when the drag operation is
        completed. A typical reason to use this signal handler is to undo things
        done in the do_drag_begin() handler.
        '''
        self.log.debug('do_drag_end: %s - %s', context, context.drag_drop_succeeded())
        self._dragged_tabs = []
        #self._drop_tab_index = None

        self.queue_resize()

    # There doesn't seem to be a do_drag_failed virtual method that handles
    # the drag-failed event, so we have specifically connected _do_drag_failed.
    #TODO: check bugs.gnome.org.
    def _do_drag_failed(self, context, result):
        self.log.debug('_do_drag_failed: %s, %s' % (context, result))
        if not self._dragged_tab.item.get_parent():
            self.insert_item(self._dragged_tab.item, position=self._dragged_tab_index)
        #context.drop_finish(False, 0)
        return True

    ############################################################################
    # GtkWidget drag destination
    ############################################################################
    def drag_highlight(self):
        '''
        Highlight the currently selected drag destination "widget" in the default
        manner.
        '''
        self.log.debug('drag_highlight')

    def drag_unhighlight(self):
        '''
        Remove the currently applied drag highlight.
        '''
        self.log.debug('drag_unhighlight')

    def do_drag_motion(self, context, x, y, timestamp):
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
        self.log.debug('do_drag_motion: %s, %s, %s, %s' % (context, x, y, timestamp))

        # Insert the dragged tab before the tab under (x, y)
        drop_tab = self._get_tab_at_pos(x, y)

        if drop_tab:
            self._drop_tab_index = self._visible_tabs.index(drop_tab)
        elif self._tabs:
            self._drop_tab_index = self._visible_tabs.index(self._current_tab)
        target = self.drag_dest_find_target(context, ());
        #self.log.info('%d move over tab %s, target = %s', timestamp, self._drop_tab_index, target)
        return True

    def do_drag_leave(self, context, timestamp):
        '''
        :param context: the gdk.DragContext
        :param timestamp: the time of the drag event

        The dp_drag_leave() signal handler is executed when the drag operation
        moves off of a drop target widget. A typical reason to use this signal
        handler is to undo things done in the do_drag_motion() handler, e.g. undo
        highlighting with the drag_unhighlight() method.
        '''
        # Can do something here like stopping an animation for creating some
        # space between tabs where the dragged tan can be dropped
        self.log.debug('do_drag_leave, %s, %s' % (context, timestamp))
        self.drag_unhighlight()

    def do_drag_drop(self, context, x, y, timestamp):
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
        self.log.debug('do_drag_drop, %s, %s, %s, %s' % (context, x, y, timestamp))

        target = self.drag_dest_find_target(context, [DRAG_TARGET_ITEM_LIST])
        # TODO: check if target is x-etk-docking/item|group
        item_target = gdk.atom_intern(DRAG_TARGET_ITEM_LIST[0])

        if target == item_target:
            # Register location where to drop
            self.log.debug('Dropping item/group at index %s with target %s' % (self._drop_tab_index, target))
            self.drag_get_data(context, target, timestamp)
            return True

        return False

    def do_drag_data_received(self, context, x, y, selection_data, info, timestamp):
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
        self.log.debug('do_drag_data_received, %s, %s, %s, %s, %s, %s' % (context, x, y, selection_data, info, timestamp))

        source = context.get_source_widget()
        assert source

        if selection_data.target == gdk.atom_intern(DRAG_TARGET_ITEM_LIST[0]):
            self.log.debug('Recieving item %s' % source._dragged_tabs)
            for tab in reversed(source._dragged_tabs):
                self.insert_item(tab.item, visible_position=self._drop_tab_index)
            context.finish(True, True, timestamp) # success, delete, time
        else:
            context.finish(False, False, timestamp) # success, delete, time


    ############################################################################
    # GtkContainer
    ############################################################################
    def do_forall(self, internals, callback, data):
        # Internal widgets
        if internals:
            for tab in self._tabs:
                callback(tab.image, data)
                callback(tab.label, data)
                callback(tab.button, data)

            callback(self._list_button, data)
            callback(self._min_button, data)
            callback(self._max_button, data)

        # Docked items
        for tab in self._tabs:
            callback(tab.item, data)

    def do_add(self, widget):
        self.insert_item(widget)

    def do_remove(self, widget):
        self.remove_item(self.item_num(widget))

    ############################################################################
    # EtkDockGroup
    ############################################################################
    def _get_tab_at_pos(self, x, y):
        '''
        :param x: the x coordinate of the position
        :param y: the y coordinate of the position
        :returns: the item tab at the position specified by x and y or None

        The _get_tab_at_pos() method returns the _DockGroupTab whose area
        contains the position specified by x and y or None if no _DockGroupTab
        area contains position.
        '''
        for tab in self._visible_tabs:
            if (x, y) in tab:
                return tab
        else:
            return None

    def append_item(self, item):
        '''
        :param item: a DockItem
        :returns: the index number of the item tab in the DockGroup

        The append_item() method appends a DockItem to the DockGroup using the
        DockItem specified by item.
        '''
        return self.insert_item(item)

    def prepend_item(self, item):
        '''
        :param item: a DockItem
        :returns: the index number of the item tab in the DockGroup

        The prepend_item() method prepends a DockItem to the DockGroup using the
        DockItem specified by item.
        '''
        return self.insert_item(item, position=0)

    def insert_item(self, item, position=None, visible_position=None):
        '''
        :param item: a DockItem
        :param position: the index (starting at 0) at which to insert the item,
                         or None to append the item after all other item tabs.
        :returns: the index number of the item tab in the DockGroup

        The insert_item() method inserts a DockItem into the DockGroup at the
        location specified by position (0 is the first item). item is the
        DockItem to insert. If position is None the item is appended to the
        DockGroup.
        '''
        if not isinstance(item, DockItem):
            raise TypeError('item should be of type "DockItem", got: "%s"' % type(item).__name__)
        if item in self._tabs:
            raise ValueError('Inserted item is already in the group')

        if position is None:
            position = self.get_n_items()

        # Create composite children for tab
        gtk.widget_push_composite_child()
        tab = _DockGroupTab()
        tab.image = gtk.image_new_from_icon_name(item.get_icon_name(), gtk.ICON_SIZE_MENU)
        tab.label = gtk.Label()
        tab.button = CompactButton(has_frame=False)
        tab.menu_item = gtk.ImageMenuItem()
        gtk.widget_pop_composite_child()

        # Configure child widgets for tab
        tab.item = item
        tab.item.set_parent(self)
        tab.item_title_handler = tab.item.connect('notify::title', self._on_item_title_changed, tab)
        tab.item_title_tooltip_text_handler = tab.item.connect('notify::title-tooltip-text', self._on_item_title_tooltip_text_changed, tab)
        tab.image.set_parent(self)
        tab.label.set_text(item.get_title())
        tab.label.set_parent(self)
        tab.button.set_icon_name_normal('compact-close')
        tab.button.set_icon_name_prelight('compact-close-prelight')
        tab.button.set_parent(self)
        tab.button.connect('clicked', self._on_tab_button_clicked, item)
        tab.menu_item.set_image(gtk.image_new_from_icon_name(item.get_icon_name(), gtk.ICON_SIZE_MENU))
        tab.menu_item.set_label(item.get_title())
        tab.menu_item.connect('activate', self._on_list_menu_item_activated, tab)
        self._list_menu.append(tab.menu_item)
        tab.state = gtk.STATE_NORMAL
        tab.area = gdk.Rectangle()
        tab.last_focused = time()

        self._tabs.insert(position, tab)
        
        if visible_position is not None:
            self._visible_tabs.insert(visible_position, tab)

        if self.flags() & gtk.REALIZED:
            tab.item.set_parent_window(self.window)
            tab.image.set_parent_window(self.window)
            tab.label.set_parent_window(self.window)
            tab.button.set_parent_window(self.window)

        item_num = self.item_num(item)
        self.set_current_item(item_num)
        return item_num

    def remove_item(self, item_num, retain_item=False):
        '''
        :param item_num: the index of an item tab, starting from 0. If None,
                         the last item will be removed.

        The remove_item() method removes the item at the location specified by
        item_num. The value of item_num starts from 0.
        '''
        if item_num is None:
            tab = self._tabs[-1]
        else:
            tab = self._tabs[item_num]

        # We need this to reset the current item below
        old_tab_index = self._tabs.index(self._current_tab)

        # Remove tab item
        tab.item.disconnect(tab.item_title_handler)
        tab.item.disconnect(tab.item_title_tooltip_text_handler)
        tab.item.unparent()
        if not retain_item:
            tab.item.destroy()

        # Remove child widgets
        tab.image.unparent()
        tab.image.destroy()
        tab.label.unparent()
        tab.label.destroy()
        tab.button.unparent()
        tab.button.destroy()
        self._list_menu.remove(tab.menu_item)
        tab.menu_item.destroy()
        self._tabs.remove(tab)

        # Refresh ourselves
        current_tab_index = old_tab_index

        if item_num < current_tab_index:
            item_num = current_tab_index - 1

        self.set_current_item(item_num)

    def item_num(self, item):
        '''
        :param item: a DockItem
        :returns: the index of the item tab specified by item, or None if item
                  is not in the DockGroup

        The item_num() method returns the index of the item tab which contains
        the DockItem specified by item or None if no item tab contains item.
        '''
        for tab in self._tabs:
            if tab.item is item:
                return self._tabs.index(tab)
        else:
            return None

    def get_n_items(self):
        '''
        :returns: the number of item tabs in the DockGroup.

        The get_n_items() method returns the number of item tabs in the
        DockGroup.
        '''
        return len(self._tabs)

    def get_nth_item(self, item_num):
        '''
        :param item_num: the index of an item tab in the DockGroup.
        :returns: a DockItem, or None if item_num is out of bounds

        The get_nth_item() method returns the DockItem contained in the item tab
        with the index specified by item_num. If item_num is out of bounds for
        the item range of the DockGroup this method returns None.
        '''
        if item_num >= 0 and item_num <= len(self._tabs) - 1:
            return self._tabs[item_num].item
        else:
            return None

    def get_current_item(self):
        '''
        :returns: the index (starting from 0) of the current item tab in the
                  DockGroup. If the DockGroup has no item tabs, then None will
                  be returned.

        The get_current_item() method returns the index of the current item tab
        numbered from 0, or None if there are no item tabs.
        '''
        if self._current_tab:
            return self._tabs.index(self._current_tab)
        else:
            return None

    def set_current_item(self, item_num):
        '''
        :param item_num: the index of the item tab to switch to, starting from
                         0. If negative, the first item tab will be used. If
                         greater than the number of item tabs in the DockGroup,
                         the last item tab will be used.

        Switches to the item number specified by item_num. If item_num is
        negative the first item is selected. If greater than the number of
        items in the DockGroup, the last item is selected.
        '''
        # Store a reference to the old current tab
        if self._current_tab and self._current_tab in self._tabs:
            old_tab = self._current_tab
        else:
            old_tab = None

        # Switch to the new current tab
        if self._tabs:
            if item_num < 0:
                current_tab_index = 0
            elif item_num > len(self._tabs) - 1:
                current_tab_index = len(self._tabs) - 1
            else:
                current_tab_index = item_num

            self._current_tab = self._tabs[current_tab_index]
            self._current_tab.last_focused = time()
            # Update properties on new current tab
            self._on_item_title_changed(self._current_tab)
            self._on_item_title_tooltip_text_changed(self._current_tab)
        else:
            self._current_tab = None

        # Update properties on old current tab
        if old_tab:
            self._on_item_title_changed(old_tab)
            self._on_item_title_tooltip_text_changed(old_tab)

        # Refresh ourselves
        self.queue_resize()

    def next_item(self):
        '''
        The next_item() method switches to the next item. Nothing happens if
        the current item is the last item.
        '''
        ci = self.get_current_item()

        if not ci == self.get_n_items() - 1:
            self.set_current_item(ci + 1)

    def prev_item(self):
        '''
        The prev_item() method switches to the previous item. Nothing happens
        if the current item is the first item.
        '''
        ci = self.get_current_item()

        if not ci == 0:
            self.set_current_item(ci - 1)

    def reorder_item(self, item, position):
        '''
        :param item: the DockItem widget to move
        :param position: the index of the item tab that item is to move to

        The reorder_item() method reorders the DockGroup items so that item
        appears in the location specified by position. If position is greater
        than or equal to the number of children in the list, item will be moved
        to the end of the list. If position is negative, item will be moved
        to the beginning of the list.
        '''
        if position < 0:
            position = 0
        elif position > self.get_n_items() - 1:
            position = self.get_n_items()

        tab = self._tabs[self.item_num(item)]
        self._tabs.remove(tab)
        self._tabs.insert(position, tab)


    def merge_items_from_group(self, group, position=0):
        """
        Merge the items in group with the current item
        """
        while group._tabs:
            tab = group._tabs[0]
            group.remove_item(0, retain_item=True)
            self.insert_item(tab.item, position)
            position += 1


    ############################################################################
    # Property notification signal handlers
    ############################################################################
    def _on_item_title_changed(self, tab):
        if tab is self._current_tab:
            tab.menu_item.child.set_use_markup(True)
            tab.menu_item.child.set_markup('<b>%s</b>' % tab.item.get_title())
        else:
            tab.menu_item.child.set_use_markup(False)
            tab.menu_item.child.set_markup(tab.item.get_title())

    def _on_item_title_tooltip_text_changed(self, tab):
        tab.menu_item.set_tooltip_text(tab.item.get_title_tooltip_text())

    ############################################################################
    # Decoration area signal handlers
    ############################################################################
    def _on_tab_button_clicked(self, button, item):
        self.remove(item)

    def _on_list_button_clicked(self, button):
        def _menu_position(menu):
            wx, wy = self.window.get_origin()
            x = wx + button.allocation.x
            y = wy + button.allocation.y + button.allocation.height
            return (x, y, True)

        self._list_menu.show_all()
        self._list_menu.popup(parent_menu_shell=None, parent_menu_item=None,
                              func=_menu_position, button=1,
                              activate_time=0)

    def _on_list_menu_item_activated(self, menuitem, tab):
        self.set_current_item(self._tabs.index(tab))

    def _on_min_button_clicked(self, button):
        #TODO: Hiding the dockgroup is not a good idea, as it will be 'minimized'
        # into a toolbar, managed by DockLayout. We'll probably want to emit
        # a signal instead...
        #self.hide()
        pass

    def _on_max_button_clicked(self, button):
        if button.get_icon_name_normal() == 'compact-maximize':
            button.set_icon_name_normal('compact-restore')
            button.set_tooltip_text(_('Restore'))
        else:
            button.set_icon_name_normal('compact-maximize')
            button.set_tooltip_text(_('Maximize'))
