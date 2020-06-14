# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest

from rdhlang5.executor import test as executor_tests
from rdhlang5.parser import test as parser_tests
from rdhlang5.type_system import test as type_system_tests

from rdhlang5.executor.test import *
from rdhlang5.parser.test import *
from rdhlang5.type_system.test import *

from rdhlang5.utils import set_bind_runtime_contexts, set_debug

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    set_debug(True)
    set_bind_runtime_contexts(True) # Some tests rely on this being True
    unittest.main()
