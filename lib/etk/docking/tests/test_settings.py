# -*- coding: utf-8 -*-
# vim:sw=4:et:ai

import unittest

from etk.docking.docksettings import DockSettingsDict

class TestDockLayout(unittest.TestCase):

    def test_settings(self):
        settings = DockSettingsDict()
        s = settings['gid']
        assert s.auto_remove is True
        assert s.can_float is True
        assert s.inherit_settings is True

        # On subsequent fetches, get the same settings.
        assert s is settings['gid']

        s2 = settings['other-gid']
        assert s2 is not settings

