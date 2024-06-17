#!/usr/bin/env python
# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2008-2014,2016-2019  Contributor
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
"""Location formatter."""

from aquilon.aqdb.model import Building, Location, Rack, Room
from aquilon.worker.formats.formatters import ObjectFormatter


class LocationFormatter(ObjectFormatter):
    def format_raw(self, location, indent="", embedded=True,
                   indirect_attrs=True):
        details = [indent + f"{location:c}: {location.name}"]
        if location.fullname:
            details.append(indent + f"  Fullname: {location.fullname}")
        if hasattr(location, 'timezone'):
            details.append(indent + f"  Timezone: {location.timezone}")
        # Rack could have been a separate formatter, but since this is
        # the only difference...
        if isinstance(location, Rack):
            details.append(indent + f"  Row: {location.rack_row}")
            details.append(indent + f"  Column: {location.rack_column}")
        elif isinstance(location, Building):
            details.append(indent + f"  Address: {location.address}")
            details.append(indent + f"  Next Rack ID: {location.next_rackid}")
            details.append(indent + f"  Network Devices Require Racks: {location.netdev_rack}")
        elif isinstance(location, Room) and location.floor:
            details.append(indent + f"  Floor: {location.floor}")
        if location.uri:
            details.append(indent + f"  Location URI: {location.uri}")
        if location.comments:
            details.append(indent + f"  Comments: {location.comments}")
        if location.parents:
            details.append(indent + "  Location Parents: [{}]".format(", ".join(format(p) for p in location.parents)))
        if location.default_dns_domain:
            details.append(indent + f"  Default DNS Domain: {location.default_dns_domain.name}")
        return "\n".join(details)

    def fill_proto(self, loc, skeleton, embedded=True, indirect_attrs=True):
        skeleton.name = loc.name
        if loc.default_dns_domain is not None:
            skeleton.default_dns_domain = loc.default_dns_domain.name
        # Backwards compatibility
        if loc.location_type == "organization":
            skeleton.location_type = "company"
        else:
            skeleton.location_type = loc.location_type
        skeleton.fullname = loc.fullname
        if isinstance(loc, Rack) and loc.rack_row and loc.rack_column:
            skeleton.row = loc.rack_row
            skeleton.col = loc.rack_column
        if hasattr(loc, "timezone"):
            skeleton.timezone = loc.timezone
        if hasattr(loc, "uri") and loc.uri:
            skeleton.uri = loc.uri

        if indirect_attrs:
            for p in loc.parents:
                parent = skeleton.parents.add()
                parent.name = p.name
                # Backwards compatibility
                if p.location_type == "organization":
                    parent.location_type = "company"
                else:
                    parent.location_type = p.location_type

    def format_json(self, loc, embedded=True, indirect_attrs=True):
        details = {
            "name": loc.name,
            "type": loc.location_type,
        }
        if indirect_attrs:
            details.update(
                {
                    "fullname": loc.fullname,
                    "default_dns_domain": loc.default_dns_domain.name if loc.default_dns_domain else None,
                    "timezone": loc.timezone if hasattr(loc, "timezone") else None,
                    "uri": loc.uri,
                    "comments": loc.comments,
                    "parent": {},
                }
            )
            if isinstance(loc, Rack) and loc.rack_row and loc.rack_column:
                details["rack_row"] = loc.rack_row
                details["rack_column"] = loc.rack_column
            elif isinstance(loc, Room) and loc.floor:
                details["floor"] = loc.floor
            elif isinstance(loc, Building):
                details.update(
                    {
                        "address": loc.address,
                        "next_rackid": loc.next_rackid,
                        "netdev_rack": loc.netdev_rack,
                    }
                )
            if loc.parent:
                details["parent"] = {
                    "name": loc.parent.name,
                    "type": loc.parent.location_type,
                }
        return details

    def csv_fields(self, location):
        """Yield a CSV-ready list of selected attribute values for location."""
        # Columns 0 and 1
        details = [location.location_type, location.name]
        # Columns 2 and 3
        if location.parent:
            details.append(location.parent.location_type)
            details.append(location.parent.name)
        else:
            details.extend([None, None])
        # Columns 4 and 5
        if isinstance(location, Rack):
            details.append(location.rack_row)
            details.append(location.rack_column)
        else:
            details.extend([None, None])
        # Column 6
        if hasattr(location, 'timezone'):
            details.append(location.timezone)
        else:
            details.append(None)
        # Column 7
        details.append(location.fullname)
        # Column 8
        if location.default_dns_domain:
            details.append(location.default_dns_domain)
        else:
            details.append(None)
        yield details

for location_type, mapper in list(Location.__mapper__.polymorphic_map.items()):
    ObjectFormatter.handlers[mapper.class_] = LocationFormatter()
