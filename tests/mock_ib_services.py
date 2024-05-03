import json
import logging
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer
from urllib.parse import parse_qs, quote_plus, urlencode, urlparse, urlunparse
import re

from aquilon.exceptions_ import ArgumentError
from aq_test_client import AqTestClient

import ms.version
ms.version.addpkg('protobuf', '4.23.1')
ms.version.addpkg("protocols", "2024.01.25-1", meta="aquilon")

from aqddnsdomains_pb2 import DNSRecordList, DNSRecordData, DNSDomainList
from aqdsystems_pb2 import HostList

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

class DNSData():
    def __init__(self, init=None):
        self.dns_data = DNSRecordList()
        if init is not None:
            self.dns_data.CopyFrom(init)

    def __str__(self):
        return str(self.dns_data.records)

    def add_a(self, fqdn, target, ttl=None):
        self._add_item(
            rrtype=DNSRecordData.DNSRecordType.A,
            fqdn=fqdn,target=target,ttl=ttl)

    def delete_a(self, fqdn, target):
        self._delete_item(DNSRecordData.DNSRecordType.A, fqdn, target)

    def update_a(self, from_fqdn, from_target, to_target, to_ttl=None):
        self._update_item(DNSRecordData.DNSRecordType.A, from_fqdn=from_fqdn, from_target=from_target, to_target=to_target, to_ttl=to_ttl)

    def add_cname(self, fqdn, target, ttl=None):
        self._add_item(
            rrtype=DNSRecordData.DNSRecordType.CNAME,
            fqdn=fqdn,target=target,ttl=ttl)

    def delete_cname(self, fqdn):
        self._delete_item(DNSRecordData.DNSRecordType.CNAME, fqdn)

    def update_cname(self, from_fqdn, to_target, to_ttl=None):
        self._update_item(DNSRecordData.DNSRecordType.CNAME, from_fqdn=from_fqdn, to_target=to_target, to_ttl=to_ttl)

    def add_ptr(self, fqdn, target, ttl=None):
        self._add_item(
            rrtype=DNSRecordData.DNSRecordType.PTR,
            fqdn=self._in_arpa_address(fqdn),target=target,ttl=ttl)

    def delete_ptr(self, fqdn):
        self._delete_item(DNSRecordData.DNSRecordType.PTR, self._in_arpa_address(fqdn))

    def update_ptr(self, from_fqdn, to_target, to_ttl=None):
        self._update_item(DNSRecordData.DNSRecordType.PTR, from_fqdn=self._in_arpa_address(from_fqdn), to_target=to_target, to_ttl=to_ttl)

    def _in_arpa_address(self, ip):
        octets = str(ip).split('.')
        octets.reverse()
        return "%s.in-addr.arpa" % '.'.join(octets)

    def add_srv(self, service, protocol, domain, target, priority=None, weight=None, port=None, ttl=None):
        self._add_item(
            rrtype=DNSRecordData.DNSRecordType.SRV,
            fqdn=self._get_srv_fqdn(service, protocol, domain),
            target=target, ttl=ttl, priority=priority, weight=weight, port=port)

    def update_srv(self, from_service, from_protocol, from_domain, from_target, from_priority, from_weight, from_port, from_ttl, to_service, to_protocol, to_domain, to_target, to_priority, to_weight, to_port, to_ttl):
        self._update_item(
            rrtype=DNSRecordData.DNSRecordType.SRV,
            from_fqdn=self._get_srv_fqdn(from_service, from_protocol, from_domain),
            from_target=from_target, from_priority=from_priority, from_weight=from_weight, from_port=from_port,
            to_fqdn=self._get_srv_fqdn(to_service, to_protocol, to_domain),
            to_target=to_target, to_priority=to_priority, to_weight=to_weight, to_port=to_port, to_ttl=to_ttl)

    def delete_srv(self, service, protocol, domain, target, priority, weight, port):
        self._delete_item(DNSRecordData.DNSRecordType.SRV, self._get_srv_fqdn(service, protocol, domain), target=target, priority=priority, weight=weight, port=port)

    def _get_srv_fqdn(self, service, protocol, domain):
        return f"_{service}._{protocol}.{domain}"

    def _add_item(self, rrtype, fqdn, target, ttl=None, priority=None, weight=None, port=None):
        dns_records = list(filter(lambda d: d.fqdn == fqdn, self.dns_data.records))
        dns_record = None
        if dns_records:
            dns_record = dns_records[0]
        else:
            dns_record = self.dns_data.records.add()
            dns_record.fqdn = fqdn
        rr = dns_record.rdata.add()
        rr.rrtype = rrtype
        rr.target = target
        if ttl is not None and ttl != -1:
            rr.ttl = ttl
        if priority is not None:
            rr.priority = priority
        if weight is not None:
            rr.weight = weight
        if port is not None:
            rr.port = port

    def _delete_item(self, rrtype, fqdn, target=None, priority=None, weight=None, port=None):
        (item_to_remove, rdata_to_remove) = self._find_item(rrtype, fqdn, target, priority, weight, port)

        if rdata_to_remove is not None:
            if len(item_to_remove.rdata) == 1:
                self.dns_data.records.remove(item_to_remove)
            else:
                item_to_remove.rdata.remove(rdata_to_remove)

    def _update_item(self, rrtype, from_fqdn=None, from_target=None, from_priority=None, from_weight=None, from_port=None, to_fqdn=None, to_target=None, to_ttl=None, to_priority=None, to_weight=None, to_port=None):
        if from_fqdn is None and from_target is None:
            raise Exception("fqdn and target can't both be None")

        (item_to_update, rdata_to_update) = self._find_item(rrtype, from_fqdn, from_target, from_priority, from_weight, from_port)

        if item_to_update is not None:
            if to_fqdn is not None:
                item_to_update.fqdn = to_fqdn
            if to_target is not None:
                rdata_to_update.target = to_target
            if to_ttl is not None:
                if int(to_ttl) == -1:
                    rdata_to_update.ClearField('ttl')
                else:
                    rdata_to_update.ttl = int(to_ttl)
            else:
                rdata_to_update.ClearField('ttl')
            if to_priority is not None:
                rdata_to_update.priority = int(to_priority)
            if to_weight is not None:
                rdata_to_update.weight = int(to_weight)
            if to_port is not None:
                rdata_to_update.port = int(to_port)

    def _find_item(self, rrtype, fqdn, target=None, priority=None, weight=None, port=None):
        item_found = None
        rdata_found = None

        break_outer_loop = False
        for item in self.dns_data.records:
            if item.fqdn == fqdn:
                for rdata in item.rdata:
                    if rdata.rrtype == rrtype and \
                       (target is None or rdata.target == target) and \
                       (priority is None or rdata.priority == int(priority)) and \
                       (weight is None or rdata.weight == int(weight)) and \
                       (port is None or rdata.port == int(port)):
                        item_found = item
                        rdata_found = rdata
                        break_outer_loop = True
                        break
            if break_outer_loop:
                break

        return (item_found, rdata_found)


