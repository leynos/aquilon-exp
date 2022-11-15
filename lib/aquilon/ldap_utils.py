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
# Uses ldapsearch capabilities and returns the data.

import aquilon.worker.depends

import functools
import logging

def disable_logging(func):
    @functools.wraps(func)
    def wrapper(*args,**kwargs):
        logging.disable(logging.DEBUG)
        result = func(*args,**kwargs)
        logging.disable(logging.NOTSET)
        return result
    return wrapper

@disable_logging
def check_ldapgroup(server, group):
    # The ms.directory module is included in this try catch block
    # since this module is not available in upstream repo. The server
    # start-up will continue without using this method.
    try:
        from ms.directory import LDAPConnection
        conn = LDAPConnection(host=server, kerberos=True)
        group_members = conn.getGroup(group).members
        skip_members = []
        for i in group_members:
            skip_members.append(i.get_userid())
        return ','.join(skip_members)
    except Exception as e:
        # If there are issues due to LDAP End Points not returning
        # data,the return value will be set to None which will not
        # skip the change management calls
        return None