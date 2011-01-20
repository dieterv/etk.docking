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


import os
import re
import fnmatch

from ez_setup import use_setuptools; use_setuptools()
from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

def version():
    file = os.path.join(os.path.dirname(__file__), 'lib', 'etk', 'docking', '__init__.py')
    return re.compile(r".*__version__ = '(.*?)'", re.S).match(read(file)).group(1)

def _get_data_files(dest, src, filter):
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), src))
    files = []

    if os.path.isdir(path):
        for item in fnmatch.filter(os.listdir(path), filter):
            if os.path.isfile(os.path.join(path, item)):
                files.append(('%s/%s' % (src, item)))
    else:
        print 'get_data_files: "%s" does not exist, ignoring' % src

    return files

def get_data_files(*args):
    data_files = []

    for (dest, src, filter) in args:
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), src))

        if os.path.isdir(path):
            data_files.append(('%s' % dest, _get_data_files('%s' % dest, '%s' % src, filter)))

            for item in os.listdir(path):
                if os.path.isdir(os.path.join(path, item)):
                    data_files.append(('%s/%s' % (dest, item), _get_data_files('%s/%s' % (dest, item), '%s/%s' % (src, item), filter)))
        else:
            print 'get_data_files: "%s" does not exist, ignoring' % src

    return data_files


setup(namespace_packages = ['etk'],
      name = 'etk.docking',
      version = version(),
      description = 'PyGTK Docking Widgets',
      long_description = read('README'),
      author = 'etk.docking Contributors',
      author_email = 'etk-list@googlegroups.com',
      url = 'http://github.com/dieterv/etk.docking/',
      download_url = 'http://github.com/dieterv/etk.docking/downloads/',
      license = 'GNU Lesser General Public License',
      classifiers = ['Development Status :: 3 - Alpha',
                    'Environment :: X11 Applications :: GTK',
                    'Intended Audience :: Developers',
                    'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
                    'Natural Language :: English',
                    'Operating System :: MacOS :: MacOS X',
                    'Operating System :: Microsoft :: Windows',
                    'Operating System :: POSIX',
                    'Programming Language :: Python',
                    'Topic :: Software Development :: Libraries :: Python Modules'],

      install_requires = ['setuptools',
                          'simplegeneric >= 0.6'],
      zip_safe = False,
      include_package_data = True,

      packages = find_packages('lib'),
      package_dir = {'': 'lib'},
      data_files = get_data_files(('doc/examples', 'doc/examples', '*.py'),
                                  ('doc/reference', 'doc/reference/build/html', '*')),

      tests_require = ['nose'],
      test_suite = 'nose.collector')
