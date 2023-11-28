import logging
import socket
import sys
import threading
import time
import unittest

from mock_ib_services import run_server, PORT

from http.client import HTTPConnection

try:
    import ms.version
except ImportError:
    pass
else:
    ms.version.addpkg("coloredlogs", "14.0")
    ms.version.addpkg("humanfriendly", "8.1")
import coloredlogs

LOGGER = logging.getLogger(__name__)
LOG_FORMAT = '%(asctime)s %(levelname).1s [%(threadName)s] [%(module)s:%(funcName)s:%(lineno)d] %(message)s'


class TestIBServicesStart(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        level = logging.INFO
        HTTPConnection.debuglevel = 1
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(level)
        requests_log.propagate = True
        coloredlogs.install(
            logger=logging.getLogger(),
            fmt=LOG_FORMAT,
            level=level
        )

    def test_ibservices_start(self):
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

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestIBServicesStart)
    unittest.TextTestRunner(verbosity=2).run(suite)
