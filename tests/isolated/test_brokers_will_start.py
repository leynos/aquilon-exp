# This must come first as it includes dependencies
import bootstrap_tests
from broker.brokertest import TestBrokerCommand

from ipaddress import IPv4Address

from httmock import response, urlmatch, HTTMock
from httplib2 import httplib

import logging
import unittest
from aquilon.exceptions_ import ArgumentError
from aquilon.worker.processes import IBServices

LOGGER = logging.getLogger(__name__)


@urlmatch(method='post')
def mock_ib_post_204(url, request):
    status_code = httplib.CREATED
    return response(status_code)


@urlmatch(method='post')
def mock_ib_post_400(url, request):
    status_code = httplib.BAD_REQUEST
    return response(status_code)


class TestBrokersStart(TestBrokerCommand):

    @classmethod
    def setUpClass(cls):
        bootstrap_tests.setup_logger()
        bootstrap_tests.start_brokers()
        #import time
        #time.sleep(1000)

    @classmethod
    def tearDownClass(cls):
        bootstrap_tests.stop_brokers()

    def setUp(self):
        self.ip = IPv4Address(u'1.2.3.4')
        self.default_payload = {
            'hostname': 'foo.bar.ms.com',
            'aliases': []
        }

    def test_aq_broker_success(self):
        LOGGER.info("Testing the aqd broker by running aqd status")
        out = self.commandtest("status")
        self.matchoutput(out, "Aquilon Broker ", "status")

    def test_ib_create_host_success(self):
        LOGGER.info("Testing a valid create host call to the broker")
        with HTTMock(mock_ib_post_204):
            ib_services = IBServices()
            response = ib_services.create_host(self.ip, self.default_payload)
            self.assertIsNone(response)

    def test_ib_create_host_failure(self):
        LOGGER.info("Testing an invalid create host call to the broker")
        with HTTMock(mock_ib_post_400):
            ib_services = IBServices()
            with self.assertRaises(ArgumentError):
                ib_services.create_host(self.ip, self.default_payload)


if __name__ == '__main__':
    bootstrap_tests.setup_logger()
    unittest.main()
