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


'''
Prints a colored html table containing all themeable GTK+ colors in each state
to stdout.
'''

from __future__ import absolute_import

import pygtk
pygtk.require('2.0')

import gtk


def main():
    w = gtk.Window()
    w.show()

    colors1 = ['fg', 'bg', 'base', 'light', 'mid', 'dark', 'text', 'text_aa']
    colors2 = ['white', 'black']

    print '    <table border=0>'
    print '      <tr>'
    print '        <td>&nbsp;</td>'
    print '        <td><b>STATE_INSENSITIVE</b></td>'
    print '        <td><b>STATE_NORMAL</b></td>'
    print '        <td><b>STATE_PRELIGHT</b></td>'
    print '        <td><b>STATE_ACTIVE</b></td>'
    print '        <td><b>STATE_SELECTED</b></td>'
    print '      </tr>'

    for attribute in colors1:
        print '      <tr>'
        print '        <td><b>%s</b></td>' % attribute

        color = w.style.__getattribute__(attribute)[gtk.STATE_INSENSITIVE]
        print '        <td bgcolor="#%x%x%x">&nbsp;</td>' % (int(color.red / 256.00), int(color.green / 256.00), int(color.blue / 256.00))
        color =  w.style.__getattribute__(attribute)[gtk.STATE_NORMAL]
        print '        <td bgcolor="#%x%x%x">&nbsp;</td>' % (int(color.red / 256.00), int(color.green / 256.00), int(color.blue / 256.00))
        color =  w.style.__getattribute__(attribute)[gtk.STATE_PRELIGHT]
        print '        <td bgcolor="#%x%x%x">&nbsp;</td>' % (int(color.red / 256.00), int(color.green / 256.00), int(color.blue / 256.00))
        color =  w.style.__getattribute__(attribute)[gtk.STATE_ACTIVE]
        print '        <td bgcolor="#%x%x%x">&nbsp;</td>' % (int(color.red / 256.00), int(color.green / 256.00), int(color.blue / 256.00))
        color =  w.style.__getattribute__(attribute)[gtk.STATE_SELECTED]
        print '        <td bgcolor="#%x%x%x">&nbsp;</td>' % (int(color.red / 256.00), int(color.green / 256.00), int(color.blue / 256.00))

        print '      </tr>'

    for attribute in colors2:
        print '      <tr>'
        print '        <td><b>%s</b></td>' % attribute
        color = w.style.__getattribute__(attribute)
        print '        <td colspan="5" bgcolor="#%x%x%x">&nbsp;</td>' % (int(color.red / 256.00), int(color.green / 256.00), int(color.blue / 256.00))
        print '      </tr>'

    print '    </table>'


if __name__ == '__main__':
    main()
