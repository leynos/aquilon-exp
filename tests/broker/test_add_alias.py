#!/usr/bin/env python
# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2011,2012,2013,2014,2015,2016,2017  Contributor
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
"""Module for testing the add/show alias command."""

import unittest
import json

from mock_ib_services import ib_expect_add_alias
from mock_ib_services import ib_expect_del_alias
from mock_ib_services import ib_expect_update_alias

if __name__ == '__main__':
    from broker import utils
    utils.import_depends()

from broker.brokertest import TestBrokerCommand
from .eventstest import EventsTestMixin
from broker.utils import MockHub


class TestAddAlias(EventsTestMixin, TestBrokerCommand):
    def test_100_add_alias2host(self):
        self.event_add_dns(
            fqdn='alias2host.aqd-unittest.ms.com',
            dns_environment='internal',
            dns_records=[
                {
                    'target': 'arecord13.aqd-unittest.ms.com',
                    'targetEnvironmentName': 'internal',
                    'rrtype': 'CNAME'
                },
            ],
        )
        ib_expect_add_alias('alias2host.aqd-unittest.ms.com', 'arecord13.aqd-unittest.ms.com')
        cmd = ['add', 'alias', '--fqdn', 'alias2host.aqd-unittest.ms.com',
               '--target', 'arecord13.aqd-unittest.ms.com']
        self.noouttest(cmd)
        self.events_verify()
        self.ib_verify()

    def test_105_add_aliasduplicate(self):
        cmd = ['add', 'alias', '--fqdn', 'alias2host.aqd-unittest.ms.com',
               '--target', 'arecord13.aqd-unittest.ms.com']
        out = self.badrequesttest(cmd)
        self.matchoutput(out, "Alias alias2host.aqd-unittest.ms.com "
                         "already exists.", cmd)

    def test_110_mscom_alias(self):
        self.event_add_dns(
            fqdn='alias.ms.com',
            dns_environment='internal',
            dns_records=[
                {
                    'target': 'arecord13.aqd-unittest.ms.com',
                    'targetEnvironmentName': 'internal',
                    'rrtype': 'CNAME'
                },
            ],
        )
        cmd = ['add', 'alias', '--fqdn', 'alias.ms.com',
               '--target', 'arecord13.aqd-unittest.ms.com',
               '--comments', 'Some alias comments']
        ib_expect_add_alias('alias.ms.com', 'arecord13.aqd-unittest.ms.com')
        self.dsdb_expect("add_host_alias "
                         "-host_name arecord13.aqd-unittest.ms.com "
                         "-alias_name alias.ms.com "
                         "-comments Some alias comments")
        self.noouttest(cmd)
        self.dsdb_verify()
        self.events_verify()
        self.ib_verify()

    def test_120_conflict_a_record(self):
        cmd = ['add', 'alias', '--fqdn', 'arecord14.aqd-unittest.ms.com',
               '--target', 'arecord13.aqd-unittest.ms.com']
        out = self.badrequesttest(cmd)
        self.matchoutput(out, "DNS Record arecord14.aqd-unittest.ms.com "
                         "already exists.", cmd)

    def test_130_conflict_reserver_name(self):
        cmd = ['add', 'alias', '--fqdn', 'nyaqd1.ms.com',
               '--target', 'arecord13.aqd-unittest.ms.com']
        out = self.badrequesttest(cmd)
        self.matchoutput(out, "Reserved Name nyaqd1.ms.com already exists.", cmd)

    def test_140_restricted_domain(self):
        cmd = ["add", "alias", "--fqdn", "foo.restrict.aqd-unittest.ms.com",
               "--target", "arecord13.aqd-unittest.ms.com"]
        out = self.badrequesttest(cmd)
        self.matchoutput(out,
                         "DNS Domain restrict.aqd-unittest.ms.com is "
                         "restricted, aliases are not allowed.",
                         cmd)

    def test_150_add_alias2diff_environment_fail(self):
        self.event_add_dns(
            fqdn='alias2host.aqd-unittest-ut-env.ms.com',
            dns_environment='ut-env',
            dns_records=[
                {
                    'target': 'arecord13.aqd-unittest.ms.com',
                    'targetEnvironmentName': 'internal',
                    'rrtype': 'CNAME'
                },
            ],
        )
        cmd = ['add', 'alias', '--fqdn', 'alias2host.aqd-unittest-ut-env.ms.com',
               '--dns_environment', 'ut-env',
               '--target', 'arecord13.aqd-unittest.ms.com',
               '--target_environment', 'internal']
        out = self.badrequesttest(cmd)
        self.matchoutput(out, "Please provide valid "
                              "justification number",
                         cmd)

    def test_151_add_alias2diff_environment(self):
        self.event_add_dns(
            fqdn='alias2host.aqd-unittest-ut-env.ms.com',
            dns_environment='ut-env',
            dns_records=[
                {
                    'target': 'arecord13.aqd-unittest.ms.com',
                    'targetEnvironmentName': 'internal',
                    'rrtype': 'CNAME'
                },
            ],
        )
        cmd = ['add', 'alias', '--fqdn', 'alias2host.aqd-unittest-ut-env.ms.com',
               '--dns_environment', 'ut-env',
               '--target', 'arecord13.aqd-unittest.ms.com',
               '--target_environment', 'internal'] + self.valid_just_sn
        self.noouttest(cmd)
        self.events_verify()

    def test_155_add_alias2explicit_target_environment(self):
        cmd = ['add', 'alias', '--fqdn', 'alias2alias.aqd-unittest-ut-env.ms.com',
               '--dns_environment', 'ut-env',
               '--target', 'alias2host.aqd-unittest-ut-env.ms.com',
               '--target_environment', 'ut-env'] + self.valid_just_sn
        self.noouttest(cmd)

    def test_160_add_alias_with_fqdn_in_diff_environment(self):
        cmd = ['add', 'alias', '--fqdn', 'alias13.aqd-unittest.ms.com',
               '--dns_environment', 'ut-env',
               '--target', 'arecord13.aqd-unittest.ms.com',
               '--target_environment', 'internal'] + self.valid_just_sn
        self.noouttest(cmd)

    def test_200_autocreate_target(self):
        ib_expect_add_alias('restrict1.aqd-unittest.ms.com', 'target.restrict.aqd-unittest.ms.com')
        cmd = ["add", "alias", "--fqdn", "restrict1.aqd-unittest.ms.com",
               "--target", "target.restrict.aqd-unittest.ms.com"]
        out = self.statustest(cmd)
        self.matchoutput(out,
                         "WARNING: Will create a reference to "
                         "target.restrict.aqd-unittest.ms.com, but ",
                         cmd)
        self.ib_verify()

    def test_201_verify_autocreate(self):
        cmd = ["search", "dns", "--fullinfo",
               "--fqdn", "target.restrict.aqd-unittest.ms.com"]
        out = self.commandtest(cmd)
        self.matchoutput(out,
                         "Reserved Name: target.restrict.aqd-unittest.ms.com",
                         cmd)

    def test_201_verify_noprimary(self):
        cmd = ["search", "dns", "--noprimary_name",
               "--record_type", "reserved_name"]
        out = self.commandtest(cmd)
        self.matchoutput(out, "target.restrict.aqd-unittest.ms.com", cmd)

    def test_202_verify_autocreate_json_data(self):
        cmd = ["search", "dns", "--fullinfo",
               "--fqdn", "target.restrict.aqd-unittest.ms.com", "--format",
               "json"]
        out = self.commandtest(cmd)
        expected = [
            {
                "record_type": "dns_record",
                "dns_environment": "internal",
                "fqdn": "target.restrict.aqd-unittest.ms.com",
                "aliases": ["restrict1.aqd-unittest.ms.com"]
            }
        ]
        self.assertEqual(json.loads(out), expected)

    def test_210_autocreate_second_alias(self):
        ib_expect_add_alias('restrict2.aqd-unittest.ms.com', 'target.restrict.aqd-unittest.ms.com')
        cmd = ["add", "alias", "--fqdn", "restrict2.aqd-unittest.ms.com",
               "--target", "target.restrict.aqd-unittest.ms.com"]
        self.noouttest(cmd)
        self.ib_verify()

    def test_220_restricted_alias_no_dsdb(self):
        ib_expect_add_alias('restrict.ms.com', 'no-dsdb.restrict.aqd-unittest.ms.com')
        cmd = ["add", "alias", "--fqdn", "restrict.ms.com",
               "--target", "no-dsdb.restrict.aqd-unittest.ms.com"]
        out = self.statustest(cmd)
        self.matchoutput(out,
                         "WARNING: Will create a reference to "
                         "no-dsdb.restrict.aqd-unittest.ms.com, but ",
                         cmd)
        self.dsdb_verify(empty=True)
        self.ib_verify()

    def test_400_verify_alias2host(self):
        cmd = "show alias --fqdn alias2host.aqd-unittest.ms.com"
        out = self.commandtest(cmd.split(" "))

        self.matchoutput(out, "Alias: alias2host.aqd-unittest.ms.com", cmd)
        self.matchoutput(out, "Target: arecord13.aqd-unittest.ms.com", cmd)
        self.matchoutput(out, "DNS Environment: internal", cmd)

        command = ["show_alias",
                   "--fqdn", "alias2host.aqd-unittest.ms.com", "--format", "json"]
        out = self.commandtest(command)
        self.assertIsInstance(json.loads(out)[0], dict)

    def test_405_verify_host_shows_alias(self):
        cmd = "show address --fqdn arecord13.aqd-unittest.ms.com"
        out = self.commandtest(cmd.split(" "))
        self.matchoutput(out, "Aliases: alias.ms.com, "
                         "alias13.aqd-unittest.ms.com [environment: ut-env], "
                         "alias2alias.aqd-unittest-ut-env.ms.com [environment: ut-env], "
                         "alias2host.aqd-unittest-ut-env.ms.com [environment: ut-env], "
                         "alias2host.aqd-unittest.ms.com", cmd)

        command = ["show_address",
                   "--fqdn", "arecord13.aqd-unittest.ms.com", "--format", "json"]
        out = self.commandtest(command)
        self.assertIsInstance(json.loads(out)[0], dict)

    def test_410_verify_mscom_alias(self):
        cmd = "show alias --fqdn alias.ms.com"
        out = self.commandtest(cmd.split(" "))

        self.matchoutput(out, "Alias: alias.ms.com", cmd)
        self.matchoutput(out, "Target: arecord13.aqd-unittest.ms.com", cmd)
        self.matchoutput(out, "DNS Environment: internal", cmd)
        self.matchoutput(out, "Comments: Some alias comments", cmd)

    def test_420_verify_alias2diff_environment(self):
        cmd = "show alias --fqdn alias2host.aqd-unittest-ut-env.ms.com --dns_environment ut-env"
        out = self.commandtest(cmd.split(" "))
        self.matchoutput(out, "Alias: alias2host.aqd-unittest-ut-env.ms.com", cmd)
        self.matchoutput(out, "Target: arecord13.aqd-unittest.ms.com [environment: internal]", cmd)
        self.matchoutput(out, "DNS Environment: ut-env", cmd)

    def test_425_verify_alias2alias_with_diff_environment(self):
        cmd = "show alias --fqdn alias2alias.aqd-unittest-ut-env.ms.com --dns_environment ut-env"
        out = self.commandtest(cmd.split(" "))
        self.matchoutput(out, "Alias: alias2alias.aqd-unittest-ut-env.ms.com", cmd)
        self.matchoutput(out, "Target: alias2host.aqd-unittest-ut-env.ms.com", cmd)
        self.matchoutput(out, "DNS Environment: ut-env", cmd)

    def test_500_add_alias2alias(self):
        ib_expect_add_alias('alias2alias.aqd-unittest.ms.com', 'alias2host.aqd-unittest.ms.com', ttl=60)
        cmd = ['add', 'alias', '--fqdn', 'alias2alias.aqd-unittest.ms.com',
               '--target', 'alias2host.aqd-unittest.ms.com', '--ttl', 60]
        self.noouttest(cmd)
        self.ib_verify()

    def test_510_add_alias3alias(self):
        ib_expect_add_alias('alias3alias.aqd-unittest.ms.com', 'alias2alias.aqd-unittest.ms.com')
        cmd = ['add', 'alias', '--fqdn', 'alias3alias.aqd-unittest.ms.com',
               '--target', 'alias2alias.aqd-unittest.ms.com']
        self.noouttest(cmd)
        self.ib_verify()

    def test_520_add_alias4alias(self):
        ib_expect_add_alias('alias4alias.aqd-unittest.ms.com', 'alias3alias.aqd-unittest.ms.com')
        cmd = ['add', 'alias', '--fqdn', 'alias4alias.aqd-unittest.ms.com',
               '--target', 'alias3alias.aqd-unittest.ms.com']
        self.noouttest(cmd)
        self.ib_verify()

    def test_530_add_alias5alias_fail(self):
        cmd = ['add', 'alias', '--fqdn', 'alias5alias.aqd-unittest.ms.com',
               '--target', 'alias4alias.aqd-unittest.ms.com']
        out = self.badrequesttest(cmd)
        self.matchoutput(out, "Maximum alias depth exceeded", cmd)

    def test_600_verify_alias2alias(self):
        cmd = 'show alias --fqdn alias2alias.aqd-unittest.ms.com'
        out = self.commandtest(cmd.split(" "))
        self.matchoutput(out, 'Alias: alias2alias.aqd-unittest.ms.com', cmd)
        self.matchoutput(out, 'TTL: 60', cmd)

    def test_601_verify_alias2alias_backwards(self):
        cmd = 'show alias --fqdn alias2host.aqd-unittest.ms.com'
        out = self.commandtest(cmd.split(" "))
        self.matchoutput(out, "Aliases: alias2alias.aqd-unittest.ms.com", cmd)

    def test_602_verify_alias2alias_recursive(self):
        cmd = 'show address --fqdn arecord13.aqd-unittest.ms.com'
        out = self.commandtest(cmd.split(" "))
        self.matchoutput(out,
                         "Aliases: alias.ms.com, "
                         "alias13.aqd-unittest.ms.com [environment: ut-env], "
                         "alias2alias.aqd-unittest-ut-env.ms.com [environment: ut-env], "
                         "alias2alias.aqd-unittest.ms.com, "
                         "alias2host.aqd-unittest-ut-env.ms.com [environment: ut-env], "
                         "alias2host.aqd-unittest.ms.com, "
                         "alias3alias.aqd-unittest.ms.com, "
                         "alias4alias.aqd-unittest.ms.com",
                         cmd)

    def test_700_show_alias_host(self):
        ip = self.net["zebra_eth0"].usable[0]
        ib_expect_add_alias('alias0.aqd-unittest.ms.com', 'unittest20-e0.aqd-unittest.ms.com')
        command = ["add", "alias", "--fqdn", "alias0.aqd-unittest.ms.com",
                   "--target", "unittest20-e0.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.ib_verify()

        ib_expect_add_alias('alias01.aqd-unittest.ms.com', 'alias0.aqd-unittest.ms.com')
        command = ["add", "alias", "--fqdn", "alias01.aqd-unittest.ms.com",
                   "--target", "alias0.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.ib_verify()

        command = ["show", "host", "--hostname", "unittest20.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.searchoutput(out,
                          r'Provides: unittest20-e0.aqd-unittest.ms.com \[%s\]\s*'
                          r'Aliases: alias0.aqd-unittest.ms.com, alias01.aqd-unittest.ms.com'
                          % ip,
                          command)

        command = ["show", "host", "--hostname", "unittest20.aqd-unittest.ms.com",
                   "--format", "proto"]
        host = self.protobuftest(command, expect=1)[0]
        self.assertEqual(host.hostname, 'unittest20')
        interfaces = {iface.device: iface for iface in host.machine.interfaces}
        self.assertIn("eth0", interfaces)
        self.assertEqual(interfaces["eth0"].aliases[0], 'alias0.aqd-unittest.ms.com')
        self.assertEqual(interfaces["eth0"].aliases[1], 'alias01.aqd-unittest.ms.com')
        self.assertEqual(interfaces["eth0"].ip, str(ip))
        self.assertEqual(interfaces["eth0"].fqdn, 'unittest20-e0.aqd-unittest.ms.com')

        ib_expect_del_alias('alias01.aqd-unittest.ms.com')
        command = ["del", "alias", "--fqdn", "alias01.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.ib_verify()

        ib_expect_del_alias('alias0.aqd-unittest.ms.com')
        command = ["del", "alias", "--fqdn", "alias0.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.ib_verify()

    def test_710_show_alias_host(self):
        ip = self.net["zebra_eth1"].usable[3]
        ib_expect_add_alias('alias1.aqd-unittest.ms.com', "unittest20-e1-1.aqd-unittest.ms.com")
        command = ["add", "alias", "--fqdn", "alias1.aqd-unittest.ms.com",
                   "--target", "unittest20-e1-1.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.ib_verify()

        ib_expect_add_alias('alias11.aqd-unittest.ms.com', "alias1.aqd-unittest.ms.com")
        command = ["add", "alias", "--fqdn", "alias11.aqd-unittest.ms.com",
                   "--target", "alias1.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.ib_verify()

        command = ["show", "host", "--hostname", "unittest20.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.searchoutput(out,
                          r'Provides: unittest20-e1-1.aqd-unittest.ms.com \[%s\] \(label: e1\)\s*'
                          r'Aliases: alias1.aqd-unittest.ms.com, alias11.aqd-unittest.ms.com'
                          % ip,
                          command)

        command = ["show", "host", "--hostname", "unittest20.aqd-unittest.ms.com",
                   "--format", "proto"]
        host = self.protobuftest(command, expect=1)[0]
        self.assertEqual(host.hostname, 'unittest20')
        interfaces = {iface.device: iface for iface in host.machine.interfaces}
        self.assertIn("eth1:e1", interfaces)
        self.assertEqual(interfaces["eth1:e1"].aliases[0], 'alias1.aqd-unittest.ms.com')
        self.assertEqual(interfaces["eth1:e1"].aliases[1], 'alias11.aqd-unittest.ms.com')
        self.assertEqual(interfaces["eth1:e1"].ip, str(ip))
        self.assertEqual(interfaces["eth1:e1"].fqdn, 'unittest20-e1-1.aqd-unittest.ms.com')

        ib_expect_del_alias('alias11.aqd-unittest.ms.com')
        command = ["del", "alias", "--fqdn", "alias11.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.ib_verify()

        ib_expect_del_alias('alias1.aqd-unittest.ms.com')
        command = ["del", "alias", "--fqdn", "alias1.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.ib_verify()

    def test_800_grn(self):
        ib_expect_add_alias('alias2host-grn.aqd-unittest.ms.com', "arecord50.aqd-unittest.ms.com")
        command = ["add", "alias",
                   "--fqdn", "alias2host-grn.aqd-unittest.ms.com",
                   "--target", "arecord50.aqd-unittest.ms.com",
                   "--grn", "grn:/ms/ei/aquilon/aqd"]
        self.noouttest(command)
        self.ib_verify()

    def test_805_verify_grn(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "alias2host-grn.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out, "Owned by GRN: grn:/ms/ei/aquilon/aqd",
                         command)

    def test_806_verify_grn_json_data(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "alias2host-grn.aqd-unittest.ms.com",
                   "--format", "json"]
        out = self.commandtest(command)
        expected = [
            {
                "record_type": "alias",
                "fqdn": "alias2host-grn.aqd-unittest.ms.com",
                "dns_environment": "internal",
                "target": "arecord50.aqd-unittest.ms.com",
                "eon_id": 2
            }
        ]
        self.assertEqual(json.loads(out), expected)

    def test_810_eon_id(self):
        ib_expect_add_alias('alias2host-eon-id.aqd-unittest.ms.com', "arecord51.aqd-unittest.ms.com")
        command = ["add", "alias",
                   "--fqdn", "alias2host-eon-id.aqd-unittest.ms.com",
                   "--target", "arecord51.aqd-unittest.ms.com",
                   "--eon_id", "3"]
        self.noouttest(command)
        self.ib_verify()

    def test_815_verify_eon_id(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "alias2host-eon-id.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out, "Owned by GRN: grn:/ms/ei/aquilon/unittest",
                         command)

    def test_850_grn_conflict_with_primary_name(self):
        command = ["add", "alias",
                   "--fqdn", "alias2host-bad-target.aqd-unittest.ms.com",
                   "--target", "unittest00.one-nyp.ms.com",
                   "--grn", "grn:/ms/ei/aquilon/unittest"]
        out = self.badrequesttest(command)
        self.matchoutput(out,
                         "Alias alias2host-bad-target.aqd-unittest.ms.com "
                         "depends on DNS Record unittest00.one-nyp.ms.com. "
                         "It conflicts with GRN grn:/ms/ei/aquilon/unittest: "
                         "DNS Record unittest00.one-nyp.ms.com is a primary "
                         "name. GRN should not be set but derived from the "
                         "device.",
                         command)

    def test_860_grn_conflict_with_service_address(self):
        command = ["add", "alias",
                   "--fqdn", "alias2host-bad-target.aqd-unittest.ms.com",
                   "--target", "zebra2.aqd-unittest.ms.com",
                   "--grn", "grn:/ms/ei/aquilon/unittest"]
        out = self.badrequesttest(command)
        self.matchoutput(out,
                         "Alias alias2host-bad-target.aqd-unittest.ms.com "
                         "depends on DNS Record zebra2.aqd-unittest.ms.com. "
                         "It conflicts with GRN grn:/ms/ei/aquilon/unittest: "
                         "DNS Record zebra2.aqd-unittest.ms.com is a service "
                         "address. GRN should not be set but derived from the "
                         "device.",
                         command)

    def test_870_grn_conflict_with_interface_address(self):
        command = ["add", "alias",
                   "--fqdn", "alias2host-bad-target.aqd-unittest.ms.com",
                   "--target", "unittest20-e1.aqd-unittest.ms.com",
                   "--grn", "grn:/ms/ei/aquilon/unittest"]
        out = self.badrequesttest(command)
        self.matchoutput(out,
                         "Alias alias2host-bad-target.aqd-unittest.ms.com "
                         "depends on DNS Record "
                         "unittest20-e1.aqd-unittest.ms.com. "
                         "It conflicts with GRN grn:/ms/ei/aquilon/unittest: "
                         "DNS Record unittest20-e1.aqd-unittest.ms.com is "
                         "already be used by the interfaces "
                         "unittest20.aqd-unittest.ms.com/eth1. GRN should not "
                         "be set but derived from the device.",
                         command)

    def test_900_ib_alias(self):
        mh = MockHub(self)

        mh.add_dns_domain('test-infoblox.cc', restricted=False)
        mh.add_network()

        for dns_environment in ['internal', 'external']:
            mh.add_address("alias-target-1.test-infoblox.cc", "10.25.0.1", dns_environment=dns_environment)
            mh.add_address("alias-target-2.test-infoblox.cc", "10.25.0.2", dns_environment=dns_environment)

            command = ['add_alias',
                       '--fqdn', 'alias-fqdn.test-infoblox.cc',
                       '--target', 'alias-target-1.test-infoblox.cc',
                       '--dns_environment', dns_environment] + self.valid_just_tcm

            if dns_environment == 'internal':
                ib_expect_add_alias("alias-fqdn.test-infoblox.cc", "alias-target-1.test-infoblox.cc",
                                    justification=self.valid_justification, fail=True)
                self.iberrortest(command)
                ib_expect_add_alias("alias-fqdn.test-infoblox.cc", "alias-target-1.test-infoblox.cc",
                                    justification=self.valid_justification)
            self.noouttest(command)

            command = ['update_alias',
                       '--fqdn', 'alias-fqdn.test-infoblox.cc',
                       '--ttl', 100,
                       '--dns_environment', dns_environment] + self.valid_just_tcm
            if dns_environment == 'internal':
                ib_expect_update_alias("alias-fqdn.test-infoblox.cc", target="alias-target-1.test-infoblox.cc", ttl=100,
                                       justification=self.valid_justification, fail=True)
                self.iberrortest(command)
                ib_expect_update_alias("alias-fqdn.test-infoblox.cc", target="alias-target-1.test-infoblox.cc", ttl=100,
                                       justification=self.valid_justification)
            self.noouttest(command)

            command = ['update_alias',
                       '--fqdn', 'alias-fqdn.test-infoblox.cc',
                       '--comments', 'check no IB request',
                       '--dns_environment', dns_environment] + self.valid_just_tcm
            self.noouttest(command)

            command = ['del_alias',
                       '--fqdn', 'alias-fqdn.test-infoblox.cc',
                       '--dns_environment', dns_environment] + self.valid_just_tcm
            if dns_environment == 'internal':
                ib_expect_del_alias("alias-fqdn.test-infoblox.cc", justification=self.valid_justification, fail=True)
                self.iberrortest(command)
                ib_expect_del_alias("alias-fqdn.test-infoblox.cc", justification=self.valid_justification)
            self.noouttest(command)

            self.dsdb_verify(empty=True)
            self.ib_verify(False if dns_environment == "internal" else True)

            mh.delete_address("alias-target-1.test-infoblox.cc", "10.25.0.1", dns_environment=dns_environment)

        mh.delete()


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAddAlias)
    unittest.TextTestRunner(verbosity=2).run(suite)
