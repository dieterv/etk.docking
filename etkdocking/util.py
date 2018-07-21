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


import gtk


def rect_contains(rect, x, y):
    '''
    The rect_contains function checks if a point, defined by x and y falls
    within the gdk.Rectangle defined by rect.

    Note: Unlike rect_overlaps defined below, this function ignores a 1 pixel border.
    '''
    if x > rect.x and x < rect.x + rect.width and y > rect.y and y < rect.y + rect.height:
        return True
    else:
        return False

def rect_overlaps(rect, x, y):
    '''
    The rect_overlaps function checks if a point, defined by x and y overlaps
    the gdk.Rectangle defined by rect.

    Note: Unlike rect_contains defined above, this function does not ignore a 1 pixel border.
    '''
    if x >= rect.x and x <= rect.x + rect.width and y >= rect.y and y <= rect.y + rect.height:
        return True
    else:
        return False

# TODO: Should change/add on this 'cause it does not work well with IconFactories for example.
def load_icon(icon_name, size):
    icontheme = gtk.icon_theme_get_default()

    if not icontheme.has_icon(icon_name):
        icon_name = 'gtk-missing-image'

    return icontheme.load_icon(icon_name, size, gtk.ICON_LOOKUP_USE_BUILTIN)

def load_icon_image(icon_name, size):
    icontheme = gtk.icon_theme_get_default()

    if not icontheme.has_icon(icon_name):
        icon_name = 'gtk-missing-image'

    return gtk.image_new_from_icon_name(icon_name, size)

def flatten(w, child_getter=gtk.Container.get_children):
    """
    Generator function that returns all items in a hierarchy.
    Default `child_getter` returns children in a GTK+ widget hierarchy.
    """
    yield w
    try:
        for c in child_getter(w):
            for d in flatten(c, child_getter):
                yield d
    except TypeError:
        pass # Not a child of the right type
