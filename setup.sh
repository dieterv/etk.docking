#!/bin/bash

# Configure the path to your Python interpreter installations.
INTERPRETERS="/d/bin/Python27 /d/bin/Python26"

# Build documentation
/d/bin/Python27/python setup.py build_sphinx

# Build eggs
for INTERPRETER in ${INTERPRETERS}; do
    ${INTERPRETER}/python setup.py bdist_egg
done
