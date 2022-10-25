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
import ldap

def check_ldap_filter(uid, config):
    try:
        # Get the LDAP Server configs from config file
        os.environ['LDAPTLS_CACERTDIR'] = config.get("ldap", "LDAPTLS_CACERTDIR")
        ldap_server = config.get("ldap", "server")
        baseDN = config.get("ldap", "baseDN")

        # Setup connection to LDAP
        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_ALLOW)
        ldap_conn = ldap.initialize(ldap_server)
        ldap_conn.set_option(ldap.OPT_REFERRALS, 0)
        ldap_conn.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
        ldap_conn.set_option(ldap.OPT_X_TLS, ldap.OPT_X_TLS_DEMAND)
        ldap_conn.set_option(ldap.OPT_X_TLS_DEMAND, True)
        ldap_conn.set_option(ldap.OPT_X_TLS_NEWCTX, 0)
        sasl = ldap.sasl.gssapi()
        ldap_conn.sasl_interactive_bind_s('', sasl)

        # Define the search attributes on LDAP
        searchFilter = "uid=%s" % uid

        attrlist = ['cn']
        searchScope = ldap.SCOPE_SUBTREE

        result_id = ldap_conn.search(baseDN, searchScope, searchFilter, attrlist)
        result_type, result_data = ldap_conn.result(result_id)

        if result_data:
            return result_data
        return False
    except Exception as e:
        '''If there are issues due to LDAP End Points not returning data, 
        the return value will be set to False which will route the requests 
        to RO VIP and not BATCH VIP.'''
        return False
