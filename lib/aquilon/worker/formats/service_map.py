# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2008,2009,2010,2011,2012,2013,2014,2015,2016  Contributor
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
"""ServiceMap formatter."""

from aquilon.aqdb.model import ServiceMap
from aquilon.worker.formats.formatters import ObjectFormatter


class ServiceMapFormatter(ObjectFormatter):
    def format_raw(self, sm, indent="", embedded=True, indirect_attrs=True):
        details = []
        if sm.personality:
            details.append(
                f"{sm.personality.archetype:c}: {sm.personality.archetype.name} {sm.personality:c}: {sm.personality.name}"
            )
        if sm.host_environment:
            details.append(f"{sm.host_environment:c}: {sm.host_environment.name}")

        details.append(
            f"{sm.service_instance.service:c}: {sm.service_instance.service.name} Instance: {sm.service_instance.name}"
        )
        details.append(f"Map: {sm.scope}")

        return indent + " ".join(details)

    def fill_proto(self, service_map, skeleton, embedded=True,
                   indirect_attrs=True):
        if service_map.location:
            self.redirect_proto(service_map.location, skeleton.location,
                                indirect_attrs=False)
        else:
            self.redirect_proto(service_map.network, skeleton.network,
                                indirect_attrs=False)

        self.redirect_proto(service_map.service_instance, skeleton.service,
                            indirect_attrs=False)

        if service_map.personality:
            self.redirect_proto(service_map.personality, skeleton.personality,
                                indirect_attrs=False)
        elif service_map.host_environment:
            skeleton.host_environment = service_map.host_environment.name

    def format_json(self, sm, embedded=True, indirect_attrs=True):
        details = {
            "environment": sm.host_environment.name if sm.host_environment else None,
            "service_instance": sm.service_instance.name if sm.service_instance else None,
            "service": sm.service_instance.service.name
            if sm.service_instance and sm.service_instance.service
            else None,
            "location": self.redirect_json(sm.location, indirect_attrs=False) if sm.location else {},
            "network": self.redirect_json(sm.network, indirect_attrs=False) if sm.network else {},
            "personality": self.redirect_json(sm.personality, indirect_attrs=False) if sm.personality else {},
        }
        return details

ObjectFormatter.handlers[ServiceMap] = ServiceMapFormatter()
