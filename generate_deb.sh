#!/bin/bash

# Requirements: http://pypi.python.org/pypi/stdeb/0.3.2
python setup.py --command-packages=stdeb.command bdist_deb
