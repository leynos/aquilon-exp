# This must come first as it includes dependencies
import sys

import bootstrap_tests
import logging
import unittest
from isolated import BaseIsolatedTest

LOGGER = logging.getLogger(__name__)


class TestAddDelNetworkDevice(BaseIsolatedTest):
    FQDN = "ut3gd1r03.aqd-unittest.ms.com"
    IP = "8.6.8.30"

    def assert_create_a_ptr(self):
        self.assertIn("POST", BaseIsolatedTest.IB_SERVICES_CALLBACKS,
                      "The ib-services POST /dns/a_ptr endpoint was not invoked")

    def assert_delete_a_ptr(self):
        self.assertIn("DELETE", BaseIsolatedTest.IB_SERVICES_CALLBACKS,
                      "The ib-services DELETE /dns/a_ptr endpoint was not invoked")

    def test_100_add_network_device(self):
        LOGGER.info("Running add_network_device to invoke DSDB and IB broker")
        BaseIsolatedTest.IB_SERVICES_CALLBACKS.clear()
        self.dsdb_expect_add(TestAddDelNetworkDevice.FQDN, TestAddDelNetworkDevice.IP, "xge49")
        command = ["add", "network_device", "--network_device", TestAddDelNetworkDevice.FQDN,
                   "--ip", TestAddDelNetworkDevice.IP,
                   "--model", "uttorswitch", "--rack", "ut3", "--type", "tor", "--interface", "xge49",
                   "--iftype", "physical"]
        self.statustest(command)
        self.dsdb_verify()
        self.assert_create_a_ptr()

    def test_200_del_network_device(self):
        """ This test depends on test_100_add_network_device """
        LOGGER.info("Running del_network_device to invoke DSDB and IB broker")
        self.dsdb_expect_delete(ip=TestAddDelNetworkDevice.IP)
        command = ["del", "network_device", "--network_device", TestAddDelNetworkDevice.FQDN]
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
