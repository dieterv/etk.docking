#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2010 Dieter Verfaillie <dieterv@optionexplicit.be>
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
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib')))
    from etk.docking import DockLayout, DockPaned, DockGroup, DockItem
    del os, sys


class MainWindow(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self)

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

        self.dockpaned = DockPaned()
        self.dockpaned.set_orientation(gtk.ORIENTATION_HORIZONTAL)
        vbox.pack_start(self.dockpaned)

        self.dg1 = DockGroup()
        self.dockpaned.add(self.dg1)

        self.dg2 = DockGroup()
        self.dockpaned.add(self.dg2)

        self.dg3 = DockGroup()
        self.dockpaned.add(self.dg3)

        ########################################################################
        # Testing Tools
        ########################################################################
        hbox = gtk.HBox()
        hbox.set_spacing(4)
        vbox.pack_start(hbox, False, False)

        adddgbutton = gtk.Button('Add DockGroup')
        adddgbutton.connect('clicked', self._on_add_dg_button_clicked)
        hbox.pack_start(adddgbutton, True, True)

        removedgbutton = gtk.Button('Remove DockGroup')
        removedgbutton.connect('clicked', self._on_remove_dg_button_clicked)
        hbox.pack_start(removedgbutton, True, True)

        adddibutton = gtk.Button('Create DockItems')
        adddibutton.connect('clicked', self._on_add_di_button_clicked)
        vbox.pack_start(adddibutton, False, False)

        showbutton = gtk.Button('Show Hidden DockGroups')
        showbutton.connect('clicked', self._on_show_button_clicked)
        vbox.pack_start(showbutton, False, False)

        orientationbutton = gtk.Button('Switch Orientation')
        orientationbutton.connect('clicked', self._on_orientation_button_clicked)
        vbox.pack_start(orientationbutton, False, False)

        self.show_all()

    def _on_add_dg_button_clicked(self, button):
        dg = DockGroup()
        dg.show()
        self.dockpaned.add(dg)

    def _on_remove_dg_button_clicked(self, button):
        items = self.dockpaned.get_children()
        try:
            dg = items[len(items) - 1]
        except IndexError:
            pass
        else:
            self.dockpaned.remove(dg)

    def _on_add_di_button_clicked(self, button):
        for dg in self.dockpaned:
            self._add_dockitems(dg)

    def _on_show_button_clicked(self, button):
        for dg in self.dockpaned:
            if not dg.props.visible:
                dg.props.visible = True

    def _on_orientation_button_clicked(self, button):
        if self.dockpaned.get_orientation() == gtk.ORIENTATION_HORIZONTAL:
            self.dockpaned.set_orientation(gtk.ORIENTATION_VERTICAL)
        else:
            self.dockpaned.set_orientation(gtk.ORIENTATION_HORIZONTAL)

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
