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

from aquilon.config import Config
from aquilon.exceptions_ import ProcessException
from broker.brokertest import TestBrokerCommand
from broker.utils import MockHub

from ipaddress import IPv4Address

from requests.adapters import HTTPAdapter
from requests.adapters import Retry
from requests import Session
from requests import Timeout
from requests_kerberos import DISABLED
from requests_kerberos import HTTPKerberosAuth
from subprocess import PIPE
from subprocess import Popen
from urllib import quote

import logging as log
import time


class IBServicesClient(object):

    def __init__(self):
        config = Config()

        self.base_url = config.get("ib-services", "urls")
        self.timeout = float(config.get("ib-services", "timeout"))
        self.eonid = config.get("broker", "aqd_eonid")
        self.ca_chain = config.get("ib-services", "ca_chain")

        self.session = Session()
        self.session.auth = HTTPKerberosAuth(mutual_authentication=DISABLED, force_preemptive=True)
        self.session.verify = self.ca_chain
        retries = Retry(total=1, status_forcelist=(500, 501, 502, 503, 504))
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

    def add_network(self, network, name, compartment="interior.lab.access", side="a", sysloc="np.ny.na"):
        url = "/networks/{}".format(quote(network, safe=''))

        payload = {
            "name": name,
            "compartment": compartment,
            "side": side,
            "sysloc": sysloc,
        }

        self._http_request("POST", url, payload)

    def get_network(self, network):
        url = "/networks/{}".format(quote(network, safe=''))

        return self._http_request("GET", url, ignore_statuses=[404])

    def delete_network(self, network):
        url = "/networks/{}".format(quote(network, safe=''))

        self._http_request("DELETE", url)

    def add_zone(self, fqdn, city="ny"):
        url = "/dns/zones/"
        payload = {"fqdn": fqdn, "city": city, "eonid": self.eonid}
        self._http_request("POST", url, payload)

    def get_zone(self, fqdn):
        url = "/dns/zones/{}".format(fqdn)

        return self._http_request("GET", url, ignore_statuses=[404])

    def delete_zone(self, fqdn):
        url = "/dns/zones/{}".format(fqdn)
        self._http_request("DELETE", url)

    def add_a_ptr(self, fqdn, ip):
        url = "/dns/a_ptr/"
        payload = {"name": fqdn, "address": ip, "eonid": self.eonid}
        self._http_request("POST", url, payload)

    def delete_a_ptr(self, fqdn, ip):
        url = "/dns/a_ptr/{}/{}".format(fqdn, ip)
        self._http_request("DELETE", url)

    def add_dns_alias(self, fqdn, target):
        url = "/dns/aliases/".format(fqdn)
        payload = {"name": fqdn, "target": target, "eonid": self.eonid}
        self._http_request("POST", url, payload)

    def delete_dns_alias(self, fqdn):
        url = "/dns/aliases/{}".format(fqdn)
        self._http_request("DELETE", url)

    def delete_dynamic_range(self, start_address, end_address):
        url = "/ranges/{}/{}".format(start_address, end_address)

        self._http_request("DELETE", url, ignore_statuses=[404])

    def show_dynamic_range(self, start_address, end_address):
        url = "/ranges/{}/{}".format(str(start_address), str(end_address))

        return self._http_request("GET", url, ignore_statuses=[404])

    def _http_request(self, http_cmd, url, data=None, ignore_statuses=[]):
        response = None

        full_url = self.base_url + url

        try:
            log_msg = "Sending request {} {}".format(http_cmd, full_url)
            if data:
                log_msg += " with data {}".format(data)
            log.info(log_msg)

            response = self.session.request(http_cmd, full_url, json=data, timeout=self.timeout)
        except Timeout:
            log.warning("Request to {} timed out after {}s.".format(full_url, self.timeout))

        # There are several possible other exception types.  Not all possibilities are known.
        # In all cases, the logic depends on another pass through the loop to try any remaining URLs.
        except Exception as e:
            log.warning("Request to {} failed with exception {}".format(full_url, e))

        if response is None:
            raise ProcessException("Infoblox returned errors or no Infoblox servers could be reached, aborting change")

        response_str = "{} {}".format(response.status_code, response.reason)

        if response.ok:
            log.info("Successful response from Infoblox: got {} for {} {} {})".format(response_str, http_cmd, full_url,
                                                                                      data))
            if http_cmd == "GET":
                return response
        else:
            if response.status_code in ignore_statuses:
                return response
            error_msg = ""
            try:
                error_msg = response.json().get("message")
            except ValueError:
                # Probably a JSON decode error.  Fall back to showing whole body of response.
                error_msg = response.text

            message = "Infoblox error: '{}' ({}) for {} {} {})".format(error_msg, response_str, http_cmd, full_url,
                                                                       data)
            raise ProcessException(message)


