#!/ms/dist/python/PROJ/core/2.7.18-64/bin/python

# Test runner with support for coverage and xml test outout

# Avoid polluting general dependencies with test specific libs,
# only pull it here
import ms.version
ms.version.addpkg("unittest-xml-reporting", "2.5.1")
ms.version.addpkg("setuptools", "41.0.1")
ms.version.addpkg("six", "1.14.0")

import os
import sys
import unittest
import xmlrunner

# Output file path is relative to the current directory. As we're expected to be run by
# "train test", that would be the src/ folder (and not the tests/ subdirectory!)
DEFAULT_OUTPUT = "../install/common/test-results/unit"

BASEDIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(BASEDIR)

import dependency

from commands import test_compile, test_search_audit, test_compile_hostname, test_del_host
from dbwrappers import test_location, test_change_management
from formats import test_location
from templates import test_domain

modules_to_test = [
    test_compile,
    test_search_audit,
    test_compile_hostname,
    test_del_host,
    test_location,
    test_change_management,
    test_location,
    test_domain
]

loader = unittest.TestLoader()
suite = unittest.TestSuite()

for module in modules_to_test:
    suite.addTests(loader.loadTestsFromModule(module))
out_file = os.path.join(BASEDIR,
                            '../install/common/test-results/'
                            'unittest/tests.xml')
with open(out_file, 'wb') as output:
    results = xmlrunner.XMLTestRunner(output=output).run(suite)

if results.failures or results.errors:
    exit(-1)