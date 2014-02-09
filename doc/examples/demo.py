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

from gi.repository import Gtk
from gi.repository import Pango

try:
    import etk.docking
except ImportError:
    # The lib directory is most likely not on PYTHONPATH, so add it here.
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'lib')))
    del os, sys
finally:
    from etk.docking import DockLayout, DockFrame, DockPaned, \
                            DockGroup, DockItem, dockstore, settings


class MainWindow(Gtk.Window):
    def __init__(self, docklayout=None, dockframe=None):
        Gtk.Window.__init__(self)

        self.set_default_size(500, 150)
        self.set_title('etk.docking demo')
        self.set_border_width(4)
        self.file_counter = 1
        self.subwindows = []

        vbox = Gtk.VBox()
        vbox.set_spacing(4)
        self.add(vbox)

        ########################################################################
        # Docking
        ########################################################################
        if docklayout and dockframe:
            self.dockframe = dockframe
            self.docklayout = docklayout
        else:
            self.dockframe = DockFrame()
            self.dockframe.set_border_width(8)
            g = DockGroup()
            g.set_name('main')
            self.dockframe.add(g)
            self.docklayout = DockLayout()
            self.docklayout.add(self.dockframe)

        settings['main'].auto_remove = False
        settings['main'].can_float = True
        settings['main'].inherit_settings = False
        settings['main'].expand = False


        # To change default group behaviour:
        #self.docklayout.settings[None].inherit_settings = False

        vbox.pack_start(self.dockframe, True, True, 0)

        def on_item_closed(layout, group, item):
            item.destroy()
            print 'closed item:', item.title

        self.docklayout.connect('item-closed', on_item_closed)

        def on_item_selected(layout, group, item):
            print 'Selected item:', item.title

        self.docklayout.connect('item-selected', on_item_selected)

        ########################################################################
        # Testing Tools
        ########################################################################
        adddibutton = Gtk.Button('Create docked items')
        #adddibutton.get_child().set_ellipsize(pango.ELLIPSIZE_MIDDLE)
        adddibutton.connect('clicked', self._on_add_di_button_clicked)
        vbox.pack_start(adddibutton, False, False, 0)

        orientationbutton = Gtk.Button('Switch Orientation')
        #orientationbutton.child.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
        orientationbutton.connect('clicked', self._on_orientation_button_clicked)
        vbox.pack_start(orientationbutton, False, False, 0)

        hbox = Gtk.HBox()

        savebutton = Gtk.Button('Save layout')
        #savebutton.child.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
        savebutton.connect('clicked', self._on_save_button_clicked)
        hbox.pack_start(savebutton, True, True, 0)

        loadbutton = Gtk.Button('Load layout')
        #loadbutton.child.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
        loadbutton.connect('clicked', self._on_load_button_clicked)
        hbox.pack_start(loadbutton, True, True, 0)

        vbox.pack_start(hbox, False, False, 0)

        self.show_all()

        #def on_has_toplevel_focus(window, pspec):
        #    print 'Has toplevel focus', window, pspec
        #    print 'Focus widget is', window.get_focus()

        #self.connect('notify::has-toplevel-focus', on_has_toplevel_focus)

    def _on_add_di_button_clicked(self, button):
        def add_dockitems(child):
            if isinstance(child, DockGroup):
                self._add_dockitems(child)
            elif isinstance(child, DockPaned):
                for child in child:
                    add_dockitems(child)

        for child in self.dockframe:
            add_dockitems(child)

    def _on_orientation_button_clicked(self, button):
        def switch_orientation(paned):
            if isinstance(paned, DockPaned):
                if paned.get_orientation() == Gtk.Orientation.HORIZONTAL:
                    paned.set_orientation(Gtk.Orientation.VERTICAL)
                else:
                    paned.set_orientation(Gtk.Orientation.HORIZONTAL)

                for child in paned.get_children():
                    switch_orientation(child)

        paned = self.dockframe.get_children()[0]
        switch_orientation(paned)

    def _on_save_button_clicked(self, button):
        file = 'demo.sav'
        s = dockstore.serialize(self.docklayout)

        with open(file, 'w') as f:
            f.write(s)

    def _on_load_button_clicked(self, button):
        file = 'demo.sav'

        with open(file) as f:
            s = f.read()

        newlayout = dockstore.deserialize(s, self._create_content)
        main_frames = list(dockstore.get_main_frames(newlayout))
        assert len(main_frames) == 1, main_frames
        subwindow = MainWindow(newlayout, main_frames[0])
        self.subwindows.append(subwindow)
        dockstore.finish(newlayout, main_frames[0])

        for f in newlayout.frames:
            f.get_toplevel().show_all()

    def _create_content(self, text=None):
        # Create a TextView and set some example text
        scrolledwindow = Gtk.ScrolledWindow()
        #scrolledwindow.set_policy(Gtk.ScrollablePolicy.AUTOMATIC, Gtk.ScrollablePolicy.AUTOMATIC)
        textview = Gtk.TextView()
        textview.get_buffer().set_text(text)
        scrolledwindow.add(textview)
        return scrolledwindow

    def _add_dockitems(self, dockgroup):
        examples = [(Gtk.STOCK_EXECUTE, 'calculator', '#!/usr/bin/env python\n\nprint \'Hello!\''),
                    (Gtk.STOCK_OPEN, 'Hi!', 'Hello!'),
                    (Gtk.STOCK_FILE, 'ABC', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'),
                    (Gtk.STOCK_FIND, 'abc', 'abcdefghijklmnopqrstuvwxyz'),
                    (Gtk.STOCK_HARDDISK, 'browser', '0123456789'),
                    (Gtk.STOCK_HOME, 'today', '9876543210'),
                    Gtk.Notebook]

        for i in [1]: #range(random.randrange(1, 10, 1)):
            example = random.choice(examples)

            if example is Gtk.Notebook:
                child = Gtk.Notebook()
                child.append_page(Gtk.Button('Click me'),
                                  Gtk.Label('New %s' % self.file_counter))
                stock_id = ''
                tooltip_text = 'notebook'
            else:
                stock_id, tooltip_text, text = example
                child = self._create_content(text)
                child.set_name(stock_id)

            # Create a DockItem and add our TextView
            di = DockItem(title='New %s' % self.file_counter, title_tooltip_text=tooltip_text, stock_id=stock_id)
            def on_close(item):
                print 'close:', item
            di.connect('close', on_close)
            di.add(child)
            di.show_all()

            # Add out DockItem to the DockGroup
            dockgroup.add(di)

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
    #    handler.addFilter(logging.Filter('EtkDockPaned'))

    # Initialize mainwindow
    mainwindow = MainWindow()
    mainwindow.connect('delete-event', Gtk.main_quit)
    mainwindow.show()

    Gtk.main()


if __name__ == '__main__':
    main()