class DnsChecker(object):

    def __init__(self, broker_test):
        self.broker_test = broker_test

    def shellout(self, command, **kwargs):
        p = Popen(command, stdout=PIPE, stderr=PIPE, **kwargs)
        (out, err) = p.communicate()
        if err:
            log.debug(err)
        return (p, out, err)

    def _run_dns_check(self, args):
        dns_server = '10.253.74.75'
        # Using /usr/bin/host makes this code compatible with both python 2 and 3.
        # Ideally change this to use a python library after the broker is migrated to python 3.
        command = ['/usr/bin/host'] + args + [dns_server]
        time.sleep(0.3)  # Sometimes the dns server takes that bit longer to return the expected answer
        return self.shellout(command)

    def a_record(self, fqdn, ip):
        expected_stdout = "{} has address {}".format(fqdn, ip)

        (p, out, err) = self._run_dns_check([fqdn])
        self.broker_test.assertEmptyErr(err, [fqdn])
        self.broker_test.assertEqual(p.returncode, 0)
        self.broker_test.assertTrue(out.find(expected_stdout) >= 0,
                                    "STDOUT for %s did not include '%s':\n@@@\n'%s'\n@@@\n" % (fqdn, expected_stdout,
                                                                                               out))

    def cname(self, fqdn, target, ips):
        expected_stdout = "{} is an alias for {}.\n".format(fqdn, target)

        (p, out, err) = self._run_dns_check([fqdn])
        self.broker_test.assertEmptyErr(err, [fqdn])
        self.broker_test.assertTrue(out.find(expected_stdout) >= 0,
                                    "STDOUT for %s did not include '%s':\n@@@\n'%s'\n@@@\n" % (fqdn, expected_stdout,
                                                                                               out))
        for ip in ips:
            expected_stdout = "{} has address {}\n".format(target, ip)
            self.broker_test.assertTrue(out.find(expected_stdout) >= 0,
                                        "STDOUT for %s did not include '%s':\n@@@\n'%s'\n@@@\n" % (fqdn,
                                                                                                   expected_stdout,
                                                                                                   out))

        self.broker_test.assertEqual(p.returncode, 0)

    def notfound(self, fqdn):
        expected_stdout = "Host {} not found:".format(fqdn)

        (p, out, err) = self._run_dns_check([fqdn])
        self.broker_test.assertTrue(out.find(expected_stdout) >= 0,
                                    "STDOUT for %s did not include '%s':\n@@@\n'%s'\n@@@\n" % (fqdn, expected_stdout,
                                                                                               err))
        self.broker_test.assertEmptyErr(err, [fqdn])
        self.broker_test.assertEqual(p.returncode, 1)


