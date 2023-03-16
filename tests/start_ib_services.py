#!/usr/bin/env python
import sys

import httplib
import json
import logging
import os
import re
from SimpleHTTPServer import SimpleHTTPRequestHandler
from SocketServer import TCPServer
from aquilon.config import Config

CALLBACKS = []
FIXTURES = dict()
LOGGER = logging.getLogger('ib-services')
HOST_PATH = re.compile(r'^/hosts/ipv4addr/((\d+\.){3}\d+)$')
PORT = 8900
QUERIES_NETWORK_BY_IP_PATH = re.compile(r'^/queries/network_by_ip/((\d+\.){3}\d+)$')
QUERIES_NEXT_AVAILABLE_IPS_PATH = re.compile(r'^/queries/next_available_ips/((\d+\.){3}\d+/\d+)(\?.*)$')


class IBServicesRequestHandler(SimpleHTTPRequestHandler, object):

    def inform_callbacks(self, method, path):
        for callback in CALLBACKS:
            callback({"method":method, "path":path})

    def do_GET(self):
        self.inform_callbacks("GET", self.path)

        LOGGER.info("Received GET request: {0}".format(self.path))
        response_code = httplib.OK

        if QUERIES_NETWORK_BY_IP_PATH.match(self.path):
            # This is network_by_ip endpoint
            ib_endpoint = "network_by_ip"
            ip_address = QUERIES_NETWORK_BY_IP_PATH.match(self.path).group(1)
            # Is this ip address defined in the test fixtures?
            for fixture in FIXTURES.get(ib_endpoint, []):
                if fixture.get('ip_address', None) == ip_address:
                    output = fixture.pop("output", None)
                    if output:
                        output = json.dumps(output)
                        LOGGER.info("Responding with HTTP {} and payload {}".format(httplib.OK, output))
                        self.send_response(httplib.OK)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(output)
                        return

            LOGGER.warning("Failed to find fixture for ip address {}".format(ip_address))
            response_code = httplib.BAD_REQUEST

            # Default, validation error (invalid mac address, badly formatted JSON, etc)
            if not response_code:
                response_code = httplib.UNPROCESSABLE_ENTITY

        if QUERIES_NEXT_AVAILABLE_IPS_PATH.match(self.path):
            # This is next_available_ip endpoint
            ib_endpoint = "next_available_ip"
            network = QUERIES_NEXT_AVAILABLE_IPS_PATH.match(self.path).group(1)
            # Is this network defined in the test fixtures?
            for fixture in FIXTURES.get(ib_endpoint, []):
                if fixture.get('network', None) == network:
                    output = fixture.pop("output", None)
                    if output:
                        output = json.dumps(output)
                        LOGGER.info("Responding with HTTP {} and payload {}".format(httplib.OK, output))
                        self.send_response(httplib.OK)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(output)
                        return

            LOGGER.warning("Failed to find fixture for network {}".format(network))
            response_code = httplib.BAD_REQUEST

            # Default, validation error (invalid mac address, badly formatted JSON, etc)
            if not response_code:
                response_code = httplib.UNPROCESSABLE_ENTITY

        LOGGER.info("Responding with HTTP {0}".format(response_code))
        self.send_response(response_code)

    def do_POST(self):
        self.inform_callbacks("POST", self.path)

        if HOST_PATH.match(self.path):
            # This is create_host endpoint
            ib_endpoint = "create_host"
            LOGGER.info("Received POST request: {0}".format(self.path))
            content_length = int(self.headers.getheader('content-length', 0))
            body = json.loads(self.rfile.read(content_length))
            LOGGER.debug("Request body: {0}".format(body))
            # Use-case where a host already exists in Infoblox
            hostname = body.get("hostname", "")
            if self.check_if_exists(ib_endpoint, hostname):
                response_code = httplib.BAD_REQUEST
            # Use-case where a host is successfully created in Infoblox
            elif self.validate_request_body(ib_endpoint, hostname):
                response_code = httplib.CREATED
            # Default, validation error (invalid mac address, badly formatted JSON, etc)
            else:
                response_code = httplib.UNPROCESSABLE_ENTITY
            LOGGER.info("Responding with HTTP {0}".format(response_code))
            self.send_response(response_code)

    def validate_request_body(self, endpoint, hostname):
        return hostname in FIXTURES.get(endpoint, {}).get('allow_hostnames', [])

    def check_if_exists(self, endpoint, hostname):
        if hostname in FIXTURES.get(endpoint, {}).get("deny_hostnames", []):
            LOGGER.info("Hostname {0} already exists in Infoblox".format(hostname))
            return True


class IBServicesServer(TCPServer):
    allow_reuse_address = True


def run_server():
    path = os.path.join(Config().get("unittest", "datadir"), "ib-services.json")
    LOGGER.info("Loading fixture file: {}".format(path))
    global FIXTURES
    FIXTURES = _load_ib_services_fixture(path)
    LOGGER.debug("Loaded fixtures: {}".format(json.dumps(FIXTURES, indent=4)))

    handler = IBServicesRequestHandler
    httpd = IBServicesServer(("", PORT), handler)
    LOGGER.info("Starting ib-services HTTP proxy on port: {0}".format(PORT))
    httpd.serve_forever()


def _load_ib_services_fixture(path):
    try:
        with open(path) as f:
            return json.load(f)
    except ValueError as e:
        LOGGER.warning("Failed to load fixtures from JSON file {}: {}".format(file, str(e)))
        sys.exit(1)


def add_fixture_get_network_by_ip(ip, network):
    """
    When network_by_ip is invoked for the given ip, return network once.
    """
    global FIXTURES
    FIXTURES["network_by_ip"].append({
      "ip_address": ip,
      "output": {
        "network": network
      }
    })


def add_fixture_get_next_ip(network, ip):
    """
    When next_available_ip is invoked for the given network, return ip once.
    """
    global FIXTURES
    FIXTURES["next_available_ip"].append({
      "network": network,
      "output": {
        "ips": [ ip ]
    }})


def add_callback(callback):
    """ Add a callback to inform tests when this broker receives an HTTP request """
    CALLBACKS.append(callback)
