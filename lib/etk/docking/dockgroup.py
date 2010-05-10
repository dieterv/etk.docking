# -*- coding: utf-8 -*-
#
# Copyright © 2010 Dieter Verfaillie <dieterv@optionexplicit.be>
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

import cairo
import pangocairo
import gobject
import gtk
import gtk.gdk as gdk

from . import _
from .compactbutton import CompactButton
from .dockitem import DockItem
from .util import _rect_contains


#DRAG_TARGET_GROUP = 0
#DRAG_TARGET_ITEM = 1


class _DockGroupTab(object):
    '''
    Convenience class storing information about a tab.
    '''
    __slots__ = ['item',                # DockItem associated with this tab
                 'item_title_handler',
                 'item_title_tooltip_text_handler',
                 'image',               # icon (gtk.Image)
                 'label',               # title (gtk.Label)
                 'button',              # close button (etk.docking.CompactButton)
                 'menu_item',           # menu item (gtk.ImageMenuItem)
                 'state',               # state (one of the GTK State Type Constants)
                 'area']                # area, used for hit testing (gdk.Rectangle)


class DockGroup(gtk.Container):
    '''
    The etk.DockGroup class groups etk.DockItem children in a tabbed interface.

    You can reorder tabs by dragging them to the desired location within the
    same or another etk.DockGroup having the same group-id. You can also drag
    a complete etk.DockGroup onto another etk.DockGroup having the same group-id
    to merge all etk.DockItems from the source into the destination etk.DockGroup.
    '''
    __gtype_name__ = 'EtkDockGroup'
    __gproperties__ = {'group-id': (gobject.TYPE_UINT,
                                    'group id',
                                    'group id',
                                    0,
                                    gobject.G_MAXINT,
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

#        # Configure drag/drop
#        self.drag_source_set(gdk.BUTTON1_MASK,
#                             [('application/x-rootwin-drop', gtk.TARGET_SAME_APP, DRAG_TARGET_GROUP)],
#                             gdk.ACTION_PRIVATE)
#        self.drag_dest_set(gtk.DEST_DEFAULT_ALL,
#                           [('application/x-rootwin-drop', gtk.TARGET_SAME_APP, DRAG_TARGET_GROUP)],
#                           gdk.ACTION_PRIVATE)

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
#    def _drag_hightlight_expose(self, widget, event):
#        pass
#
#    def drag_highlight(self, widget):
#        '''
#        Highlight the given widget in the default manner.
#        '''
#        pass
#
#    def drag_unhighlight(self, widget):
#        '''
#        Refresh the given widget to remove the highlight.
#        '''
#        pass

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

            tab.area.width = (self._frame_width + self._spacing + iw +
                             self._spacing + lw + self._spacing + bw +
                             self._spacing + self._frame_width)
            tab.area.height = (self._frame_width + self._spacing + max(ih, lh, bh) +
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
        if self._tabs:
            current_tab_index = self._tabs.index(self._current_tab)

            # We'll try to keep the current item's tab in the same location to
            # prevent tabs from jumping around. To do this we need to store the
            # current item's tab position before we reset self._visible_tabs.
            max_tabs_before_current = len(self._tabs)
            if self._visible_tabs and self._current_tab in self._visible_tabs:
                max_tabs_before_current = self._visible_tabs.index(self._current_tab)

            # Reset visible tabs
            self._visible_tabs = []

            # Calculate available tab area width
            available_width = (allocation.width - self._frame_width - self._spacing -
                               max_w - min_w - list_w - self._spacing -
                               self._current_tab.area.width)

            # Show tabs to the left of the current item's tab, but don't make
            # the current item's tab jump position.
            count = 0
            for tab in reversed(self._tabs[:current_tab_index]):
                if available_width - tab.area.width >= 0:
                    if count < max_tabs_before_current:
                        count += 1
                        available_width -= tab.area.width
                        self._visible_tabs.insert(0, tab)
                    else:
                        break
                else:
                    break

            # Current item's tab is always visible
            self._visible_tabs.append(self._current_tab)

            # Show tabs to the right of the current item's tab
            for tab in self._tabs[current_tab_index + 1:]:
                if available_width - tab.area.width >= 0:
                    available_width -= tab.area.width
                    self._visible_tabs.append(tab)
                else:
                    break

            # Check if we can add extra tabs to the left of the current
            # item's tab. Only add tabs that have been skipped above while
            # preventing the current item's tab from jumping position
            for tab in reversed(self._tabs[:current_tab_index - count]):
                if available_width - tab.area.width >= 0:
                    available_width -= tab.area.width
                    self._visible_tabs.insert(0, tab)
                else:
                    break

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

            lx = cx + self._frame_width + self._spacing + iw + self._spacing
            ly = (tab.area.height - lh) / 2 + 1
            tab.label.size_allocate(gdk.Rectangle(lx, ly, lw, lh))

            bx = (cx + self._frame_width + self._spacing + iw +
                  self._spacing + lw + self._spacing)
            by = (tab.area.height - bh) / 2 + 1
            tab.button.size_allocate(gdk.Rectangle(bx, by, bw, bh))

            cx += tab.area.width

        # Allocate space for the current item
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
        c = pangocairo.CairoContext(event.window.cairo_create())
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
        if self._tabs:
            current_tab_index = self._tabs.index(self._current_tab)
            visible_index = 0
            for index, tab in enumerate(self._tabs):
                if tab in self._visible_tabs:
                    tx = tab.area.x
                    ty = tab.area.y
                    tw = tab.area.width
                    th = tab.area.height

                    if index < current_tab_index and visible_index != 0:
                        c.move_to(tx + 0.5, ty + th)
                        c.line_to(tx + 0.5, ty + 8.5)
                        c.arc(tx + 8.5, 8.5, 8, 180 * (pi / 180), 270 * (pi / 180))
                        c.set_source_rgb(*dark)
                        c.stroke()
                    elif index > current_tab_index:
                        c.arc(tx + tw - 8.5, 8.5, 8, 270 * (pi / 180), 360 * (pi / 180))
                        c.line_to(tx + tw - 0.5, ty + th)
                        c.set_source_rgb(*dark)
                        c.stroke()
                    elif index == current_tab_index:
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

                    # Keep track of visible tabs
                    visible_index  += 1

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

        for tab in self._visible_tabs:
            if _rect_contains(tab.area, event.x, event.y):
                # Update tooltip for tab under the cursor
                self.set_tooltip_text(tab.item.get_title_tooltip_text())

                if tab.state == gtk.STATE_NORMAL:
                    tab.state = gtk.STATE_PRELIGHT
                    self.queue_resize()
            else:
                if tab.state == gtk.STATE_PRELIGHT:
                    tab.state = gtk.STATE_NORMAL
                    self.queue_resize()

    def do_button_release_event(self, event):
        for tab in self._visible_tabs:
            if _rect_contains(tab.area, event.x, event.y):
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

#    # drag/drop source
#    def do_drag_begin(self, context):
#        self.log.debug('%s' % context)
#
#    def do_drag_data_get(self, context, selection_data, info, timestamp):
#        self.log.debug('%s, %s, %s' % (context, selection_data, info))
#
#    def do_drag_data_delete(self, context):
#        self.log.debug('%s' % context)
#
#    def do_drag_end(self, context):
#        self.log.debug('%s', context)
#
#    def do_drag_failed(self, context, result):
#        self.log.debug('%s, %s' % [context, result])
#
#    # drag/drop destination
#    def do_drag_motion(self, context, x, y, timestamp):
#        self.log.debug('%s, %s, %s' % (context, x, y))
#
#        # Insert the dragged tab before the tab under (x, y)
#        if _rect_contains(self._decoration_area, x, y):
#            for tab in self._tabs:
#                if _rect_contains(tab.area, x, y):
#                    self.log.info('insert dragged tab before %s' % tab)
#                    return
#
#        self.log.info('append dragged tab')
#
#    def do_drag_leave(self, context, timestamp):
#        self.log.debug('%s, %s' % (context, timestamp))
#
#    def do_drag_drop(self, context, x, y, timestamp):
#        self.log.debug('%s, %s, %s' % (context, x, y))
#
#    def do_drag_data_received(self, context, x, y, selection_data, info, timestamp):
#        self.log.debug('%s, %s, %s, %s, %s' % (context, x, y, selection_data, info))

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

    def insert_item(self, item, position=None):
        '''
        :param item: a DockItem
        :param position: the index (starting at 0) at which to insert the item,
                         or None to append the item after all other item tabs.
        :returns: the index number of the item tab in the DockGroup

        The insert_item() method inserts a DockItem into the DockGroup at the
        location specified by position (0 is the first item). item is the
        DockItem to use. If position is None the item is appended to the DockGrup.
        '''
        if not isinstance(item, DockItem):
            #TODO: raise something specific
            raise

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

        self._tabs.insert(position, tab)

        if self.flags() & gtk.REALIZED:
            tab.item.set_parent_window(self.window)
            tab.image.set_parent_window(self.window)
            tab.label.set_parent_window(self.window)
            tab.button.set_parent_window(self.window)

        item_num = self.item_num(item)
        self.set_current_item(item_num)

        return item_num

    def remove_item(self, item_num):
        '''
        :param item_num: the index of an item tab, starting from 0. If None,
                         the last item will be removed.

        The remove_item() method removes the item at the location specified by
        index. The value of index starts from 0.
        '''
        if item_num is None:
            tab = self._tabs[-1]
        else:
            tab = self._tabs[item_num]

        # We need this to reset the current item below
        old_tab_index = self._tabs.index(self._current_tab)

        # Remove from self._visible_tabs list
        if tab in self._visible_tabs:
            self._visible_tabs.remove(tab)

        # Remove tab item
        tab.item.disconnect(tab.item_title_handler)
        tab.item.disconnect(tab.item_title_tooltip_text_handler)
        tab.item.unparent()
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

        The get_n_items() method returns the number of item tabs in the DockGroup.
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