class TestIBEndToEnd(TestBrokerCommand):

    test_network_obj = {"ip": "2.3.4.0", "prefixlen": "24"}
    test_network = test_network_obj["ip"] + "/" + test_network_obj["prefixlen"]
    test_domain = "aqd-ib-test.com"

    def __init__(self, *args, **kwargs):
        super(TestIBEndToEnd, self).__init__(*args, **kwargs)
        self.ib_services = IBServicesClient()
        if not self.ib_services.get_zone(self.test_domain).ok:
            self.fail("Required test zone {} does not exist in IB instance.".format(self.test_domain))

    def _clean_ib_services(self):
        if self.ib_services.get_network(self.test_network).status_code != 404:
            self.ib_services.delete_network(network=self.test_network)

        # TODO: hard-coded dns zone
        # if self.ib_services.get_zone(self.test_domain).status_code != 404:
        #     self.ib_services.delete_zone(fqdn=self.test_domain)

    def setUp(self, *args, **kwargs):
        super(TestIBEndToEnd, self).setUp(*args, **kwargs)

        self._clean_ib_services()
        self.ib_services.add_network(network=self.test_network, name="aqd-unittest")
        # TODO: Zone changes in the l2 IB instance require a restart of the dns server before domains in that zone can
        # be resolved, so for now rely on a previously created zone instead
        # self.ib_services.add_zone(fqdn=self.test_domain)

    def tearDown(self, *args, **kwargs):
        super(TestIBEndToEnd, self).tearDown(*args, **kwargs)
        self._clean_ib_services()

    def test_100_aptr_cname(self):
        mh = MockHub(self)
        dns_checker = DnsChecker(self)

        test_a_fqdn = 'test.' + self.test_domain
        test_alias_fqdn = 'alias.' + self.test_domain
        test_alias2_fqdn = 'alias2.' + self.test_domain

        # An a-record which initially exists only in IB
        test_ib_a_fqdn = 'exists-in-ib.' + self.test_domain
        test_ib_a_fqdn2 = 'exists-in-ib2.' + self.test_domain

        mh.add_dns_domain(self.test_domain, restricted=False)
        building = mh.add_building()

        # Make sure the addresses we are going to create were not left lingering from a previous test run
        self.ib_services.delete_dns_alias(test_alias_fqdn)
        self.ib_services.delete_dns_alias(test_alias2_fqdn)
        self.ib_services.delete_a_ptr(test_a_fqdn, '2.3.4.1')
        self.ib_services.delete_a_ptr(test_a_fqdn, '2.3.4.2')
        self.ib_services.delete_a_ptr(test_a_fqdn, '2.3.4.3')
        self.ib_services.delete_a_ptr(test_ib_a_fqdn, '2.3.4.4')
        self.ib_services.delete_a_ptr(test_ib_a_fqdn, '2.3.4.5')
        self.ib_services.delete_a_ptr(test_ib_a_fqdn2, '2.3.4.4')
        self.ib_services.delete_a_ptr(test_ib_a_fqdn2, '2.3.4.5')
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
        self.ib_services.delete_dns_alias('alias.' + self.test_domain)
        # And test that updating the alias in AQ will re-create it in IB
        # Note that we are not specifying the alias target here, that's on purpose to test that the aq code knows to
        # send the target, without which IB can't possibly know how to create the alias
        self.noouttest(['update_alias', '--fqdn', 'alias.' + self.test_domain, '--ttl', '300'])
        dns_checker.cname('alias.' + self.test_domain, test_a_fqdn, ['2.3.4.2'])

        self.noouttest(['del_alias', '--fqdn', 'alias.' + self.test_domain])
        dns_checker.notfound('alias.' + self.test_domain)

        # Delete a_ptr record in IB (but not in AQ)
        self.ib_services.delete_a_ptr(test_a_fqdn, '2.3.4.2')
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
        self.ib_services.add_a_ptr(test_ib_a_fqdn, '2.3.4.4')
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
        self.ib_services.add_a_ptr(test_ib_a_fqdn2, '2.3.4.4')
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
        self.ib_services.add_dns_alias(test_alias2_fqdn, test_ib_a_fqdn)
        # Check it resolves
        dns_checker.cname(test_alias2_fqdn, test_ib_a_fqdn, ['2.3.4.4'])
        # Create same cname in aq
        self.noouttest(['add_alias', '--fqdn', test_alias2_fqdn, '--target', test_ib_a_fqdn])
        # Check it resolves
        dns_checker.cname(test_alias2_fqdn, test_ib_a_fqdn, ['2.3.4.4'])

        # Now delete the alias in IB but not in AQ
        self.ib_services.delete_dns_alias(test_alias2_fqdn)
        dns_checker.notfound(test_alias2_fqdn)
        # And the delete it in AQ and check that it works
        self.noouttest(['del_alias', '--fqdn', test_alias2_fqdn])
        dns_checker.notfound(test_alias2_fqdn)

        # Create cname in ib
        self.ib_services.add_dns_alias(test_alias2_fqdn, test_ib_a_fqdn)
        # Check it resolves
        dns_checker.cname(test_alias2_fqdn, test_ib_a_fqdn, ['2.3.4.4'])
        # Create same cname in aq pointing to a different fqdn
        self.noouttest(['add_alias', '--fqdn', test_alias2_fqdn, '--target', test_ib_a_fqdn2])
        # Check it resolves
        dns_checker.cname(test_alias2_fqdn, test_ib_a_fqdn2, ['2.3.4.4', '2.3.4.5'])

        # Now delete the alias in IB but not in AQ
        self.ib_services.delete_dns_alias(test_alias2_fqdn)
        dns_checker.notfound(test_alias2_fqdn)
        # And the delete it in AQ and check that it works
        self.noouttest(['del_alias', '--fqdn', test_alias2_fqdn])
        dns_checker.notfound(test_alias2_fqdn)

        # Final clean up
        self.dsdb_expect_delete('2.3.4.4')
        self.noouttest(['del_address', '--fqdn', test_ib_a_fqdn] + self.valid_just_tcm)
        dns_checker.notfound(test_ib_a_fqdn)
        self.dsdb_expect_delete('2.3.4.5')
        self.noouttest(['del_address', '--fqdn', test_ib_a_fqdn2] + self.valid_just_tcm)
        self.dsdb_verify()
        dns_checker.a_record(test_ib_a_fqdn2, '2.3.4.4')
        self.ib_services.delete_a_ptr(test_ib_a_fqdn2, '2.3.4.4')
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
        for ip in range(int(IPv4Address(start_ip.decode('UTF-8'))),
                        int(IPv4Address(end_ip.decode('UTF-8'))) + 1):
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
        for ip in range(int(IPv4Address(start_ip.decode('UTF-8'))),
                        int(IPv4Address(end_ip.decode('UTF-8'))) + 1):
            address = IPv4Address(ip)
            messages.append("DSDB: delete_host -ip_address %s" % address)
            self.dsdb_expect_delete(address)
        err = self.statustest(command)
        for message in messages:
            self.matchoutput(err, message, command)
        self.dsdb_verify()

        if self.ib_services.show_dynamic_range(start_ip, end_ip).status_code != 404:
            self.fail("Expected dynamic range to be not found in infoblox")

        self.noouttest(['del_network', '--ip', self.test_network_obj['ip']])
        mh.delete()


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestIBEndToEnd)
    unittest.TextTestRunner(verbosity=2).run(suite)
