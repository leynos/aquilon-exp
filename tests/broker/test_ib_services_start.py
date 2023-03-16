import sys

import logging
import socket
import threading
import time
import unittest
from start_ib_services import run_server, PORT

if __name__ == "__main__":
    import utils
    utils.import_depends()

LOGGER = logging.getLogger(__name__)


class TestIBServicesStart(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    def test_ibservices_start(self):
        logging.getLogger('ib-services').setLevel(logging.DEBUG)
        LOGGER.info("Starting ib services proxy in thread")
        ibs_broker = threading.Thread(target=run_server)
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
