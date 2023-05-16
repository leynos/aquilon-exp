import os
import sys
import shutil

SRC_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
sys.path.append(os.path.join(SRC_DIR, "tests"))
sys.path.append(os.path.join(SRC_DIR, "lib"))

import depends  # NOQA pylint: disable=W0611
# These must come first - do not allow this to be reordered.
import aquilon.aqdb.depends  # NOQA pylint: disable=W0611
import aquilon.worker.depends  # NOQA pylint: disable=W0611

from aquilon.config import Config
from broker.brokertest import TestBrokerCommand
from broker.test_ib_services_start import TestIBServicesStart
from broker.test_restart import TestBrokerReStart
from broker.test_stop import TestBrokerStop
from start_ib_services import run_server

try:
    from http_client import HTTPConnection
except ImportError:
    from httplib import HTTPConnection

import logging

try:
    import ms.version
except ImportError:
    pass
else:
    ms.version.addpkg("coloredlogs", "14.0")
    ms.version.addpkg("httmock", "1.2.6")
    ms.version.addpkg("httplib2", "0.9-py27")
    ms.version.addpkg("humanfriendly", "8.1")

import coloredlogs

"""
This object makes some attempt to wrap up and re-use the existing test code in order to start and stop the AQ broker
and HTTP IB services proxy, for the benefit of the isolated unit tests.
"""


LOGGER = logging.getLogger(__name__)
LOG_FORMAT = '%(asctime)s %(levelname).1s [%(threadName)s] [%(module)s:%(funcName)s:%(lineno)d] %(message)s'


def setup_logger(level = logging.INFO):
    HTTPConnection.debuglevel = 1
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(level)
    requests_log.propagate = True
    coloredlogs.install(
        logger=logging.getLogger(),
        fmt=LOG_FORMAT,
        level=level
    )


IBSERVICES_BROKER = None


def start_brokers():
    # Setup static variables in this base class
    TestBrokerCommand.setUpClass()
    # Clear DSDB mock history
    TestBrokerCommand(methodName="setUp").setUp()

    # Copy the template database into position before broker starts
    config = Config()
    modeldb = config.get("unittest", "model_database_location")
    if not os.path.exists(modeldb):
        LOGGER.error("The model database ({}) is missing or not configured under unittest.model_database_location".format(modeldb))
        sys.exit(1)
    testdb = config.get("unittest", "test_database_location")
    LOGGER.info("Copying model database {} to {}".format(modeldb, testdb))
    shutil.copyfile(modeldb, testdb)

    LOGGER.info("Starting aq broker as separate process")
    TestBrokerReStart.setUpClass()
    broker = TestBrokerReStart(methodName="teststart")
    broker.teststart()

    global IBSERVICES_BROKER
    if not IBSERVICES_BROKER:
        IBSERVICES_BROKER = TestIBServicesStart(methodName="test_ibservices_start").test_ibservices_start()

def stop_brokers():
    LOGGER.info("Stopping aq broker")
    TestBrokerStop.setUpClass()
    TestBrokerStop(methodName="teststop").teststop()
