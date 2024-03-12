#!/usr/bin/env python
# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2012,2013,2014,2015,2016,2018  Contributor
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
"""Module for testing the update network device command."""

import unittest

if __name__ == "__main__":
    from . import utils
    utils.import_depends()

from mock_ib_services import ib_expect_add_a
from mock_ib_services import ib_expect_add_ptr
from mock_ib_services import ib_expect_del_a
from mock_ib_services import ib_expect_del_ptr

from .brokertest import TestBrokerCommand
from .netdevtest import VerifyNetworkDeviceMixin
from broker.utils import MockHub


class TestRenameNetworkDevice(TestBrokerCommand, VerifyNetworkDeviceMixin):

    def test_100_rename_ut3gd1r04(self):
        self.dsdb_expect_rename("ut3gd1r04-vlan110-hsrp.aqd-unittest.ms.com",
                                "renametest-vlan110-hsrp.aqd-unittest.ms.com")
        self.dsdb_expect_rename("ut3gd1r04-vlan110.aqd-unittest.ms.com",
                                "renametest-vlan110.aqd-unittest.ms.com")
        self.dsdb_expect_rename("ut3gd1r04-loop0.aqd-unittest.ms.com",
                                "renametest-loop0.aqd-unittest.ms.com")
        self.dsdb_expect_rename("ut3gd1r04.aqd-unittest.ms.com",
                                "renametest.aqd-unittest.ms.com")

        ib_expect_del_a("ut3gd1r04-loop0.aqd-unittest.ms.com", "4.2.1.64")
        ib_expect_del_ptr("4.2.1.64")
        ib_expect_del_a("ut3gd1r04-vlan110.aqd-unittest.ms.com", "4.2.1.113")
        ib_expect_del_ptr("4.2.1.113")
        ib_expect_del_a("ut3gd1r04-vlan110-hsrp.aqd-unittest.ms.com", "4.2.1.111")
        ib_expect_del_ptr("4.2.1.111")
        ib_expect_del_a("ut3gd1r04.aqd-unittest.ms.com", "4.2.9.9")
        ib_expect_del_ptr("4.2.9.9")

        ib_expect_add_a("renametest-loop0.aqd-unittest.ms.com", "4.2.1.64")
        ib_expect_add_ptr("renametest-loop0.aqd-unittest.ms.com", "4.2.1.64")
        ib_expect_add_a("renametest-vlan110.aqd-unittest.ms.com", "4.2.1.113")
        ib_expect_add_ptr("renametest-vlan110.aqd-unittest.ms.com", "4.2.1.113")
        ib_expect_add_a("renametest-vlan110-hsrp.aqd-unittest.ms.com", "4.2.1.111")
        ib_expect_add_ptr("renametest-vlan110-hsrp.aqd-unittest.ms.com", "4.2.1.111")
        ib_expect_add_a("renametest.aqd-unittest.ms.com", "4.2.9.9")
        ib_expect_add_ptr("renametest.aqd-unittest.ms.com", "4.2.9.9")

        self.check_plenary_exists("switchdata", "ut3gd1r04.aqd-unittest.ms.com")
        self.check_plenary_exists('network_device', 'americas', 'ut', 'ut3gd1r04')
        self.check_plenary_exists('hostdata', 'ut3gd1r04.aqd-unittest.ms.com')

        command = ["update", "network_device",
                   "--network_device", "ut3gd1r04.aqd-unittest.ms.com",
                   "--rename_to", "renametest"]
        self.noouttest(command)

        self.check_plenary_gone("switchdata", "ut3gd1r04.aqd-unittest.ms.com")
        self.check_plenary_gone('network_device', 'americas', 'ut', 'ut3gd1r04')
        self.check_plenary_gone('hostdata', 'ut3gd1r04.aqd-unittest.ms.com')
        self.check_plenary_exists("switchdata", "renametest.aqd-unittest.ms.com")
        self.check_plenary_exists('network_device', 'americas', 'ut', 'renametest')
        self.check_plenary_exists('hostdata', 'renametest.aqd-unittest.ms.com')

        self.dsdb_verify()
        self.ib_verify()

    def test_110_verify(self):
        self.verifynetdev("renametest.aqd-unittest.ms.com", "hp", "uttorswitch",
                          "ut3", "a", "3", switch_type='bor',
                          ip=self.net["ut10_eth1"].usable[1],
                          mac=self.net["ut10_eth1"].usable[0].mac,
                          interface="xge49",
                          comments="Some new switch comments")

    def test_200_rename_ut3gd1r04_back(self):
        self.dsdb_expect_rename("renametest-vlan110-hsrp.aqd-unittest.ms.com",
                                "ut3gd1r04-vlan110-hsrp.aqd-unittest.ms.com")
        self.dsdb_expect_rename("renametest-vlan110.aqd-unittest.ms.com",
                                "ut3gd1r04-vlan110.aqd-unittest.ms.com")
        self.dsdb_expect_rename("renametest-loop0.aqd-unittest.ms.com",
                                "ut3gd1r04-loop0.aqd-unittest.ms.com")
        self.dsdb_expect_rename("renametest.aqd-unittest.ms.com",
                                "ut3gd1r04.aqd-unittest.ms.com")

        ib_expect_del_a("renametest-loop0.aqd-unittest.ms.com", "4.2.1.64")
        ib_expect_del_ptr("4.2.1.64")
        ib_expect_del_a("renametest-vlan110.aqd-unittest.ms.com", "4.2.1.113")
        ib_expect_del_ptr("4.2.1.113")
        ib_expect_del_a("renametest-vlan110-hsrp.aqd-unittest.ms.com", "4.2.1.111")
        ib_expect_del_ptr("4.2.1.111")
        ib_expect_del_a("renametest.aqd-unittest.ms.com", "4.2.9.9")
        ib_expect_del_ptr("4.2.9.9")

        ib_expect_add_a("ut3gd1r04-loop0.aqd-unittest.ms.com", "4.2.1.64")
        ib_expect_add_ptr("ut3gd1r04-loop0.aqd-unittest.ms.com", "4.2.1.64")
        ib_expect_add_a("ut3gd1r04-vlan110.aqd-unittest.ms.com", "4.2.1.113")
        ib_expect_add_ptr("ut3gd1r04-vlan110.aqd-unittest.ms.com", "4.2.1.113")
        ib_expect_add_a("ut3gd1r04-vlan110-hsrp.aqd-unittest.ms.com", "4.2.1.111")
        ib_expect_add_ptr("ut3gd1r04-vlan110-hsrp.aqd-unittest.ms.com", "4.2.1.111")
        ib_expect_add_a("ut3gd1r04.aqd-unittest.ms.com", "4.2.9.9")
        ib_expect_add_ptr("ut3gd1r04.aqd-unittest.ms.com", "4.2.9.9")


        command = ["update", "network_device",
                   "--network_device", "renametest",
                   "--rename_to", "ut3gd1r04.aqd-unittest.ms.com"]
        self.noouttest(command)
        self.dsdb_verify()
        self.ib_verify()

    def test_210_verify(self):
        self.verifynetdev("ut3gd1r04.aqd-unittest.ms.com", "hp", "uttorswitch",
                          "ut3", "a", "3", switch_type='bor',
                          ip=self.net["ut10_eth1"].usable[1],
                          mac=self.net["ut10_eth1"].usable[0].mac,
                          interface="xge49",
                          comments="Some new switch comments")

    def test_215_rename_ut3gd1r04_domain(self):
        self.dsdb_expect_rename("ut3gd1r04-vlan110-hsrp.aqd-unittest.ms.com",
                                "ut3gd1r04-vlan110-hsrp.aqd-unittest-ut-env.ms.com")
        self.dsdb_expect_rename("ut3gd1r04-vlan110.aqd-unittest.ms.com",
                                "ut3gd1r04-vlan110.aqd-unittest-ut-env.ms.com")
        self.dsdb_expect_rename("ut3gd1r04-loop0.aqd-unittest.ms.com",
                                "ut3gd1r04-loop0.aqd-unittest-ut-env.ms.com")
        self.dsdb_expect_rename("ut3gd1r04.aqd-unittest.ms.com",
                                "ut3gd1r04.aqd-unittest-ut-env.ms.com")

        ib_expect_del_a("ut3gd1r04-loop0.aqd-unittest.ms.com", "4.2.1.64")
        ib_expect_del_ptr("4.2.1.64")
        ib_expect_del_a("ut3gd1r04-vlan110.aqd-unittest.ms.com", "4.2.1.113")
        ib_expect_del_ptr("4.2.1.113")
        ib_expect_del_a("ut3gd1r04-vlan110-hsrp.aqd-unittest.ms.com", "4.2.1.111")
        ib_expect_del_ptr("4.2.1.111")
        ib_expect_del_a("ut3gd1r04.aqd-unittest.ms.com", "4.2.9.9")
        ib_expect_del_ptr("4.2.9.9")

        ib_expect_add_a("ut3gd1r04-loop0.aqd-unittest-ut-env.ms.com", "4.2.1.64")
        ib_expect_add_ptr("ut3gd1r04-loop0.aqd-unittest-ut-env.ms.com", "4.2.1.64")
        ib_expect_add_a("ut3gd1r04-vlan110.aqd-unittest-ut-env.ms.com", "4.2.1.113")
        ib_expect_add_ptr("ut3gd1r04-vlan110.aqd-unittest-ut-env.ms.com", "4.2.1.113")
        ib_expect_add_a("ut3gd1r04-vlan110-hsrp.aqd-unittest-ut-env.ms.com", "4.2.1.111")
        ib_expect_add_ptr("ut3gd1r04-vlan110-hsrp.aqd-unittest-ut-env.ms.com", "4.2.1.111")
        ib_expect_add_a("ut3gd1r04.aqd-unittest-ut-env.ms.com", "4.2.9.9")
        ib_expect_add_ptr("ut3gd1r04.aqd-unittest-ut-env.ms.com", "4.2.9.9")


        command = ["update", "network_device",
                   "--network_device", "ut3gd1r04.aqd-unittest.ms.com",
                   "--rename_to", "ut3gd1r04.aqd-unittest-ut-env.ms.com"]
        self.noouttest(command)
        self.dsdb_verify()
        self.ib_verify()

    def test_220_domain_verify(self):
        self.verifynetdev("ut3gd1r04.aqd-unittest-ut-env.ms.com", "hp", "uttorswitch",
                          "ut3", "a", "3", switch_type='bor',
                          ip=self.net["ut10_eth1"].usable[1],
                          mac=self.net["ut10_eth1"].usable[0].mac,
                          interface="xge49",
                          comments="Some new switch comments")

    def test_225_rename_ut3gd1r04_domain_back(self):
        self.dsdb_expect_rename("ut3gd1r04-vlan110-hsrp.aqd-unittest-ut-env.ms.com",
                                "ut3gd1r04-vlan110-hsrp.aqd-unittest.ms.com")
        self.dsdb_expect_rename("ut3gd1r04-vlan110.aqd-unittest-ut-env.ms.com",
                                "ut3gd1r04-vlan110.aqd-unittest.ms.com")
        self.dsdb_expect_rename("ut3gd1r04-loop0.aqd-unittest-ut-env.ms.com",
                                "ut3gd1r04-loop0.aqd-unittest.ms.com")
        self.dsdb_expect_rename("ut3gd1r04.aqd-unittest-ut-env.ms.com",
                                "ut3gd1r04.aqd-unittest.ms.com")

        ib_expect_del_a("ut3gd1r04-loop0.aqd-unittest-ut-env.ms.com", "4.2.1.64")
        ib_expect_del_ptr("4.2.1.64")
        ib_expect_del_a("ut3gd1r04-vlan110.aqd-unittest-ut-env.ms.com", "4.2.1.113")
        ib_expect_del_ptr("4.2.1.113")
        ib_expect_del_a("ut3gd1r04-vlan110-hsrp.aqd-unittest-ut-env.ms.com", "4.2.1.111")
        ib_expect_del_ptr("4.2.1.111")
        ib_expect_del_a("ut3gd1r04.aqd-unittest-ut-env.ms.com", "4.2.9.9")
        ib_expect_del_ptr("4.2.9.9")

        ib_expect_add_a("ut3gd1r04-loop0.aqd-unittest.ms.com", "4.2.1.64")
        ib_expect_add_ptr("ut3gd1r04-loop0.aqd-unittest.ms.com", "4.2.1.64")
        ib_expect_add_a("ut3gd1r04-vlan110.aqd-unittest.ms.com", "4.2.1.113")
        ib_expect_add_ptr("ut3gd1r04-vlan110.aqd-unittest.ms.com", "4.2.1.113")
        ib_expect_add_a("ut3gd1r04-vlan110-hsrp.aqd-unittest.ms.com", "4.2.1.111")
        ib_expect_add_ptr("ut3gd1r04-vlan110-hsrp.aqd-unittest.ms.com", "4.2.1.111")
        ib_expect_add_a("ut3gd1r04.aqd-unittest.ms.com", "4.2.9.9")
        ib_expect_add_ptr("ut3gd1r04.aqd-unittest.ms.com", "4.2.9.9")

        command = ["update", "network_device",
                   "--network_device", "ut3gd1r04.aqd-unittest-ut-env.ms.com",
                   "--rename_to", "ut3gd1r04.aqd-unittest.ms.com"]
        self.noouttest(command)
        self.dsdb_verify()
        self.ib_verify()

    def test_230_domain_verify_back(self):
        self.verifynetdev("ut3gd1r04.aqd-unittest.ms.com", "hp", "uttorswitch",
                          "ut3", "a", "3", switch_type='bor',
                          ip=self.net["ut10_eth1"].usable[1],
                          mac=self.net["ut10_eth1"].usable[0].mac,
                          interface="xge49",
                          comments="Some new switch comments")

    # A standalone rename_to test that can be run without depending on other tests running first
    def test_900_ib_rename_netdev(self):
        mh = MockHub(self)

        dns_domain = "test-infoblox.cc"
        netdev_hostname = "networkdevice"
        netdev_renamed_hostname = "renametest"
        netdev_primary_fqdn = netdev_hostname + "." + dns_domain
        netdev_primary_fqdn_renamed = netdev_renamed_hostname + "." + dns_domain
        netdev_primary_ip = "10.25.0.1"
        netdev_if_name = "vlan110"
        netdev_if_fqdn = netdev_hostname + "-" + netdev_if_name + "." + dns_domain
        netdev_if_fqdn_renamed = netdev_renamed_hostname + "-" + netdev_if_name + "." + dns_domain
        netdev_if_ip = "10.25.0.2"

        mh.add_dns_domain(dns_domain, restricted=False)
        mh.add_network()
        rack_name = mh.add_rack()

        command = ["add_network_device", "--network_device", netdev_primary_fqdn,
                   "--model", "temp_switch", "--type", "tor", "--interface", "gi0", "--iftype", "physical", "--osname", mh.default_os, "--osversion", mh.default_os_version,
                   "--rack", rack_name, "--archetype", mh.default_archetype, "--domain", mh.default_domain, "--personality", mh.default_personality, "--ip", netdev_primary_ip]


        self.dsdb_expect_add(netdev_primary_fqdn, netdev_primary_ip, interface="gi0")
        ib_expect_add_a(netdev_primary_fqdn, netdev_primary_ip)
        ib_expect_add_ptr(netdev_primary_fqdn, netdev_primary_ip)
        self.noouttest(command)
        self.dsdb_verify()
        self.ib_verify()

        self.noouttest(["add_interface", "--interface", netdev_if_name, "--iftype", "virtual", "--network_device", netdev_primary_fqdn])

        self.dsdb_expect_add(netdev_if_fqdn, netdev_if_ip, netdev_if_name, primary=netdev_primary_fqdn)
        ib_expect_add_a(netdev_if_fqdn, netdev_if_ip)
        ib_expect_add_ptr(netdev_if_fqdn, netdev_if_ip)
        self.noouttest(["add_interface_address", "--network_device", netdev_primary_fqdn, "--interface", netdev_if_name, "--ip", netdev_if_ip])
        self.dsdb_verify()
        self.ib_verify()

        self.dsdb_expect_rename(netdev_primary_fqdn, netdev_primary_fqdn_renamed)
        self.dsdb_expect_rename(netdev_if_fqdn, netdev_if_fqdn_renamed)
        ib_expect_del_a(netdev_primary_fqdn, netdev_primary_ip)
        ib_expect_del_ptr(netdev_primary_ip)  # TODO, changing the PTR could be done with a single update call, rather than delete then add
        ib_expect_del_a(netdev_if_fqdn, netdev_if_ip)
        ib_expect_del_ptr(netdev_if_ip)
        ib_expect_add_a(netdev_primary_fqdn_renamed, netdev_primary_ip)
        ib_expect_add_ptr(netdev_primary_fqdn_renamed, netdev_primary_ip)
        ib_expect_add_a(netdev_if_fqdn_renamed, netdev_if_ip)
        ib_expect_add_ptr(netdev_if_fqdn_renamed, netdev_if_ip)
        self.noouttest(["update_network_device", "--network_device", netdev_primary_fqdn, "--rename_to", netdev_renamed_hostname])
        self.dsdb_verify()
        self.ib_verify()

        self.dsdb_expect_delete(netdev_if_ip)
        ib_expect_del_a(netdev_if_fqdn_renamed, netdev_if_ip)
        ib_expect_del_ptr(netdev_if_ip)
        self.noouttest(["del_interface_address", "--network_device", netdev_primary_fqdn_renamed, "--interface", netdev_if_name, "--ip", netdev_if_ip])
        self.dsdb_verify()
        self.ib_verify()

        self.dsdb_expect_delete(netdev_primary_ip)
        ib_expect_del_a(netdev_primary_fqdn_renamed, netdev_primary_ip)
        ib_expect_del_ptr(netdev_primary_ip)
        self.noouttest(['del_network_device', '--network_device', netdev_primary_fqdn_renamed])
        self.dsdb_verify()
        self.ib_verify()

        mh.delete()

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRenameNetworkDevice)
    unittest.TextTestRunner(verbosity=2).run(suite)
