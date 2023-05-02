# This must come first as it includes dependencies
import sys

import bootstrap_tests
import logging
import unittest
from isolated import BaseIsolatedTest

LOGGER = logging.getLogger(__name__)


class TestAddDelAlias(BaseIsolatedTest):
    FQDN = 'ut9c7.aqd.isolated-unittest.ms.com'
    TARGET = 'arecord13.aqd-unittest.ms.com',

    def assert_add_dns_alias(self):
        self.assertIn("POST", BaseIsolatedTest.IB_SERVICES_CALLBACKS,
                      "The ib-services POST /dns/aliases endpoint was not invoked")

    def assert_del_dns_alias(self):
        self.assertIn("DELETE", BaseIsolatedTest.IB_SERVICES_CALLBACKS,
                      "The ib-services DELETE /dns/aliases/ endpoint was not invoked")

    def test_100_add_alias(self):
        LOGGER.info("Running add_alias to invoke DSDB and IB broker")
        self.dsdb_expect_add(TestAddDelAlias.FQDN)
        BaseIsolatedTest.IB_SERVICES_CALLBACKS.clear()
        command = ["add", "alias", "--fqdn", TestAddDelAlias.FQDN, "--target", TestAddDelAlias.TARGET, "--eon_id", "11"]
        self.statustest(command)
        self.dsdb_verify()
        self.assert_add_dns_alias()

    def test_200_del_dns_alias(self):
        """ This test depends on test_100_add_alias """
        LOGGER.info("Running del_alias to invoke DSDB and IB broker")
        self.dsdb_expect_delete(TestAddDelAlias.FQDN)
        command = ["del", "alias", "--fqdn", TestAddDelAlias.FQDN]
        self.statustest(command)
        self.dsdb_verify()
        self.assert_del_dns_alias()


if __name__ == '__main__':
    log_level = logging.INFO
    if "-v" in sys.argv:
        log_level = logging.DEBUG
        sys.argv.remove("-v")
    bootstrap_tests.setup_logger(log_level)
    unittest.main()
