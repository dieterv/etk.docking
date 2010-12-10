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


import unittest

import gtk

from etk.docking import DockItem


class TestDockItem(unittest.TestCase):
    ############################################################################
    # Test properties
    ############################################################################
    def test_prop_title(self):
        global notify_called

        def _on_notify(gobject, pspec):
            global notify_called
            notify_called = True

        dockitem = DockItem()
        dockitem.connect('notify::title', _on_notify)

        notify_called = False
        dockitem.set_title('sometitle')
        self.assertEquals(dockitem.get_title(), 'sometitle',
                          msg='get_title method did not return expected value')
        self.assertTrue(notify_called,
                        msg='title property change notification failed when using set_title method')

        notify_called = False
        dockitem.set_property('title', 'anothertitle')
        self.assertEquals(dockitem.get_property('title'), 'anothertitle',
                          msg='get_property method did not return expected value')
        self.assertTrue(notify_called,
                        msg='title property change notification failed when using set_property method')

        notify_called = False
        dockitem.props.title = 'hello'
        self.assertEquals(dockitem.props.title, 'hello',
                          msg='.props attribute did not return expected value')
        self.assertTrue(notify_called,
                        msg='title property change notification failed when using .props attribute')

        dockitem.destroy()

    def test_prop_title_tooltip_text(self):
        global notify_called

        def _on_notify(gobject, pspec):
            global notify_called
            notify_called = True

        dockitem = DockItem()
        dockitem.connect('notify::title-tooltip-text', _on_notify)

        notify_called = False
        dockitem.set_title_tooltip_text('sometext')
        self.assertEquals(dockitem.get_title_tooltip_text(), 'sometext',
                          msg='get_title_tooltip_text method did not return expected value')
        self.assertTrue(notify_called,
                        msg='title-tooltip-text property change notification failed when using set_title_tooltip_text method')

        notify_called = False
        dockitem.set_property('title-tooltip-text', 'anothertext')
        self.assertEquals(dockitem.get_property('title-tooltip-text'), 'anothertext',
                          msg='get_property method did not return expected value')
        self.assertTrue(notify_called,
                        msg='title-tooltip-text property change notification failed when using set_title_tooltip_text method')

        notify_called = False
        dockitem.props.title_tooltip_text = 'hello'
        self.assertEquals(dockitem.props.title_tooltip_text, 'hello',
                          msg='.props attribute did not return expected value')
        self.assertTrue(notify_called,
                        msg='title-tooltip-text property change notification failed when using .props attribute')

        dockitem.destroy()

    def test_prop_icon_name(self):
        global notify_called

        def _on_notify(gobject, pspec):
            global notify_called
            notify_called = True

        dockitem = DockItem()
        dockitem.connect('notify::icon-name', _on_notify)

        notify_called = False
        dockitem.set_icon_name('someicon')
        self.assertEquals(dockitem.get_icon_name(), 'someicon',
                          msg='get_icon_name method did not return expected value')
        self.assertTrue(notify_called,
                        msg='icon-name property change notification failed when using set_icon_name method')

        notify_called = False
        dockitem.set_property('icon-name', 'anothericon')
        self.assertEquals(dockitem.get_property('icon-name'), 'anothericon',
                          msg='get_property method did not return expected value')
        self.assertTrue(notify_called,
                        msg='icon-name property change notification failed when using set_property method')

        notify_called = False
        dockitem.props.icon_name = 'niceicon'
        self.assertEquals(dockitem.props.icon_name, 'niceicon',
                          msg='.props attribute did not return expected value')
        self.assertTrue(notify_called,
                        msg='icon-name property change notification failed when using .props attribute')

        dockitem.destroy()

    def test_prop_stock(self):
        global notify_called

        def _on_notify(gobject, pspec):
            global notify_called
            notify_called = True

        dockitem = DockItem()
        dockitem.connect('notify::stock', _on_notify)

        notify_called = False
        dockitem.set_stock(gtk.STOCK_ABOUT)
        self.assertEquals(dockitem.get_stock(), gtk.STOCK_ABOUT,
                          msg='get_stock method did not return expected value')
        self.assertTrue(notify_called,
                        msg='stock property change notification failed when using set_stock method')

        notify_called = False
        dockitem.set_property('stock', gtk.STOCK_ADD)
        self.assertEquals(dockitem.get_property('stock'), gtk.STOCK_ADD,
                          msg='get_property method did not return expected value')
        self.assertTrue(notify_called,
                        msg='stock property change notification failed when using set_property method')

        notify_called = False
        dockitem.props.stock = gtk.STOCK_APPLY
        self.assertEquals(dockitem.props.stock, gtk.STOCK_APPLY,
                          msg='.props attribute did not return expected value')
        self.assertTrue(notify_called,
                        msg='stock property change notification failed when using .props attribute')

        dockitem.destroy()

    def test_prop_image(self):
        #TODO: is there a way to check we actually received the image we expect?
        dockitem = DockItem()
        dockitem.set_icon_name('someicon')
        self.assertTrue(isinstance(dockitem.get_image(), gtk.Image))
        self.assertTrue(isinstance(dockitem.props.image, gtk.Image))
        self.assertTrue(isinstance(dockitem.get_property('image'), gtk.Image))
        dockitem.destroy()

        dockitem = DockItem()
        dockitem.set_stock(gtk.STOCK_ABOUT)
        self.assertTrue(isinstance(dockitem.get_image(), gtk.Image))
        self.assertTrue(isinstance(dockitem.props.image, gtk.Image))
        self.assertTrue(isinstance(dockitem.get_property('image'), gtk.Image))
        dockitem.destroy()

    ############################################################################
    # Test public api
    ############################################################################
    def test_add(self):
        button = gtk.Button()
        dockitem = DockItem()
        dockitem.add(button)

        self.assertTrue(dockitem.child is button)

        button.destroy()
        dockitem.destroy()

    def test_remove(self):
        button = gtk.Button()
        dockitem = DockItem()
        dockitem.add(button)
        dockitem.remove(button)

        self.assertTrue(dockitem.child is None)

        button.destroy()
        dockitem.destroy()

    ############################################################################
    # Test appearance
    ############################################################################
#    def test_appearance(self):
#        frame = gtk.Frame()
#        frame.set_shadow_type(gtk.SHADOW_NONE)
#        frame.set_size_request(25, 25)
#        di = DockItem('gtk-missing-image', 'test')
#        di.add(frame)
#        dg = DockGroup()
#        dg.add(di)
#        window = gtk.Window()
#        window.add(dg)
#        window.show_all()
#
#        snapshot = dg.get_snapshot(None)
#        pixbuf = gdk.Pixbuf(gdk.COLORSPACE_RGB, True, 8, *snapshot.get_size())
#        pixbuf.get_from_drawable(snapshot, window.get_colormap(), 0, 0, 0, 0, *snapshot.get_size())
#        pixbuf.save(os.path.join(os.path.dirname(__file__), 'test_dockitem.test_appearance.png'), 'png', {})
