# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2020  Contributor
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
"""Contains the logic for `aq search issue --list`."""

from aquilon.worker.broker import BrokerCommand
from aquilon.aqdb.model import (
                                Issue,
                                Model,
                                OperatingSystem,
                                )
from aquilon.worker.dbwrappers.host import hostlist_to_hosts
from aquilon.worker.formats.list import StringAttributeList


class CommandSearchIssueList(BrokerCommand):

    required_parameters = ["list"]

    def render(self, session, logger, list, model, vendor, osname, osversion,
               archetype, state, category, fullinfo, style, **_):

        issues = session.query(Issue)
        # --------------------------------------------------
        # filters
        do_filter_model = (model is not None or
                           vendor is not None)
        do_filter_state = (state is not None)
        do_filter_category = (category is not None)
        do_filter_os = (osname is not None or
                        osversion is not None or
                        archetype is not None)

        if do_filter_state:
            issues = issues.filter(Issue.state == state)

        if do_filter_category:
            issues = issues.filter(Issue.category == category)

        # query model to filter
        if do_filter_model:
            model = Model.get_unique(session,
                                     name=model,
                                     vendor=vendor,
                                     compel=True)
            issues = issues.filter(Issue.models.contains(model))

        if do_filter_os:
            os = OperatingSystem.get_unique(session, name=osname,
                                            version=osversion,
                                            archetype=archetype,
                                            compel=True)
            issues = issues.filter(Issue.os.contains(os))

        # --------------------------------------------------
        # link issues with hosts

        issues_ret = None
        dbhosts = hostlist_to_hosts(session, list)
        for host in dbhosts:
            if host is not None:
                model_host = host.hardware_entity.model
                os_host = host.operating_system

                # if model OR os are present in a issue, keep it
                issues_model = issues.filter(Issue.models.contains(model_host))
                issues_os = issues.filter(Issue.os.contains(os_host))
                issues_temp = issues_model.union(issues_os)

                if issues_ret is None:
                    issues_ret = issues_temp
                else:
                    issues_ret = issues_ret.union(issues_temp)

        # --------------------------------------------------
        # output options

        if fullinfo or style != "raw":
            return issues_ret
        return StringAttributeList(issues_ret, "tracker")