http_monitor = HTTPMonitor()
ib_dns = None


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

    def _parse_dns(self):

        command = self.command
        if command == 'GET':
            return

        path = self.path
        if re.search('^/ranges', path):
            return

        if path == '/dns/a_ptr/a':
            if command == 'POST':
                host = self.json_body.get("name")
                ip = self.json_body.get("address")
                ttl = self.json_body.get("ttl", None)
                ib_dns.add_a(fqdn=host, target=ip, ttl=ttl)
            else:
                raise Exception(f"Don't know how to handle request {command} {path} {self.body}")

        elif re.search('^/dns/a_ptr/a/([^/]+)/([^/?]+)', path):
            match = re.search('^/dns/a_ptr/a/([^/]+)/([^/?]+)', path)
            from_host = match.group(1)
            from_ip = match.group(2)

            if command == "PATCH":
                to_ip = self.json_body.get("address", None)
                to_ttl = self.json_body.get("ttl", None)
                ib_dns.update_a(from_fqdn=from_host, from_target=from_ip, to_target=to_ip, to_ttl=to_ttl)

            elif command == "DELETE":
                ib_dns.delete_a(from_host, from_ip)

            else:
                raise Exception(f"Don't know how to handle request {command} {path} {self.body}")

        elif path == '/dns/a_ptr/ptr':
            if command == 'POST':
                host = self.json_body.get("name")
                ip = self.json_body.get("address")
                ttl = self.json_body.get("ttl")
                ib_dns.add_ptr(fqdn=ip, target=host, ttl=ttl)
            else:
                raise Exception(f"Don't know how to handle request {command} {path} {self.body}")

        elif re.search('^/dns/a_ptr/ptr/([^/?]+)', path):
            match = re.search('^/dns/a_ptr/ptr/([^/?]+)', path)
            ip = match.group(1)

            if command == "PATCH":
                to_name = self.json_body.get("name", None)
                to_ttl = self.json_body.get("ttl", None)
                ib_dns.update_ptr(from_fqdn=ip, to_target=to_name, to_ttl=to_ttl)
            elif command == "DELETE":
                ib_dns.delete_ptr(fqdn=ip)

            else:
                raise Exception(f"Don't know how to handle request {command} {path} {self.body}")
        elif path == '/dns/aliases/':
            if command == "POST":
                host = self.json_body.get("name")
                target = self.json_body.get("target")
                ttl = self.json_body.get("ttl", None)
                ib_dns.add_cname(fqdn=host, target=target, ttl=ttl)
            else:
                raise Exception(f"Don't know how to handle request {command} {path} {self.body}")
        elif re.search('^/dns/aliases/([^/?]+)', path):
            match = re.search('^/dns/aliases/([^/?]+)', path)
            name = match.group(1)

            if command == "PATCH":
                to_target = self.json_body.get("target", None)
                to_ttl = self.json_body.get("ttl", None)
                ib_dns.update_cname(from_fqdn=name, to_target=to_target, to_ttl=to_ttl)
            elif command == "DELETE":
                ib_dns.delete_cname(fqdn=name)
            else:
                raise Exception(f"Don't know how to handle request {command} {path} {self.body}")
        elif path == '/dns/srv':
            service = self.json_body.get("service")
            protocol = self.json_body.get("protocol")
            domain = self.json_body.get("domain")
            target = self.json_body.get("target")
            priority = self.json_body.get("priority")
            weight = self.json_body.get("weight")
            port = self.json_body.get("port")
            ttl = self.json_body.get("ttl")
            if command == "POST":
                ib_dns.add_srv(service, protocol, domain, target, priority, weight, port, ttl)
            else:
                raise Exception(f"Don't know how to handle request {command} {path} {self.body}")
        elif re.search('^/dns/srv?(.+)$', path):
            qs_args = parse_qs(urlparse(path).query)

            from_service = qs_args.get("service", [None])[0]
            from_protocol = qs_args.get("protocol", [None])[0]
            from_domain = qs_args.get("domain", [None])[0]
            from_target = qs_args.get("target", [None])[0]
            from_priority = qs_args.get("priority", [None])[0]
            from_weight = qs_args.get("weight", [None])[0]
            from_port = qs_args.get("port", [None])[0]
            from_ttl = qs_args.get("ttl", [None])[0]

            to_service = self.json_body.get("service", None)
            to_protocol = self.json_body.get("protocol", None)
            to_domain = self.json_body.get("domain", None)
            to_target = self.json_body.get("target", None)
            to_priority = self.json_body.get("priority", None)
            to_weight = self.json_body.get("weight", None)
            to_port = self.json_body.get("port", None)
            to_ttl = self.json_body.get("ttl", None)
            if command == "PATCH":
                ib_dns.update_srv(from_service, from_protocol, from_domain, from_target, from_priority, from_weight, from_port, from_ttl, to_service, to_protocol, to_domain, to_target, to_priority, to_weight, to_port, to_ttl)
            elif command == "DELETE":
                ib_dns.delete_srv(from_service, from_protocol, from_domain, from_target, from_priority, from_weight, from_port)
            else:
                raise Exception(f"Don't know how to handle request {command} {path} {self.body}")
        else:
            raise Exception(f"Don't know how to handle request {command} {path} {self.body}")


    def _handle_request(self):
        content_length = int(self.headers.get("content-length", 0))
        self.body = self.rfile.read(content_length)
        if self.body:
            self.json_body = json.loads(self.body)
        else:
            self.json_body = {}

        unique_id = self.headers.get("X-MS-Unique-ID")
        assert unique_id is not None and len(str(unique_id)) > 0, "Expected X-MS-Unique-ID header"

        if http_monitor.expects:
            test_case = http_monitor.expects.pop(0)
            r = test_case["request"]

            assert r["method"] == self.command and r["path"] == self.path, "Expected request:\n{} {} {}\ngot:\n{} {} {}\n".format(
                    r["method"], r["path"], r["payload"], self.command, self.path, self.body)

            if self.json_body:
                got_body = json.dumps(self.json_body, sort_keys=True)
                expected_body = json.dumps(r["payload"], sort_keys=True)
                assert expected_body == got_body, "{} {}: Expected request with payload:\n '{}'\ngot:\n '{}'".format(
                    r["method"], r["path"], expected_body, got_body)
            else:
                assert r["payload"] is None, "{} {}: Expected request with no payload, but received:\n '{}'".format(
                    r["method"], r["path"], r["payload"])

            response_code = test_case["response"]["code"]
            if response_code >= 200 and response_code < 300:
                self._parse_dns()

            self.send_response(code=response_code)
            self.end_headers()
        else:
            http_monitor.invoked_without_expected_test = True
            # When this happens is because the test suite sent a request for
            # which a corresponding ib_expect call has not been made
            msg = f"Mock IB server received unexpected request:\n\t{self.command} {self.path} {self.body}"
            self.send_response(code=400, message=msg)
            self.end_headers()
            raise AssertionError(msg)


