# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2008,2009,2010,2011,2012,2013,2014,2017  Contributor
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
""" Suggested versions of external libraries, and the defaults for the
    binaries shipped.
"""

try:
    import ms.version
except ImportError:
    pass
else:
    import sys

    ms.version.addpkg('lxml', '3.2.5')
    ms.version.addpkg('six', '1.15.0')
    ms.version.addpkg("ms.directory", "3.2.0")
    ms.version.addpkg("decorator", "4.4.2")
    ms.version.addpkg("pykerberos", "1.2.1-1.16")
    ms.version.addpkg("winkerberos", "0.7.0")
    ms.version.addpkg("pyasn1", "0.4.8")
    ms.version.addpkg("ldap3", "2.7")
    ms.version.addpkg("setuptools", "41.0.1")
    ms.version.addpkg("kerberos", "1.1.5-ms3")

    if sys.platform == "sunos5":
        # ctypes is missing from the default Python build on Solaris, due to
        # http://bugs.python.org/issue2552. It is available as a separate package
        # though.
        ms.version.addpkg("ctypes", "1.0.2")

        # ms.version.addpkg() appends to sys.path, but we need the entry at the
        # front
        sys.path.insert(0, sys.path.pop())
