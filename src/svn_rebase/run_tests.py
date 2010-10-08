#!/usr/bin/env python

import os
import sys
import unittest

import tests

suite = unittest.TestLoader().loadTestsFromModule(tests)
unittest.TextTestRunner().run(suite)
