import logging
import socket
import sys
import threading
import time
import unittest

from start_ib_services import run_server, PORT, IBServicesRequestHandler, UnitTestIBServicesRequestHandler

if __name__ == "__main__":
    import utils
    utils.import_depends()

LOGGER = logging.getLogger(__name__)


class TestIBServicesStart(unittest.TestCase):
    HANDLER = IBServicesRequestHandler

    def test_ibservices_start(self):
        LOGGER.info("Starting ib services proxy in thread with HTTP handler {}".format(TestIBServicesStart.HANDLER))
        ibs_broker = threading.Thread(target=run_server, args=(TestIBServicesStart.HANDLER,))
        ibs_broker.daemon = True
        ibs_broker.start()

        # Wait for proxy to start
        open = False
        attempts = 0
        while not open and attempts<5:
            attempts += 1
            time.sleep(1)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', PORT))
            sock.close()
            if result == 0:
                open = True
        if not open:
            LOGGER.warning("The IB services proxy has not started")
            sys.exit(1)

        return ibs_broker


class TestIBServicesStartForUnits(TestIBServicesStart):
    """ Start the IB services mock broker with no functionality beyond reporting success for all invocations """

    @classmethod
    def setUpClass(cls):
        TestIBServicesStart.HANDLER = UnitTestIBServicesRequestHandler
