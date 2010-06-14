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
from .dockframe import DockFrame
from .dockgroup import DRAG_TARGET_ITEM_LIST



class DockLayout(object):

    def __init__(self):

        # Initialize logging
        self.log = getLogger('<%s object at %s>' % (self.__class__.__name__, hex(id(self))))

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
        # TODO: Add DND handlers
        widget.drag_dest_set(gtk.DEST_DEFAULT_MOTION | gtk.DEST_DEFAULT_HIGHLIGHT,
                             [DRAG_TARGET_ITEM_LIST],
                             gdk.ACTION_MOVE)

        # TODO: We're also interested in drag-failed on DockGroups
        for name, callback in (('add', self.on_widget_add),
                               ('remove', self.on_widget_remove),
                               ('drag_motion', self.on_widget_drag_motion),
                               ('drag-leave', self.on_widget_drag_leave),
                               ('drag-drop', self.on_widget_drag_drop),
                               ('drag-data-received', self.on_widget_drag_data_received)):
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
        if isinstance(widget, gtk.Container):
            self.remove_signal_handlers(widget)

    def on_widget_drag_motion(self, widget, context, x, y, timestamp):
        self.log.debug('on widget drag motion %s: %s %s', widget, x, y)

    def on_widget_drag_leave(self, widget, context, timestamp):
        self.log.debug('on widget drag leave')

    def on_widget_drag_drop(self, widget, context, x, y, timestamp):
        self.log.debug('on widget drag drop: %s %s', x, y)

    def on_widget_drag_data_received(self, widget, context, x, y, selection_data, info, timestamp):
        self.log.debug('on widget drag data recieved, %s, %s, %s, %s, %s, %s' % (context, x, y, selection_data, info, timestamp))

