#!/bin/bash

# Configure the path to your Python interpreter installations.
INTERPRETERS="/d/bin/Python27 /d/bin/Python26"

# Build documentation
/d/bin/Python27/python setup.py build_sphinx

# Build source distribution
# There's a bug in gztar on windows: a "dist" dir is created in the .gz
# part that contains the .tar part. bztar does not have this bug. *sigh*
/d/bin/Python27/python setup.py sdist --formats=bztar

# Build eggs
for INTERPRETER in ${INTERPRETERS}; do
    ${INTERPRETER}/python setup.py bdist_egg
done
