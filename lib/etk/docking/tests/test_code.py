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


import os
import sys
import unittest
import tabnanny


class Capture(object):
    def __init__(self):
        self._output = []
        self.old_stdout = None
        self.old_stderr = None

    def start(self):
        self.old_stdout = sys.stdout
        sys.stdout = self
        self.old_stderr = sys.stderr
        sys.stderr = self

    def stop(self):
        if self.old_stdout:
            sys.stdout = self.old_stdout

        if self.old_stderr:
            sys.stderr = self.old_stderr

    def output(self):
        count = 0

        while count < len(self._output):
            yield (self._output[count], self._output[count + 1], self._output[count + 2])
            count += 3

    def write(self, message):
        message = message.strip()
        if message != '':
            self._output.append(message)


class TestCode(unittest.TestCase):
    ############################################################################
    # Test indentation (tab/spaces)
    ############################################################################
    def test_indentation(self):
        capture = Capture()
        capture.start()
        tabnanny.verbose = 0
        tabnanny.check(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')))
        capture.stop()

        for line in capture.output():
            raise IndentationError('Ambiguous indentation detected in %s on line %s' % (line[0], line[1]))
