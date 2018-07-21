#!/usr/bin/env python
# Copyright (C) 2010 etk.docking Contributors
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


from __future__ import print_function

from os import path

from setuptools import setup, find_packages
from codecs import open

__version__ = '0.3'

here = path.abspath(path.dirname(__file__))

# Get the long description from the README.md file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# get the dependencies and installs
with open(path.join(here, 'requirements.txt'), encoding='utf-8') as f:
    all_reqs = f.read().split('\n')

install_requires = [x.strip() for x in all_reqs if 'git+' not in x]
dependency_links = [x.strip().replace('git+', '') for x in all_reqs if x.startswith('git+')]

setup(
    name='etk.docking',
    version=__version__,
    description='PyGTK Docking Widgets',
    long_description=long_description,
    author='etk.docking Contributors',
    author_email='etk-list@googlegroups.com',
    url='http://github.com/dieterv/etk.docking/',
    download_url='http://github.com/dieterv/etk.docking/downloads/',
    license='GNU Lesser General Public License',
    classifiers=['Development Status :: 4 - Beta',
                 'Environment :: X11 Applications :: GTK',
                 'Intended Audience :: Developers',
                 'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
                 'Natural Language :: English',
                 'Operating System :: MacOS :: MacOS X',
                 'Operating System :: Microsoft :: Windows',
                 'Operating System :: POSIX',
                 'Programming Language :: Python',
                 'Topic :: Software Development :: Libraries :: Python Modules'],
    include_package_data=True,
    packages=find_packages(exclude=['docs', 'tests*']),
    tests_require=['nose'],
    install_requires=install_requires,
    dependency_links=dependency_links,
    test_suite='nose.collector')
