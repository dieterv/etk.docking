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


from __future__ import absolute_import


__all__ = ['DockLayout', 'DockPaned', 'DockGroup', 'DockItem']
__version__ = '0.0.1'
__docformat__ = 'restructuredtext'


############################################################################
# Initialize intl
############################################################################
import os, gtk, elib.intl
_ = elib.intl.install_module('etk.docking', os.path.abspath(os.path.join(
                                                os.path.dirname(__file__),
                                                '..', '..', 'share', 'locale')))

############################################################################
# Register some custom icons into the default icon theme
############################################################################
path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'icons', '16x16'))
gtk.icon_theme_add_builtin_icon('compact-close', 16, gtk.gdk.pixbuf_new_from_file(os.path.join(path, 'compact-close.png')))
gtk.icon_theme_add_builtin_icon('compact-close-prelight', 16, gtk.gdk.pixbuf_new_from_file(os.path.join(path, 'compact-close-prelight.png')))
gtk.icon_theme_add_builtin_icon('compact-list', 16, gtk.gdk.pixbuf_new_from_file(os.path.join(path, 'compact-list.png')))
gtk.icon_theme_add_builtin_icon('compact-minimize', 16, gtk.gdk.pixbuf_new_from_file(os.path.join(path, 'compact-minimize.png')))
gtk.icon_theme_add_builtin_icon('compact-maximize', 16, gtk.gdk.pixbuf_new_from_file(os.path.join(path, 'compact-maximize.png')))
gtk.icon_theme_add_builtin_icon('compact-restore', 16, gtk.gdk.pixbuf_new_from_file(os.path.join(path, 'compact-restore.png')))
del os, gtk,elib.intl, path

############################################################################
# GtkBuilder and Glade create GObject instances (and thus GTK+ widgets) using
# gobject.new(). For this to work, we have to be sure our subclasses have been
# registered with the GObject type system when etk.docking is imported.
# This also defines the widgets that can be considered public.
############################################################################
from .docklayout import DockLayout
from .dockpaned import DockPaned
from .dockgroup import DockGroup
from .dockitem import DockItem
