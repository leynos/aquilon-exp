import json
import logging
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer
from urllib.parse import quote_plus, urlencode, urlparse, urlunparse

from aquilon.exceptions_ import ArgumentError

LOGGER = logging.getLogger("ib-services")
LOGGER.setLevel(logging.DEBUG)
PORT = 8900


class HTTPMonitor:

    def __init__(self):
        self.reset()

    def reset(self):
        self.expects = []
        self.invoked_without_expected_test = False

    def expect(self, testcase):
        self.expects.append(testcase)


http_monitor = HTTPMonitor()


class IBServicesRequestHandler(SimpleHTTPRequestHandler):
    def do_DELETE(self):
        self._handle_request()

    def do_GET(self):
        self._handle_request()

    def do_PATCH(self):
        self._handle_request()

    def do_POST(self):
        self._handle_request()

    def log_request(self, code="-", size="-"):
        """overewrite to not log any request"""

    def _handle_request(self):
        unique_id = self.headers.get("X-MS-Unique-ID")
        assert unique_id is not None and len(str(unique_id)) > 0, "Expected X-MS-Unique-ID header"

        content_length = int(self.headers.get("content-length", 0))
        body = self.rfile.read(content_length)

        if http_monitor.expects:
            test_case = http_monitor.expects.pop(0)
            r = test_case["request"]

            assert r["method"] == self.command, "Expected request {} {} {}, got {} {} {}".format(
                r["method"], r["path"], r["payload"], self.command, self.path, body)

            assert r["path"] == self.path, "Expected {} request {} {}, got {} {}".format(
                r["method"], r["path"], r["payload"], self.path, body)

            if body:
                expected_body = json.dumps(r["payload"], sort_keys=True)
                got_body = json.dumps(json.loads(body), sort_keys=True)
                assert expected_body == got_body, "{} {}: Expected request with payload:\n '{}'\ngot:\n '{}'".format(
                    r["method"], r["path"], expected_body, got_body)
            else:
                assert r["payload"] is None, "{} {}: Expected request with no payload, but received:\n '{}'".format(
                    r["method"], r["path"], r["payload"])

            self.send_response(code=test_case["response"]["code"])
            self.end_headers()
        else:
            http_monitor.invoked_without_expected_test = True
            # When this happens is because the test suite sent a request for
            # which a corresponding ib_expect call has not been made
            msg = f"Mock IB server received unexpected request: {self.command} {self.path} {body}"
            self.send_response(code=400, message=msg)
            self.end_headers()
            raise AssertionError(msg)


class IBServicesServer(TCPServer):
    allow_reuse_address = True


def run_server(handler=IBServicesRequestHandler):
    httpd = IBServicesServer(("", PORT), handler)
    LOGGER.info(f"Starting ib-services HTTP proxy on port: {PORT}")
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

def ib_expect_add_ptr(fqdn, ip, ttl=None, response_code=201, response_body="", justification=None, fail=False):
    ip = str(ip)
    if fail:
        response_code = 400
    payload = {
        "name": fqdn,
        "address": ip,
        "eonid": eonid,
    }
    if ttl:
        payload["ttl"] = ttl
    if justification is not None:
        payload["cm_token"] = justification

    test_case = ib_test_case("POST", "/dns/a_ptr/ptr", payload, response_code, response_body)
    http_monitor.expect(test_case)


def ib_expect_del_ptr(ip, response_code=204, response_body="", justification=None, fail=False):
    ip = str(ip)
    if fail:
        response_code = 400
    path = "/dns/a_ptr/ptr/{}?eonid={}".format(ip, eonid)
    if justification is not None:
        path = path + "&cm_token={}".format(quote_plus(justification))
    test_case = ib_test_case(
        "DELETE",
        path,
        None, response_code, response_body)
    http_monitor.expect(test_case)


def ib_expect_update_ptr(ip, new_fqdn, new_ttl=None, response_code=201, response_body="", justification=None,
                         fail=False):
    ip = str(ip)
    if fail:
        response_code = 400
    payload = {
        "name": new_fqdn,
        "eonid": eonid,
    }
    if new_ttl:
        payload["ttl"] = new_ttl
    if justification is not None:
        payload["cm_token"] = justification

    test_case = ib_test_case("PATCH", "/dns/a_ptr/ptr/{}".format(ip), payload, response_code, response_body)
    http_monitor.expect(test_case)


