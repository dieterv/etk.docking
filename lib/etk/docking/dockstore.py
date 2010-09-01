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
from xml.etree.ElementTree import Element, SubElement, tostring
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


def parent_attributes(widget):
    container = widget.get_parent()
    if isinstance(container, DockPaned):
        paned_item = [i for i in container.items if i.child is widget][0]
        d = { 'expand': str(paned_item.expand).lower() }
        if paned_item.min_weight:
            d['min-weight'] = str(paned_item.min_weight)
        if paned_item.weight:
            d['weight'] = str(paned_item.weight)
    return {}

@generic
def attributes(widget):
    raise NotImplemented()

@attributes.when_type(DockItem)
def dock_item_attributes(widget):
    return { "name": widget.get_name() or 'empty',
             "icon-name": widget.props.icon_name,
             "title": widget.props.title, 
             "title-tooltip-text": widget.props.title_tooltip_text }

@attributes.when_type(DockGroup)
def dock_group_attributes(widget):
    a = widget.allocation
    return dict(width=str(a.width), height=str(a.height),
                **parent_attributes(widget))

@attributes.when_type(DockPaned)
def dock_paned_attributes(widget):
    a = widget.allocation
    return dict(width=str(a.width), height=str(a.height),
                orientation=(widget.get_orientation() == gtk.ORIENTATION_HORIZONTAL and "horizontal" or "vertical"),
                **parent_attributes(widget))

@attributes.when_type(DockFrame)
def dock_frame_attributes(widget):
    a = widget.allocation
    return dict(width=str(a.width), height=str(a.height))

