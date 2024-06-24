#!/ms/dist/python/PROJ/core/3.10.11-0/bin/python

# Test runner with support for coverage and xml test outout

# Avoid polluting general dependencies with test specific libs,
# only pull it here
import ms.version

ms.version.addpkg("unittest-xml-reporting", "2.5.1")
ms.version.addpkg("setuptools", "46.1.3")
ms.version.addpkg("six", "1.16.0")

import os
import sys
import unittest

import xmlrunner

# Output file path is relative to the current directory. As we're expected to be run by
# "train test", that would be the src/ folder (and not the tests/ subdirectory!)
DEFAULT_OUTPUT = "../install/common/test-results/unit"

BASEDIR = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASEDIR)


from commands import test_compile, test_compile_hostname, test_del_host, test_search_audit
from dbwrappers import test_change_management, test_location
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
out_file = os.path.join(BASEDIR, "../install/common/test-results/UNIT/xml/test.xml")
with open(out_file, "wb") as output:
    results = xmlrunner.XMLTestRunner(output=output).run(suite)

if results.failures or results.errors:
    sys.exit(-1)
