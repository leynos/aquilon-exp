#!/usr/bin/env python
# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2023  Contributor
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
"""Module for testing the add dynamic range command."""

from ipaddress import ip_address, IPv4Address
import re
import unittest

from mock_ib_services import ib_expect_add_address, ib_expect_add_range, ib_expect_del_range, ib_expect_show_range

if __name__ == "__main__":
    import utils
    utils.import_depends()

from .brokertest import TestBrokerCommand


class TestUpdateDynamicRange(TestBrokerCommand):
    def test_000_add_networks(self):
        # Add some networks for later tests to use.
        self.net.allocate_network(self, "dyndhcp8", 25, "tor_net2",
                                  "building", "ut")
        self.net.allocate_network(self, "dyndhcp9", 25, "tor_net2",
                                  "building", "ut")

    def test_100_add_range(self):
        # Add a dynamic range with range class "vm", for further tests to update.
        startip = str(self.net["dyndhcp9"].usable[2])
        endip = str(self.net["dyndhcp9"].usable[-3])
        range_class = "vm"

        messages = []
        for ip in range(int(self.net["dyndhcp9"].usable[2]),
                        int(self.net["dyndhcp9"].usable[-3]) + 1):
            address = IPv4Address(ip)
            hostname = self.dynname(address)
            self.dsdb_expect_add(hostname, address)
            messages.append("DSDB: add_host -host_name %s -ip_address %s "
                            "-status aq" % (hostname, address))
            ib_expect_add_address(hostname, str(address), justification=self.valid_justification)

        command = ["add_dynamic_range",
                   "--startip=%s" % startip,
                   "--endip=%s" % endip,
                   "--range_class={}".format(range_class),
                   "--dns_domain=aqd-unittest.ms.com"] + self.valid_just_tcm
        err = self.statustest(command)
        for message in messages:
            self.matchoutput(err, message, command)
        self.dsdb_verify()
        self.ib_verify()

        self.assert_range_class(startip, range_class)

    def test_110_update_range_class_to_infoblox(self):
        # Update the range class of an existing range from "vm" to "infoblox_managed".
        startip = str(self.net["dyndhcp9"].usable[2])
        endip = str(self.net["dyndhcp9"].usable[-3])
        range_class = "infoblox_managed"

        # We add the range to Infoblox whenever the range class is changed to infoblox_managed.
        ib_expect_add_range("dynamic-{}-{}".format(startip, endip), startip, endip,
                            justification=self.valid_justification)

        command = ["update_dynamic_range",
            "--ip={}".format(startip),
            "--range_class={}".format(range_class)] + self.valid_just_tcm
        err = self.statustest(command)
        self.ib_verify()

        self.assert_range_class(startip, range_class)

    def test_120_update_range_class_to_vm(self):
        # Update the range class of an existing range back from "infoblox_managed" to "vm".
        startip = str(self.net["dyndhcp9"].usable[2])
        endip = str(self.net["dyndhcp9"].usable[-3])
        range_class = "vm"

        # The code should do a GET to confirm the range exists, for an "infoblox_managed" range:
        ib_expect_show_range(startip, endip)

        # We delete the range in Infoblox whenever the range class is changed from
        # infoblox_managed to something else--"vm", here:
        ib_expect_del_range(startip, endip, justification=self.valid_justification)

        # We're specifying endip as the ip value here arbitrarily, as any IP in the range will do.
        # We used startip in the previous test, so let's mix it up.
        command = ["update_dynamic_range",
                   "--ip={}".format(endip),
                   "--range_class={}".format(range_class)] + self.valid_just_tcm
        err = self.statustest(command)
        self.ib_verify()

        self.assert_range_class(startip, range_class)

    def test_130_fail_not_a_dynamic_range(self):
        # Show that changing a range class for an IP not in a dynamic range fails
        ip = str(self.net["dyndhcp8"].usable[2])
        range_class = "infoblox_managed"

        command = ["update_dynamic_range",
                   "--ip={}".format(ip),
                   "--range_class={}".format(range_class)
                   ] + self.valid_just_tcm
        out, err = self.failuretest(command, 4)

        self.searchoutput(err, r"Not Found: {} is not part of a dynamic range".format(ip), " ".join(command))

    def test_140_fail_no_range_class_change(self):
        # Show that specifying the same range class as the class of a current dynamic range fails
        ip = str(self.net["dyndhcp9"].usable[2])
        range_class = "vm"

        command = ["update_dynamic_range",
                   "--ip={}".format(ip),
                   "--range_class={}".format(range_class)
                   ] + self.valid_just_tcm
        out, err = self.failuretest(command, 4)

        self.searchoutput(err, r"The range class of this range is already vm", " ".join(command))

    def test_150_update_range_class_to_infoblox(self):
        # Update the range class of an existing range from "vm" to "infoblox_managed", needed for the next test.
        startip = str(self.net["dyndhcp9"].usable[2])
        endip = str(self.net["dyndhcp9"].usable[-3])
        range_class = "infoblox_managed"

        ib_expect_add_range("dynamic-{}-{}".format(startip, endip), startip, endip,
                            justification=self.valid_justification)

        # Pick an IP in the middle of the range to test against this time
        ip = str(ip_address(int(self.net["dyndhcp9"].usable[2]) + 42))

        command = ["update_dynamic_range",
            "--ip={}".format(ip),
            "--range_class={}".format(range_class)] + self.valid_just_tcm
        err = self.statustest(command)
        self.ib_verify()

        self.assert_range_class(startip, range_class)

    def test_160_fail_update_range_not_in_infoblox(self):
        # Show that if the range is missing from Infoblox, that the update fails
        startip = str(self.net["dyndhcp9"].usable[2])
        endip = str(self.net["dyndhcp9"].usable[-3])
        range_class = "vm"

        ib_expect_show_range(startip, endip, response_code=404, fail=True)

        command = ["update_dynamic_range",
                   "--ip={}".format(endip),
                   "--range_class={}".format(range_class)] + self.valid_just_tcm
        out, err = self.failuretest(command, 5)

        self.searchoutput(err, r"(404 Not Found)", " ".join(command))

    def assert_range_class(self, ip, range_class):
        # Assert that the range including <ip> has the specified range class
        command = ["show_dynamic_range", "--ip=%s" % ip]
        out, err = self.successtest(command)

        self.searchoutput(out, r"Range Class: {}".format(range_class), " ".join(command))


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAddDynamicRange)
    unittest.TextTestRunner(verbosity=2).run(suite)

