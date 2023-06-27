# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2008,2009,2010,2011,2013,2016  Contributor
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
"""Contains a wrapper for `aq add service --instance`."""

from aquilon.aqdb.model import Service
from aquilon.aqdb.model import ServiceInstance
from aquilon.exceptions_ import ArgumentError
from aquilon.worker.broker import BrokerCommand


class CommandAddServiceInstance(BrokerCommand):
    requires_plenaries = True

    required_parameters = ["service", "instance"]

    def render(self, session, plenaries, service, instance, comments, need_client_list=None, allow_alias_bindings=None,
               **_):

        if need_client_list is not None:
            raise ArgumentError("The --need_client_list option cannot be used with the --instance option")

        if allow_alias_bindings is not None:
            raise ArgumentError("The --allow_alias_bindings option cannot be used with the --instance option")

        dbservice = Service.get_unique(session, service, compel=True)
        ServiceInstance.get_unique(session, service=dbservice, name=instance,
                                   preclude=True)

        dbsi = ServiceInstance(service=dbservice, name=instance,
                               comments=comments)
        session.add(dbsi)

        plenaries.add(dbsi)

        session.flush()
        plenaries.write()
        return
