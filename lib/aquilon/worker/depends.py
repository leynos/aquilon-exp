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
    ms.version.addpkg('protobuf', '4.23.1')
    ms.version.addpkg('twisted', '21.2.0')
    ms.version.addpkg('incremental', '16.10.1')
    ms.version.addpkg('Automat', '20.2.0')
    ms.version.addpkg('PyHamcrest', '2.0.2')
    ms.version.addpkg('hyperlink', '20.0.1')
    ms.version.addpkg('importlib-metadata', '6.6.0')
    ms.version.addpkg('zipp', '3.15.0')
    ms.version.addpkg('typing-extensions', '4.7.0')
    ms.version.addpkg('pbr', '5.4.4')
    ms.version.addpkg('prettytable', '1.0.1')
    ms.version.addpkg('wcwidth', '0.1.9')
    ms.version.addpkg('constantly', '15.1.0')
    ms.version.addpkg('ipaddress', '1.0.23')
    ms.version.addpkg('mako', '1.0.7')
    ms.version.addpkg('markupsafe', '2.1.1')
    ms.version.addpkg('pure-cdb', '3.1.0')
    ms.version.addpkg('six', '1.16.0')
    ms.version.addpkg('jsonschema', '4.19.0')
    ms.version.addpkg("ms.directory", "4.0.0")
    ms.version.addpkg("ldap3", "2.9.1")
    ms.version.addpkg("pyasn1", "0.5.0")
    ms.version.addpkg('attrs', '23.1.0')
    ms.version.addpkg('decorator', '5.1.1')
    ms.version.addpkg('requests-gssapi', '1.2.3')
    ms.version.addpkg('gssapi', '1.8.2')
    ms.version.addpkg('pyspnego', '0.9.0-ms1')
    ms.version.addpkg('chardet', '5.1.0')
    ms.version.addpkg('certifi', '2022.9.24')
    ms.version.addpkg("httplib2", "0.22.0")
    ms.version.addpkg("idna", "3.4")
    ms.version.addpkg('urllib3', '2.0.3')
    ms.version.addpkg("requests", "2.31.0")
    ms.version.addpkg("requests-kerberos", "0.14.0")
    ms.version.addpkg('requests-cache', '1.1.0')
    ms.version.addpkg('url-normalize', '1.4.3')  # Required by requests-cache
    ms.version.addpkg('cattrs', '22.2.0')  # Required by requests-cache
    ms.version.addpkg('exceptiongroup', '1.1.2')  # Required by cattrs
    ms.version.addpkg('platformdirs', '3.8.0')  # Required by requests-cache/backend/sqlite
    ms.version.addpkg("kerberos", "1.3.1-1.16")
    ms.version.addpkg("cffi", "1.15.1")
    ms.version.addpkg("pycparser", "2.21")

    ms.version.addpkg('zope.interface', '6.0-ms1')
    ms.version.addpkg('coverage', '7.2.7-ms1')
    ms.version.addpkg('pyrsistent', '0.19.3')
    ms.version.addpkg("orjson", "3.8.8")
    ms.version.addpkg("krb5", "0.5.0") # Required by HTTPKerberosAuth used in infoblox integration
    ms.version.addpkg("cryptography", "41.0.3")