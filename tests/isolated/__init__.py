# This must come first as it includes dependencies
import bootstrap_tests

from broker.brokertest import TestBrokerCommand
from isolated import bootstrap_tests
from start_ib_services import add_callback


class BaseIsolatedTest(TestBrokerCommand):
    IB_SERVICES_CALLBACKS = {}

    @classmethod
    def setUpClass(cls):
        bootstrap_tests.setup_logger()
        bootstrap_tests.start_brokers()

        """
        We listen for HTTP requests to the proxy, so we can verify a transaction took place through the broker
        invoking ib-services.
        """

        def ib_proxy_callback(data):
            if data["method"] not in cls.IB_SERVICES_CALLBACKS:
                cls.IB_SERVICES_CALLBACKS[data["method"]] = []
            cls.IB_SERVICES_CALLBACKS[data["method"]].append(data["path"])

        add_callback(ib_proxy_callback)

    @classmethod
    def tearDownClass(cls):
        bootstrap_tests.stop_brokers()

    def assert_create_host(self):
        self.assertIn("POST", BaseIsolatedTest.IB_SERVICES_CALLBACKS,
                      "The ib-services POST endpoint was not invoked")

    def assert_delete_host(self, path=None):
        self.assertIn("DELETE", BaseIsolatedTest.IB_SERVICES_CALLBACKS,
                      "The ib-services DELETE endpoint was not invoked")
        if path:
            self.assertIn(path, BaseIsolatedTest.IB_SERVICES_CALLBACKS["DELETE"],
                          "The ib-services DELETE endpoint was not invoked with path {}".format(path))
