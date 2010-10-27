#!/usr/bin/env python

import os
import sys
import unittest

import svn_rebase.tests

suite = unittest.TestLoader().loadTestsFromModule(svn_rebase.tests)
unittest.TextTestRunner().run(suite)
