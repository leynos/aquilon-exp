#!/usr/bin/env python
# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2018  Contributor
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

from broker.utils import MockHub
from mock_ib_services import ib_expect_add_a
from mock_ib_services import ib_expect_add_ptr
from mock_ib_services import ib_expect_del_a
from mock_ib_services import ib_expect_del_ptr
from mock_ib_services import ib_expect_update_a

if __name__ == "__main__":
    from . import utils
    utils.import_depends()

from .utils import MockHub
from .brokertest import TestBrokerCommand
from .consoleservertest import VerifyConsoleServerMixin

class TestAddConsoleServer(TestBrokerCommand, VerifyConsoleServerMixin):
    def test_100_add_utcs01(self):
        hostname = "utcs01.aqd-unittest.ms.com"
        ip = self.net["ut9_conservers"].usable[1]
        ib_expect_add_a(hostname, str(ip))
        ib_expect_add_ptr(hostname, str(ip))
        self.dsdb_expect_add(hostname, ip, "mgmt", ip.mac, comments="Some console server comments")
        command = ["add", "console_server", "--console_server", hostname,
                   "--rack", "ut9", "--model", "utconserver",
                   "--serial", "ABC12345", "--comments", "Some console server comments",
                   "--ip", ip, "--mac", ip.mac]
        self.noouttest(command)
        self.dsdb_verify()
        self.ib_verify()

    def test_105_verify_utcs01(self):
        ip = self.net["ut9_conservers"].usable[1]
        self.verifyconsoleserver("utcs01.aqd-unittest.ms.com", "aurora_vendor",
                           "utconserver", "ut9", "g", "3", "ABC12345",
                           ip, ip.mac, comments="Some console server comments")

#    def test_106_show_utc01_proto(self):
#        command = ["show", "console_server", "--console_server", "utcs01.aqd-unittest.ms.com",
#                   "--format", "proto"]
#        console_server = self.protobuftest(command, expect=1)[0]
#
#        self.assertEqual(console_server.name, 'utcs01')
#        self.assertEqual(console_server.primary_name, 'utcs01.aqd-unittest.ms.com')
#        self.assertEqual(console_server.serial_no, 'ABC12345')
#
#        self.assertEqual(console_server.model.model_type, 'console_server')
#        self.assertEqual(console_server.model.name, 'utconserver')
#        self.assertEqual(console_server.model.vendor, 'aurora_vendor')
#
#        self.assertEqual(console_server.location.location_type, 'rack')
#        self.assertEqual(console_server.location.name, 'np3')
#        self.assertEqual(console_Server.location.fullname, 'np3bad')
#        self.assertEqual(console_server.location.col, '3')
#        self.assertEqual(console_server.location.row, 'a')
#
#        self.assertEqual(len(console_server.slots), 0)
#
#        self.assertEqual(len(console_server.interfaces), 1)


    def test_120_add_more_console_server(self):
        for i in range(2, 8):
            hostname = "ut9csa%d.aqd-unittest.ms.com" % i
            ip = self.net["ut9_conservers"].usable[i]
            ib_expect_add_a(hostname, str(ip))
            ib_expect_add_ptr(hostname, str(ip))
            self.dsdb_expect_add(hostname, ip, "mgmt", ip.mac)
            command = ["add", "console_server",
                       "--console_server", hostname,
                       "--rack", "ut9", "--model", "utconserver",
                       "--ip", ip, "--mac", ip.mac]
            self.noouttest(command)
        self.dsdb_verify()
        self.ib_verify()

    def test_125_verify_ut9_console_server(self):
        for i in range(2, 6):
            self.verifyconsoleserver("ut9csa%d.aqd-unittest.ms.com" % i,
                               "aurora_vendor", "utconserver", "ut9", "", "",
                               ip=str(self.net["ut9_conservers"].usable[i]),
                               mac=self.net["ut9_conservers"].usable[i].mac,
                               interface="mgmt")

    def test_300_verifyconsoleserverall(self):
        command = ["show", "console_server", "--all"]
        out = self.commandtest(command)
        self.matchoutput(out, "utcs01.aqd-unittest.ms.com", command)
        self.matchoutput(out, "ut9csa2.aqd-unittest.ms.com", command)
        self.matchoutput(out, "ut9csa4.aqd-unittest.ms.com", command)
        self.matchoutput(out, "ut9csa6.aqd-unittest.ms.com", command)

