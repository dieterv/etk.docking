#!/usr/bin/env python
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

import logging
import random

import gobject
import gtk
import gtk.gdk as gdk

try:
    from etk.docking import DockLayout, DockPaned, DockGroup, DockItem
except ImportError:
    # The lib directory is most likely not on PYTHONPATH, so add it here.
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'lib')))
    from etk.docking import DockLayout, DockPaned, DockGroup, DockItem
    del os, sys


class MainWindow(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self)

        self.set_default_size(500, 150)
        self.set_title('etk.docking demo')
        self.set_border_width(4)
        self._counter = 1

        vbox = gtk.VBox()
        vbox.set_spacing(4)
        self.add(vbox)

        ########################################################################
        # DockLayout
        ########################################################################
        #self.docklayout = DockLayout()
        #vbox.pack_start(self.docklayout)

        self.dp1 = DockPaned()
        self.dp1.set_orientation(gtk.ORIENTATION_HORIZONTAL)
        vbox.pack_start(self.dp1)

        self.dg1 = DockGroup()
        self.dp1.add(self.dg1)

        self.dp2 = DockPaned()
        self.dp2.set_orientation(gtk.ORIENTATION_VERTICAL)
        self.dp1.add(self.dp2)

        self.dg2 = DockGroup()
        self.dp2.add(self.dg2)

        self.dg3 = DockGroup()
        self.dp2.add(self.dg3)

        self.dg4 = DockGroup()
        self.dp1.add(self.dg4)

        ########################################################################
        # Testing Tools
        ########################################################################
        adddgbutton = gtk.Button('Add DockGroup')
        adddgbutton.connect('clicked', self._on_add_dg_button_clicked)
        vbox.pack_start(adddgbutton, False, False)

        adddibutton = gtk.Button('Create DockItems')
        adddibutton.connect('clicked', self._on_add_di_button_clicked)
        vbox.pack_start(adddibutton, False, False)

        orientationbutton = gtk.Button('Switch Orientation')
        orientationbutton.connect('clicked', self._on_orientation_button_clicked)
        vbox.pack_start(orientationbutton, False, False)

        self.show_all()

    def _on_add_dg_button_clicked(self, button):
        dg = DockGroup()
        dg.show()
        self.dp1.add(dg)

        dg = DockGroup()
        dg.show()
        self.dp2.add(dg)

    def _on_add_di_button_clicked(self, button):
        for child in self.dp1:
            if isinstance(child, DockGroup):
                self._add_dockitems(child)
            elif isinstance(child, DockPaned):
                for child in child:
                    self._add_dockitems(child)

    def _on_orientation_button_clicked(self, button):
        if self.dp1.get_orientation() == gtk.ORIENTATION_HORIZONTAL:
            self.dp1.set_orientation(gtk.ORIENTATION_VERTICAL)
            self.dp2.set_orientation(gtk.ORIENTATION_HORIZONTAL)
        else:
            self.dp1.set_orientation(gtk.ORIENTATION_HORIZONTAL)
            self.dp2.set_orientation(gtk.ORIENTATION_VERTICAL)

    def _add_dockitems(self, dockgroup):
        examples = [('calc', 'calculator', '#!/usr/bin/env python\n\nprint \'Hello!\''),
                    ('file-manager', 'Hi!', 'Hello!'),
                    ('fonts', 'ABC', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'),
                    ('style', 'abc', 'abcdefghijklmnopqrstuvwxyz'),
                    ('web-browser', 'browser', '0123456789'),
                    ('date', 'today', '9876543210')]

        for i in range(random.randrange(1, 10, 1)):
            icon_name, tooltip_text, text = random.choice(examples)

            # Create a TextView and set some example text
            scrolledwindow = gtk.ScrolledWindow()
            scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
            textview = gtk.TextView()
            textview.get_buffer().set_text(text)
            scrolledwindow.add(textview)

            # Create a DockItem and add our TextView
            di = DockItem(icon_name=icon_name, title='New %s' % self._counter, title_tooltip_text=tooltip_text)
            di.add(scrolledwindow)
            di.show_all()
            self._counter += 1

            # Add out DockItem to the DockGroup
            dockgroup.add(di)


def quit(widget, event, mainloop):
    mainloop.quit()

def main():
    # Initialize logging
    logging.basicConfig(level=logging.DEBUG,
                        format='%(levelname)s:%(name)s:%(message)s')

    # Initialize mainloop
    gobject.threads_init()
    mainloop = gobject.MainLoop()

    # Initialize mainwindow
    mainwindow = MainWindow()
    mainwindow.connect('delete-event', quit, mainloop)
    mainwindow.show()

    # Run mainloop
    mainloop.run()


if __name__ == '__main__':
    main()
