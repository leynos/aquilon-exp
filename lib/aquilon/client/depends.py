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

    # ms.version.addpkg('lxml', '4.5.1-2.9.3-py37')
    ms.version.addpkg('lxml', '4.5.1-2.9.3')
    ms.version.addpkg('six', '1.15.0')
    ms.version.addpkg("requests-kerberos", "0.12.0")
    ms.version.addpkg("pykerberos", "1.2.1-1.16")
    ms.version.addpkg("urllib3", "1.25.9")
    ms.version.addpkg("chardet", "3.0.4")
    ms.version.addpkg("certifi", "2020.6.20")
    ms.version.addpkg("cffi", "1.13.2-py37")
    ms.version.addpkg("idna", "2.10")
    ms.version.addpkg("cryptography", "3.1")
    ms.version.addpkg("requests", "2.23.0")
    ms.version.addpkg("ms.netkrb", "2.1a")
    ms.version.addpkg("kerberos", "1.3.1-1.16")
    ms.version.addpkg("setuptools", "45.0.0")


if sys.platform == "sunos5":
        # ctypes is missing from the default Python build on Solaris, due to
        # http://bugs.python.org/issue2552. It is available as a separate package
        # though.
        ms.version.addpkg("ctypes", "1.0.2")

        # ms.version.addpkg() appends to sys.path, but we need the entry at the
        # front
        sys.path.insert(0, sys.path.pop())
