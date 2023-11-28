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
"""Module for testing the add chassis command."""

import unittest

from mock_ib_services import ib_expect_add_address
from mock_ib_services import ib_expect_del_address
from mock_ib_services import ib_expect_update_address

if __name__ == "__main__":
    from . import utils
    utils.import_depends()

from .brokertest import TestBrokerCommand
from .chassistest import VerifyChassisMixin
from broker.utils import MockHub


class TestAddChassis(TestBrokerCommand, VerifyChassisMixin):
    def test_100_add_ut3c5(self):
        command = ["add", "chassis", "--chassis", "ut3c5.aqd-unittest.ms.com",
                   "--rack", "ut3", "--model", "utchassis",
                   "--serial", "ABC1234", "--comments", "Some chassis comments"]
        self.noouttest(command)

    def test_105_verify_ut3c5(self):
        self.verifychassis("ut3c5.aqd-unittest.ms.com", "aurora_vendor",
                           "utchassis", "ut3", "a", "3", "ABC1234",
                           comments="Some chassis comments",
                           grn="grn:/ms/ei/aquilon/aqd")

    def test_106_show_ut3c5_proto(self):
        command = ["show", "chassis", "--chassis", "ut3c5.aqd-unittest.ms.com",
                   "--format", "proto"]
        chassis = self.protobuftest(command, expect=1)[0]

        self.assertEqual(chassis.name, 'ut3c5')
        self.assertEqual(chassis.primary_name, 'ut3c5.aqd-unittest.ms.com')
        self.assertEqual(chassis.serial_no, 'ABC1234')

        self.assertEqual(chassis.model.model_type, 'chassis')
        self.assertEqual(chassis.model.name, 'utchassis')
        self.assertEqual(chassis.model.vendor, 'aurora_vendor')

        self.assertEqual(chassis.location.location_type, 'rack')
        self.assertEqual(chassis.location.name, 'ut3')
        self.assertEqual(chassis.location.fullname, 'ut3')
        self.assertEqual(chassis.location.col, '3')
        self.assertEqual(chassis.location.row, 'a')

        self.assertEqual(len(chassis.slots), 0)

        self.assertEqual(len(chassis.interfaces), 1)

    def test_110_add_ut3c1(self):
        command = "add_chassis --chassis ut3c1.aqd-unittest.ms.com --rack ut3 --model aurora_chassis_model"
        self.noouttest(command.split(" "))

    def test_115_verify_ut3c1(self):
        self.verifychassis("ut3c1.aqd-unittest.ms.com",
                           "aurora_vendor", "aurora_chassis_model", "ut3", "a", "3")

    def test_116_add_ut3c1(self):
        command = "update_chassis --chassis ut3c1.aqd-unittest.ms.com --model utchassis"
        self.noouttest(command.split(" "))

    def test_117_verify_ut3c1(self):
        self.verifychassis("ut3c1.aqd-unittest.ms.com",
                           "aurora_vendor", "utchassis", "ut3", "a", "3")

    def test_118_verify_chassis_dns(self):
        command = "search_dns --fqdn ut3c1.aqd-unittest.ms.com"
        out = self.commandtest(command.split(" "))
        self.matchoutput(out, "ut3c1.aqd-unittest.ms.com", command)

    def test_119_add_ut3c2_dsdb_fail(self):
        command = ["add_chassis", "--chassis", "ut3c2.aqd-unittest.ms.com",
                   "--rack", "ut3", "--model", "aurora_chassis_model"]
        out, err = self.successtest(command)
        self.matchoutput(err, "Chassis with the same name already found in DSDB, "
                              "adding chassis just to aqdb.", command)

    def test_120_add_ut3c2_dsdb_fail_delete(self):
        command = ["del_chassis", "--chassis", "ut3c2.aqd-unittest.ms.com"]
        self.noouttest(command)

    def test_121_add_ut9_chassis(self):
        for i in range(1, 8):
            ip = self.net["ut9_chassis"].usable[i]
            hostname = "ut9c%d.aqd-unittest.ms.com" % i
            ib_expect_add_address(hostname, str(ip))
            self.dsdb_expect_add(hostname, ip, "oa", ip.mac)
            command = ["add", "chassis",
                       "--chassis", hostname,
                       "--rack", "ut9", "--model", "c-class",
                       "--ip", ip, "--mac", ip.mac, "--interface", "oa"]
            self.noouttest(command)
        self.dsdb_verify()
        self.ib_verify()

    def test_122_add_chassis_wrong_name_format(self):
        command = ["add_chassis", "--chassis", "testchassis.aqd-unittest.ms.com",
                   "--rack", "ut3", "--model", "aurora_chassis_model"]
        err = self.badrequesttest(command)
        self.matchoutput(err, "Invalid chassis name 'testchassis'. Correct name format: "
                              "rack ID + 'c' + numeric chassis ID (integer without leading 0).", command)

    def test_125_verify_ut9_chassis(self):
        for i in range(1, 6):
            self.verifychassis("ut9c%d.aqd-unittest.ms.com" % i,
                               "hp", "c-class", "ut9", "", "",
                               ip=str(self.net["ut9_chassis"].usable[i]),
                               mac=self.net["ut9_chassis"].usable[i].mac,
                               interface="oa")

    def test_130_add_np3c5(self):
        self.noouttest(["add_chassis", "--chassis", "np3c5.one-nyp.ms.com",
                        "--rack", "np3", "--model", "utchassis"])

    def test_200_reject_bad_label_implicit(self):
        command = ["add", "chassis", "--chassis", "not-alnum.aqd-unittest.ms.com",
                   "--rack", "ut3", "--model", "utchassis"]
        out = self.badrequesttest(command)
        self.matchoutput(out, "Invalid chassis name 'not-alnum'. "
                              "Correct name format: rack ID + 'c' + "
                              "numeric chassis ID (integer without leading 0).",
                         command)

    def test_200_reject_bad_label_explicit(self):
        command = ["add", "chassis", "--chassis", "ut3c6.aqd-unittest.ms.com",
                   "--label", "not-alnum", "--rack", "ut3", "--model", "utchassis"]
        out = self.badrequesttest(command)
        self.matchoutput(out, "Invalid chassis name 'not-alnum'. "
                              "Correct name format: rack ID + 'c' + numeric "
                              "chassis ID (integer without leading 0).",
                         command)

    def test_300_verifychassisall(self):
        command = ["show", "chassis", "--all"]
        out = self.commandtest(command)
        self.matchoutput(out, "ut3c5.aqd-unittest.ms.com", command)
        self.matchoutput(out, "ut3c1.aqd-unittest.ms.com", command)
        self.matchoutput(out, "ut9c1.aqd-unittest.ms.com", command)

    def test_305_show_chassis_all_proto(self):
        command = ["show", "chassis", "--all", "--format", "proto"]
        chassis_list = self.protobuftest(command, expect=10)

        # Verify that the chassis that were created in the previous
        # methods of this class are in the protobuf dump too
        search_chassis_primary_name = set([
            'ut3c5.aqd-unittest.ms.com',
            'ut3c1.aqd-unittest.ms.com',
            'ut9c1.aqd-unittest.ms.com',
        ])
        for chassis in chassis_list:
            search_chassis_primary_name.discard(chassis.primary_name)

        self.assertFalse(
            search_chassis_primary_name,
            'The following chassis have not been found in the protobuf '
            'output: {}'.format(', '.join(search_chassis_primary_name)))

    def test_400_add_chassis_grn(self):
        command = ["add_chassis", "--chassis", "ut3c6.aqd-unittest.ms.com",
                   "--rack", "ut3", "--model", "utchassis",
                   "--grn", "grn:/ms/ei/aquilon/ut2"]
        self.noouttest(command)

    def test_410_verify_add_chassis_grn(self):
        command = ["show_chassis", "--chassis", "ut3c6.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out, "Primary Name: ut3c6.aqd-unittest.ms.com",
                         command)
        self.matchoutput(out, "Owned by GRN: grn:/ms/ei/aquilon/ut2", command)

    def test_420_del_chassis_grn(self):
        command = ["del_chassis", "--chassis", "ut3c6.aqd-unittest.ms.com"]
        self.noouttest(command)

    def test_430_add_chassis_eon_id(self):
        command = ["add_chassis", "--chassis", "ut3c6.aqd-unittest.ms.com",
                   "--rack", "ut3", "--model", "utchassis",
                   "--eon_id", "3"]
        self.noouttest(command)

    def test_440_verify_add_chassis_eon_id(self):
        command = ["show_chassis", "--chassis", "ut3c6.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out, "Primary Name: ut3c6.aqd-unittest.ms.com",
                         command)
        self.matchoutput(out, "Owned by GRN: grn:/ms/ei/aquilon/unittest",
                         command)

    def test_450_verify_add_chassis_eon_id_proto(self):
        command = ["show_chassis", "--chassis", "ut3c6.aqd-unittest.ms.com",
                   "--format", "proto"]
        chassis_list = self.protobuftest(command, expect=1)
        chassis = chassis_list[0]

        self.assertEqual(chassis.owner_eonid, 3)

    def test_460_del_chassis_eon_id(self):
        command = ["del_chassis", "--chassis", "ut3c6.aqd-unittest.ms.com"]
        self.noouttest(command)

    def test_900_ib_chassis(self):
        mh = MockHub(self)

        mh.add_dns_domain('test-infoblox.cc', restricted=False)
        mh.add_network()

        rack = mh.add_rack()
        chassis = rack + "c1.test-infoblox.cc"

        # Test case when creating a chassis without an IP
        command = ['add_chassis', "--chassis", chassis, "--rack", rack, "--model", "c-class"]
        self.noouttest(command)
        self.dsdb_verify(empty=True)
        self.ib_verify(empty=True)

        command = ['del_chassis', "--chassis", chassis]
        self.noouttest(command)
        self.dsdb_verify(empty=True)
        self.ib_verify(empty=True)

        # Test case when updating from noip to an ip
        command = ['add_chassis', "--chassis", chassis, "--rack", rack, "--model", "c-class"]
        self.noouttest(command)
        self.dsdb_verify(empty=True)
        self.ib_verify(empty=True)

        command = ['update_chassis', '--chassis', chassis, '--ip', '10.25.0.1']

        self.dsdb_expect_add(chassis, "10.25.0.1", interface="oa", fail=True)
        self.dsdberrortest(command)
        self.dsdb_verify()

        self.dsdb_expect_add(chassis, "10.25.0.1", interface="oa")
        ib_expect_add_address(chassis, "10.25.0.1", fail=True)
        self.dsdb_expect_delete("10.25.0.1")
        self.iberrortest(command)
        self.dsdb_verify()

        self.dsdb_expect_add(chassis, "10.25.0.1", interface="oa")
        ib_expect_add_address(chassis, "10.25.0.1")
        self.noouttest(command)
        self.dsdb_verify()

        # Test case when updating from one ip to a different ip
        command = ['update_chassis', '--chassis', chassis, '--ip', '10.25.0.2']

        self.dsdb_expect_update(chassis, ip="10.25.0.2", iface="oa", fail=True)
        self.dsdberrortest(command)
        self.dsdb_verify()

        self.dsdb_expect_update(chassis, ip="10.25.0.2", iface="oa")
        ib_expect_update_address(chassis, "10.25.0.1", new_ip="10.25.0.2", fail=True)
        self.dsdb_expect_update(chassis, ip="10.25.0.1", iface="oa")
        self.iberrortest(command)
        self.dsdb_verify()

        self.dsdb_expect_update(chassis, ip="10.25.0.2", iface="oa")
        ib_expect_update_address(chassis, "10.25.0.1", new_ip="10.25.0.2")
        self.noouttest(command)
        self.dsdb_verify()

        command = ['del_chassis', "--chassis", chassis]

        self.dsdb_expect_delete("10.25.0.2", fail=True)
        self.dsdberrortest(command)
        self.dsdb_verify()
        self.ib_verify(empty=True)

        self.dsdb_expect_delete("10.25.0.2")
        ib_expect_del_address(chassis, "10.25.0.2", fail=True)
        self.dsdb_expect_add(chassis, "10.25.0.2", interface="oa")
        self.iberrortest(command)
        self.dsdb_verify()

        self.dsdb_expect_delete("10.25.0.2")
        ib_expect_del_address(chassis, "10.25.0.2")
        self.noouttest(command)
        self.dsdb_verify()

        command = ['add_chassis', "--chassis", chassis, "--rack", rack, "--model", "c-class", "--ip", "10.25.0.1"]

        # test case when dsdb fails and ib is not called
        self.dsdb_expect_add(chassis, "10.25.0.1", interface="oa", fail=True)
        self.dsdberrortest(command)
        self.dsdb_verify()
        self.ib_verify(empty=True)  # no IB requests when dsdb fails

        # test case when dsdb succeeds, ib fails and dsdb is rolled back
        self.dsdb_expect_add(chassis, "10.25.0.1", interface="oa")
        ib_expect_add_address(chassis, "10.25.0.1", fail=True)
        self.dsdb_expect_delete("10.25.0.1")
        self.iberrortest(command)
        self.dsdb_verify()

        # test case when both dsdb and ib succeed
        self.dsdb_expect_add(chassis, "10.25.0.1", interface="oa")
        ib_expect_add_address(chassis, "10.25.0.1")
        self.noouttest(command)
        self.dsdb_verify()

        # test case when chassis is updated without changing ip
        command = ['update_chassis', "--chassis", chassis, "--comments", "check no IB requests when IP is unchanged"]
        self.dsdb_expect_update(chassis, iface="oa", comments="check no IB requests when IP is unchanged")
        self.noouttest(command)

        command = ['del_chassis', "--chassis", chassis]
        self.dsdb_expect_delete("10.25.0.1")
        ib_expect_del_address(chassis, "10.25.0.1")
        self.noouttest(command)
        self.dsdb_verify()

        self.ib_verify()

        mh.delete()

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAddChassis)
    unittest.TextTestRunner(verbosity=2).run(suite)
