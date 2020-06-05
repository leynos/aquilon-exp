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
"""Contains the logic for `aq search issue hostname`."""

from aquilon.aqdb.model import Issue
from aquilon.worker.broker import BrokerCommand
from aquilon.worker.dbwrappers.host import hostname_to_host
from aquilon.worker.formats.list import StringAttributeList


class CommandSearchIssueHostname(BrokerCommand):

    required_parameters = ["hostname"]

    def render(self, session, logger, hostname, fullinfo, style, **_):

        issues = session.query(Issue)

        host = hostname_to_host(session, hostname)
        model_host = host.hardware_entity.model
        os_host = host.operating_system

        # if model OR os are present in a issue, keep it
        issues_model = issues.filter(Issue.models.contains(model_host))
        issues_os = issues.filter(Issue.os.contains(os_host))

        issues_host = issues_model.union(issues_os)

        if fullinfo or style != "raw":
            return issues_host.all()
        return StringAttributeList(issues_host, "tracker")
