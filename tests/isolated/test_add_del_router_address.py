# This must come first as it includes dependencies
import bootstrap_tests

import logging
import sys
import unittest
from isolated import BaseIsolatedTest

LOGGER = logging.getLogger(__name__)


class TestAddDelRouterAddress(BaseIsolatedTest):
    FQDN = "ut3gd1r04-v110-hsrp.aqd-unittest.ms.com"
    IP = "8.6.8.20"

    def setUp(self):
        BaseIsolatedTest.IB_SERVICES_CALLBACKS.clear()

    def assert_create_a_ptr(self):
        self.assertIn("POST", BaseIsolatedTest.IB_SERVICES_CALLBACKS,
                      "The ib-services POST /dns/a_ptr endpoint was not invoked")

    def assert_delete_a_ptr(self):
        self.assertIn("DELETE", BaseIsolatedTest.IB_SERVICES_CALLBACKS,
                      "The ib-services DELETE /dns/a_ptr endpoint was not invoked")

    def test_100_add_router_address(self):
        LOGGER.info("Running add_router_address to invoke DSDB and IB broker")
        command = ["add", "router_address", "--fqdn", TestAddDelRouterAddress.FQDN, "--ip", TestAddDelRouterAddress.IP]
        self.statustest(command)
        self.assert_create_a_ptr()

    def test_200_del_router_address(self):
        """ This test depends on test_100_add_router_address """
        LOGGER.info("Running del_router_address to invoke DSDB and IB broker")
        command = ["del", "router_address", "--fqdn", TestAddDelRouterAddress.FQDN]
        self.statustest(command)
        self.assert_delete_a_ptr()


if __name__ == '__main__':
    log_level = logging.INFO
    if "-v" in sys.argv:
        log_level = logging.DEBUG
        sys.argv.remove("-v")
    bootstrap_tests.setup_logger(log_level)
    unittest.main()
