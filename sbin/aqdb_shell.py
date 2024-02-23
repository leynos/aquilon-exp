#!/usr/bin/env python
# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2008,2009,2010,2011,2012,2013,2014,2015,2016,2017  Contributor
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

import argparse
import os
import sys
import logging

try:
    import ms.version
except ImportError:
    pass
else:
    ms.version.addpkg("backports.shutil-get-terminal-size", "1.0.0")
    ms.version.addpkg("decorator", "4.4.2")
    ms.version.addpkg("enum34", "1.1.6")
    ms.version.addpkg("ipython", "5.8.0")
    ms.version.addpkg("ipython_genutils", "0.2.0")
    ms.version.addpkg("pathlib2", "2.3.2")
    ms.version.addpkg("pexpect", "4.8.0")
    ms.version.addpkg("pickleshare", "0.7.4")
    ms.version.addpkg("prompt_toolkit", "1.0.15")
    ms.version.addpkg("ptyprocess", "0.6.0")
    ms.version.addpkg("pygments", "2.5.2")
    ms.version.addpkg("scandir", "1.9.0")
    ms.version.addpkg("setuptools", "41.0.1")
    ms.version.addpkg("simplegeneric", "0.8.1")
    ms.version.addpkg("six", "1.14.0")
    ms.version.addpkg("traitlets", "4.3.2")
    ms.version.addpkg("wcwidth", "0.1.9")

# -- begin path_setup --
BINDIR = os.path.dirname(os.path.realpath(sys.argv[0]))
LIBDIR = os.path.join(BINDIR, "..", "lib")

if LIBDIR not in sys.path:
    sys.path.append(LIBDIR)
# -- end path_setup --

import aquilon.aqdb.depends  # pylint: disable=W0611

# pylint: disable=W0611
from ipaddress import (IPv4Address, IPv4Network, IPv6Address, IPv6Network,
                       ip_address, ip_network)
from IPython.config.loader import Config as IPyConfig
from IPython import embed

from aquilon.config import Config  # pylint: disable=W0611
from aquilon.aqdb.db_factory import DbFactory, db_prompt

# Make all classes from the model available inside the shell
from aquilon.aqdb.model import *  # pylint: disable=W0401,W0614

_banner = '<<<Welcome to the Aquilon shell (courtesy of IPython). Ctrl-D to quit>>>\n'


def main():
    parser = argparse.ArgumentParser(
        description='An ipython shell, useful for testing and exploring aqdb')

    parser.add_argument('-v', action='store_true', dest='verbose',
                        help='show queries')
    opts = parser.parse_args()

    db = DbFactory(verbose=opts.verbose)
    Base.metadata.bind = db.engine
    session = s = db.Session()

    rootlogger = logging.getLogger('aquilon.aqdb')
    if opts.verbose:
        rootlogger.setLevel(logging.INFO)
    elif rootlogger.level == logging.NOTSET:
        rootlogger.setLevel(logging.WARN)

    if not rootlogger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s %(name)s %(message)s'))
        rootlogger.addHandler(handler)

    prompt = db_prompt(session) + '> '

    ipycfg = IPyConfig()
    ipycfg.PromptManager.in_template = prompt
    ipycfg.PlaintextFormatter.pprint = True
    ipycfg.InteractiveShell.separate_in = ''
    ipycfg.InteractiveShell.separate_out = ''
    ipycfg.InteractiveShell.separate_out2 = ''
    ipycfg.InteractiveShell.colors = 'Linux'
    embed(config=ipycfg, banner1=_banner)


if __name__ == '__main__':
    main()