def ib_expect_add_a(fqdn, ip, ttl=None, response_code=201, response_body="", justification=None, fail=False):
    ip = str(ip)
    if fail:
        response_code = 400
    payload = {
        "name": fqdn,
        "address": ip,
        "eonid": eonid,
    }
    if ttl:
        payload["ttl"] = ttl
    if justification is not None:
        payload["cm_token"] = justification

    test_case = ib_test_case("POST", "/dns/a_ptr/a", payload, response_code, response_body)
    http_monitor.expect(test_case)


def ib_expect_del_a(fqdn, ip, response_code=204, response_body="", justification=None, fail=False):
    ip = str(ip)
    if fail:
        response_code = 400
    path = "/dns/a_ptr/a/{}/{}?eonid={}".format(str(fqdn), ip, eonid)
    if justification is not None:
        path = path + "&cm_token={}".format(quote_plus(justification))
    test_case = ib_test_case(
        "DELETE",
        path,
        None, response_code, response_body)
    http_monitor.expect(test_case)


def ib_expect_update_a(fqdn, original_ip, new_ip=None,
                       new_ttl=None, response_code=204, response_body="",
                       justification=None, fail=False):
    original_ip = str(original_ip)
    if fail:
        response_code = 400
    payload = {"eonid": eonid}
    if new_ip:
        payload["address"] = str(new_ip)
    if new_ttl:
        payload["ttl"] = new_ttl
    if justification is not None:
        payload["cm_token"] = justification

    test_case = ib_test_case(
        "PATCH",
        "/dns/a_ptr/a/{}/{}".format(fqdn, original_ip),
        payload, response_code, response_body)
    http_monitor.expect(test_case)


def ib_expect_add_address(fqdn, ip, reverse_ptr=None, create_ptr=True, ttl=None, response_code=201, response_body="",
                          justification=None, fail=False):
    ip = str(ip)
    if fail:
        response_code = 400
    payload = {
        "create_ptr": create_ptr,
        "address": ip,
        "eonid": eonid,
        "create_if_doesnt_exist": True,
        "update_ptr": False,
    }
    if ttl:
        payload["ttl"] = ttl
    if reverse_ptr:
        payload["assign_ptr_to_fqdn"] = reverse_ptr
    if justification is not None:
        payload["cm_token"] = justification

    test_case = ib_test_case("PATCH", f"/dns/a_ptr/{fqdn}/{ip}", payload, response_code, response_body)
    http_monitor.expect(test_case)


def ib_expect_update_address(fqdn, original_ip, new_ip=None, reverse_ptr=None,
                             new_ttl=None, response_code=204, response_body="", update_ptr=True,
                             create_ptr=False, justification=None, fail=False):
    original_ip = str(original_ip)
    if fail:
        response_code = 400
    payload = {"create_if_doesnt_exist": True, "eonid": eonid}
    if new_ip:
        payload["address"] = str(new_ip)
    if reverse_ptr is not None:
        payload["assign_ptr_to_fqdn"] = reverse_ptr
    payload["create_ptr"] = create_ptr
    payload["update_ptr"] = update_ptr
    if new_ttl:
        payload["ttl"] = new_ttl
    if justification is not None:
        payload["cm_token"] = justification

    test_case = ib_test_case(
        "PATCH",
        f"/dns/a_ptr/{fqdn}/{original_ip}",
        payload, response_code, response_body)
    http_monitor.expect(test_case)


def ib_expect_del_address(fqdn, ip, delete_ptr=True, response_code=204, response_body="", justification=None,
                          fail=False):
    ip = str(ip)
    if fail:
        response_code = 400
    path = f"/dns/a_ptr/{str(fqdn)}/{ip}?delete_ptr={str(delete_ptr).lower()}&eonid={eonid}"
    if justification is not None:
        path = path + f"&cm_token={quote_plus(justification)}"
    test_case = ib_test_case(
        "DELETE",
        path,
        None, response_code, response_body)
    http_monitor.expect(test_case)


def ib_expect_add_alias(fqdn, target, ttl=None, response_code=204, response_body="", justification=None, fail=False):
    return ib_expect_update_alias(fqdn, target=target, ttl=ttl, response_code=response_code,
                                  response_body=response_body, justification=justification, fail=fail)


