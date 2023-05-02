# This must come first as it includes dependencies
import sys

import bootstrap_tests
import logging
import unittest
from isolated import BaseIsolatedTest

LOGGER = logging.getLogger(__name__)


class TestAddDelConsoleServer(BaseIsolatedTest):
    FQDN = "utcs11.aqd-unittest.ms.com"

    def assert_create_a_ptr(self):
        self.assertIn("POST", BaseIsolatedTest.IB_SERVICES_CALLBACKS,
                      "The ib-services POST /dns/a_ptr endpoint was not invoked")

    def assert_delete_a_ptr(self):
        self.assertIn("DELETE", BaseIsolatedTest.IB_SERVICES_CALLBACKS,
                      "The ib-services DELETE /dns/a_ptr endpoint was not invoked")

    def test_100_add_console_server(self):
        LOGGER.info("Running add_console_server to invoke DSDB and IB broker")
        ip = self.net["ut9_conservers"].usable[0]
        self.dsdb_expect_add(TestAddDelConsoleServer.FQDN, ip, "mgmt")
        BaseIsolatedTest.IB_SERVICES_CALLBACKS.clear()
        command = ["add", "console_server", "--console_server", TestAddDelConsoleServer.FQDN, "--rack", "ut3",
                   "--model", "utconserver", "--ip", ip]
        self.statustest(command)
        self.dsdb_verify()
        self.assert_create_a_ptr()

    def test_200_del_console_server(self):
        """ This test depends on test_100_add_console_server """
        LOGGER.info("Running del_console_server to invoke DSDB and IB broker")
        ip = self.net["ut9_conservers"].usable[0]
        self.dsdb_expect_delete(ip)
        command = ["del", "console_server", "--console_server", TestAddDelConsoleServer.FQDN]
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
