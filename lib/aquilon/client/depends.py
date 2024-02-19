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
import sys
import ms.version

ms.version.addpkg('six', '1.16.0')
ms.version.addpkg("requests-kerberos", "0.12.0")
ms.version.addpkg("ms.directory", "4.0.0")
ms.version.addpkg("pykerberos", "1.2.4")
ms.version.addpkg("urllib3", "2.0.2")
ms.version.addpkg("chardet", "3.0.4")
ms.version.addpkg("certifi", "2020.6.20")
ms.version.addpkg("cffi", "1.15.1")
ms.version.addpkg("idna", "2.10")
ms.version.addpkg("requests", "2.31.0")
ms.version.addpkg("ms.netkrb", "2.1a")
ms.version.addpkg("kerberos", "1.3.1-1.16")
ms.version.addpkg("setuptools", "45.0.0")


if sys.platform == "sunos5":
    ms.version.addpkg('lxml', '4.6.3-S')
    ms.version.addpkg("cryptography", "41.0.3")
    ms.version.addpkg("krb5", "0.4.1-1.16")

    # ms.version.addpkg() appends to sys.path, but we need the entry at the
    # front
    sys.path.insert(0, sys.path.pop())
else:
    if sys.version_info >= (3, 9):
        ms.version.addpkg("lxml", "4.9.2-ms1")
        ms.version.addpkg("cryptography", "41.0.3")
        ms.version.addpkg("krb5", "0.5.0")
    else:
        ms.version.addpkg("lxml", "4.6.3-2.9.10")
        ms.version.addpkg("cryptography", "39.0.0")
        ms.version.addpkg("krb5", "0.4.0")
    # ms.version.addpkg() appends to sys.path, but we need the entry at the
    # front
    sys.path.insert(0, sys.path.pop())
