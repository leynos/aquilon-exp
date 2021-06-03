# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2021  Contributor
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
"""Contains the logic for `aq search issue osversion`."""

from aquilon.aqdb.model import Issue
from aquilon.worker.broker import BrokerCommand
from aquilon.worker.formats.list import StringAttributeList


class CommandSearchIssueOSVersion(BrokerCommand):

    required_parameters = ["osversion"]

    def render(self, session, logger, osversion, fullinfo,
               style, state_all=False, state=None, **_):

        issues = session.query(Issue)
        issues_os = issues.filter(Issue.os.any(version=osversion))

        if state:
            issues_os = issues_os.filter_by(state=state)
        elif not state_all:
            # If state filter is not provided then display only open issues.
            issues_os = issues_os.filter_by(state="open")

        if fullinfo:
            return issues_os.all()
        else:
            return StringAttributeList(issues_os, "tracker")
