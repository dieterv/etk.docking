# -*- coding: utf-8 -*-
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


def rect_contains(rect, x, y):
    '''
    The rect_contains function checks if a point, defined by x and y falls
    within the gdk.Rectangle defined by rect.
    '''
    if x > rect.x and x < rect.x + rect.width and y > rect.y and y < rect.y + rect.height:
        return True
    else:
        return False

def rect_overlaps(rect, x, y):
    '''
    The rect_overlaps function checks if a point, defined by x and y overlaps
    the gdk.Rectangle defined by rect.
    '''
    if x >= rect.x and x <= rect.x + rect.width and y >= rect.y and y <= rect.y + rect.height:
        return True
    else:
        return False
