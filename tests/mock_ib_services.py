import json
import logging

from SimpleHTTPServer import SimpleHTTPRequestHandler
from SocketServer import TCPServer

LOGGER = logging.getLogger('ib-services')
PORT = 8900


class HTTPMonitor(object):
    def __init__(self):
        self.reset()

    def reset(self):
        self.expects = []
        self.invoked_without_expected_test = False

    def expect(self, testcase):
        self.expects.append(testcase)


http_monitor = HTTPMonitor()


class IBServicesRequestHandler(SimpleHTTPRequestHandler, object):
    def do_DELETE(self):
        self._handle_request()

    def do_GET(self):
        self._handle_request()

    def do_PATCH(self):
        self._handle_request()

    def do_POST(self):
        self._handle_request()

    def _handle_request(self):
        content_length = int(self.headers.getheader('content-length', 0))
        body = self.rfile.read(content_length)

        if http_monitor.expects:
            test_case = http_monitor.expects.pop(0)
            r = test_case["request"]

            assert r["method"] == self.command, "Expected request with method '{}', got '{}' instead".format(
                r["method"], self.command)

            assert r["path"] == self.path, "Expected request with path '{}', got '{}' instead".format(
                r["path"], self.path)

            if body:
                expected_body = json.dumps(r["payload"], sort_keys=True)
                got_body = json.dumps(json.loads(body), sort_keys=True)
                assert expected_body == got_body, "Expected {} request with payload:\n '{}'\nbut got:\n '{}'".format(
                    r["method"], expected_body, got_body)
            else:
                assert r["payload"] is None, "Expected {} request with no payload, but received:\n '{}'".format(
                    r["method"], r["payload"])

            self.send_response(test_case["response"]["code"])
        else:
            http_monitor.invoked_without_expected_test = True

            # When this happens is because the test suite sent a request for
            # which a corresponding ib_expect call has not been made
            raise AssertionError("Mock IB server received unexpected request: {} {} {}".format(
                self.command, self.path, body))


class IBServicesServer(TCPServer):
    allow_reuse_address = True

def run_server(handler = IBServicesRequestHandler):
    httpd = IBServicesServer(("", PORT), handler)
    LOGGER.info("Starting ib-services HTTP proxy on port: {0}".format(PORT))
    httpd.serve_forever()


def ib_test_case(method, path, payload, response_code, response_body):
    return {
        "request": {
            "method": method,
            "path": path,
            "payload": payload
        },
        "response": {
            "code": response_code,
            "payload": response_body
        }
    }

eonid = "1156"

def ib_expect_add_address(fqdn, ip, reverse_ptr=None, create_ptr=True, ttl=None, response_code=201, response_body="", fail=False):
    ip = str(ip)
    if fail:
        response_code = 400
    payload = {"name": fqdn, "create_ptr": create_ptr, "address": ip, "eonid": eonid}
    if ttl:
        payload["ttl"] = ttl
    if reverse_ptr:
        payload["assign_ptr_to_fqdn"] = reverse_ptr
    test_case = ib_test_case("POST", "/dns/a_ptr", payload, response_code, response_body)
    http_monitor.expect(test_case)


def ib_expect_update_address(fqdn, original_ip, new_ip=None, reverse_ptr=None,
                             new_ttl=None, response_code=204, response_body="", update_ptr=True,
                             fail = False):
    original_ip = str(original_ip)
    if fail:
        response_code = 400
    payload = {"create_if_doesnt_exist": True, "eonid": eonid}
    if new_ip:
        payload["address"] = str(new_ip)
    if reverse_ptr is not None:
        payload["assign_ptr_to_fqdn"] = reverse_ptr
    payload["update_ptr"] = update_ptr
    if new_ttl:
        payload["ttl"] = new_ttl

    test_case = ib_test_case(
        "PATCH",
        "/dns/a_ptr/{}/{}".format(fqdn, original_ip),
        payload, response_code, response_body)
    http_monitor.expect(test_case)


def ib_expect_del_address(fqdn, ip, delete_ptr=True, response_code=204, response_body="", fail=False):
    ip = str(ip)
    if fail:
        response_code = 400
    test_case = ib_test_case(
        "DELETE",
        "/dns/a_ptr/{}/{}?delete_ptr={}&eonid={}".format(str(fqdn), ip, str(delete_ptr).lower(), eonid),
        None, response_code, response_body)
    http_monitor.expect(test_case)


def ib_expect_add_alias(fqdn, target, ttl=None, response_code=201, response_body="", fail=False):
    if fail:
        response_code = 400
    payload = {"name": fqdn, "target": target, "eonid": eonid}
    if ttl:
        payload["ttl"] = ttl
    test_case = ib_test_case(
        "POST",
        "/dns/aliases",
        payload, response_code, response_body)
    http_monitor.expect(test_case)


def ib_expect_update_alias(fqdn, target=None, ttl=None, response_code=204, response_body="", fail=False):
    if fail:
        response_code = 400
    payload = {"eonid": eonid}
    if target:
        payload["target"] = target
    if ttl:
        payload["ttl"] = ttl
    test_case = ib_test_case(
        "PATCH",
        "/dns/aliases/{}".format(fqdn),
        payload, response_code, response_body)
    http_monitor.expect(test_case)


def ib_expect_del_alias(fqdn, response_code=204, response_body="", fail=False):
    if fail:
        response_code = 400
    test_case = ib_test_case(
        "DELETE",
        "/dns/aliases/{}?eonid={}".format(fqdn, eonid),
        None, response_code, response_body)
    http_monitor.expect(test_case)
