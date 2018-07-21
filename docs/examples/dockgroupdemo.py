#!/usr/bin/env python
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

import logging
import random

import gobject
import gtk
import gtk.gdk as gdk
import pango

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
        self.set_title('DockGroup Demo')
        self.set_border_width(4)
        self.file_counter = 1

        vbox = gtk.VBox()
        vbox.set_spacing(4)
        self.add(vbox)

        ########################################################################
        # Docking
        ########################################################################
        self.dg = DockGroup()
        vbox.pack_start(self.dg)

        ########################################################################
        # Testing Tools
        ########################################################################
        adddibutton = gtk.Button('Create docked items')
        adddibutton.child.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
        adddibutton.connect('clicked', self._on_add_di_button_clicked)
        vbox.pack_start(adddibutton, False, False)

        self.show_all()

    def _on_add_di_button_clicked(self, button):
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
            di = DockItem(icon_name=icon_name, title='New %s' % self.file_counter, title_tooltip_text=tooltip_text)
            di.add(scrolledwindow)
            di.show_all()

            # Add out DockItem to the DockGroup
            self.dg.add(di)

            # Increment file counter
            self.file_counter += 1


def quit(widget, event, mainloop):
    mainloop.quit()

def main():
    # Initialize logging
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s\t%(levelname)s\t%(name)s\t%(funcName)s\t%(message)s')

    # Uncomment to enable log filtering
    #for handler in logging.getLogger('').handlers:
    #    handler.addFilter(logging.Filter('EtkDockGroup'))

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
