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

from gi.repository import GObject
from gi.repository import Gtk
import Gtk.gdk as gdk


class DockItem(Gtk.Bin):
    __gtype_name__ = 'EtkDockItem'
    __gproperties__ = {'title':
                           (GObject.TYPE_STRING,
                            'Title',
                            'The title for the DockItem.',
                            '',
                            GObject.PARAM_READWRITE),
                       'title-tooltip-text':
                           (GObject.TYPE_STRING,
                            'Title tooltip text',
                            'The tooltip text for the title.',
                            '',
                            GObject.PARAM_READWRITE),
                        'icon-name':
                           (GObject.TYPE_STRING,
                            'Icon name',
                            'The name of the icon from the icon theme.',
                            '',
                            GObject.PARAM_READWRITE),
                        'stock':
                           (GObject.TYPE_STRING,
                            'Stock',
                            'Stock ID for a stock image to display.',
                            '',
                            GObject.PARAM_READWRITE),
                        'image':
                           (GObject.TYPE_PYOBJECT,
                            'Image',
                            'The image constructed from the specified stock ID or icon-name. Default value is Gtk.STOCK_MISSING_IMAGE.',
                            GObject.PARAM_READABLE)}
    __gsignals__ = {'close':
                        (GObject.SignalFlags.RUN_LAST,
                         None, ())}

    def __init__(self, title='', title_tooltip_text='', icon_name=None, stock_id=None):
        GObject.GObject.__init__(self)
        self.set_flags(self.flags() | Gtk.NO_WINDOW)
        self.set_redraw_on_allocate(False)

        # Initialize logging
        self.log = getLogger('%s.%s' % (self.__gtype_name__, hex(id(self))))

        # Internal housekeeping
        self._icon_name = icon_name
        self._stock_id = stock_id

        self.set_title(title)
        self.set_title_tooltip_text(title_tooltip_text)
        self.set_icon_name(icon_name)
        self.set_stock(stock_id)

    ############################################################################
    # GObject
    ############################################################################
    def do_get_property(self, pspec):
        if pspec.name == 'title':
            return self.get_title()
        elif pspec.name == 'title-tooltip-text':
            return self.get_title_tooltip_text()
        elif pspec.name == 'icon-name':
            return self.get_icon_name()
        elif pspec.name == 'stock':
            return self.get_stock()
        elif pspec.name == 'image':
            return self.get_image()

    def do_set_property(self, pspec, value):
        if pspec.name == 'title':
            self.set_title(value)
        elif pspec.name == 'title-tooltip-text':
            self.set_title_tooltip_text(value)
        elif pspec.name == 'icon-name':
            self.set_icon_name(value)
        elif pspec.name == 'stock':
            self.set_stock(value)

    def get_title(self):
        return self._title

    def set_title(self, text):
        self._title = text
        self.notify('title')

    def get_title_tooltip_text(self):
        return self._title_tooltip_text

    def set_title_tooltip_text(self, text):
        self._title_tooltip_text = text
        self.notify('title-tooltip-text')

    def get_icon_name(self):
        return self._icon_name

    def set_icon_name(self, icon_name):
        self._icon_name = icon_name
        self.notify('icon-name')

    def get_stock(self):
        return self._stock_id

    def set_stock(self, stock_id):
        self._stock_id = stock_id
        self.notify('stock')

    def get_image(self):
        if self._icon_name:
            return Gtk.Image.new_from_icon_name(self._icon_name, Gtk.IconSize.MENU)
        elif self._stock_id:
            return Gtk.Image.new_from_stock(self._stock_id, Gtk.IconSize.MENU)
        else:
            return Gtk.Image()

    title = property(get_title, set_title)
    title_tooltip_text = property(get_title_tooltip_text, set_title_tooltip_text)
    icon_name = property(get_icon_name, set_icon_name)
    stock = property(get_stock, set_stock)

    ############################################################################
    # GtkWidget
    ############################################################################
    def do_size_request(self, requisition):
        requisition.width = 0
        requisition.height = 0

        if self.get_child() and self.get_child().flags() & Gtk.VISIBLE:
            (requisition.width, requisition.height) = self.get_child().size_request()
            requisition.width += self.border_width * 2
            requisition.height += self.border_width * 2

    def do_size_allocate(self, allocation):
        self.allocation = allocation

        if self.get_child() and self.get_child().flags() & Gtk.VISIBLE:
            child_allocation = ()
            child_allocation.x = allocation.x + self.border_width
            child_allocation.y = allocation.y + self.border_width
            child_allocation.width = allocation.width - (2 * self.border_width)
            child_allocation.height = allocation.height - (2 * self.border_width)
            self.get_child().size_allocate(child_allocation)

    ############################################################################
    # DockItem
    ############################################################################
    def do_close(self):
        group = self.get_parent()
        if group:
            group.remove(self)

    def close(self):
        self.emit('close')
