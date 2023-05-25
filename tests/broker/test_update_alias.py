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
"""Module for testing the update archetype command."""

import unittest
import json

if __name__ == "__main__":
    from broker import utils
    utils.import_depends()

from broker.brokertest import TestBrokerCommand
from eventstest import EventsTestMixin


class TestUpdateAlias(EventsTestMixin, TestBrokerCommand):

    def test_100_update(self):
        command = ["update", "alias",
                   "--fqdn", "alias2host.aqd-unittest.ms.com",
                   "--target", "arecord14.aqd-unittest.ms.com"]
        self.noouttest(command)

    def test_105_update_self(self):
        command = ["update_alias",
                   "--fqdn", "alias2alias.aqd-unittest.ms.com",
                   "--target", "alias2alias.aqd-unittest.ms.com"]
        out = self.badrequesttest(command)
        self.matchoutput(out,
                         "Cannot alias alias2alias.aqd-unittest.ms.com "
                         "to itself",
                         command)

    def test_105_update_mutual(self):
        command = ["update_alias",
                   "--fqdn", "alias2alias.aqd-unittest.ms.com",
                   "--target", "alias4alias.aqd-unittest.ms.com"]
        out = self.badrequesttest(command)
        self.matchoutput(out,
                         "Cannot alias alias2alias.aqd-unittest.ms.com to "
                         "alias4alias.aqd-unittest.ms.com, as that is an "
                         "alias of alias2alias.aqd-unittest.ms.com",
                         command)

    def test_110_update_mscom(self):
        self.event_upd_dns(
            fqdn='alias.ms.com',
            dns_environment='internal',
            dns_records=[
                {
                    'target': 'arecord14.aqd-unittest.ms.com',
                    'targetEnvironmentName': 'internal',
                    'rrtype': 'CNAME'
                },
            ],
        )
        command = ["update", "alias", "--fqdn", "alias.ms.com",
                   "--target", "arecord14.aqd-unittest.ms.com",
                   "--comments", "New alias comments"]
        self.dsdb_expect("update_host_alias "
                         "-alias alias.ms.com "
                         "-new_host arecord14.aqd-unittest.ms.com "
                         "-new_comments New alias comments")
        self.noouttest(command)
        self.dsdb_verify()
        self.events_verify()

    def test_200_missing_target(self):
        command = ["update", "alias",
                   "--fqdn", "alias2host.aqd-unittest.ms.com",
                   "--target", "no-such-name.aqd-unittest.ms.com"]
        out = self.notfoundtest(command)
        self.matchoutput(out,
                         "Target FQDN no-such-name.aqd-unittest.ms.com "
                         "does not exist in DNS environment internal.",
                         command)

    def test_210_not_an_alias(self):
        command = ["update", "alias",
                   "--fqdn", "arecord13.aqd-unittest.ms.com",
                   "--target", "arecord14.aqd-unittest.ms.com"]
        out = self.notfoundtest(command)
        self.matchoutput(out,
                         "Alias arecord13.aqd-unittest.ms.com not found.",
                         command)

    def test_211_non_restricted_alias_to_restricted(self):
        fqdn = "alias2alias.aqd-unittest.ms.com"
        cmd = ["update", "alias", "--fqdn", fqdn,
               "--target", "target.restrict.aqd-unittest.ms.com"]
        out = self.badrequesttest(cmd)
        self.matchoutput(out,
                         "Cannot update alias {0} because the "
                         "value of the restricted flag does not "
                         "match between old and new DNS domains"
                         .format(fqdn), cmd)

    def test_300_verify_alias(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "alias2host.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out, "Target: arecord14.aqd-unittest.ms.com", command)

    def test_301_verify_alias_json_data(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "alias2host.aqd-unittest.ms.com", "--format",
                   "json"]
        out = self.commandtest(command)
        expected = [
            {
                "record_type": "alias",
                "fqdn": "alias2host.aqd-unittest.ms.com",
                "dns_environment": "internal",
                "aliases": ["alias2alias.aqd-unittest.ms.com",
                            "alias3alias.aqd-unittest.ms.com",
                            "alias4alias.aqd-unittest.ms.com"],
                "target": "arecord14.aqd-unittest.ms.com"
            }
        ]
        self.assertEqual(json.loads(out), expected)

    def test_310_verify_mscom(self):
        command = ["search", "dns", "--fullinfo", "--fqdn", "alias.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out, "Target: arecord14.aqd-unittest.ms.com", command)
        self.matchoutput(out, "Comments: New alias comments", command)

    def test_311_verify_mscom_json(self):
        command = ["search", "dns", "--fullinfo", "--fqdn", "alias.ms.com",
                   "--format", "json"]
        out = self.commandtest(command)
        expected = [
            {
                "record_type": "alias",
                "fqdn": "alias.ms.com",
                "dns_environment": "internal",
                "target": "arecord14.aqd-unittest.ms.com",
                "comments": "New alias comments"
            }
        ]
        self.assertEqual(json.loads(out), expected)

    def test_320_verify_oldtarget(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "arecord13.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchclean(out, "alias2host.aqd-unittest.ms.com", command)
        self.matchclean(out, "alias.ms.com", command)

    def test_330_verify_newtarget(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "arecord14.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out, "Aliases: alias.ms.com, "
                         "alias2alias.aqd-unittest.ms.com, "
                         "alias2host.aqd-unittest.ms.com", command)

    def test_331_verify_newtarget_json(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "arecord14.aqd-unittest.ms.com", "--format",
                   "json"]
        out = self.commandtest(command)
        expected = [
            {
                "record_type": "a_record",
                "fqdn": "arecord14.aqd-unittest.ms.com",
                "dns_environment": "internal",
                "address_aliases": ["addralias1.aqd-unittest.ms.com", "addralias3.aqd-unittest.ms.com"],
                "network": "unknown0",
                "ip": "4.2.1.19",
                "netmask": "4.2.1.0/26",
                "network_environment": "internal",
                "aliases": ["alias.ms.com", "alias2alias.aqd-unittest.ms.com",
                            "alias2host.aqd-unittest.ms.com", "alias3alias.aqd-unittest.ms.com",
                            "alias4alias.aqd-unittest.ms.com"],
                "eon_id": 2,
                "reverse_ptr": "arecord13.aqd-unittest.ms.com"
            }
        ]
        self.assertEqual(json.loads(out), expected)

    def test_400_repoint_restrict1(self):
        command = ["update", "alias", "--fqdn", "restrict1.aqd-unittest.ms.com",
                   "--target", "target2.restrict.aqd-unittest.ms.com"]
        out = self.statustest(command)
        self.matchoutput(out,
                         "WARNING: Will create a reference to "
                         "target2.restrict.aqd-unittest.ms.com, but ",
                         command)

    def test_410_verify_target(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "target.restrict.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.searchoutput(out, r'Aliases: restrict2.aqd-unittest.ms.com$',
                          command)

    def test_410_verify_target2(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "target2.restrict.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.searchoutput(out, r'Aliases: restrict1.aqd-unittest.ms.com$',
                          command)

    def test_420_repoint_restrict2(self):
        command = ["update", "alias", "--fqdn", "restrict2.aqd-unittest.ms.com",
                   "--target", "target2.restrict.aqd-unittest.ms.com"]
        self.noouttest(command)

    def test_430_verify_target_gone(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "target.restrict.aqd-unittest.ms.com"]
        self.notfoundtest(command)

    def test_430_verify_target2(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "target2.restrict.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out,
                         "Aliases: restrict1.aqd-unittest.ms.com, "
                         "restrict2.aqd-unittest.ms.com",
                         command)

    def test_431_verify_target2_json(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "target2.restrict.aqd-unittest.ms.com",
                   "--format", "json"]
        out = self.commandtest(command)
        expected = [
            {
                "record_type": "dns_record",
                "fqdn": "target2.restrict.aqd-unittest.ms.com",
                "dns_environment": "internal",
                "aliases": ["restrict1.aqd-unittest.ms.com",
                            "restrict2.aqd-unittest.ms.com"]
            }
        ]
        self.assertEqual(json.loads(out), expected)

    def test_432_restricted_alias_to_non_restricted(self):
        fqdn = "restrict1.aqd-unittest.ms.com"
        cmd = ["update", "alias", "--fqdn", fqdn,
               "--target", "arecord14.aqd-unittest.ms.com"]
        out = self.badrequesttest(cmd)
        self.matchoutput(out,
                         "Cannot update alias {0} because the "
                         "value of the restricted flag does not "
                         "match between old and new DNS domains"
                         .format(fqdn), cmd)

    def test_500_repoint2diff_environment_fail(self):
        command = ["update", "alias",
                   "--fqdn", "alias2host.aqd-unittest-ut-env.ms.com",
                   "--dns_environment", "ut-env",
                   "--target", "alias13.aqd-unittest.ms.com",
                   "--target_environment", "ut-env"]
        out = self.badrequesttest(command)
        self.matchoutput(out, "Please provide valid "
                              "justification number",
                         command)

    def test_500_repoint2diff_environment(self):
        command = ["update", "alias",
                   "--fqdn", "alias2host.aqd-unittest-ut-env.ms.com",
                   "--dns_environment", "ut-env",
                   "--target", "alias13.aqd-unittest.ms.com",
                   "--target_environment", "ut-env"] \
                  + self.valid_just_sn
        self.noouttest(command)

    def test_505_verify_alias_repoint2diff_environment(self):
        command = ["show", "alias",
                   "--fqdn", "alias2host.aqd-unittest-ut-env.ms.com",
                   "--dns_environment", "ut-env"]
        out = self.commandtest(command)

        self.matchoutput(out, "Alias: alias2host.aqd-unittest-ut-env.ms.com", command)
        self.matchoutput(out, "Target: alias13.aqd-unittest.ms.com", command)
        self.matchoutput(out, "DNS Environment: ut-env", command)

    def test_600_update_ttl(self):
        command = ["update", "alias",
                   "--fqdn", "alias2alias.aqd-unittest.ms.com",
                   "--ttl", 120]
        self.noouttest(command)

    def test_620_verify_update_ttl(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "alias2alias.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out, "Alias: alias2alias.aqd-unittest.ms.com", command)
        self.matchoutput(out, "TTL: 120", command)

    def test_621_verify_update_ttl_json(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "alias2alias.aqd-unittest.ms.com",
                   "--format", "json"]
        out = self.commandtest(command)
        expected = [
            {
                "record_type": "alias",
                "fqdn": "alias2alias.aqd-unittest.ms.com",
                "dns_environment": "internal",
                "target": "alias2host.aqd-unittest.ms.com",
                "aliases": ["alias3alias.aqd-unittest.ms.com", "alias4alias.aqd-unittest.ms.com"],
                "ttl": 120
            }
        ]
        self.assertEqual(json.loads(out), expected)

    def test_700_remove_ttl(self):
        command = ["update", "alias",
                   "--fqdn", "alias2alias.aqd-unittest.ms.com",
                   "--clear_ttl"]
        self.noouttest(command)

    def test_720_verify_remove_ttl(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "alias2alias.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchclean(out, "TTL", command)

    def test_800_update_grn(self):
        command = ["update", "alias",
                   "--fqdn", "alias2host-grn.aqd-unittest.ms.com",
                   "--grn", "grn:/ms/ei/aquilon/unittest"]
        self.noouttest(command)

    def test_805_verify_update_grn(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "alias2host-grn.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out, "Owned by GRN: grn:/ms/ei/aquilon/unittest",
                         command)

    def test_810_update_eon_id(self):
        command = ["update", "alias",
                   "--fqdn", "alias3alias.aqd-unittest.ms.com",
                   "--eon_id", "2"]
        self.noouttest(command)

    def test_815_verify_update_eon_id(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "alias3alias.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out, "Owned by GRN: grn:/ms/ei/aquilon/aqd",
                         command)

    def test_815_verify_update_eon_id_json(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "alias3alias.aqd-unittest.ms.com",
                   "--format", "json"]
        out = self.commandtest(command)
        expected = [
            {
                "record_type": "alias",
                "fqdn": "alias3alias.aqd-unittest.ms.com",
                "dns_environment": "internal",
                "aliases": ["alias4alias.aqd-unittest.ms.com"],
                "target": "alias2alias.aqd-unittest.ms.com",
                "eon_id": 2
            }
        ]
        self.assertEqual(json.loads(out), expected)

    def test_816_grn_conflict_with_multi_level_alias(self):
        command = ["update", "alias",
                   "--fqdn", "alias2alias.aqd-unittest.ms.com",
                   "--target", "unittest00.one-nyp.ms.com"]
        out = self.badrequesttest(command)
        self.matchoutput(out,
                         "Alias alias2alias.aqd-unittest.ms.com "
                         "is assoicated with GRN grn:/ms/ei/aquilon/aqd. "
                         "It conflicts with target "
                         "DNS Record unittest00.one-nyp.ms.com: "
                         "DNS Record unittest00.one-nyp.ms.com is a "
                         "primary name. GRN should not be set but derived "
                         "from the device.",
                         command)

    def test_820_clear_grn(self):
        command = ["update", "alias",
                   "--fqdn", "alias3alias.aqd-unittest.ms.com",
                   "--clear_grn"]
        self.noouttest(command)

    def test_825_verify_clear_grn(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "alias3alias.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchclean(out, "Owned by GRN:", command)

    def test_830_update_grn_conflict(self):
        command = ["add", "alias",
                   "--fqdn", "temp-alias.aqd-unittest.ms.com",
                   "--target", "unittest00.one-nyp.ms.com"]
        self.noouttest(command)

        command = ["update", "alias",
                   "--fqdn", "temp-alias.aqd-unittest.ms.com",
                   "--grn", "grn:/ms/ei/aquilon/aqd"]
        out = self.badrequesttest(command)
        self.matchoutput(out,
                         "Alias temp-alias.aqd-unittest.ms.com depends on "
                         "DNS Record unittest00.one-nyp.ms.com. "
                         "It conflicts with GRN grn:/ms/ei/aquilon/aqd: "
                         "DNS Record unittest00.one-nyp.ms.com is a "
                         "primary name. GRN should not be set but derived "
                         "from the device.",
                         command)

        command = ["del", "alias",
                   "--fqdn", "temp-alias.aqd-unittest.ms.com"]
        self.noouttest(command)

    def test_835_grn_conflict_with_primary_name(self):
        command = ["update", "alias",
                   "--fqdn", "alias2host-grn.aqd-unittest.ms.com",
                   "--target", "unittest00.one-nyp.ms.com"]
        out = self.badrequesttest(command)
        self.matchoutput(out,
                         "Alias alias2host-grn.aqd-unittest.ms.com "
                         "is assoicated with GRN grn:/ms/ei/aquilon/unittest. "
                         "It conflicts with target "
                         "DNS Record unittest00.one-nyp.ms.com: "
                         "DNS Record unittest00.one-nyp.ms.com is a "
                         "primary name. GRN should not be set but derived "
                         "from the device.",
                         command)

    def test_840_grn_conflict_with_service_address(self):
        command = ["update", "alias",
                   "--fqdn", "alias2host-grn.aqd-unittest.ms.com",
                   "--target", "zebra2.aqd-unittest.ms.com"]
        out = self.badrequesttest(command)
        self.matchoutput(out,
                         "Alias alias2host-grn.aqd-unittest.ms.com "
                         "is assoicated with GRN grn:/ms/ei/aquilon/unittest. "
                         "It conflicts with target "
                         "DNS Record zebra2.aqd-unittest.ms.com: "
                         "DNS Record zebra2.aqd-unittest.ms.com is a "
                         "service address. GRN should not be set but derived "
                         "from the device.",
                         command)

    def test_850_grn_conflict_with_interface_name(self):
        command = ["update", "alias",
                   "--fqdn", "alias2host-grn.aqd-unittest.ms.com",
                   "--target", "unittest20-e1.aqd-unittest.ms.com"]
        out = self.badrequesttest(command)
        self.matchoutput(out,
                         "Alias alias2host-grn.aqd-unittest.ms.com "
                         "is assoicated with GRN grn:/ms/ei/aquilon/unittest. "
                         "It conflicts with target "
                         "DNS Record unittest20-e1.aqd-unittest.ms.com: "
                         "DNS Record unittest20-e1.aqd-unittest.ms.com is "
                         "already be used by the interfaces "
                         "unittest20.aqd-unittest.ms.com/eth1. "
                         "GRN should not be set but derived from the device.",
                         command)

    def test_900_add_deep_alias(self):
        # Create alias with max depth
        cmd = ['add', 'alias', '--fqdn', 'test.aqd-unittest.ms.com',
               '--target', 'arecord13.aqd-unittest.ms.com']
        self.noouttest(cmd)
        cmd = ['add', 'alias', '--fqdn', 'test2.aqd-unittest.ms.com',
               '--target', 'test.aqd-unittest.ms.com']
        self.noouttest(cmd)
        cmd = ['add', 'alias', '--fqdn', 'test3.aqd-unittest.ms.com',
               '--target', 'test2.aqd-unittest.ms.com']
        self.noouttest(cmd)
        cmd = ['add', 'alias', '--fqdn', 'test4.aqd-unittest.ms.com',
               '--target', 'test3.aqd-unittest.ms.com']
        self.noouttest(cmd)
        # Create alias with depth 1
        cmd = ['add', 'alias', '--fqdn', 'testtest.aqd-unittest.ms.com',
               '--target', 'arecord13.aqd-unittest.ms.com']
        self.noouttest(cmd)

        # Create alias with depth 2
        cmd = ['add', 'alias', '--fqdn', 'testtest1.aqd-unittest.ms.com',
               '--target', 'arecord13.aqd-unittest.ms.com']
        self.noouttest(cmd)
        cmd = ['add', 'alias', '--fqdn', 'testtest2.aqd-unittest.ms.com',
               '--target', 'testtest1.aqd-unittest.ms.com']
        self.noouttest(cmd)

        # Create alias with depth 3
        cmd = ['add', 'alias', '--fqdn', 'testtest3.aqd-unittest.ms.com',
               '--target', 'arecord13.aqd-unittest.ms.com']
        self.noouttest(cmd)
        cmd = ['add', 'alias', '--fqdn', 'testtest4.aqd-unittest.ms.com',
               '--target', 'testtest3.aqd-unittest.ms.com']
        self.noouttest(cmd)
        cmd = ['add', 'alias', '--fqdn', 'testtest5.aqd-unittest.ms.com',
               '--target', 'testtest4.aqd-unittest.ms.com']
        self.noouttest(cmd)

    def test_910_update_alias_target_deep_alias_1(self):
        command = ['update', 'alias', '--fqdn', 'testtest1.aqd-unittest.ms.com',
                   '--target', 'testtest5.aqd-unittest.ms.com']
        out = self.badrequesttest(command)
        self.matchoutput(out,
                         "Maximum alias depth would be exceeded - "
                         "new target is an alias.",
                         command)

    def test_910_update_alias_target_deep_alias_2(self):
        command = ['update', 'alias', '--fqdn', 'testtest.aqd-unittest.ms.com',
                   '--target', 'test4.aqd-unittest.ms.com']
        out = self.badrequesttest(command)
        self.matchoutput(out,
                         "Maximum alias depth would be exceeded - "
                         "new target is an alias.",
                         command)

    def test_910_update_alias_target_deep_alias_3(self):
        command = ['update', 'alias', '--fqdn', 'test.aqd-unittest.ms.com',
                   '--target', 'testtest.aqd-unittest.ms.com']
        out = self.badrequesttest(command)
        self.matchoutput(out,
                         "Maximum alias depth would be exceeded - "
                         "new target is an alias.",
                         command)

    def test_920_delete_deep_alias(self):
        # Delete alias with max depth
        cmd = ['del', 'alias', '--fqdn', 'test4.aqd-unittest.ms.com']
        self.noouttest(cmd)
        cmd = ['del', 'alias', '--fqdn', 'test3.aqd-unittest.ms.com']
        self.noouttest(cmd)
        cmd = ['del', 'alias', '--fqdn', 'test2.aqd-unittest.ms.com']
        self.noouttest(cmd)
        cmd = ['del', 'alias', '--fqdn', 'test.aqd-unittest.ms.com']
        self.noouttest(cmd)
        # Delete alias with depth 1
        cmd = ['del', 'alias', '--fqdn', 'testtest.aqd-unittest.ms.com']
        self.noouttest(cmd)
        # Delete alias with depth 2
        cmd = ['del', 'alias', '--fqdn', 'testtest2.aqd-unittest.ms.com']
        self.noouttest(cmd)
        cmd = ['del', 'alias', '--fqdn', 'testtest1.aqd-unittest.ms.com']
        self.noouttest(cmd)
        # Delete alias with depth 3
        cmd = ['del', 'alias', '--fqdn', 'testtest5.aqd-unittest.ms.com']
        self.noouttest(cmd)
        cmd = ['del', 'alias', '--fqdn', 'testtest4.aqd-unittest.ms.com']
        self.noouttest(cmd)
        cmd = ['del', 'alias', '--fqdn', 'testtest3.aqd-unittest.ms.com']
        self.noouttest(cmd)


    if __name__ == '__main__':
        suite = unittest.TestLoader().loadTestsFromTestCase(TestUpdateAlias)
        unittest.TextTestRunner(verbosity=2).run(suite)
