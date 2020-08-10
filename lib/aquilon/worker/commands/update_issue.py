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
"""Contains the logic for `aq update issue`."""

from aquilon.aqdb.model import (
    Issue,
    Model,
    OperatingSystem,
)
from aquilon.worker.broker import BrokerCommand

class CommandUpdateIssue(BrokerCommand):

    required_parameters = ["tracker"]

    def render(self, session, logger, tracker, description, state, category,
               osversion, osname, archetype, model, vendor, new_tracker, **_):

        update_tracker = (new_tracker is not None)
        update_state = (state is not None)
        update_category = (category is not None)
        update_description = (description is not None)

        update_model = (model is not None or
                        vendor is not None)
        update_os = (osname is not None or
                     osversion is not None or
                     archetype is not None)

        issue = Issue.get_unique(session, tracker, compel=True)

        if update_tracker:
            # not possible to add a duplicate tracker
            Issue.get_unique(session, tracker=new_tracker, preclude=True)
            issue.tracker = new_tracker
        if update_state:
            issue.state = state
        if update_category:
            issue.category = category
        if update_description:
            issue.description = description
        if update_model:
            model = Model.get_unique(session, name=model,
                                     vendor=vendor, compel=True)
            issue.models.append(model)
        if update_os:
            os = OperatingSystem.get_unique(session, name=osname,
                                            version=osversion,
                                            archetype=archetype,
                                            compel=True)
            issue.os.append(os)

        session.add(issue)
        session.flush()

        return