class IBServicesServer(TCPServer):
    allow_reuse_address = True


def get_ib_dns():
    return ib_dns

def get_aq_dns_data():
    aq = AqTestClient()
    (p, out, err) = aq.runcommand(["dump_dns", "--format", "proto"])

    aq_dns_data = DNSRecordList()
    aq_dns_data.ParseFromString(out.encode("ISO-8859-1"))

    (p, out, err) = aq.runcommand(["show_dns_domain", "--all", "--format", "proto"])
    aq_dns_domains = DNSDomainList()
    aq_dns_domains.ParseFromString(out.encode("ISO-8859-1"))
    restricted_domain_names = list(map(lambda d: d.name, filter(lambda d: d.restricted , aq_dns_domains.dns_domains)))

    (p, out, err) = aq.runcommand(["search_host", "--archetype", "aurora", "--format", "proto"])
    aq_aurora_hosts = HostList()
    aq_aurora_hosts.ParseFromString(out.encode("ISO-8859-1"))
    aurora_fqdns = []
    aurora_ips = []

    for host in aq_aurora_hosts.hosts:
        for iface in host.machine.interfaces:
            aurora_fqdns.append(iface.fqdn)
            aurora_ips.append(iface.ip)

    ib_expected_dns_data = DNSRecordList()
    # This block deals with filtering out records/properties returned by `aq dump dns` that are not sent to infoblox
    # NOTE, this implementation assumes than when a dns_record has multiple rdata items, we either want to keep or discard the all record,
    # ie, it doesn't support the case where we want to keep on rdata but discard the other
    for record in aq_dns_data.records:
        keep_record = False
        # Ignore IPv6 addresses because they are not expected to be sent to infoblox
        for rdata in record.rdata:
            if rdata.rrtype == DNSRecordData.DNSRecordType.AAAA or (rdata.rrtype == DNSRecordData.DNSRecordType.PTR and re.search('ip6.arpa$', record.fqdn)):
                continue
            elif rdata.rrtype == DNSRecordData.DNSRecordType.A:
                # Ignore A-records from restricted domains because they should never be sent to infoblox
                _, _, record_domain = record.fqdn.partition('.')
                if record_domain in restricted_domain_names:
                    continue

                # Ignore A records of dynamic ranges (dynamic range dns entries are not sent to infoblox)
                if record.fqdn[:8] == 'dynamic-':
                    continue

                # Ignore A-records of aurora hosts because they should not be sent to infoblox
                if record.fqdn in aurora_fqdns and rdata.target in aurora_ips:
                    continue
            elif rdata.rrtype == DNSRecordData.DNSRecordType.PTR:
                # Ignore PTR records of aurora hosts
                # this expression converts "D.C.B.A.in-addr.arpa" to "A.B.C.D"
                ip_address = ".".join(record.fqdn.replace(".in-addr.arpa", "").split(".")[::-1])
                if ip_address in aurora_ips and rdata.target in aurora_fqdns:
                    continue

                # Ignore PTR records of dynamic ranges (dynamic range dns entries are not sent to infoblox)
                if rdata.target[:8] == 'dynamic-':
                    continue

            rdata.ClearField('target_environment_name')
            rdata.ClearField('target_network_environment_name')
            keep_record = True

        if keep_record:
            record.ClearField('owner_eonid')
            record.ClearField('environment_name')
            ib_expected_dns_data.records.append(record)

    return ib_expected_dns_data

