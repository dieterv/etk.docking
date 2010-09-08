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
import sys
import gtk
from logging import getLogger
from simplegeneric import generic
from xml.etree.ElementTree import Element, SubElement, tostring, fromstring
from .docklayout import DockLayout
from .dockframe import DockFrame
from .dockpaned import DockPaned
from .dockgroup import DockGroup
from .dockitem import DockItem

SERIALIZABLE = ( DockFrame, DockPaned, DockGroup, DockItem )

def serialize(layout):
    def _ser(widget, element):
        if isinstance(widget, SERIALIZABLE):
            sub = SubElement(element, type(widget).__name__.lower(),
                             attributes(widget))
            widget.foreach(_ser, sub)
    tree = Element('layout')
    map(_ser, layout.frames, [tree] * len(layout.frames))
    return tostring(tree, encoding=sys.getdefaultencoding())

widget_factory = {}

def deserialize(layoutstr, itemfactory):
    def _des(element, parent_widget=None):
        factory = widget_factory[element.tag]
        widget = factory(parent=parent_widget, **element.attrib)
        if isinstance(widget, DockItem):
            widget.add(itemfactory(widget.get_name()))
        assert widget, 'No widget (%s)' % widget
        if element:
            map(_des, element, [widget] * len(element))
        return widget
    tree = fromstring(layoutstr)
    layout = DockLayout()
    map(_des, tree, [ layout ] * len(tree))
    return layout


def parent_attributes(widget):
    container = widget.get_parent()
    d = {}
    if isinstance(container, DockPaned):
        paned_item = [i for i in container.items if i.child is widget][0]
        d = { 'expand': str(paned_item.expand).lower() }
        if paned_item.weight:
            d['weight'] = str(paned_item.weight)
    return d

@generic
def attributes(widget):
    raise NotImplementedError

@attributes.when_type(DockItem)
def dock_item_attributes(widget):
    return { 'name': widget.get_name() or 'empty',
             'icon': widget.props.icon_name,
             'title': widget.props.title, 
             'tooltip': widget.props.title_tooltip_text }

@attributes.when_type(DockGroup)
def dock_group_attributes(widget):
    return parent_attributes(widget)

@attributes.when_type(DockPaned)
def dock_paned_attributes(widget):
    return dict(orientation=(widget.get_orientation() == gtk.ORIENTATION_HORIZONTAL and 'horizontal' or 'vertical'),
                **parent_attributes(widget))

@attributes.when_type(DockFrame)
def dock_frame_attributes(widget):
    a = widget.allocation
    return dict(width=str(a.width), height=str(a.height))

def factory(typename):
    '''
    Simple decorator for populating the widget_factory dictionary.
    '''
    def _factory(func):
        widget_factory[typename] = func
        return func
    return _factory

@factory('dockitem')
def dock_item(parent, icon, name, title, tooltip, pos=None, vispos=None, current=None):
    item = DockItem(icon, title, tooltip)
    item.set_name(name)
    if pos: pos = int(pos)
    if vispos: vispos = int(vispos)
    parent.insert_item(item, pos, vispos)
    return item

@factory('dockgroup')
def dock_paned_factory(parent, expand=None, weight=None):
    group = DockGroup()
    if expand is not None:
        item = parent.insert_child(group, expand=(expand == 'true'))
        item.weight = float(weight)
    else:
        parent.add(group)
    if isinstance(parent, DockPaned):
        parent._reset_weights = False
    return group

@factory('dockpaned')
def dock_paned_factory(parent, orientation, expand=None, weight=None):
    paned = DockPaned()
    if orientation == 'horizontal':
        paned.set_orientation(gtk.ORIENTATION_HORIZONTAL)
    else:
        paned.set_orientation(gtk.ORIENTATION_VERTICAL)
    if expand is not None:
        item = parent.insert_child(paned, expand=(expand == 'true'))
        item.weight = float(weight)
    else:
        parent.add(paned)
    if isinstance(parent, DockPaned):
        parent._reset_weights = False
    return paned
    
@factory('dockframe')
def dock_frame_factory(parent, width, height):
    frame = DockFrame()
    #frame.realize()
    frame.set_size_request(int(width), int(height))
    if parent: parent.add(frame)
    return frame
