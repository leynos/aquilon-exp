# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2008-2015,2018,2021  Contributor
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
"""Contains the logic for `aq search filesystem`."""

from aquilon.aqdb.model import Filesystem
from aquilon.worker.broker import BrokerCommand  # pylint: disable=W0611
from aquilon.worker.commands.search_resource import CommandSearchResource


class CommandSearchFilesystem(CommandSearchResource):

    resource_class = Filesystem
    resource_name = "filesystem"

    def render(self, session, logger, hostname, cluster, metacluster,
               personality=None, archetype=None, grn=None, eon_id=None,
               host_environment=None, transport_type=None, **kwargs):

        query_filters = None

        if transport_type is not None:
            if transport_type.lower() == "none":
                query_filters = {'transport_type': None}
            else:
                query_filters = {'transport_type': transport_type}

        return CommandSearchResource.render(self,
                                            session=session,
                                            logger=logger,
                                            hostname=hostname,
                                            cluster=cluster,
                                            metacluster=metacluster,
                                            personality=personality,
                                            archetype=archetype,
                                            grn=grn,
                                            eon_id=eon_id,
                                            host_environment=host_environment,
                                            query_filters=query_filters,
                                            **kwargs)