def run_server(handler=IBServicesRequestHandler):

    global ib_dns
    ib_dns = DNSData(init=get_aq_dns_data())

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


def ib_expect_add_ptr(fqdn, ip, ttl=None, response_code=201, response_body="", justification=None, fail=False):
    ip = str(ip)
    if fail:
        response_code = 400
    payload = {
        "name": fqdn,
        "address": ip,
    }
    if ttl is not None and ttl != -1: #  In ib add_ptr, a ttl value of -1 triggers an error, see http://jiraeai.ms.com/jira/browse/DDI-2982
        payload["ttl"] = ttl
    if justification is not None:
        payload["cm_token"] = justification

    test_case = ib_test_case("POST", "/dns/a_ptr/ptr", payload, response_code, response_body)
    http_monitor.expect(test_case)


def ib_expect_del_ptr(ip, response_code=204, response_body="", justification=None, fail=False):
    ip = str(ip)
    if fail:
        response_code = 400
    path = "/dns/a_ptr/ptr/{}".format(ip)
    if justification is not None:
        path = path + "?cm_token={}".format(quote_plus(justification))
    test_case = ib_test_case(
        "DELETE",
        path,
        None, response_code, response_body)
    http_monitor.expect(test_case)


def ib_expect_update_ptr(ip, new_fqdn, new_ttl=-1, response_code=201, response_body="", justification=None,
                         fail=False):
    ip = str(ip)
    if fail:
        response_code = 400
    payload = {
        "name": new_fqdn,
    }
    if new_ttl is not None:
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
    }
    if ttl is not None:
        payload["ttl"] = ttl
    if justification is not None:
        payload["cm_token"] = justification

    test_case = ib_test_case("POST", "/dns/a_ptr/a", payload, response_code, response_body)
    http_monitor.expect(test_case)


