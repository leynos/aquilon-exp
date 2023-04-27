# This must come first as it includes dependencies
import sys

import bootstrap_tests
import logging
import unittest
from isolated import BaseIsolatedTest
from start_ib_services import add_fixture_get_network_by_ip, add_fixture_get_next_ip, add_fixture_delete_host, \
    add_fixture_delete_a_ptr

LOGGER = logging.getLogger(__name__)


class TestAddDelChassis(BaseIsolatedTest):

    def assert_create_a_ptr(self):
        self.assertIn("POST", BaseIsolatedTest.IB_SERVICES_CALLBACKS,
                      "The ib-services POST /dns/a_ptr endpoint was not invoked")

    def assert_delete_a_ptr(self):
        self.assertIn("DELETE", BaseIsolatedTest.IB_SERVICES_CALLBACKS,
                      "The ib-services DELETE /dns/a_ptr endpoint was not invoked")

    def test_100_add_chassis(self):
        LOGGER.info("Running add_chassis to invoke DSDB and IB broker")
        ip = self.net["zebra_eth1"].usable[0]
        fqdn = "ut9c7.aqd-unittest.ms.com"
        self.dsdb_expect_add(fqdn, ip, "oa")
        BaseIsolatedTest.IB_SERVICES_CALLBACKS.clear()
        command = ["add", "chassis", "--chassis", "ut9c7.aqd-unittest.ms.com", "--rack", "ut9",
                   "--model", "c-class", "--ip", ip, "--eon_id", "11"]
        self.statustest(command)
        self.dsdb_verify()
        self.assert_create_a_ptr()

    def test_200_del_chassis(self):
        """ This test depends on test_100_add_chassis """
        LOGGER.info("Running del_chassis to invoke DSDB and IB broker")
        ip = self.net["zebra_eth1"].usable[0]
        self.dsdb_expect_delete(ip)
        add_fixture_delete_a_ptr("success", str(ip))
        command = ["del", "chassis", "--chassis", "ut9c7.aqd-unittest.ms.com"]
        self.statustest(command)
        self.dsdb_verify()
        self.assert_delete_a_ptr()


if __name__ == '__main__':
    log_level = logging.INFO
    if "-v" in sys.argv:
        log_level = logging.DEBUG
        sys.argv.remove("-v")
    bootstrap_tests.setup_logger(log_level)
    unittest.main()
