# This must come first as it includes dependencies
import bootstrap_tests

from ipaddress import IPv4Address

import logging
import unittest

import start_ib_services
from aquilon.worker.processes import IBServices
from isolated import BaseIsolatedTest

LOGGER = logging.getLogger(__name__)


class TestBrokersStart(BaseIsolatedTest):

    def setUp(self):
        self.ip = IPv4Address(u'1.2.3.4')
        self.default_payload = {
            'hostname': 'ut3gd1r03.aqd-unittest.ms.com'
        }
        start_ib_services.add_fixture_create_host("allow_hostnames", self.default_payload["hostname"])

    def test_aq_broker_success(self):
        LOGGER.info("Testing the aqd broker by running aqd status")
        out = self.commandtest("status")
        self.matchoutput(out, "Aquilon Broker ", "status")

    def test_ib_services_broker_available(self):
        LOGGER.info("Testing the ib-services broker is available")
        IBServices().create_host(self.ip, self.default_payload)


if __name__ == '__main__':
    bootstrap_tests.setup_logger()
    unittest.main()
