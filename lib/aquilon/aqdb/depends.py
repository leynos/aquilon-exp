# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2008,2009,2010,2011,2012,2013,2014,2015,2017  Contributor
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
""" Pull dependencies onto sys.path via ms.version """

try:
    import ms.version
except ImportError:
    pass
else:
    ms.version.addpkg('sqlalchemy', '1.3.23')
    ms.version.addpkg('cx_Oracle', '7.2.3-12.2.0.1.0-py37')
    ms.version.addpkg('psycopg2', '2.8.5-11.4.0-py37')
    ms.version.addpkg('ms.modulecmd', '1.1.1')
    ms.version.addpkg('ipaddress', '1.0.23')
    ms.version.addpkg('dateutil', '2.8.1')
    ms.version.addpkg('pure-cdb', '3.1.0')
    ms.version.addpkg('six', '1.15.0')
    ms.version.addpkg('jsonschema', '3.2.0')
    ms.version.addpkg('importlib-metadata', '4.9.0')
    ms.version.addpkg('zipp', '3.0.0')
    ms.version.addpkg('typing-extensions', '3.7.4.3')
    ms.version.addpkg('pbr', '5.4.4')
    ms.version.addpkg('prettytable', '1.0.1')
    ms.version.addpkg('attrs', '20.3.0')
    ms.version.addpkg('pyrsistent', '0.15.7-py37')
