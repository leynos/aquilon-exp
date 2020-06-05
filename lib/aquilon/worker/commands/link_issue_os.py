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
"""Contains the logic for `aq link issue os`."""

from aquilon.worker.broker import BrokerCommand
from aquilon.aqdb.model import (
                                Issue,
                                OperatingSystem,
                               )
from aquilon.exceptions_ import AquilonError


class CommandLinkIssueOs(BrokerCommand):

    required_parameters = ["tracker", "osname", "osversion", "archetype"]

    def render(self, session, logger, tracker, osname, osversion,
               archetype, **_):

        os = OperatingSystem.get_unique(session, name=osname,
                                        version=osversion,
                                        archetype=archetype, compel=True)
        issue = Issue.get_unique(session, tracker=tracker, compel=True)

        if os in issue.os:
            raise AquilonError("Issue with same tracker and os "
                               "already in database")
        else:
            issue.os.append(os)
            session.add(issue)
            session.flush()

            return
