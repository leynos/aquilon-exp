#!/usr/bin/env python
# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2018-2019  Contributor
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""This sets up and runs the broker unit tests in tests/unit/."""

from __future__ import print_function
from __future__ import absolute_import

import argparse
import os
import re
from shutil import rmtree
from subprocess import call
import sys
import unittest

from unittest import defaultTestLoader

try:
    # noinspection PyUnresolvedReferences
    import ms.version
except ImportError:
    pass
else:
    ms.version.addpkg('mock', '3.0.5')

# noinspection SpellCheckingInspection
BINDIR = os.path.dirname(os.path.realpath(__file__))
default_config_file = os.path.join(BINDIR, 'unittest.conf')
# noinspection SpellCheckingInspection
SRCDIR = os.path.join(BINDIR, '..')
sys.path.append(os.path.join(SRCDIR, "lib"))
sys.path.append(os.path.join(SRCDIR, "bin"))


# The below import fixes 'ImportError: No module named twisted.python'.
# noinspection PyUnresolvedReferences
import aquilon.worker.depends  # NOQA pylint: disable=W0611
# noinspection PyUnresolvedReferences
import depends  # NOQA pylint: disable=W0611

from aquilon.config import Config

epilog = """
    Note that configuration file "{}" will be used by default, and setting the
    AQDCONF environment variable will *not* work.
    """.format(default_config_file)


def parse_args(args=sys.argv):
    parser = argparse.ArgumentParser(
        description='Run the broker unit (not functional or integration!) '
                    'tests.', epilog=epilog)
    parser.add_argument('-g', '--config', dest='config',
                        default=default_config_file,
                        help='supply an alternate config file')
    parser.add_argument('--no-interactive', dest='interactive',
                        action='store_false', default=True,
                        help='automatically send yes to queries')
    return parser.parse_args()


class AquilonTestProgram(unittest.TestCase):
    # def __init__(self, opts):
    #     self.opts = opts

    def run_test(self):
        loader = unittest.TestLoader()
        tests = loader.discover((os.path.realpath(os.path.join(BINDIR, 'unit'))), 'test_*.py')
        testRunner = unittest.runner.TextTestRunner(failfast=True)
        # if self.opts.failfast:
        #     testRunner = unittest.runner.TextTestRunner(failfast=True)
        # else:
        #     testRunner = unittest.runner.TextTestRunner()
        testRunner.run(tests)

def force_yes(msg):
    print(msg, file=sys.stderr)
    print('Please confirm (type "yes" followed by [ENTER]): ',
          file=sys.stderr)
    answer = sys.stdin.readline()
    if answer.strip().lower() != 'yes':
        print('Aborting.', file=sys.stderr)
        sys.exit(1)


def load_config(opts, srcdir):
    if os.environ.get('AQDCONF') and os.path.realpath(opts.config) != \
            os.path.realpath(os.environ['AQDCONF']):
        if opts.interactive:
            force_yes('Will ignore AQDCONF variable value "{}" and use "{}" '
                      'instead.'.format(os.environ['AQDCONF'], opts.config))
    if not os.path.exists(opts.config):
        print('The configuration file "{}" does not exist.  Exiting...'.format(
            opts.config), file=sys.stderr)
        sys.exit(1)
    config = Config(configfile=opts.config)
    if not config.has_section('unittest'):
        config.add_section('unittest')
    if not config.has_option('unittest', 'srcdir'):
        config.set('unittest', 'srcdir', srcdir)
    return config


if __name__ == '__main__':
    '''Working
    loader = unittest.TestLoader()
    tests = loader.discover((os.path.realpath(os.path.join(BINDIR, 'unit'))), 'test_*.py')
    testRunner = unittest.runner.TextTestRunner()
    testRunner.run(tests)
    '''
    opts = parse_args()
    config = load_config(opts, SRCDIR)
    unit_test = AquilonTestProgram()
    unit_test.run_test()
    # runner.runTests()

