#!/bin/bash

# Configure the path to your Python interpreter installations.
INTERPRETERS="/d/bin/Python26 /d/bin/Python27"

# Build documentation
SPHINXOPTS="-W" make -e -C doc/reference/ html &&

# Build eggs
for INTERPRETER in ${INTERPRETERS}; do
    ${INTERPRETER}/python setup.py bdist_egg
done
