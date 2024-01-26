#!/usr/bin/env python
# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2015,2016  Contributor
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
"""Module for testing the update address alias command."""

import unittest
import json

if __name__ == '__main__':
    import utils
    utils.import_depends()

from .brokertest import TestBrokerCommand

from mock_ib_services import ib_expect_update_a

class TestUpdateAddressAlias(TestBrokerCommand):

    def test_100_update_to_add_comment_fail(self):
        command = ["update", "address", "alias",
                   "--fqdn", "addralias1.aqd-unittest.ms.com",
                   "--target", "arecord13.aqd-unittest.ms.com",
                   "--ttl", "900",
                   "--comments", "New address alias comments"]
        out = self.badoptiontest(command)
        self.matchoutput(out, "Not all mandatory options specified!", command)

    def test_101_update_to_add_comment(self):
        ib_expect_update_a("addralias1.aqd-unittest.ms.com", original_ip="4.2.1.18", new_ttl=900,
                           justification=self.just_sn)
        command = ["update", "address", "alias",
                   "--fqdn", "addralias1.aqd-unittest.ms.com",
                   "--target", "arecord13.aqd-unittest.ms.com",
                   "--ttl", "900",
                   "--comments", "New address alias comments"] \
                  + self.valid_just_sn
        self.noouttest(command)
        self.ib_verify()

    def test_120_verify_add_comment(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "addralias1.aqd-unittest.ms.com",
                   "--target", "arecord13.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out, "Comments: New address alias comments", command)
        self.matchoutput(out, "TTL: 900", command)

    def test_121_verify_add_comment_json_data(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "addralias1.aqd-unittest.ms.com",
                   "--target", "arecord13.aqd-unittest.ms.com",
                   "--format", "json"]
        out = self.commandtest(command)
        expected = [
            {
                "record_type": "address_alias",
                "fqdn": "addralias1.aqd-unittest.ms.com",
                "dns_environment": "internal",
                "target": "arecord13.aqd-unittest.ms.com",
                "comments": "New address alias comments",
                "ip": "4.2.1.18",
                "ttl": 900
            }
        ]
        self.assertEqual(json.loads(out), expected)

    def test_130_update_to_change_comment(self):
        command = ["update", "address", "alias",
                   "--fqdn", "addralias1.aqd-unittest.ms.com",
                   "--target", "arecord14.aqd-unittest.ms.com",
                   "--comments", "New other address alias comments"] \
                  + self.valid_just_sn
        self.noouttest(command)

    def test_140_verify_update_to_change_comment(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "addralias1.aqd-unittest.ms.com",
                   "--target", "arecord14.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out, "Comments: New other address alias comments", command)

    def test_141_verify_update_to_change_comment_json_data(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "addralias1.aqd-unittest.ms.com",
                   "--target", "arecord14.aqd-unittest.ms.com",
                   "--format", "json"]
        out = self.commandtest(command)
        expected = [
            {
                "record_type": "address_alias",
                "fqdn": "addralias1.aqd-unittest.ms.com",
                "dns_environment": "internal",
                "target": "arecord14.aqd-unittest.ms.com",
                "ip": "4.2.1.19",
                "comments": "New other address alias comments",
                "ttl": 1800
            }
        ]
        self.assertEqual(json.loads(out), expected)

    def test_150_update_to_no_comment(self):
        command = ["update", "address", "alias",
                   "--fqdn", "addralias1.aqd-unittest.ms.com",
                   "--target", "arecord14.aqd-unittest.ms.com",
                   "--comments", ""] + self.valid_just_sn
        self.noouttest(command)

    def test_160_verify_update_to_no_comment(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "addralias1.aqd-unittest.ms.com",
                   "--target", "arecord14.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchclean(out, "Comments:", command)

    def test_161_verify_update_to_no_comment_json(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "addralias1.aqd-unittest.ms.com",
                   "--target", "arecord14.aqd-unittest.ms.com",
                   "--format", "json"]
        out = self.commandtest(command)
        self.matchclean(out, '"comments":" "', command)

    def test_162_verify_update_to_no_comment_json_data(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "addralias1.aqd-unittest.ms.com",
                   "--target", "arecord14.aqd-unittest.ms.com",
                   "--format", "json"]
        out = self.commandtest(command)
        expected = [
            {
                "record_type": "address_alias",
                "fqdn": "addralias1.aqd-unittest.ms.com",
                "dns_environment": "internal",
                "target": "arecord14.aqd-unittest.ms.com",
                "ip": "4.2.1.19",
                "ttl": 1800
            }
        ]
        self.assertEqual(json.loads(out), expected)

    def test_170_update_to_no_ttl(self):
        command = ["update", "address", "alias",
                   "--fqdn", "addralias1.aqd-unittest.ms.com",
                   "--target", "arecord14.aqd-unittest.ms.com",
                   "--clear_ttl"] + self.valid_just_sn
        self.noouttest(command)

    def test_175_verify_update_to_no_ttl(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "addralias1.aqd-unittest.ms.com",
                   "--target", "arecord14.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchclean(out, "TTL", command)

    def test_200_update_nonexistent_fqdn(self):
        command = ["update", "address", "alias",
                   "--fqdn", "nonexistent.aqd-unittest.ms.com",
                   "--target", "arecord14.aqd-unittest.ms.com",
                   "--comments", "nonexistent alias"] \
                  + self.valid_just_sn
        out = self.notfoundtest(command)
        self.matchoutput(out,
                         "Fqdn nonexistent, DNS environment internal, "
                         "DNS domain aqd-unittest.ms.com not found.",
                         command)

    def test_230_update_nonexistent_address_alias(self):
        command = ["update", "address", "alias",
                   "--fqdn", "arecord13.aqd-unittest.ms.com",
                   "--target", "arecord14.aqd-unittest.ms.com",
                   "--comments", "nonexistent alias"] \
                  + self.valid_just_sn
        out = self.notfoundtest(command)
        self.matchoutput(out,
                         "Address Alias arecord13.aqd-unittest.ms.com, "
                         "fqdn arecord14.aqd-unittest.ms.com not found.",
                         command)

    def test_250_update_nonexistent_target(self):
        command = ["update", "address", "alias",
                   "--fqdn", "addralias1.aqd-unittest.ms.com",
                   "--target", "nonexistent.aqd-unittest.ms.com",
                   "--comments", "nonexistent target"] \
                  + self.valid_just_sn
        out = self.notfoundtest(command)
        self.matchoutput(out,
                         "Fqdn nonexistent, DNS environment internal, "
                         "DNS domain aqd-unittest.ms.com not found.",
                         command)

    def test_300_update_grn(self):
        command = ["update", "address", "alias",
                   "--fqdn", "addralias3.aqd-unittest.ms.com",
                   "--grn", "grn:/ms/ei/aquilon/unittest"] \
                  + self.valid_just_sn
        self.noouttest(command)

    def test_305_verify_grn(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "addralias3.aqd-unittest.ms.com",
                   "--target", "arecord13.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out,
                         "Owned by GRN: grn:/ms/ei/aquilon/unittest",
                         command)

        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "addralias3.aqd-unittest.ms.com",
                   "--target", "arecord14.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out,
                         "Owned by GRN: grn:/ms/ei/aquilon/unittest",
                         command)

    def test_310_clear_grn(self):
        command = ["update", "address", "alias",
                   "--fqdn", "addralias3.aqd-unittest.ms.com",
                   "--clear_grn"] + self.valid_just_sn
        self.noouttest(command)

    def test_315_verify_clear_grn(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "addralias3.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchclean(out, "Owned by GRN:", command)

    def test_316_verify_clear_grn_json(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "addralias3.aqd-unittest.ms.com",
                   "--format", "json"]
        out = self.commandtest(command)
        self.matchclean(out, '"eon_id": ', command)

    def test_320_update_eon_id(self):
        command = ["update", "address", "alias",
                   "--fqdn", "addralias3.aqd-unittest.ms.com",
                   "--eon_id", "2"] + self.valid_just_sn
        self.noouttest(command)

    def test_325_verify_eon_id(self):
        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "addralias3.aqd-unittest.ms.com",
                   "--target", "arecord13.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out,
                         "Owned by GRN: grn:/ms/ei/aquilon/aqd",
                         command)

        command = ["search", "dns", "--fullinfo",
                   "--fqdn", "addralias3.aqd-unittest.ms.com",
                   "--target", "arecord14.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out,
                         "Owned by GRN: grn:/ms/ei/aquilon/aqd",
                         command)

    def test_330_update_grn_with_target(self):
        command = ["update", "address", "alias",
                   "--fqdn", "addralias3.aqd-unittest.ms.com",
                   "--target", "arecord14.aqd-unittest.ms.com",
                   "--eon_id", "2"] + self.valid_just_sn
        out = self.badoptiontest(command)
        self.matchoutput(out,
                         "Option or option group eon_id conflicts with target",
                         command)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUpdateAddressAlias)
    unittest.TextTestRunner(verbosity=2).run(suite)