#    def test_305_show_console_server_all_proto(self):
#        command = ["show", "console_server", "--all", "--format", "proto"]
#        console_server_list = self.protobuftest(command, expect=10)
#
#        # Verify that the console server that were created in the previous
#        # methods of this class are in the protobuf dump too
#        search_console_server_primary_name = set([
#            'utcs01.aqd-unittest.ms.com',
#            'ut9csa3.aqd-unittest.ms.com',
#            'ut9csa5.aqd-unittest.ms.com',
#            'ut9csa7.aqd-unittest.ms.com',
#        ])
#        for console_server in console_server_list:
#            search_console_server_primary_name.discard(console_server.primary_name)
#
#        self.assertFalse(
#            search_console_server_primary_name,
#            'The following chassis have not been found in the protobuf '
#            'output: {}'.format(', '.join(search_console_server_primary_name)))

    def test_310_duplicate_label(self):
        mh = MockHub(self)

        # Create test pre-requisites
        rack_name = mh.add_rack(row=1, column="a")
        mh.add_dns_domain('test-console-server.cc', restricted=False)
        mh.add_network()
        self.noouttest(["add_model", "--model", "generic_cs", "--vendor", "generic", "--type", "console_server"])

        # Add one console server
        self.dsdb_expect_add("cs1.test-console-server.cc", "10.25.0.1", "mgmt")
        ib_expect_add_a("cs1.test-console-server.cc", "10.25.0.1")
        ib_expect_add_ptr("cs1.test-console-server.cc", "10.25.0.1")
        command = ["add", "console_server", "--console_server", "cs1.test-console-server.cc", "--ip", "10.25.0.1",
                   "--rack", rack_name, "--model", "generic_cs", "--label", "cslabel"]
        self.noouttest(command)
        self.dsdb_verify()

        # Add a second console server with same label and check error message
        command = ["add", "console_server", "--console_server", "cs2.test-console-server.cc", "--ip", "10.25.0.2",
                   "--rack", rack_name, "--model", "generic_cs", "--label", "cslabel"]
        out = self.badrequesttest(command)
        self.matchoutput(out, "Item already exists: ", command)

        # Revert database to the original state so that other tests cannot depend on data generated by this test
        self.dsdb_expect_delete("10.25.0.1")
        ib_expect_del_a("cs1.test-console-server.cc", "10.25.0.1")
        ib_expect_del_ptr("10.25.0.1")
        command = ["del", "console_server", "--console_server", "cs1.test-console-server.cc"]
        self.noouttest(command)
        self.dsdb_verify()
        self.noouttest(["del_model", "--model", "generic_cs", "--vendor", "generic"])
        mh.delete()

    def test_900_ib_console_server(self):
        mh = MockHub(self)

        self.noouttest(['add_model', '--model', 'console_server_model', '--vendor', 'generic',
                        '--type', 'console_server'])
        mh.add_dns_domain('test-infoblox.cc', restricted=False)
        mh.add_network()

        rack = mh.add_rack()
        console_server = "console-server.test-infoblox.cc"

        command = ['add_console_server', "--console_server", console_server, "--rack", rack,
                   "--model", "console_server_model", "--ip", "10.25.0.1", "--label", "consolerserverlabel"]

        self.dsdb_expect_add(console_server, "10.25.0.1", interface="mgmt", fail=True)
        self.dsdberrortest(command)
        self.dsdb_verify()

        self.dsdb_expect_add(console_server, "10.25.0.1", interface="mgmt")
        ib_expect_add_a(console_server, "10.25.0.1", fail=True)
        self.dsdb_expect_delete("10.25.0.1")  # Check dsdb rollback when ib fails
        self.iberrortest(command)
        self.dsdb_verify()

        self.dsdb_expect_add(console_server, "10.25.0.1", interface="mgmt")
        ib_expect_add_a(console_server, "10.25.0.1")
        ib_expect_add_ptr(console_server, "10.25.0.1")
        self.noouttest(command)
        self.dsdb_verify()

        command = ['update_console_server', "--console_server", console_server, "--ip", "10.25.0.2"]

        self.dsdb_expect_update(console_server, iface="mgmt", ip="10.25.0.2", fail=True)
        self.dsdberrortest(command)
        self.dsdb_verify()

        self.dsdb_expect_update(console_server, iface="mgmt", ip="10.25.0.2")
        ib_expect_update_a(console_server, "10.25.0.1", new_ip="10.25.0.2", fail=True)
        self.dsdb_expect_update(console_server, iface="mgmt", ip="10.25.0.1")  # Check dsdb rollback when ib fails
        self.iberrortest(command)
        self.dsdb_verify()

        self.dsdb_expect_update(console_server, iface="mgmt", ip="10.25.0.2")
        ib_expect_update_a(console_server, "10.25.0.1", new_ip="10.25.0.2")
        ib_expect_del_ptr("10.25.0.1")
        ib_expect_add_ptr(console_server, "10.25.0.2")
        self.noouttest(command)
        self.dsdb_verify()

        command = ['update_console_server', "--console_server", console_server,
                   "--comments", "Test that updating comments does not send a request to IB"]
        self.dsdb_expect_update(console_server, iface="mgmt",
                                comments="Test that updating comments does not send a request to IB")
        self.noouttest(command)
        self.dsdb_verify()

        command = ['del_console_server', "--console_server", console_server]

        self.dsdb_expect_delete("10.25.0.2", fail=True)
        self.dsdberrortest(command)
        self.dsdb_verify()

        self.dsdb_expect_delete("10.25.0.2")
        ib_expect_del_a(console_server, "10.25.0.2", fail=True)
        self.dsdb_expect_add(console_server, "10.25.0.2", interface="mgmt",  # Check dsdb rollback when ib fails
                             comments="Test that updating comments does not send a request to IB")
        self.iberrortest(command)
        self.dsdb_verify()

        self.dsdb_expect_delete("10.25.0.2")
        ib_expect_del_a(console_server, "10.25.0.2")
        ib_expect_del_ptr("10.25.0.2")
        self.noouttest(command)
        self.dsdb_verify()

        self.ib_verify()

        self.noouttest(['del_model', '--model', 'console_server_model', '--vendor', 'generic'])
        mh.delete()

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAddChassis)
    unittest.TextTestRunner(verbosity=2).run(suite)
