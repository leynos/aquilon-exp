#!/usr/bin/env python
# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2023  Contributor
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Module for testing aq integration with infoblox a_record_ptr endpoint."""

import unittest

if __name__ == "__main__":
    from broker import utils
    utils.import_depends()

import aquilon.worker.depends
from aquilon.worker.ib_services import IBServices
from broker.brokertest import TestBrokerCommand
from broker.utils import MockHub

from ipaddress import IPv4Address
from itertools import chain

from subprocess import PIPE
from subprocess import Popen
from urllib.parse import quote

import logging as log
import time

class IBServicesTest(IBServices):
    def _add_network(self, network, name, compartment=None, side=None, sysloc=None):
        url = "/networks/{}".format(quote(network, safe=""))

        payload = {
            "name": name,
            "compartment": compartment,
            "side": side,
            "sysloc": sysloc,
        }
        if self.eonid:
            payload["eonid"] = self.eonid

        self._http_request("POST", url, payload)

    def _show_network(self, network):
        url = "/networks/{}".format(quote(network, safe=""))

        return self._http_request("GET", url, ignore_statuses=[404])

    def _del_network(self, network):
        url = "/networks/{}".format(quote(network, safe=""))

        self._http_request("DELETE", url, ignore_statuses=[404])

    def _add_zone(self, fqdn, city=None):
        url = "/dns/zones/"
        payload = {"fqdn": fqdn, "city": city}
        if self.justification is not None:
            payload["cm_token"] = self.justification
        self._http_request("POST", url, payload)

    def _show_zone(self, fqdn):
        url = f"/dns/zones/{fqdn}"

        return self._http_request("GET", url, ignore_statuses=[404])

    def _del_zone(self, fqdn):
        url = f"/dns/zones/{fqdn}"
        self._http_request("DELETE", url, ignore_statuses=[404])


class IBChecker:
    def __init__(self, broker_test):
        self.broker_test = broker_test

    def _get_srv_record(self, **kwargs):
        response = self.broker_test.ib_services.show_dns_srv_record(
            kwargs["service"],
            kwargs["protocol"],
            kwargs["dns_domain"],
            kwargs["target"],
            kwargs.get("port", None),
            kwargs.get("priority", None),
            kwargs.get("weight", None),
        )
        return response

    def srv_record_matches(self, **kwargs):
        response = self._get_srv_record(**kwargs)
        self.broker_test.assertIsNotNone(response)
        self.broker_test.assertTrue(response.ok, "SRV record exists and matches required values")

    def srv_record_does_not_exist(self, **kwargs):
        response = self._get_srv_record(**kwargs)
        self.broker_test.assertIsNotNone(response)
        self.broker_test.assertEqual(response.status_code, 404, "SRV record does not exist")

    def check_headers(self, response):
        "Check that a header containing the request ID is present and has sane-looking content"
        self.broker_test.assertIsNotNone(response)

        self._check_header(response.request.headers)
        self._check_header(response.headers)

    def _check_header(self, headers):
        self.broker_test.assertIsNotNone(headers)

        transaction_id_header = self.broker_test.ib_services.transaction_id_header
        header_value = headers.get(transaction_id_header)
        self.broker_test.assertIsNotNone(header_value)

        self.broker_test.assertRegexpMatches(header_value, r"^[\w-]+$", f"Header '{transaction_id_header}' contains '{header_value}', seems sane")

class DnsChecker:

    def __init__(self, broker_test):
        self.broker_test = broker_test

    def shellout(self, command, **kwargs):
        p = Popen(command, stdout=PIPE, stderr=PIPE, **kwargs)
        (out, err) = p.communicate()
        if err:
            log.debug(err)
        return (p, out, err)

    def _run_dns_check(self, args):
        dns_server = '10.253.123.138'
        # Using /usr/bin/host makes this code compatible with both python 2 and 3.
        # Ideally change this to use a python library after the broker is migrated to python 3.
        command = ['/usr/bin/host'] + args + [dns_server]
        time.sleep(0.3)  # Sometimes the dns server takes that bit longer to return the expected answer
        return self.shellout(command, text=True)

    def a_record(self, fqdn, ip):
        expected_stdout = f"{fqdn} has address {ip}"

        (p, out, err) = self._run_dns_check([fqdn])
        self.broker_test.assertEmptyErr(err, [fqdn])
        self.broker_test.assertTrue(out.find(expected_stdout) >= 0,
                                    "STDOUT for {} did not include '{}':\n@@@\n'{}'\n@@@\n".format(fqdn, expected_stdout,
                                                                                               out))
        self.broker_test.assertEqual(p.returncode, 0)

    def cname(self, fqdn, target, ips):
        expected_stdout = f"{fqdn} is an alias for {target}.\n"

        (p, out, err) = self._run_dns_check([fqdn])
        self.broker_test.assertEmptyErr(err, [fqdn])
        self.broker_test.assertTrue(out.find(expected_stdout) >= 0,
                                    "STDOUT for {} did not include '{}':\n@@@\n'{}'\n@@@\n".format(fqdn, expected_stdout,
                                                                                               out))
        for ip in ips:
            expected_stdout = f"{target} has address {ip}\n"
            self.broker_test.assertTrue(out.find(expected_stdout) >= 0,
                                        "STDOUT for {} did not include '{}':\n@@@\n'{}'\n@@@\n".format(fqdn,
                                                                                                   expected_stdout,
                                                                                                   out))

        self.broker_test.assertEqual(p.returncode, 0)

    def notfound(self, fqdn):
        expected_stdout = f"Host {fqdn} not found:"

        (p, out, err) = self._run_dns_check([fqdn])
        self.broker_test.assertTrue(out.find(expected_stdout) >= 0,
                                    "STDOUT for {} did not include '{}':\n@@@\n'{}'\n@@@\n".format(fqdn, expected_stdout,
                                                                                               err))
        self.broker_test.assertEmptyErr(err, [fqdn])
        self.broker_test.assertEqual(p.returncode, 1)


class TestIBEndToEnd(TestBrokerCommand):

    test_network_obj = {"ip": "2.3.4.0", "prefixlen": "24"}
    test_network = test_network_obj["ip"] + "/" + test_network_obj["prefixlen"]
    test_domain = "aqd-ib-test.com"
    dummy_request_id = "7bbf547c-a1c2-4144-b35f-d93f338d9c86"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ib_services = IBServicesTest(log, requestid=self.dummy_request_id)
        zone_response = self.ib_services._show_zone(self.test_domain)

        if zone_response and not zone_response.ok:
            self.fail(f"Required test zone {self.test_domain} does not exist in IB instance.")

    def _clean_ib_services(self):
        response = self.ib_services._show_network(self.test_network)
        if response and response.status_code != 404:
            self.ib_services._del_network(network=self.test_network)

        # TODO: hard-coded dns zone
        # if self.ib_services.show_zone(self.test_domain).status_code != 404:
        #     self.ib_services.delete_zone(fqdn=self.test_domain)

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)

        self._clean_ib_services()
        self.ib_services._add_network(network=self.test_network, name="aqd-unittest", side="a", sysloc="np.ny.na",
                                     compartment="interior.lab.access")
        # TODO: Zone changes in the l2 IB instance require a restart of the dns server before domains in that zone can
        # be resolved, so for now rely on a previously created zone instead
        # self.ib_services.add_zone(fqdn=self.test_domain, city="ny")

    def tearDown(self, *args, **kwargs):
        super().tearDown(*args, **kwargs)
        self._clean_ib_services()

    def _delete_a_ptr(self, fqdn, ip):
        self.ib_services._del_a(fqdn,ip)
        self.ib_services._del_ptr(ip)

    def _add_a_ptr(self, fqdn, ip, ib_checker):
        response = self.ib_services._add_a(fqdn,ip)
        ib_checker.check_headers(response)
        response = self.ib_services._add_ptr(fqdn, ip)
        ib_checker.check_headers(response)

    def test_100_aptr_cname(self):
        mh = MockHub(self)
        dns_checker = DnsChecker(self)
        ib_checker = IBChecker(self)

        test_a_fqdn = 'test.' + self.test_domain
        test_alias_fqdn = 'alias.' + self.test_domain
        test_alias2_fqdn = 'alias2.' + self.test_domain

        # An a-record which initially exists only in IB
        test_ib_a_fqdn = 'exists-in-ib.' + self.test_domain
        test_ib_a_fqdn2 = 'exists-in-ib2.' + self.test_domain

        mh.add_dns_domain(self.test_domain, restricted=False)
        building = mh.add_building()

        # Make sure the addresses we are going to create were not left lingering from a previous test run
        self.ib_services._del_dns_alias(test_alias_fqdn)
        self.ib_services._del_dns_alias(test_alias2_fqdn)
        self._delete_a_ptr(test_a_fqdn, '2.3.4.1')
        self._delete_a_ptr(test_a_fqdn, '2.3.4.2')
        self._delete_a_ptr(test_a_fqdn, '2.3.4.3')
        self._delete_a_ptr(test_ib_a_fqdn, '2.3.4.4')
        self._delete_a_ptr(test_ib_a_fqdn, '2.3.4.5')
        self._delete_a_ptr(test_ib_a_fqdn2, '2.3.4.4')
        self._delete_a_ptr(test_ib_a_fqdn2, '2.3.4.5')
        dns_checker.notfound(test_a_fqdn)
        dns_checker.notfound(test_ib_a_fqdn)
        dns_checker.notfound(test_ib_a_fqdn2)
        dns_checker.notfound(test_alias_fqdn)
        dns_checker.notfound(test_alias2_fqdn)

        # Setup network used by the tests
        self.noouttest(['add_network', '--network', 'ib-testing', '--ip', self.test_network_obj['ip'],
                        '--prefixlen', self.test_network_obj['prefixlen'], '--building', building])

        self.dsdb_expect_add(test_a_fqdn, '2.3.4.1')
        self.noouttest(['add_address', '--fqdn', test_a_fqdn, '--ip', '2.3.4.1',
                        '--grn', mh.grn] + self.valid_just_tcm)
        self.dsdb_verify()
        dns_checker.a_record(test_a_fqdn, '2.3.4.1')

        self.dsdb_expect_update(test_a_fqdn, ip='2.3.4.2')
        self.noouttest(['update_address', '--fqdn', test_a_fqdn, '--ip', '2.3.4.2',
                        '--grn', mh.grn] + self.valid_just_tcm)
        self.dsdb_verify()
        dns_checker.a_record(test_a_fqdn, '2.3.4.2')

        self.noouttest(['add_alias', '--fqdn', 'alias.' + self.test_domain, '--target', test_a_fqdn])
        dns_checker.cname('alias.' + self.test_domain, test_a_fqdn, ['2.3.4.2'])

        # Now delete the alias in IB, but not in AQ
        self.ib_services._del_dns_alias('alias.' + self.test_domain)
        # And test that updating the alias in AQ will re-create it in IB
        # Note that we are not specifying the alias target here, that's on purpose to test that the aq code knows to
        # send the target, without which IB can't possibly know how to create the alias
        self.noouttest(['update_alias', '--fqdn', 'alias.' + self.test_domain, '--ttl', '300'])
        dns_checker.cname('alias.' + self.test_domain, test_a_fqdn, ['2.3.4.2'])

        self.noouttest(['del_alias', '--fqdn', 'alias.' + self.test_domain])
        dns_checker.notfound('alias.' + self.test_domain)

        # Delete a_ptr record in IB (but not in AQ)
        self._delete_a_ptr(test_a_fqdn, '2.3.4.2')
        # Check it is no longer in DNS
        dns_checker.notfound(test_a_fqdn)
        # Update in AQ
        self.dsdb_expect_update(test_a_fqdn, ip='2.3.4.3')
        self.noouttest(['update_address', '--fqdn', test_a_fqdn, '--ip', '2.3.4.3',
                        '--grn', mh.grn] + self.valid_just_tcm)
        # Check it propagated to DNS through IB
        dns_checker.a_record(test_a_fqdn, '2.3.4.3')

        self.dsdb_expect_delete('2.3.4.3')
        self.noouttest(['del_address', '--fqdn', test_a_fqdn] + self.valid_just_tcm)
        self.dsdb_verify()
        dns_checker.notfound(test_a_fqdn)

        # Create a-record in ib
        self._add_a_ptr(test_ib_a_fqdn, '2.3.4.4', ib_checker)

        # Check it resolves
        dns_checker.a_record(test_ib_a_fqdn, '2.3.4.4')
        # Create same a-record in aq
        self.dsdb_expect_add(test_ib_a_fqdn, '2.3.4.4')
        self.noouttest(['add_address', '--fqdn', test_ib_a_fqdn, '--ip', '2.3.4.4',
                        '--grn', mh.grn] + self.valid_just_tcm)
        # Check it resolves
        dns_checker.a_record(test_ib_a_fqdn, '2.3.4.4')
        self.dsdb_verify()

        # Create a-record in ib
        self._add_a_ptr(test_ib_a_fqdn2, '2.3.4.4', ib_checker)
        # Check it resolves
        dns_checker.a_record(test_ib_a_fqdn2, '2.3.4.4')
        # Create a-record in aq with same fqdn but different ip
        self.dsdb_expect_add(test_ib_a_fqdn2, '2.3.4.5')
        self.noouttest(['add_address', '--fqdn', test_ib_a_fqdn2, '--ip', '2.3.4.5',
                        '--grn', mh.grn] + self.valid_just_tcm)
        # Check it resolves to the new ip
        dns_checker.a_record(test_ib_a_fqdn2, '2.3.4.5')
        self.dsdb_verify()

        # Create cname in ib
        self.ib_services._add_dns_alias(test_alias2_fqdn, test_ib_a_fqdn)
        # Check it resolves
        dns_checker.cname(test_alias2_fqdn, test_ib_a_fqdn, ['2.3.4.4'])
        # Create same cname in aq
        self.noouttest(['add_alias', '--fqdn', test_alias2_fqdn, '--target', test_ib_a_fqdn])
        # Check it resolves
        dns_checker.cname(test_alias2_fqdn, test_ib_a_fqdn, ['2.3.4.4'])

        # Now delete the alias in IB but not in AQ
        self.ib_services._del_dns_alias(test_alias2_fqdn)
        dns_checker.notfound(test_alias2_fqdn)
        # And the delete it in AQ and check that it works
        self.noouttest(['del_alias', '--fqdn', test_alias2_fqdn])
        dns_checker.notfound(test_alias2_fqdn)

        # Create cname in ib
        self.ib_services._add_dns_alias(test_alias2_fqdn, test_ib_a_fqdn)
        # Check it resolves
        dns_checker.cname(test_alias2_fqdn, test_ib_a_fqdn, ['2.3.4.4'])
        # Create same cname in aq pointing to a different fqdn
        self.noouttest(['add_alias', '--fqdn', test_alias2_fqdn, '--target', test_ib_a_fqdn2])
        # Check it resolves
        dns_checker.cname(test_alias2_fqdn, test_ib_a_fqdn2, ['2.3.4.4', '2.3.4.5'])

        # Now delete the alias in IB but not in AQ
        self.ib_services._del_dns_alias(test_alias2_fqdn)
        dns_checker.notfound(test_alias2_fqdn)
        # And the delete it in AQ and check that it works
        self.noouttest(['del_alias', '--fqdn', test_alias2_fqdn])
        dns_checker.notfound(test_alias2_fqdn)

        # Final clean up

        # delete in ib first
        self._delete_a_ptr(test_ib_a_fqdn, "2.3.4.4")
        self.dsdb_expect_delete('2.3.4.4')
        # and check that deleting in aq succeeds
        self.noouttest(['del_address', '--fqdn', test_ib_a_fqdn] + self.valid_just_tcm)
        dns_checker.notfound(test_ib_a_fqdn)

        self.dsdb_expect_delete('2.3.4.5')
        self.noouttest(['del_address', '--fqdn', test_ib_a_fqdn2] + self.valid_just_tcm)
        self.dsdb_verify()
        dns_checker.a_record(test_ib_a_fqdn2, '2.3.4.4')
        self._delete_a_ptr(test_ib_a_fqdn2, '2.3.4.4')
        dns_checker.notfound(test_ib_a_fqdn2)

        self.noouttest(['del_network', '--ip', '2.3.4.0'])

        mh.delete()

    def test_200_dynamic_range(self):
        mh = MockHub(self)

        mh.add_dns_domain(self.test_domain, restricted=False)
        building = mh.add_building()
        self.noouttest(['add_network', '--network', 'ib-testing', '--ip', self.test_network_obj['ip'],
                        '--prefixlen', self.test_network_obj['prefixlen'], '--building', building])

        start_ip = "2.3.4.100"
        end_ip = "2.3.4.103"

        # Make sure the dynamic range we are about to create was not left lingering from a previous test run
        self.ib_services.delete_dynamic_range(start_ip, end_ip)

        messages = []
        for ip in range(int(IPv4Address(start_ip)),
                        int(IPv4Address(end_ip)) + 1):
            address = IPv4Address(ip)
            hostname = self.dynname(address, domain=self.test_domain)
            self.dsdb_expect_add(hostname, address)
            messages.append("DSDB: add_host -host_name %s -ip_address %s "
                            "-status aq" % (hostname, address))

        command = ['add_dynamic_range',
                   '--startip', start_ip,
                   '--endip', end_ip,
                   '--range_class', 'infoblox_managed',
                   '--dns_domain', self.test_domain] + self.valid_just_tcm
        err = self.statustest(command)
        for message in messages:
            self.matchoutput(err, message, command)
        self.dsdb_verify()

        if not self.ib_services.show_dynamic_range(start_ip, end_ip).ok:
            self.fail("Expected dynamic range does not exist in infoblox")

        command = ['del_dynamic_range',
                   '--clearnetwork', self.test_network_obj['ip']]
        messages = []
        for ip in range(int(IPv4Address(start_ip)),
                        int(IPv4Address(end_ip)) + 1):
            address = IPv4Address(ip)
            messages.append("DSDB: delete_host -ip_address %s" % address)
            self.dsdb_expect_delete(address)
        err = self.statustest(command)
        for message in messages:
            self.matchoutput(err, message, command)
        self.dsdb_verify()

        response = self.ib_services.show_dynamic_range(start_ip, end_ip)
        if response: # FIXME check for 404?
            self.fail("Expected dynamic range to be not found in infoblox")

        self.noouttest(['del_network', '--ip', self.test_network_obj['ip']])
        mh.delete()

    def test_300_srv_records(self):
        mh = MockHub(self)
        dns_checker = DnsChecker(self)
        ib_checker = IBChecker(self)

        mh.add_dns_domain(self.test_domain, restricted=False)
        building = mh.add_building()
        self.noouttest(['add_network', '--network', 'ib-testing', '--ip', self.test_network_obj['ip'],
                        '--prefixlen', self.test_network_obj['prefixlen'], '--building', building])

        test_fqdn = "aqd-ib-srv-test01." + self.test_domain
        test_ip = "2.3.4.1"

        self._delete_a_ptr(test_fqdn, test_ip)
        self.aq.runcommand(['del_address', '--fqdn', test_fqdn, '--ip', test_ip] + self.valid_just_tcm)

        self.dsdb_expect_add(test_fqdn, test_ip)
        command = ["add_address", "--fqdn", test_fqdn, "--ip", test_ip, '--grn', mh.grn] + self.valid_just_tcm
        err = self.statustest(command)
        self.dsdb_verify()

        args = {
            'service': 'kerberos',
            'protocol': 'tcp',
            'dns_domain': self.test_domain,
            'target': test_fqdn,
            'priority': 10,
            'weight': 10,
            'port': 88,
        }
        command = ["add_srv_record"] + list(chain.from_iterable([(f"--{key}", args[key]) for key in args]))
        err = self.statustest(command)
        ib_checker.srv_record_matches(**args)

        update_tests = (
            { "ttl": 300 },
            { "priority": 20, "weight": 30 },
            { "port": 8080 },
        )

        for test in update_tests:
            test_args = dict(args)
            for key in test:
                test_args[key] = test[key]

            command = ["update_srv_record"] + list(chain.from_iterable([(f"--{key}", test_args[key]) for key in test_args]))
            err = self.statustest(command)
            ib_checker.srv_record_matches(**test_args)

        command = ["del_srv_record", "--service", "kerberos", "--protocol", "tcp", "--dns_domain", self.test_domain, "--target", test_fqdn]
        self.statustest(command)
        ib_checker.srv_record_does_not_exist(**test_args)

        self.dsdb_expect_delete(test_ip)
        self.noouttest(['del_address', '--fqdn', test_fqdn, '--ip', test_ip] + self.valid_just_tcm)
        self.noouttest(['del_network', '--ip', self.test_network_obj['ip']])
        mh.delete()


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestIBEndToEnd)
    unittest.TextTestRunner(verbosity=2).run(suite)
