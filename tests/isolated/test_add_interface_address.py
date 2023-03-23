# This must come first as it includes dependencies
import sys

import bootstrap_tests
import logging
import unittest
from isolated import BaseIsolatedTest
from start_ib_services import add_fixture_get_network_by_ip, add_fixture_get_next_ip, add_fixture_delete_host

LOGGER = logging.getLogger(__name__)


class TestAddInterfaceAddress(BaseIsolatedTest):

    def assert_create_host(self):
        self.assertIn("POST", BaseIsolatedTest.IB_SERVICES_CALLBACKS,
                      "The ib-services POST /host/ipv4addr endpoint was not invoked")

    def assert_delete_host(self):
        self.assertIn("DELETE", BaseIsolatedTest.IB_SERVICES_CALLBACKS,
                      "The ib-services DELETE /host/ipv4addr endpoint was not invoked")

    def test_100_add_address_success(self):
        """
        This test ensure that when an interface is successfully created, the DSDB broker
        and Infoblox brokers are invoked, and the plenary file is updated.

        It also checks the delete_interface_address works to revert the DSDB and
        plenary file change (ib-services is not yet invoked by del_interface_address).
        """
        LOGGER.info("Running add_interface_address to invoke DSDB and IB broker")
        ip = self.net["zebra_eth1"].usable[0]
        fqdn = "unittest20-e1.aqd-unittest.ms.com"
        self.dsdb_expect_add(fqdn, ip, "eth1", ip.mac,
                             primary="unittest20.aqd-unittest.ms.com")
        BaseIsolatedTest.IB_SERVICES_CALLBACKS.clear()
        command = ["add", "interface", "address", "--machine", "ut3c5n2",
                   "--interface", "eth1", "--fqdn", fqdn, "--ip", ip]
        self.statustest(command)
        self.dsdb_verify()
        self.check_plenary_contents("hostdata", "unittest20.aqd-unittest.ms.com", contains=str(ip))
        self.assert_create_host()

        LOGGER.info("Running del_interface_address to invoke DSDB and IB broker")
        ip = self.net["zebra_eth1"].usable[0]
        self.dsdb_expect_delete(ip)
        add_fixture_delete_host("success", str(ip))
        command = ["del", "interface", "address", "--machine", "ut3c5n2",
                   "--interface", "eth1", "--ip", ip]
        self.statustest(command)
        self.dsdb_verify()
        self.check_plenary_contents("hostdata", "unittest20.aqd-unittest.ms.com", clean=str(ip))
        self.assert_delete_host()

    def test_200_add_address_ib_failure_expect_dsdb_and_plenary_rollback(self):
        """
        This test ensure that when an add_interface_address is invoked with data that causes
        ib-services to fail the create_host call, the DSDB broker rollback is invoked and
        the plenary file remains unchanged at the end of the process.
        """
        LOGGER.info("Running add_interface_address to invoke DSDB and IB broker where a host already exists in IB")
        ip = self.net["zebra_eth1"].usable[0]
        fqdn = "hostname-exists-in-ib.ms.com"
        self.dsdb_expect_add(fqdn, ip, "eth1", ip.mac,
                             primary="unittest20.aqd-unittest.ms.com")
        self.dsdb_expect_delete(ip)
        BaseIsolatedTest.IB_SERVICES_CALLBACKS.clear()
        command = ["add", "interface", "address", "--machine", "ut3c5n2",
                   "--interface", "eth1", "--fqdn", fqdn, "--ip", ip]
        out = self.badrequesttest(command)
        self.matchoutput(out, "Error calling Infoblox create_host", command)
        self.dsdb_verify()
        self.check_plenary_contents("hostdata", "unittest20.aqd-unittest.ms.com", clean=str(ip))
        self.assert_create_host()

    def test_300_add_address_ipfromip_success(self):
        add_fixture_get_network_by_ip("4.2.12.60", "4.2.12.64/26")
        add_fixture_get_next_ip("4.2.12.64/26", "4.2.12.69")

        LOGGER.info("Running add_interface_address to invoke DSDB and IB broker that invokes calls to the generate_ip "
                    "function. This will cause a network and then IP to be retrieved from ib-service.json, resulting "
                    "in the IP 4.2.12.69 being assigned.")
        ip = self.net["zebra_eth1"].usable[0]
        fqdn = "unittest20-e1.aqd-unittest.ms.com"
        self.dsdb_expect_add(fqdn, ip, "eth1", ip.mac,
                             primary="unittest20.aqd-unittest.ms.com")
        BaseIsolatedTest.IB_SERVICES_CALLBACKS.clear()
        command = ["add", "interface", "address", "--machine", "ut3c5n2",
                   "--interface", "eth1", "--fqdn", fqdn, "--ipfromip", "4.2.12.64"]
        self.statustest(command)
        self.dsdb_verify()
        self.check_plenary_contents("hostdata", "unittest20.aqd-unittest.ms.com", contains=str(ip))
        self.assert_create_host()

        LOGGER.info("Running del_interface_address to invoke DSDB and IB broker")
        self.dsdb_expect_delete(ip)
        add_fixture_delete_host("success", str(ip))
        command = ["del", "interface", "address", "--machine", "ut3c5n2",
                   "--interface", "eth1", "--ip", "4.2.12.69"]
        self.statustest(command)
        self.dsdb_verify()
        self.check_plenary_contents("hostdata", "unittest20.aqd-unittest.ms.com", clean=str(ip))
        self.assert_delete_host()


if __name__ == '__main__':
    bootstrap_tests.setup_logger(logging.DEBUG if "-v" in sys.argv else logging.INFO)
    unittest.main()
