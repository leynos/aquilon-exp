# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2022  Contributor
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

# Use ldapsearch capabilities to retrieve data for further operations

from aquilon.client import depends

import os

def check_ldap_filter(uid, config):
    try:
        # The ms.directory module is included in this try catch block
        # since this module is not available in upstream repo. The aq
        # client script will continue without using this method.

        # LDAPS is not available for the Solaris hosts.

        # LDAP module compatible on Solaris needs managing a password
        # which is also pretty undesirable.

        # Once python-ldap modules with Solaris compatibility are
        # available, use ldaps capability.

        #Get the LDAP Server configs from config file
        from ms.directory import LDAPConnection
        ldap_server = config.get("ldap", "server")

        # Setup connection to LDAP
        conn = LDAPConnection(host=ldap_server, kerberos=True)

        # Define the search attributes on LDAP
        result_data = conn.getProdID(uid)

        if result_data:
            return result_data
        return False
    except Exception as e:
        '''If there are issues due to LDAP End Points not returning data, 
        the return value will be set to False which will route the requests 
        to RO VIP and not BATCH VIP.'''
        return False
