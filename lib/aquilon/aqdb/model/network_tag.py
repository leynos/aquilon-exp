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
            if not re.fullmatch(regex, network_tags[tag]):
                errors.append(f"Network tag '{tag}' value '{network_tags[tag]}' doesn't match " +
                    f"validation regex '{regex}'.")
        else:
            errors.append(f"Network tag '{tag}' is not in the list of supported tags.")

    if errors:
        raise ArgumentError("\n".join(errors))

def valid_network_tags():
    # Keys are known (therefore valid) tags.
    # Values are dicts which indicate whether the tag is required and a validation regex.
    boolean = re.compile(r'^(?:0|1)$')

    return {
        "cloud_network_type": {
            "required": 0,
            "regex": r'^(?:none|vnet_vpc|vpn)$',
        },
        "dc_network_type": {
            "required": 1,
            "regex": r'^(?:none|mainframe|clinfra|ddi-net1)$',
        },
        "electronic_trading_network_type": {
            "required": 0,
            "regex": r'^(?:none|service|trade|msmd|rawmd|externa|management|heartbeat)$',
        },
        "ens_zone": {
            "required": 0,
            "regex": r'^[\-\w]+$', # TODO better validation once valid values determined
        },
        "fw_domain": {
            "required": 0,
            "regex": r'^[\-\w]+$', # TODO better validation once valid values determined
        },
        "is_advertised_externally": {
            "required": 0,
            "regex": boolean,
        },
        "is_dc_hosted_desktop": {
            "required": 1,
            "regex": boolean,
        },
        "is_gels": {
            "required": 0,
            "regex": boolean,
        },
        "is_infra_services": {
            "required": 1,
            "regex": boolean,
        },
        "is_network_infra": {
            "required": 0,
            "regex": boolean,
        },
        "lab_network_type": {
            "required": 0,
            "regex": r'^[\-\w]+$', # TODO better validation once valid values determined
        },
        "network_area": {
            "required": 0,
            "regex": r'^(?:user_network_type|dc_network_type|cloud_network_type|perimeter_network_type|electronic_trading_network_type|wan_network_type|lab_network_type|shared_network_type|none)$',
        },
        "perimeter_network_type": {
            "required": 0,
            "regex": r'^[\-\w]+$', # TODO better validation once valid values determined
        },
        "plant": {
            "required": 0,
            "regex": r'^(?:mssip|mssig|mdex|wan20|speedway|seti_inband_oob|seti_outofband_oob|proxima|velocity|amm|low_trust_access|low_trust_dmz|mcdmz|csdmz|azure|aws|gcp|gad|iot_access|iot_dmz|seti_lab|wm_lab|ec_lab|ens_lab|backup|voice|enclave|pod|vela|refinitive|dev|admin_domain|mssip_oob|mdex_oob|genpop_oob|btgn|admin_oob|csdmz_oob|mcdmz_oob|user_oob|ring1_oob|ring0_oob|amber_dmz|gels_dmz|wm_dmz|user|multimedia|multimedia_dmz|et_vela|et_enterprise|et_dr|et_admin_domain|et_refinitive|et_dev|et_voice|et_prod|et_old_wan_dci|et_oob|et_internet_plant_prod|et_interent_plant_enterprise|et_aws|et_vendor_environment|et_lab|mssc|msimc|msms|msfc|msbic|core|serverfarm|wan|internal_oob|cod_oob|branch_oob|infradev)$',
        },
        "plant_type": {
            "required": 1,
            "regex": r'^(?:internet|marketdata|wan|electronic_trading|low_trust|cloud|gad|iot|lab|datacenter|management|user|multimedia)$',
        },
        "shared_network_type": {
            "required": 0,
            "regex": r'^(?:none|tor_net|tor_net2|tor_net4|vm_storage_net|netbackup|oob_server|oob_fw|oob_ens)$',
        },
        "stance": {
            "required": 1,
            "regex": r'^(?:ring0|ring1|interior|amber|perimeter|lab)$',
        },
        "standard_network_environment": {
            "required": 1,
            "regex": r'^(?:prod|nonprod)$',
        },
        "user_network_type": {
            "required": 0,
            "regex": r'^(?:none|trusted_endpoint|untrusted_endpoint|lowtrusted_endpoint)$',
        },
        "version": {
            "required": 0,
            "regex": r'^(?:1|2)$',
        },
        "virtual_ip": {
            "required": 0,
            "regex": r'^(?:overlay_vip|vip|local_vip|proxy_vip|vpn_pool|loadbalancer_vip|nat|anycast|none)$',
        },
        "wan_network_type": {
            "required": 0,
            "regex": r'^(?:none|amber|corporate|[\-\w]+)$', # Spec says "etc.etc." for valid values!
        },
    };
