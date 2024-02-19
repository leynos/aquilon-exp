#!/usr/bin/env python
# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2009,2010,2011,2012,2013,2015,2016,2017,2018  Contributor
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
"""Module for testing the del address command."""

import unittest

from mock_ib_services import ib_expect_del_address

if __name__ == "__main__":
    from . import utils
    utils.import_depends()

from .brokertest import TestBrokerCommand


class TestDelAddress(TestBrokerCommand):

    def testbasic(self):
        self.dsdb_expect_delete(self.net["unknown0"].usable[13])
        ib_expect_del_address("arecord13.aqd-unittest.ms.com", self.net["unknown0"].usable[13],
                              justification=self.valid_justification)
        command = ["del_address", "--ip=%s" % self.net["unknown0"].usable[13]] + self.valid_just_tcm
        self.noouttest(command)
        self.dsdb_verify()
        self.ib_verify()

    def testverifybasic(self):
        command = ["show_address", "--fqdn=arecord13.aqd-unittest.ms.com"]
        self.notfoundtest(command)

    def testbasicipv6(self):
        command = ["del_address", "--ip=%s" % self.net["ipv6_test"].usable[1]] + self.valid_just_tcm
        exclude_err_str = "IP not valid for IBServices:  if supplied, it must be an IPv4Address object or correctly formatted IPv4 string.\n"
        self.noouttest(command, exclude_err_str=exclude_err_str)
        self.dsdb_verify(empty=True)
        self.ib_verify(empty=True)

    def testverifybasicipv6(self):
        command = ["show_address", "--fqdn=ipv6test.aqd-unittest.ms.com"]
        self.notfoundtest(command)

    def testdefaultenv(self):
        self.dsdb_expect_delete(self.net["unknown0"].usable[14])
        ib_expect_del_address("arecord14.aqd-unittest.ms.com", self.net["unknown0"].usable[14],
                              justification=self.valid_justification)
        default = self.config.get("site", "default_dns_environment")
        command = ["del_address", "--fqdn", "arecord14.aqd-unittest.ms.com",
                   "--dns_environment", default] + self.valid_just_tcm
        self.noouttest(command)
        self.dsdb_verify()
        self.ib_verify()

    def testverifydefaultenv(self):
        command = ["show_address", "--fqdn=arecord14.aqd-unittest.ms.com"]
        self.notfoundtest(command)

    def testutenvenv(self):
        command = ["del_address", "--ip", self.net["unknown1"].usable[14],
                   "--fqdn", "arecord14.aqd-unittest.ms.com",
                   "--dns_environment", "ut-env"] + self.valid_just_tcm
        self.noouttest(command)

    def testverifyutenvenv(self):
        command = ["show_address", "--fqdn", "arecord14.aqd-unittest.ms.com",
                   "--dns_environment", "ut-env"]
        self.notfoundtest(command)

    def testbadip(self):
        ip = self.net["unknown0"].usable[14]
        command = ["del_address", "--ip", ip,
                   "--fqdn=arecord15.aqd-unittest.ms.com"] + self.valid_just_tcm
        out = self.notfoundtest(command)
        self.matchoutput(out, "DNS Record arecord15.aqd-unittest.ms.com, ip "
                         "%s not found." % ip, command)
        self.dsdb_verify(empty=True)
        self.ib_verify(empty=True)

    def testcleanup(self):
        self.dsdb_expect_delete(self.net["unknown0"].usable[15])
        ib_expect_del_address("arecord15.aqd-unittest.ms.com", self.net["unknown0"].usable[15],
                              justification=self.valid_justification)
        command = ["del_address", "--ip=%s" % self.net["unknown0"].usable[15],
                   "--fqdn=arecord15.aqd-unittest.ms.com"] + self.valid_just_tcm
        self.noouttest(command)
        self.dsdb_verify()
        self.ib_verify()

    def testfailbadenv(self):
        command = ["del_address", "--ip=%s" % self.net["unknown0"].usable[15],
                   "--fqdn=arecord15.aqd-unittest.ms.com",
                   "--dns_environment=environment-does-not-exist"] + self.valid_just_tcm
        out = self.notfoundtest(command)
        self.matchoutput(out,
                         "DNS Environment environment-does-not-exist not found.",
                         command)
        self.dsdb_verify(empty=True)
        self.ib_verify(empty=True)

    def testfailprimary(self):
        ip = self.net["unknown0"].usable[2]
        command = ["del", "address", "--ip", ip, "--fqdn",
                   "unittest00.one-nyp.ms.com"] + self.valid_just_tcm
        out = self.badrequesttest(command)
        self.matchoutput(out,
                         "DNS Record unittest00.one-nyp.ms.com [%s] is the "
                         "primary name of machine unittest00.one-nyp.ms.com, "
                         "therefore it cannot be deleted." % ip,
                         command)
        self.dsdb_verify(empty=True)
        self.ib_verify(empty=True)

    def testfailipinuse(self):
        ip = self.net["unknown0"].usable[3]
        command = ["del", "address", "--ip", ip, "--fqdn",
                   "unittest00-e1.one-nyp.ms.com"] + self.valid_just_tcm
        out = self.badrequesttest(command)
        self.matchoutput(out,
                         "IP address %s is still in use by public interface "
                         "eth1 of machine unittest00.one-nyp.ms.com" % ip,
                         command)
        self.dsdb_verify(empty=True)
        self.ib_verify(empty=True)

    def test_delip_with_network_env(self):
        ip = "192.168.3.1"
        fqdn = "cardenvtest600.aqd-unittest.ms.com"
        command = ["del", "address", "--ip", ip,
                   "--network_environment", "cardenv"] + self.valid_just_tcm
        self.noouttest(command)
        # External IP addresses should not be added to DSDB
        self.dsdb_verify(empty=True)

        command = ["show_address", "--fqdn", fqdn,
                   "--network_environment", "cardenv"]
        self.notfoundtest(command)
        self.dsdb_verify(empty=True)
        self.ib_verify(empty=True)

    def test_delreservedreverse(self):
        self.dsdb_expect_delete(self.net["unknown0"].usable[32])
        ib_expect_del_address("arecord17.aqd-unittest.ms.com", self.net["unknown0"].usable[32],
                              justification=self.valid_justification)
        command = ["del", "address",
                   "--fqdn", "arecord17.aqd-unittest.ms.com"] + self.valid_just_tcm
        self.noouttest(command)
        self.dsdb_verify()
        self.ib_verify()

    def test_verifydelreserve(self):
        command = ["show", "address",
                   "--fqdn", "arecord17.aqd-unittest.ms.com"]
        self.notfoundtest(command)

        command = ["search", "dns", "--record_type", "reserved_name"]
        out = self.commandtest(command)
        self.matchclean(out, "reverse.restrict.aqd-unittest.ms.com", command)
        self.matchclean(out, "reverse2.restrict.aqd-unittest.ms.com", command)

    def test_610_addipfromip_with_network_env(self):
        fqdn = "cardenvtest610.aqd-unittest.ms.com"
        command = ["del", "address", "--fqdn", fqdn,
                   "--network_environment", "cardenv"] + self.valid_just_tcm
        self.noouttest(command)
        # External IP addresses should not be added to DSDB
        self.dsdb_verify(empty=True)

        command = ["show_address", "--fqdn=%s" % fqdn]
        self.notfoundtest(command)

    def test_700_del_address_with_ttl(self):
        fqdn = "arecord40.aqd-unittest.ms.com"
        ip = self.net["unknown0"].usable[40]
        self.dsdb_expect_delete(ip)
        ib_expect_del_address(fqdn, str(ip), justification=self.valid_justification)
        command = ["del", "address", "--ip=%s" % ip] + self.valid_just_tcm
        self.noouttest(command)
        self.dsdb_verify()
        self.ib_verify()

    def test_720_verify_delete_with_ttl(self):
        command = ["show_address", "--fqdn=arecord40.aqd-unittest.ms.com"]
        self.notfoundtest(command)

    def test_800_del_address_with_grn(self):
        fqdn = "arecord50.aqd-unittest.ms.com"
        ip = self.net["unknown0"].usable[50]
        self.dsdb_expect_delete(ip)
        ib_expect_del_address(fqdn, str(ip), justification=self.valid_justification)
        command = ["del", "address", "--ip=%s" % ip] + self.valid_just_tcm
        self.noouttest(command)
        self.dsdb_verify()
        self.ib_verify()

    def test_820_verify_delete_with_grn(self):
        command = ["show_address", "--fqdn=arecord50.aqd-unittest.ms.com"]
        self.notfoundtest(command)

    def test_830_del_address_with_grn(self):
        fqdn = "arecord51.aqd-unittest.ms.com"
        ip = self.net["unknown0"].usable[51]
        self.dsdb_expect_delete(ip)
        ib_expect_del_address(fqdn, str(ip), justification=self.valid_justification)
        command = ["del", "address", "--ip=%s" % ip] + self.valid_just_tcm
        self.noouttest(command)
        self.dsdb_verify()
        self.ib_verify()

    def test_840_verify_delete_with_grn(self):
        command = ["show_address", "--fqdn=arecord51.aqd-unittest.ms.com"]
        self.notfoundtest(command)

    def test_850_del_address_with_digit_prefix(self):
        fqdn = "1record42.aqd-unittest.ms.com"
        ip = "4.2.1.47"
        dns_env = "external"
        command = ["del", "address", "--fqdn", fqdn,
                   "--dns_environment", dns_env] + self.valid_just_tcm
        self.noouttest(command)
        self.dsdb_verify(empty=True)

        command = ["show", "address", "--fqdn", fqdn,
                   "--dns_environment", dns_env]
        self.notfoundtest(command)

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDelAddress)
    unittest.TextTestRunner(verbosity=2).run(suite)
