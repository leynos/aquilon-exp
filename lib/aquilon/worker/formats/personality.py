# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2009,2010,2011,2012,2013,2014,2015,2016  Contributor
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
""" Personality formatter """

from operator import attrgetter

from aquilon.aqdb.model import Personality, PersonalityStage
from aquilon.worker.formats.formatters import ObjectFormatter


class PersonalityFormatter(ObjectFormatter):
    def fill_proto(self, personality, skeleton, embedded=True,
                   indirect_attrs=True):
        skeleton.name = personality.name
        self.redirect_proto(personality.archetype, skeleton.archetype,
                            indirect_attrs=indirect_attrs)
        skeleton.host_environment = personality.host_environment.name
        skeleton.owner_eonid = personality.owner_eon_id

        if personality.comments:
            skeleton.comments = personality.comments

        skeleton.config_override = personality.config_override
        skeleton.cluster_required = personality.cluster_required

    def format_json(self, personality, embedded=True, indirect_attrs=True):
        details = {
            "name": personality.name,
            "archetype": personality.archetype.name,
            "environment": personality.host_environment.name,
            "owner_eonid": personality.owner_eon_id or None,
            "config_override": personality.config_override,
            "cluster_required": personality.cluster_required,
            "comments": personality.comments,
        }
        return details

    def csv_fields(self, obj):
        yield (obj.archetype.name, obj.name,)

ObjectFormatter.handlers[Personality] = PersonalityFormatter()


class PersonalityStageFormatter(PersonalityFormatter):
    def format_raw(self, persst, indent="", embedded=True,
                   indirect_attrs=True):
        personality = persst.personality
        details = []
        if personality.is_cluster:
            description = "Cluster"
        else:
            description = "Host"

        details.append(
            indent
            + f"{description} {personality:c}: {personality.name} {personality.archetype:c}: {personality.archetype.name}"
        )
        if personality.staged:
            details.append(indent + f"  Stage: {persst.name}")
        details.append(indent + f"  Environment: {personality.host_environment.name}")
        details.append(indent + f"  Owned by {personality.owner_grn:c}: {personality.owner_grn.grn}")
        for grn_rec in sorted(persst.grns, key=attrgetter("target", "eon_id")):
            details.append(indent + f"  Used by {grn_rec.grn:c}: {grn_rec.grn.grn} " f"[target: {grn_rec.target}]")

        if personality.config_override:
            details.append(indent + "  Config override: enabled")

        if personality.cluster_required:
            details.append(indent + "  Requires clustered hosts")
        for service, info in list(persst.required_services.items()):
            details.append(indent + f"  Required Service: {service.name}")
            if info.host_environment:
                details.append(indent + f"    Environment Override: {info.host_environment.name}")

        for usr in personality.root_users:
            details.append(indent + f"  Root Access User: {usr.name}")

        for ng in personality.root_netgroups:
            details.append(indent + f"  Root Access Netgroup: {ng.name}")

        for link in sorted(persst.features,
                           key=attrgetter("feature.feature_type",
                                          "feature.post_personality",
                                          "feature.name")):
            if link.feature.post_personality:
                flagstr = " [post_personality]"
            elif link.feature.post_personality_allowed:
                flagstr = " [pre_personality]"
            else:
                flagstr = ""

            details.append(indent + f"  {link.feature:c}: {link.feature.name}{flagstr}")
            if link.model:
                details.append(
                    indent + f"    {link.model.vendor:c}: {link.model.vendor.name} {link.model:c}: {link.model.name}"
                )
            if link.interface_name:
                details.append(indent + f"    Interface: {link.interface_name}")

        if personality.comments:
            details.append(indent + f"  Comments: {personality.comments}")

        for cltype, info in list(persst.cluster_infos.items()):
            details.append(indent + f"  Extra settings for {cltype} clusters:")
            if cltype == "esx":
                details.append(indent + f"    VM host capacity function: {info.vmhost_capacity_function}")
        return "\n".join(details)

    def fill_proto(self, persst, skeleton, embedded=True, indirect_attrs=True):
        super().fill_proto(persst.personality, skeleton, embedded=embedded, indirect_attrs=indirect_attrs)

        if persst.staged:
            skeleton.stage = persst.name

        if indirect_attrs:
            for dbsrv, info in list(persst.required_services.items()):
                srvrec = skeleton.required_services.add()
                srvrec.service = dbsrv.name
                if info.host_environment:
                    srvrec.host_environment = info.host_environment.name

            for link in persst.features:
                feat_msg = skeleton.features.add()
                self.redirect_proto(link.feature, feat_msg)
                if link.model:
                    self.redirect_proto(link.model, feat_msg.model)
                if link.interface_name:
                    feat_msg.interface_name = link.interface_name

            for grn_rec in persst.grns:
                map = skeleton.eonid_maps.add()
                map.target = grn_rec.target
                map.eonid = grn_rec.eon_id

        for cltype, info in list(persst.cluster_infos.items()):
            if cltype == "esx":
                skeleton.vmhost_capacity_function = info.vmhost_capacity_function

    def csv_fields(self, obj):
        yield (obj.archetype.name, obj.personality.name, obj.name)

    def format_json(self, persst, embedded=True, indirect_attrs=True):
        details = {
            "name": persst.personality.name,
            "archetype": persst.personality.archetype.name,
            "environment": persst.personality.host_environment.name,
            "owner_grn": persst.personality.owner_grn.grn,
            "owner_eonid": persst.owner_eon_id or None,
            "grns": [],
        }
        if persst.staged:
            details["stage"] = persst.name
        for grn_rec in sorted(persst.grns, key=attrgetter("target", "eon_id")):
            details["grns"].append({"grn": grn_rec.grn.grn, "target": grn_rec.target})
        if indirect_attrs:
            details["features"] = []
            for link in persst.features:
                details["features"].append(link.feature.name)
            if persst.personality.comments:
                details["comments"] = persst.personality.comments
        return details

ObjectFormatter.handlers[PersonalityStage] = PersonalityStageFormatter()
