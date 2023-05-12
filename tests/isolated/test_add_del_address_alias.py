# This must come first as it includes dependencies
import sys
import os

import bootstrap_tests
import logging
import unittest
from isolated import BaseIsolatedTest
from start_ib_services import add_fixture_get_network_by_ip, add_fixture_get_next_ip, add_fixture_delete_host

LOGGER = logging.getLogger(__name__)

BINDIR = os.path.dirname(os.path.realpath(__file__))
SRCDIR = os.path.join(BINDIR, "..../")
sys.path.append(os.path.join(SRCDIR, "lib"))


class TestAddDelAddressAlias(BaseIsolatedTest):

    FQDN = "addralias-isolated.aqd-unittest.ms.com"
    TARGET = "arecord13.aqd-unittest.ms.com"

    def assert_add_address_alias(self):
        self.assertIn("POST", BaseIsolatedTest.IB_SERVICES_CALLBACKS,
                      "The ib-services POST /host/ipv4addr endpoint was not invoked")

    def assert_delete_address_alias(self):
        self.assertIn("DELETE", BaseIsolatedTest.IB_SERVICES_CALLBACKS,
                      "The ib-services DELETE /host/ipv4addr endpoint was not invoked")

    def test_100_add_address_alias_success(self):
        command = ["add", "address", "alias",
                   "--fqdn", TestAddDelAddressAlias.FQDN,
                   "--target", TestAddDelAddressAlias.TARGET]
        self.noouttest(command)
        self.assert_add_address_alias()

    def test_200_del_addralias_success(self):
        command = ["del", "address", "alias",
                   "--fqdn", TestAddDelAddressAlias.FQDN,
                   "--target", TestAddDelAddressAlias.TARGET]
        self.noouttest(command)
        self.assert_delete_address_alias()





if __name__ == '__main__':
    bootstrap_tests.setup_logger(logging.DEBUG if "-v" in sys.argv else logging.INFO)
    unittest.main()
