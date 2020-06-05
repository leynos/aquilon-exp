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
"""Issue formatter."""

from aquilon.aqdb.model import Issue
from aquilon.worker.formats.formatters import ObjectFormatter


class IssueFormatter(ObjectFormatter):

    def format_raw(self, issue, indent="", embedded=True, indirect_attrs=True):
        details = [issue.tracker]
        details.append(indent + "  Category: %s" % issue.category)
        details.append(indent + "  State: %s" % issue.state)
        details.append(indent + "  Description: %s" % issue.description)

        if len(issue.models) > 0:
            details.append(str(self.redirect_raw(issue.models, indent + "  ",
                           indirect_attrs=False)))
        if len(issue.os) > 0:
            details.append(str(self.redirect_raw(issue.os, indent + "  ",
                           indirect_attrs=False)))
        return "\n".join(details)

    def fill_proto(self, issue, skeleton, embedded=True, indirect_attrs=True):
        skeleton.tracker = issue.tracker
        desc = skeleton.DESCRIPTOR
        skeleton.state = desc.enum_values_by_name[issue.state.upper()].number
        skeleton.description = issue.description
        skeleton.category = issue.category
        self.redirect_proto(issue.models, skeleton.models)
        self.redirect_proto(issue.os, skeleton.os)


ObjectFormatter.handlers[Issue] = IssueFormatter()
