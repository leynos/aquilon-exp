# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2008,2009,2010,2011,2012,2013,2014,2015,2017,2018  Contributor
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
""" Suggested versions of external libraries.

    These versions are the defaults for the binaries shipped.

    Anything referencing aquilon.worker.depends should also set up the
    dependencies listed in aquilon.aqdb.depends.

"""

try:
    import ms.version
except ImportError:
    pass
else:
    ms.version.addpkg('setuptools', '46.1.3')
    ms.version.addpkg('protobuf', '3.17.3')
    ms.version.addpkg('zope.interface', '4.6.0-py37')
    ms.version.addpkg('twisted', '21.2.0')
    ms.version.addpkg('incremental', '16.10.1')
    ms.version.addpkg('Automat', '20.2.0')
    ms.version.addpkg('hyperlink', '20.0.1')
    ms.version.addpkg('idna', '3.2')
    ms.version.addpkg('importlib-metadata', '4.9.0')
    ms.version.addpkg('zipp', '3.0.0')
    ms.version.addpkg('typing-extensions', '3.7.4.3')
    ms.version.addpkg('pbr', '5.4.4')
    ms.version.addpkg('prettytable', '1.0.1')
    ms.version.addpkg('constantly', '15.1.0')
    ms.version.addpkg('coverage', '5.3.1-py37')
    ms.version.addpkg('ipaddress', '1.0.23')
    ms.version.addpkg('mako', '1.0.7')
    ms.version.addpkg('pure-cdb', '3.1.0')
    ms.version.addpkg('six', '1.16.0')
    ms.version.addpkg('jsonschema', '3.2.0')
    ms.version.addpkg("ms.directory", "4.0.0")
    ms.version.addpkg('attrs', '20.3.0')
    ms.version.addpkg('pyrsistent', '0.15.7-py37')
    ms.version.addpkg('decorator', '5.1.1')
    ms.version.addpkg('requests-gssapi', '1.2.3')
    ms.version.addpkg('gssapi', '1.8.2')
    ms.version.addpkg('pyspnego', '0.8.0')
    ms.version.addpkg("cryptography", "39.0.0")
    ms.version.addpkg('chardet', '5.1.0')
    ms.version.addpkg('certifi', '2022.9.24')
    ms.version.addpkg("httplib2", "0.22.0")
    ms.version.addpkg("idna", "3.4")
    ms.version.addpkg('urllib3', '2.0.3')
    ms.version.addpkg("requests", "2.31.0")
    ms.version.addpkg("requests-kerberos", "0.14.0")
    ms.version.addpkg("kerberos", "1.3.1-1.16-ms2")
    ms.version.addpkg("krb5", "0.4.0")
    ms.version.addpkg("cffi", "1.15.1")
    ms.version.addpkg("orjson", "3.6.3-py37")

