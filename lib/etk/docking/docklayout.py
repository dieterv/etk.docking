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
from logging import getLogger

from .dockframe import DockFrame

class DockLayout(object):

    def __init__(self):
        self.frames = set()

    def add(self, frame):
        assert isinstance(frame, DockFrame)
        self.frames.add(frame)
        self.setup_signal_handlers(frame)

    def remove_layout(self, frame):
        self.remove_signal_handlers(frame)
        self.frames.remove(frame)


    def setup_signal_handlers(self, frame):
        """
        Set up signal handlers for layout and child widgets
        """
        pass

    def remove_signal_handlers(self, frame):
        """
        Remove signal handlers.
        """
        pass
