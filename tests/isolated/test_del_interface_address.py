# This must come first as it includes dependencies
import bootstrap_tests

import logging
import sys
import unittest
from isolated import BaseIsolatedTest
from start_ib_services import add_fixture_delete_host, add_fixture_create_host

LOGGER = logging.getLogger(__name__)


class TestDelInterfaceAddress(BaseIsolatedTest):

    def test_100_delete_address_host_not_in_infoblox(self):
        """
        This test ensure that when delete_interface_address fails due to the Host not being present in Infoblox,
        the DSDB delete_host occurs and the plenary file is updated.

        Also, if the host isn't in Infoblox, the REST service /legacy/aq/remove-dns-entries/ should be invoked.
        """
        LOGGER.info("Running add_interface_address to insert host into DSDB")
        ip = self.net["zebra_eth1"].usable[0]
        fqdn = "unittest20-e1.aqd-unittest.ms.com"
        command = ["add", "interface", "address", "--machine", "ut3c5n2",
                   "--interface", "eth1", "--fqdn", fqdn, "--ip", str(ip)]
        self.dsdb_expect_add(fqdn, ip, "eth1", ip.mac,
                             primary="unittest20.aqd-unittest.ms.com")
        add_fixture_create_host("allow_hostnames", fqdn)
        self.statustest(command)

        LOGGER.info("Running del_interface_address to invoke DSDB and IB broker")
        ip = self.net["zebra_eth1"].usable[0]
        self.dsdb_expect_delete(ip)
        BaseIsolatedTest.IB_SERVICES_CALLBACKS.clear()
        add_fixture_delete_host("not_found", str(ip))
        command = ["del", "interface", "address", "--machine", "ut3c5n2",
                   "--interface", "eth1", "--ip", ip]
        self.statustest(command)
        self.dsdb_verify()
        self.check_plenary_contents("hostdata", "unittest20.aqd-unittest.ms.com", clean=str(ip))
        self.assert_delete_host("/hosts/ipv4addr/{}".format(ip))
        self.assert_delete_host("/dns/a_ptr/unittest20-e1.aqd-unittest.ms.com/{}?delete_ptr=true".format(ip))


if __name__ == '__main__':
    bootstrap_tests.setup_logger(logging.DEBUG if "-v" in sys.argv else logging.INFO)
    unittest.main()
