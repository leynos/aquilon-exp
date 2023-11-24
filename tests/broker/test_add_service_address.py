#!/usr/bin/env python
# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2012-2017,2019  Contributor
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
"""Module for testing the add service address command."""

import unittest

if __name__ == "__main__":
    from . import utils
    utils.import_depends()

from .brokertest import TestBrokerCommand
from broker.utils import MockHub

from mock_ib_services import ib_expect_add_address
from mock_ib_services import ib_expect_add_alias
from mock_ib_services import ib_expect_del_address
from mock_ib_services import ib_expect_del_alias
from mock_ib_services import ib_expect_update_address


class TestAddServiceAddress(TestBrokerCommand):

    def test_100_systemzebramix(self):
        ip = self.net["unknown0"].usable[3]
        command = ["add", "service", "address",
                   "--hostname", "unittest20.aqd-unittest.ms.com",
                   "--interfaces", "eth0,eth1", "--name", "e2",
                   "--service_address", "unittest00-e1.one-nyp.ms.com"]
        out = self.badrequesttest(command)
        self.matchoutput(out,
                         "IP address %s is already in use by public interface "
                         "eth1 of machine unittest00.one-nyp.ms.com." % ip,
                         command)

    def test_200_addzebra2(self):
        # Use an address that is smaller than the primary IP to verify that the
        # primary IP is not removed
        ip = self.net["zebra_vip"].usable[14]
        ib_expect_add_address("zebra2.aqd-unittest.ms.com", str(ip))
        self.dsdb_expect_add("zebra2.aqd-unittest.ms.com", ip)
        command = ["add", "service", "address",
                   "--hostname", "unittest20.aqd-unittest.ms.com",
                   "--service_address", "zebra2.aqd-unittest.ms.com",
                   "--interfaces", "eth0,eth1", "--ip", ip,
                   "--name", "zebra2"]
        out = self.statustest(command)
        self.matchoutput(out,
                         "Host unittest20.aqd-unittest.ms.com is missing the "
                         "following required services",
                         command)
        self.dsdb_verify()
        self.ib_verify()

    def test_210_verifyzebra2(self):
        ip = self.net["zebra_vip"].usable[14]
        command = ["show", "service", "address", "--name", "zebra2",
                   "--hostname", "unittest20.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out, "Service Address: zebra2", command)
        self.matchoutput(out, "Bound to: Host unittest20.aqd-unittest.ms.com",
                         command)
        self.matchoutput(out, "Address: zebra2.aqd-unittest.ms.com [%s]" % ip,
                         command)
        self.matchoutput(out, "Interfaces: eth0, eth1", command)

    def test_220_verifyzebra2proto(self):
        ip = self.net["zebra_vip"].usable[14]
        command = ["show", "host",
                   "--hostname", "unittest20.aqd-unittest.ms.com",
                   "--format", "proto"]
        host = self.protobuftest(command, expect=1)[0]
        found = False
        for resource in host.resources:
            if resource.name == "zebra2" and resource.type == "service_address":
                found = True
                self.assertEqual(resource.service_address.ip, str(ip))
                self.assertEqual(resource.service_address.fqdn,
                                 "zebra2.aqd-unittest.ms.com")
                ifaces = ",".join(sorted(resource.service_address.interfaces))
                self.assertEqual(ifaces, "eth0,eth1")
        self.assertTrue(found,
                        "Service address zebra2 not found in the resources. "
                        "Existing resources: %s" %
                        ", ".join("%s %s" % (res.type, res.name)
                                  for res in host.resources))

    def test_230_verifyzebra2dns(self):
        command = ["show", "fqdn", "--fqdn", "zebra2.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchclean(out, "Reverse", command)

    def test_300_addzebra3(self):
        zebra3_ip = self.net["zebra_vip"].usable[13]
        ib_expect_add_address("zebra3.aqd-unittest.ms.com", str(zebra3_ip),
                              reverse_ptr="unittest20.aqd-unittest.ms.com")
        self.dsdb_expect_add("zebra3.aqd-unittest.ms.com", zebra3_ip,
                             comments="Some service address comments")
        command = ["add", "service", "address",
                   "--hostname", "unittest20.aqd-unittest.ms.com",
                   "--prefix", "zebra",
                   "--interfaces", "eth0,eth1", "--ip", zebra3_ip,
                   "--name", "zebra3", "--map_to_primary",
                   "--comments", "Some service address comments"]
        out = self.statustest(command)
        self.matchoutput(out,
                         "Host unittest20.aqd-unittest.ms.com is missing the "
                         "following required services",
                         command)
        self.dsdb_verify()
        self.ib_verify()

    def test_310_verifyzebra3dns(self):
        command = ["show", "fqdn", "--fqdn", "zebra3.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out, "Reverse PTR: unittest20.aqd-unittest.ms.com",
                         command)

    def test_320_verifyzebra3audit(self):
        command = ["search_audit", "--keyword", "zebra3.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out,
                         "[Result: service_address=zebra3.aqd-unittest.ms.com]",
                         command)

    def test_400_verifyunittest20(self):
        ip = self.net["zebra_vip"].usable[2]
        zebra2_ip = self.net["zebra_vip"].usable[14]
        zebra3_ip = self.net["zebra_vip"].usable[13]
        command = ["show", "host", "--hostname",
                   "unittest20.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchclean(out, "Provides: zebra2.aqd-unittest.ms.com", command)
        self.matchclean(out, "Provides: zebra3.aqd-unittest.ms.com", command)
        self.matchclean(out, "Auxiliary: zebra2.aqd-unittest.ms.com", command)
        self.matchclean(out, "Auxiliary: zebra3.aqd-unittest.ms.com", command)

        self.searchoutput(out,
                          r"Service Address: hostname$"
                          r"\s+Address: unittest20\.aqd-unittest\.ms\.com \[%s\]$"
                          r"\s+Interfaces: eth0, eth1$" % ip,
                          command)
        self.searchoutput(out,
                          r"Service Address: zebra2$"
                          r"\s+Address: zebra2\.aqd-unittest\.ms\.com \[%s\]$"
                          r"\s+Interfaces: eth0, eth1$" % zebra2_ip,
                          command)
        self.searchoutput(out,
                          r"Service Address: zebra3$"
                          r"\s+Comments: Some service address comments$"
                          r"\s+Address: zebra3\.aqd-unittest\.ms\.com \[%s\]$"
                          r"\s+Interfaces: eth0, eth1$" % zebra3_ip,
                          command)

    def test_500_failbadname(self):
        ip = self.net["unknown0"].usable[-1]
        command = ["add", "service", "address",
                   "--hostname", "unittest20.aqd-unittest.ms.com",
                   "--interfaces", "eth0,eth1", "--name", "hostname",
                   "--service_address", "hostname-label.one-nyp.ms.com",
                   "--ip", ip]
        out = self.badrequesttest(command)
        self.matchoutput(out,
                         "The hostname service address is reserved for Zebra.  "
                         "Please specify the --zebra_interfaces option when "
                         "calling add_host if you want the primary name of the "
                         "host to be managed by Zebra.",
                         command)

    def test_510_failbadinterface(self):
        ip = self.net["unknown0"].usable[-1]
        command = ["add", "service", "address",
                   "--hostname", "unittest20.aqd-unittest.ms.com",
                   "--interfaces", "eth0,eth2", "--name", "badiface",
                   "--service_address", "badiface.one-nyp.ms.com",
                   "--ip", ip]
        out = self.badrequesttest(command)
        self.matchoutput(out,
                         "Machine unittest20.aqd-unittest.ms.com does not have "
                         "an interface named eth2.",
                         command)

    def test_520_failbadnetenv(self):
        net = self.net["unknown0"]
        subnet = list(net.subnets())[0]
        command = ["add", "service", "address",
                   "--hostname", "unittest20.aqd-unittest.ms.com",
                   "--interfaces", "eth0,eth1", "--name", "badenv",
                   "--service_address", "badenv.one-nyp.ms.com",
                   "--ip", subnet[1], "--network_environment", "excx"]
        out = self.badrequesttest(command)
        self.matchoutput(out,
                         "Public Interface eth0 of machine "
                         "unittest20.aqd-unittest.ms.com already has an IP "
                         "address from network environment internal.  Network "
                         "environments cannot be mixed.",
                         command)

    def test_600_addunittest20eth2(self):
        command = ["add_interface", "--machine", "ut3c5n2",
                   "--interface", "eth2", "--mac", "08:00:01:02:20:00"]
        self.successtest(command)

    def test_605_addunittest20eth2addr(self):
        fqdn = "unittest20-e2.aqd-unittest.ms.com"
        ip = "192.168.5.24"
        ib_expect_add_address(fqdn, ip)
        command = ["add_interface_address", "--machine", "ut3c5n2",
                   "--interface", "eth2", "--network_environment", "excx",
                   "--fqdn", fqdn, "--ip", ip]
        self.statustest(command)
        # External IP addresses should not be added to DSDB
        self.dsdb_verify(empty=True)#
        self.ib_verify()

    def test_610_add_extserviceaddress(self):
        # check that adding an external service address does not invoke DSDB
        ib_expect_add_address("external-unittest20.aqd-unittest.ms.com", "192.168.5.25")
        command = ["add_service_address", "--ip", "192.168.5.25",
                   "--hostname", "unittest20.aqd-unittest.ms.com",
                   "--interfaces", "eth2", "--name", "et-unittest20",
                   "--service_address", "external-unittest20.aqd-unittest.ms.com",
                   "--network_environment", "excx"]
        out = self.statustest(command)
        self.matchoutput(out,
                         "Host unittest20.aqd-unittest.ms.com is missing the "
                         "following required services",
                         command)
        # External IP service addresses should not be added to DSDB
        self.dsdb_verify(empty=True)
        self.ib_verify()

    def test_620_add_service_address_ipfromtype_vip_setup(self):
        ip = self.net["np_bucket2_vip"].network_address
        command = ["show", "host", "--hostname", "aquilon67.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out, "Bunker: bucket2.ut", command)
        command = ["search", "network", "--type", "vip", "--exact_location", "--bunker", "bucket2.ut", "--fullinfo"]
        self.noouttest(command)
        command = ["search", "network", "--type", "vip", "--exact_location", "--bunker", "bucket2.np", "--fullinfo"]
        out = self.commandtest(command)
        self.matchoutput(out, "Bunker: bucket2.np", command)
        self.matchoutput(out, "IP: {}".format(ip), command)
        self.matchoutput(out, "Network: np_bucket2_vip", command)
        self.matchoutput(out, "Network Type: vip", command)

    def test_625_add_service_address_ipfromtype_vip(self):
        # Test nextip generation for VIP serviceaddreses
        ip = self.net["np_bucket2_vip"].usable[0]
        service_addr = "testaddress.ms.com"
        ib_expect_add_address(service_addr, str(ip))
        self.dsdb_expect_add(service_addr, ip)
        command = ["add", "service", "address", "--hostname", "aquilon67.aqd-unittest.ms.com",
                   "--service_address", service_addr, "--name", "test", "--ipfromtype", "vip"]
        self.successtest(command)
        self.ib_verify()
        command = ["show", "service", "address", "--name", "test",
                   "--hostname", "aquilon67.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out, "Service Address: test", command)
        self.matchoutput(out, "Bound to: Host aquilon67.aqd-unittest.ms.com",
                         command)
        self.matchoutput(out, "Address: testaddress.ms.com [{}]".format(ip),
                         command)
        self.dsdb_verify()

    def test_630_add_service_address_ipfromtype_localvip_setup(self):
        ip1 = self.net["ut_bucket2_localvip"].network_address
        ip2 = self.net["np_bucket2_localvip"].network_address
        command = ["search", "network", "--type", "localvip", "--exact_location", "--bunker", "bucket2.ut", "--fullinfo"]
        out = self.commandtest(command)
        self.matchoutput(out, "Bunker: bucket2.ut", command)
        self.matchoutput(out, "IP: {}".format(ip1), command)
        self.matchoutput(out, "Network: ut_bucket2_localvip", command)

        command = ["search", "network", "--type", "localvip", "--exact_location", "--bunker", "bucket2.np", "--fullinfo"]
        out = self.commandtest(command)
        self.matchoutput(out, "Bunker: bucket2.np", command)
        self.matchoutput(out, "IP: {}".format(ip2), command)
        self.matchoutput(out, "Network: np_bucket2_localvip", command)

    def test_635_add_service_address_ipfromtype_localvip(self):
        # Test nextip generation for localvip serviceaddreses
        ip = self.net["ut_bucket2_localvip"].usable[1]
        service_addr = "testlocalvipaddress.ms.com"
        ib_expect_add_address(service_addr, str(ip))
        self.dsdb_expect_add(service_addr, ip)
        command = ["add", "service", "address", "--hostname", "aquilon67.aqd-unittest.ms.com",
                   "--service_address", service_addr, "--name", "test2", "--ipfromtype", "localvip"]
        self.successtest(command)
        self.ib_verify()
        command = ["show", "service", "address", "--name", "test2",
                   "--hostname", "aquilon67.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out, "Service Address: test2", command)
        self.matchoutput(out, "Bound to: Host aquilon67.aqd-unittest.ms.com",
                         command)
        self.matchoutput(out, "Address: testlocalvipaddress.ms.com [{}]".format(ip),
                         command)

    def test_636_add_service_address_aliases(self):
        alias_hostname = "testlocalvipaddress.ms.com"
        ib_expect_add_alias("testlocalvipaddress-alias1.aqd-unittest.ms.com", alias_hostname)
        command = [
            'add', 'alias',
            '--fqdn', 'testlocalvipaddress-alias1.aqd-unittest.ms.com',
            '--target', alias_hostname,
        ]
        self.successtest(command)
        self.ib_verify()
        ib_expect_add_alias("testlocalvipaddress-alias2.aqd-unittest.ms.com", alias_hostname)
        command = [
            'add', 'alias',
            '--fqdn', 'testlocalvipaddress-alias2.aqd-unittest.ms.com',
            '--target', alias_hostname,
        ]
        self.successtest(command)
        self.ib_verify()

    def test_637_verify_service_address_aliases(self):
        command = ['show', 'service', 'address', '--name', 'test2',
                   '--hostname', 'aquilon67.aqd-unittest.ms.com',
                   '--format', 'proto']

        # Get the resource object from the command
        resource = self.protobuftest(command, expect=1)[0]

        # Check the resource information
        self.assertEqual(resource.type, 'service_address')
        self.assertEqual(resource.name, 'test2')

        # Get the service address object from the resource object
        service_address = resource.service_address

        # Check the service address information
        self.assertEqual(service_address.fqdn, 'testlocalvipaddress.ms.com')
        self.assertListEqual(
            list(service_address.aliases),
            [
                'testlocalvipaddress-alias1.aqd-unittest.ms.com',
                'testlocalvipaddress-alias2.aqd-unittest.ms.com',
            ],
        )

    def test_638_del_service_address_aliases(self):
        ib_expect_del_alias('testlocalvipaddress-alias1.aqd-unittest.ms.com')
        command = [
            'del', 'alias',
            '--fqdn', 'testlocalvipaddress-alias1.aqd-unittest.ms.com',
        ]
        self.successtest(command)
        self.ib_verify()
        ib_expect_del_alias('testlocalvipaddress-alias2.aqd-unittest.ms.com')
        command = [
            'del', 'alias',
            '--fqdn', 'testlocalvipaddress-alias2.aqd-unittest.ms.com',
        ]
        self.successtest(command)
        self.ib_verify()

    def test_640_add_service_address_ipfromtype_not_bunker(self):
        # Test nextip generation limited to bunkers only
        command = ["add", "service", "address", "--hostname", "unittest15.aqd-unittest.ms.com",
                   "--service_address", "dummy.ms.com", "--name", "test3", "--ipfromtype", "localvip"]
        err = self.badrequesttest(command)
        self.matchoutput(err, "Host(s) location is not "
                              "inside a Bunker, --ipfromtype cannot be used.", command)

    def test_645_test_del_ipfromtype_test(self):
        ip1 = self.net["np_bucket2_vip"].usable[0]
        ip2 = self.net["ut_bucket2_localvip"].usable[1]
        ib_expect_del_address("testaddress.ms.com", str(ip1))
        self.dsdb_expect_delete(ip1)
        command = ["del", "service", "address", "--hostname", "aquilon67.aqd-unittest.ms.com",
                   "--name", "test"]
        self.successtest(command)
        self.dsdb_verify()
        self.ib_verify()
        ib_expect_del_address("testlocalvipaddress.ms.com", str(ip2))
        self.dsdb_expect_delete(ip2)
        command = ["del", "service", "address", "--hostname", "aquilon67.aqd-unittest.ms.com",
                   "--name", "test2"]
        self.successtest(command)
        self.dsdb_verify()
        self.ib_verify()

    def test_700_default_dns_domain_from_fails_with_correct_message(self):
        # Command add_service_address should print a correct message from
        # function worker.dbwrappers.location.get_default_dns_domain when no
        # default DNS domain is found among parents of the resource holder that
        # are of a given class (in the example below: SomeLocationClass).
        ip = self.net['unknown0'].usable[0]
        command = ['add_service_address', '--cluster', 'camelcase',
                   '--shortname', 'testaddress', '--name', 'test',
                   '--default_dns_domain_from', 'SomeLocationClass',
                   '--ip', ip]
        err = self.badrequesttest(command)
        self.matchoutput(err, 'No default DNS domain at level '
                              '"SomeLocationClass" could be found for '
                              'building ut.  Please specify --dns_domain.',
                         command)

    def test_800_infoblox_host_sa(self):
        mh = MockHub(self)
        mh.add_dns_domain('test-infoblox.cc', restricted=False)
        mh.add_network()

        hname = mh.add_host()
        mh.add_address("sa.test-infoblox.cc", "10.25.0.1")

        command = ['add_service_address', '--name', 'test-service', '--service_address', 'sa.test-infoblox.cc',
                   '--hostname', hname]
        # test case when dsdb fails
        self.dsdb_expect_delete("10.25.0.1", fail=True)
        self.dsdberrortest(command)
        self.dsdb_verify()

        # test case when dsdb succeeds
        self.dsdb_expect_delete("10.25.0.1")
        self.dsdb_expect_add("sa.test-infoblox.cc", "10.25.0.1")
        self.noouttest(command)
        self.dsdb_verify()

        ib_expect_update_address(fqdn="sa.test-infoblox.cc", original_ip="10.25.0.1", reverse_ptr=hname, fail=True)
        command = ['update_service_address', '--name', 'test-service', '--hostname', hname, '--map_to_primary']
        self.iberrortest(command)

        ib_expect_update_address(fqdn="sa.test-infoblox.cc", original_ip="10.25.0.1", reverse_ptr=hname)
        command = ['update_service_address', '--name', 'test-service', '--hostname', hname, '--map_to_primary']
        self.noouttest(command)
        self.ib_verify()

        self.dsdb_expect_update("sa.test-infoblox.cc", ip="10.25.0.2", fail=True)
        command = ['update_service_address', '--name', 'test-service', '--hostname', hname, '--ip', '10.25.0.2']
        self.dsdberrortest(command)
        self.dsdb_verify()

        self.dsdb_expect_update("sa.test-infoblox.cc", ip="10.25.0.2")
        ib_expect_update_address(fqdn="sa.test-infoblox.cc", original_ip="10.25.0.1", new_ip="10.25.0.2", fail=True)
        self.dsdb_expect_update("sa.test-infoblox.cc", ip="10.25.0.1")  # Expect dsdb rollback because infoblox fails
        self.iberrortest(command)
        self.dsdb_verify()

        self.dsdb_expect_update("sa.test-infoblox.cc", ip="10.25.0.2")
        ib_expect_update_address(fqdn="sa.test-infoblox.cc", original_ip="10.25.0.1", new_ip="10.25.0.2")
        self.noouttest(command)
        self.dsdb_verify()

        command = ['del_service_address', '--name', 'test-service', '--hostname', hname]

        self.dsdb_expect_delete("10.25.0.2", fail=True)
        self.dsdberrortest(command)
        self.dsdb_verify()

        self.dsdb_expect_delete("10.25.0.2")
        ib_expect_del_address("sa.test-infoblox.cc", "10.25.0.2", fail=True)
        self.dsdb_expect_add("sa.test-infoblox.cc", ip="10.25.0.2")  # Expect dsdb rollback because infoblox fails
        self.iberrortest(command)
        self.dsdb_verify()
        self.ib_verify()

        self.dsdb_expect_delete("10.25.0.2")
        ib_expect_del_address("sa.test-infoblox.cc", "10.25.0.2")
        self.noouttest(command)
        self.dsdb_verify()
        self.ib_verify()
        del mh.addresses['sa.test-infoblox.cc', 'internal']

        mh.delete()

    def test_810_infoblox_resourcegroup_sa(self):
        mh = MockHub(self)
        mh.add_dns_domain('test-infoblox.cc', restricted=False)
        mh.add_network()

        hname = mh.add_host()
        mh.add_address("sa.test-infoblox.cc", "10.25.0.1")
        mh.add_resource_group("test-resource-group", hname)
        mh.add_shared_service_name("shared-service-name", "test-resource-group",
                                   "resource-group-shared-name.test-infoblox.cc", True)

        self.dsdb_expect_delete("10.25.0.1")
        self.dsdb_expect_add("sa.test-infoblox.cc", "10.25.0.1")
        ib_expect_add_address("resource-group-shared-name.test-infoblox.cc", "10.25.0.1")
        command = ['add_service_address', '--name', 'test-service', '--service_address', 'sa.test-infoblox.cc',
                   '--resourcegroup', 'test-resource-group']
        self.noouttest(command)
        self.dsdb_verify()
        self.ib_verify()

        self.dsdb_expect_update("sa.test-infoblox.cc", ip="10.25.0.2", fail=True)
        command = ['update_service_address', '--name', 'test-service', '--resourcegroup', 'test-resource-group',
                   '--ip', '10.25.0.2', '--map_to_shared']
        self.dsdberrortest(command)
        self.dsdb_verify()

        self.dsdb_expect_update("sa.test-infoblox.cc", ip="10.25.0.2")
        ib_expect_update_address(fqdn="sa.test-infoblox.cc", original_ip="10.25.0.1", fail=True,
                                 new_ip="10.25.0.2", reverse_ptr="resource-group-shared-name.test-infoblox.cc")
        self.dsdb_expect_update("sa.test-infoblox.cc", ip="10.25.0.1")  # Expect DSDB rollback when IB fails
        command = ['update_service_address', '--name', 'test-service', '--resourcegroup', 'test-resource-group',
                   '--ip', '10.25.0.2', '--map_to_shared']
        self.iberrortest(command)
        self.dsdb_verify()

        self.dsdb_expect_update("sa.test-infoblox.cc", ip="10.25.0.2")
        ib_expect_update_address(fqdn="sa.test-infoblox.cc", original_ip="10.25.0.1",
                                 new_ip="10.25.0.2", reverse_ptr="resource-group-shared-name.test-infoblox.cc")
        command = ['update_service_address', '--name', 'test-service', '--resourcegroup', 'test-resource-group',
                   '--ip', '10.25.0.2', '--map_to_shared']
        self.noouttest(command)
        self.dsdb_verify()

        # Test that when we send 2 IB requests and the first one succeeds but the second one fails,
        # the second one is rolled back

        #  Set a TTL on the address_alias to test that when the rollback happens, the TTL is retained
        command = ['update_address_alias',
                   '--fqdn', 'resource-group-shared-name.test-infoblox.cc', '--ttl', 100] + self.valid_just_tcm
        ib_expect_update_address('resource-group-shared-name.test-infoblox.cc',
                                 '10.25.0.2', new_ttl=100, update_ptr=False)
        self.noouttest(command)

        self.dsdb_expect_delete("10.25.0.2")
        ib_expect_del_address("resource-group-shared-name.test-infoblox.cc", "10.25.0.2")
        ib_expect_del_address("sa.test-infoblox.cc", "10.25.0.2", fail=True)
        ib_expect_add_address("resource-group-shared-name.test-infoblox.cc", "10.25.0.2", ttl=100)  # Expect IB rollback
        self.dsdb_expect_add("sa.test-infoblox.cc", "10.25.0.2")  # Expect DSDB rollback
        command = ['del_service_address', '--name', 'test-service', '--resourcegroup', 'test-resource-group']
        self.iberrortest(command)
        self.dsdb_verify()

        self.dsdb_expect_delete("10.25.0.2")
        ib_expect_del_address("resource-group-shared-name.test-infoblox.cc", "10.25.0.2")
        ib_expect_del_address("sa.test-infoblox.cc", "10.25.0.2")
        command = ['del_service_address', '--name', 'test-service', '--resourcegroup', 'test-resource-group']
        self.noouttest(command)
        self.dsdb_verify()
        self.ib_verify()
        del mh.addresses['sa.test-infoblox.cc', 'internal']

        mh.delete()


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAddServiceAddress)
    unittest.TextTestRunner(verbosity=2).run(suite)