def ib_expect_update_alias(fqdn, target=None, ttl=None, response_code=204, response_body="", justification=None,
                           fail=False):
    if fail:
        response_code = 400
    payload = {"eonid": eonid, "create_if_doesnt_exist": True}
    if target:
        payload["target"] = target
    if ttl:
        payload["ttl"] = ttl
    if justification is not None:
        payload["cm_token"] = justification
    test_case = ib_test_case(
        "PATCH",
        f"/dns/aliases/{fqdn}",
        payload, response_code, response_body)
    http_monitor.expect(test_case)


def ib_expect_del_alias(fqdn, response_code=204, response_body="", justification=None, fail=False):
    if fail:
        response_code = 400
    path = f"/dns/aliases/{fqdn}?eonid={eonid}"
    if justification is not None:
        path = path + f"&cm_token={quote_plus(justification)}"
    test_case = ib_test_case(
        "DELETE",
        path,
        None, response_code, response_body)
    http_monitor.expect(test_case)


def ib_expect_add_range(name, start_address, end_address, response_code=201, response_body="", justification=None,
                        fail=False):
    if fail:
        response_code = 400
    payload = {"eonid": eonid, "name": name, "start_address": start_address, "end_address": end_address}
    if justification is not None:
        payload["cm_token"] = justification
    test_case = ib_test_case("POST", "/ranges", payload, response_code, response_body)
    http_monitor.expect(test_case)


def ib_expect_del_range(start_address, end_address, response_code=204, response_body="", justification=None,
                        fail=False):
    if fail:
        response_code = 400
    path = f"/ranges/{start_address}/{end_address}?eonid={eonid}"
    if justification is not None:
        path = path + f"&cm_token={quote_plus(justification)}"
    test_case = ib_test_case(
        "DELETE",
        path,
        None, response_code, response_body)
    http_monitor.expect(test_case)


def ib_expect_show_range(start_address, end_address, response_code=200, response_body="", fail=False):
    if fail:
        response_code = 404
    test_case = ib_test_case(
        "GET",
        f"/ranges/{start_address}/{end_address}",
        None, response_code, response_body)
    http_monitor.expect(test_case)

def ib_expect_add_dns_srv_record(service, protocol, dns_domain, target, port, priority, weight, ttl=None,
                                 response_code=201, response_body="", justification=None, fail=False):
    if fail:
        response_code = 400
    payload = {
        "eonid":    eonid,
        "service":  service,
        "domain":   str(dns_domain),
        "target":   str(target),
        "port":     port,
        "priority": priority,
        "weight":   weight,
        "protocol": protocol,
    }
    if ttl:
        payload["ttl"] = ttl
    if justification is not None:
        payload["cm_token"] = justification

    test_case = ib_test_case("POST", "/dns/srv", payload, response_code, response_body)
    http_monitor.expect(test_case)


def _generate_url_from_params(url, params):
    parse = urlparse(url)._replace(query=urlencode(params))
    return urlunparse(parse)


def ib_expect_update_dns_srv_record(old, new, response_code=204, response_body="", justification=None, fail=False):
    if fail:
        response_code = 400

    required_fields = ("service", "protocol", "domain", "port", "target", "weight", "priority",)
    payload = {}

    for field in required_fields:
        if old.get(field, None) is None:
            raise ArgumentError(f"Required argument '{field}' is missing")
        payload[field] = new[field] if new.get(field, None) else old[field]

    if new.get("ttl", None):
        payload["ttl"] = new["ttl"]
    if payload.get("domain", None):
        payload["domain"] = str(payload["domain"])
    if payload.get("target", None):
        payload["target"] = str(payload["target"])
    payload["eonid"] = eonid

    if justification is not None:
        payload["cm_token"] = justification

    params = dict(filter(lambda item: item[1] is not None, old.items()))
    url = _generate_url_from_params("/dns/srv", params)

    test_case = ib_test_case("PATCH", url, payload, response_code, response_body)
    http_monitor.expect(test_case)


def ib_expect_del_dns_srv_record(service, protocol, dns_domain, target, port=None, priority=None, weight=None,
                                 response_code=204, response_body="", justification=None, fail=False):
    if fail:
        response_code = 400

    options = {
        "eonid":    eonid,
        "service":  service,
        "protocol": protocol,
        "domain":   dns_domain,
        "target":   target,
        "port":     port,
        "priority": priority,
        "weight":   weight,
        "cm_token": justification,
    }

    params = dict(filter(lambda item: item[1] is not None, options.items()))
    url = _generate_url_from_params("/dns/srv", params)

    test_case = ib_test_case("DELETE", url, None, response_code, response_body)
    http_monitor.expect(test_case)
