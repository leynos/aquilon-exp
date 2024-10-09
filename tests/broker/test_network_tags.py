#!/usr/bin/env python
# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018  Contributor
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
"""Test network tags for various network commands."""

import json
import unittest
import subprocess

if __name__ == "__main__":
    from . import utils
    utils.import_depends()

from .brokertest import TestBrokerCommand
from aq_test_client import AqTestClient


class TestNetworkTags(TestBrokerCommand):
    network_defaults = {
        "prefixlen": 24,
        "city": "ny",
        "type": "unknown",
        "side": "a",
    }
    network1 = network_defaults.copy()
    network1["name"] = "test_net1";
    network1["ip"] = "1.2.1.0";

    network2 = network_defaults.copy()
    network2["name"] = "test_net2";
    network2["ip"] = "1.2.2.0";
    network2["add_tags"] = True;
    tags = {
        "dc_network_type": "clinfra", 
        "is_dc_hosted_desktop": "0", 
        "is_infra_services": "0", 
        "plant_type": "lab", 
        "stance": "amber", 
        "standard_network_environment": "nonprod", 
    }

    @classmethod
    def setUpClass(cls):
        """Clean up networks that might or might not exist"""
        aq = AqTestClient()
        for network in (cls.network1, cls.network2):
            command = [
                f"del_network",
                f"--ip={network['ip']}",
            ]
            aq.runcommand(command)
        super(TestNetworkTags, cls).setUpClass()

    def test_100_add_network_missing_tag(self):
        """Show that adding a network with missing required tags fails"""
        network = self.network2
        command = self.default_add_network_command(network)
        tags = self.tags.copy()
        del tags["plant_type"]
        del tags["stance"]
        command.extend(f"--network_tag={k}={tags[k]}" for k in tags)
        out = self.badrequesttest(command)
        self.matchoutput(out, "These required network tag(s) are missing: plant_type, stance", command)

    def test_102_add_network_unknown_tag(self):
        """Show that adding a network with an invalid tag name fails"""
        network = self.network2
        command = self.default_add_network_command(network)
        tags = self.tags.copy()
        tags["foo"] = "bar"
        command.extend(f"--network_tag={k}={tags[k]}" for k in tags)
        out = self.badrequesttest(command)
        self.matchoutput(out, "Network tag 'foo' is not in the list of supported tags.", command)

    def test_104_add_network_invalid_tag_value(self):
        """Show that adding a network with an invalid tag value fails"""
        network = self.network2
        command = self.default_add_network_command(network)
        tags = self.tags.copy()
        tags["stance"] = "qwerty"
        command.extend(f"--network_tag={k}={tags[k]}" for k in tags)
        out = self.badrequesttest(command)
        self.matchoutput(out, "Network tag 'stance' value 'qwerty' doesn't match validation regex '^(?:ring0|ring1|interior|amber|perimeter|lab)$'.", command)

    def test_110_add_network(self):
        """Add 2 networks, one without tags and one with"""
        for network in (self.network1, self.network2):
            command = self.default_add_network_command(network)
            if network.get("add_tags"):
                command.extend(f"--network_tag={k}={self.tags[k]}" for k in self.tags)
            self.noouttest(command)
            self.validate_network_data(network)

    def test_120_update_network(self):
        """Update a network to add an optional tag"""
        network = self.network2
        command = [
            f"update_network",
            f"--network={network['name']}",
            f"--network_tag=network_area=user_network_type",
        ]
        self.noouttest(command)
        expected_tags = self.tags.copy()
        expected_tags["network_area"] = "user_network_type"
        self.validate_network_data(network, expected_tags)

    def test_122_update_network(self):
        """Update a network to update an optional tag"""
        network = self.network2
        command = [
            f"update_network",
            f"--network={network['name']}",
            f"--network_tag=network_area=dc_network_type",
        ]
        self.noouttest(command)
        expected_tags = self.tags.copy()
        expected_tags["network_area"] = "dc_network_type"
        self.validate_network_data(network, expected_tags)

    def test_124_update_network(self):
        """Update a network to delete an optional tag"""
        network = self.network2
        command = [
            f"update_network",
            f"--network={network['name']}",
            f"--network_tag=network_area=",
        ]
        self.noouttest(command)
        self.validate_network_data(network)

    def test_126_update_network(self):
        """Update a network without tags to add a full set of required tags"""
        network = self.network1
        command = [
            f"update_network",
            f"--network={network['name']}",
        ]
        command.extend(f"--network_tag={k}={self.tags[k]}" for k in self.tags)
        self.noouttest(command)
        self.validate_network_data(network, self.tags)

    def test_128_update_network(self):
        """Update a network to remove all its tags"""
        network = self.network1
        command = [
            f"update_network",
            f"--network={network['name']}",
        ]
        command.extend(f"--network_tag={k}=" for k in self.tags)
        self.noouttest(command)
        self.validate_network_data(network)

    def test_130_update_network_missing_tag(self):
        """Show that updating a network to remove a required tag fails"""
        network = self.network2
        command = [
            f"update_network",
            f"--network={network['name']}",
            f"--network_tag=plant_type=",
        ]
        out = self.badrequesttest(command)
        self.matchoutput(out, "These required network tag(s) are missing: plant_type", command)

    def test_132_update_network_unknown_tag(self):
        """Show that updating a network with an invalid tag name fails"""
        network = self.network2
        command = [
            f"update_network",
            f"--network={network['name']}",
            f"--network_tag=foo=bar",
        ]
        out = self.badrequesttest(command)
        self.matchoutput(out, "Network tag 'foo' is not in the list of supported tags.", command)

    def test_134_update_network_invalid_tag_value(self):
        """Show that updating a network with an invalid tag value fails"""
        network = self.network2
        command = [
            f"update_network",
            f"--network={network['name']}",
            f"--network_tag=plant_type=asdf",
        ]
        out = self.badrequesttest(command)
        self.matchoutput(out, "Network tag 'plant_type' value 'asdf' doesn't match validation regex '^(?:internet|marketdata|wan|electronic_trading|low_trust|cloud|gad|iot|lab|datacenter|management|user|multimedia)$'.", command)

    def test_200_show_network_raw(self):
        network = self.network2
        command = [
            f"show_network",
            f"--network={network['name']}",
        ]
        output = self.commandtest(command)
        expected = """Network: test_net2
  Network Environment: internal
  IP: 1.2.2.0
  Netmask: 255.255.255.0
  Sysloc: None
  City: ny
    Fullname: New York
    Timezone: US/Eastern
    Location Parents: [Organization ms, Hub ny, Continent na, Country us, Campus ny]
    Default DNS Domain: one-nyp.ms.com
  Side: a
  Network Type: unknown
  Network Tags:
    dc_network_type: clinfra
    is_dc_hosted_desktop: 0
    is_infra_services: 0
    plant_type: lab
    stance: amber
    standard_network_environment: nonprod"""
        self.matchoutput(output, expected, command)

    def test_210_show_network_csv(self):
        network = self.network2
        command = [
            f"show_network",
            f"--network={network['name']}",
            f"--format=csv",
        ]
        output = self.commandtest(command)
        expected = 'test_net2,1.2.2.0,255.255.255.0,,us,a,unknown,,"dc_network_type=clinfra,is_dc_hosted_desktop=0,is_infra_services=0,plant_type=lab,stance=amber,standard_network_environment=nonprod"'

        self.matchoutput(output, expected, command)

    def test_220_show_network_proto(self):
        network = self.network2
        command = [
            f"show_network",
            f"--network={network['name']}",
            f"--format=proto",
        ]
        expected = 1
        self.protobuftest(command, expected)

    def test_300_delete_network(self):
        """Delete the 2 test networks"""
        for network in (self.network1, self.network2):
            command = [
                f"del_network",
                f"--ip={network['ip']}",
            ]
            self.noouttest(command)

    def test_310_verify_deleted_network(self):
        """Confirm that the 2 deleted networks no longer exist"""
        for network in (self.network1, self.network2):
            command = [
                f"show_network",
                f"--network={network['name']}",
                f"--format=json",
            ]
            self.notfoundtest(command)

    def get_network_data(self, network_name):
        command = [
            f"show_network",
            f"--network={network_name}",
            f"--format=json",
        ]
        json_output = self.commandtest(command)
        decoded = json.loads(json_output)
        self.assertTrue(decoded is not None, f"Command {command} returned a valid JSON response")
        return decoded

    def validate_network_data(self, network, expected_tags=None):
        decoded = self.get_network_data(network['name'])

        expected = {
            "name": network["name"],
            "ip": network["ip"],
            "cidr": network["prefixlen"],
            "side": network["side"],
            "location": { "name": network["city"], "type": "city" },
        }
        if expected_tags:
            expected["network_tags"] = expected_tags
        elif network.get("add_tags"):
            expected["network_tags"] = self.tags

        self.assertLessEqual(expected.items(), decoded[0].items())

    def default_add_network_command(self, network):
        command = [
            f"add_network",
            f"--network={network['name']}",
            f"--ip={network['ip']}",
            f"--prefixlen={network['prefixlen']}",
            f"--city={network['city']}",
            f"--type={network['type']}",
            f"--side={network['side']}",
        ]
        return command


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNetworkTags)
    unittest.TextTestRunner(verbosity=2).run(suite)