def ib_expect_del_a(fqdn, ip, response_code=204, response_body="", justification=None, fail=False):
    ip = str(ip)
    if fail:
        response_code = 400
    path = "/dns/a_ptr/a/{}/{}".format(str(fqdn), ip)
    if justification is not None:
        path = path + "?cm_token={}".format(quote_plus(justification))
    test_case = ib_test_case(
        "DELETE",
        path,
        None, response_code, response_body)
    http_monitor.expect(test_case)


def ib_expect_update_a(fqdn, original_ip, new_ip=None,
                       new_ttl=-1, response_code=204, response_body="",
                       justification=None, fail=False):
    original_ip = str(original_ip)
    if fail:
        response_code = 400
    payload = {}
    if new_ip:
        payload["address"] = str(new_ip)
    else:
        payload["address"] = str(original_ip)
    if new_ttl is not None:
        payload["ttl"] = new_ttl
    if justification is not None:
        payload["cm_token"] = justification

    test_case = ib_test_case(
        "PATCH",
        "/dns/a_ptr/a/{}/{}".format(fqdn, original_ip),
        payload, response_code, response_body)
    http_monitor.expect(test_case)


def ib_expect_add_alias(fqdn, target, ttl=None, response_code=204, response_body="", justification=None, fail=False):
    if fail:
        response_code = 400
    payload = {"name": fqdn, "target": target}
    if ttl is not None:
        payload["ttl"] = ttl
    if justification is not None:
        payload["cm_token"] = justification
    test_case = ib_test_case(
        "POST",
        "/dns/aliases/",
        payload, response_code, response_body)
    http_monitor.expect(test_case)


def ib_expect_update_alias(fqdn, target=None, ttl=-1, response_code=204, response_body="", justification=None,
                           fail=False):
    if fail:
        response_code = 400
    payload = {}
    if target:
        payload["target"] = target
    if ttl is not None:
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
    path = f"/dns/aliases/{fqdn}"
    if justification is not None:
        path = path + f"?cm_token={quote_plus(justification)}"
    test_case = ib_test_case(
        "DELETE",
        path,
        None, response_code, response_body)
    http_monitor.expect(test_case)


def ib_expect_add_range(name, start_address, end_address, response_code=201, response_body="", justification=None,
                        fail=False):
    if fail:
        response_code = 400
    payload = {"name": name, "start_address": start_address, "end_address": end_address}
    if justification is not None:
        payload["cm_token"] = justification
    test_case = ib_test_case("POST", "/ranges", payload, response_code, response_body)
    http_monitor.expect(test_case)


def ib_expect_del_range(start_address, end_address, response_code=204, response_body="", justification=None,
                        fail=False):
    if fail:
        response_code = 400
    path = f"/ranges/{start_address}/{end_address}"
    if justification is not None:
        path = path + f"?cm_token={quote_plus(justification)}"
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
