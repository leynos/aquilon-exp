# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2008-2017,2019  Contributor
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
""" The module governing tables and objects that represent network tags
    in Aquilon.  Network tags are key/value metadata associated with networks. """

from datetime import datetime
import logging
import re

from sqlalchemy import Column, Integer, Sequence, DateTime, ForeignKey
from sqlalchemy.orm import relationship, deferred

from aquilon.exceptions_ import ArgumentError
from aquilon.aqdb.model import Base
from aquilon.aqdb.model.network import Network
from aquilon.aqdb.column_types import AqStr

LOGGER = logging.getLogger(__name__)
_TN = "network_tag"


class NetworkTag(Base):
    """Table of network tags, which are pieces of key/value metadata
    associated with a network.
    """

    __tablename__ = _TN

    id         = Column(Integer, Sequence(f'{_TN}s_id_seq'), primary_key=True)
    network_id = Column(ForeignKey(Network.id), nullable=False, index=True)
    tag_name   = Column(AqStr(30), nullable=False, index=True)
    tag_value  = Column(AqStr(30), nullable=True)

    creation_date = deferred(Column(DateTime, default=datetime.now, nullable=False))
    network = relationship(Network, back_populates="network_tags")

    def __repr__(self):
        return f"<NetworkTag {self.tag_name}={self.tag_value}>"


def validate_network_tags(network_tags):
    """Validate a dict of network tags.  This should not only represent any changes, but the 
    merge of any existing tags on a network plus any changes.  If all tags are to be deleted,
    supply an empty dict."""
    valid_tags = valid_network_tags()
    missing_tags = []

    if len(network_tags) == 0:
        # Nothing to validate.  No tags is valid, at least for now.
        return

    # Check whether all _required_ network tags are present.
    for tag in sorted(valid_tags):
        if not valid_tags[tag]["required"]:
            continue
        if network_tags.get(tag) == None:
            missing_tags.append(tag)

    errors = []

    if (missing_tags):
        errors.append(f"These required network tag(s) are missing: " + ", ".join(missing_tags))

    # Check whether network tags (the keys) are known and match a validation regex.
    for tag in sorted(network_tags):
        if (valid_tags.get(tag)):
            regex = valid_tags[tag]["regex"]
            values = []
            
            if isinstance(network_tags[tag], list):
                if valid_tags[tag]["type"] == "list":
                    values = network_tags[tag]
                else:
                    errors.append(f"Network tag '{tag}' only accepts a single value.")
            else:
                values = [network_tags[tag]]

            for value in values:
                if not re.fullmatch(regex, value):
                    errors.append(f"Network tag '{tag}' value '{value}' doesn't match " +
                        f"validation regex '{regex}'.")
        else:
            errors.append(f"Network tag '{tag}' is not in the list of supported tags.")

    if errors:
        raise ArgumentError("\n".join(errors))

def valid_network_tags():
    # Keys are known (therefore valid) tags.
    # Values are dicts which indicate whether the tag is required and a validation regex.

    # The spec shows boolean values as being represented by "0" or "1".
    boolean = re.compile(r'^(?:0|1)$')

    return {
        "custom_types": {
            "required": False,

            # The specification just says "type: list".  Of strings, one assumes.  We may consider
            # requiring some delimiter (";" perhaps?), but that hasn't been confirmed, so allow
            # anything for the time being.  We don't have support for a true list at this point.
            "regex": r".+",
            "type": "list",
        },
        "is_advertised_externally": {
            "required": True,
            "regex": boolean,
            "type": "scalar",
        },
        "is_advertised_to_internet": {
            "required": True,
            "regex": boolean,
            "type": "scalar",
        },
        "is_dc_hosted_desktop": {
            "required": True,
            "regex": boolean,
            "type": "scalar",
        },
        "is_gels": {
            "required": True,
            "regex": boolean,
            "type": "scalar",
        },
        "is_infra_services": {
            "required": True,
            "regex": boolean,
            "type": "scalar",
        },
        "is_network_infra": {
            "required": True,
            "regex": boolean,
            "type": "scalar",
        },
        "network_domain": {
            # The spec says this tag is "mandatory for FW-d zone only".  What that means, is not explained.
            # As we don't have conditional logic (if one tag has a certain value, other things are
            # allowed or not allowed) we need to make this optional for now.
            "required": False,

            # This regex includes mixed cases.  As AQD lower cases the value in the DB, allow any case.
            "regex": r"(?i)(?:NSO3-zone)",
            "type": "scalar",
        },
        "network_zone": {
            # The spec says this tag is "mandatory for FW-d zone only".  What that means, is not explained.
            # As we don't have conditional logic (if one tag has a certain value, other things are
            # allowed or not allowed) we need to make this optional for now.
            "required": False,

            # This regex includes mixed cases.  As AQD lower cases the value in the DB, allow any case.
            "regex": r"(?i)(?:NSO3-zone)",
            "type": "scalar",
        },
        "plant": {
            "required": True,

            # This regex includes mixed cases.  As AQD lower cases the value in the DB, allow any case.
            "regex": r"(?i)(?:NSO3-Plant|wan20|backup|voice|pod|vela|refinitive|dev|admin_domain|user_oob|user|et_vela|et_enterprise|et_dr|et_admin_domain|et_refinitive|et_voice|et_dev|et_old_wan_dci|core|serverfarm|wan)",
            "type": "scalar",
        },
        "plant_type": {
            "required": True,
            "regex": r"(?:internet|marketdata|wan|electronic_trading|low_trust|cloud|gad|iot|lab|datacenter|management|user|multimedia)",
            "type": "scalar",
        },
        "stance": {
            "required": True,
            "regex": r"(?:ring0|ring1|interior|amber|perimeter|lab)",
            "type": "scalar",
        },
        "standard_network_environment": {
            "required": True,
            "regex": r"(?:prod|nonprod)",
            "type": "scalar",
        },
        "version": {
            # The spec says this is mandatory, but if any tag is specified at all, that means version
            # 2 to us.  So we allow version to be specified, but ignore it.
            "required": False,
            "regex": r"(?:[\d\.]+)",
            "type": "scalar",
        },
        "virtual_ip": {
            "required": True,
            "regex": r"(?:proxy_vip|vpn_pool|mainframe|vnet_vpc|private_cloud_vpn_infra|none)",
            "type": "scalar",
        },
    }

