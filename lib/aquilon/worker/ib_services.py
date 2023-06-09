from aquilon.config import Config
from aquilon.exceptions_ import ArgumentError
from aquilon.utils import with_timer
import httplib
from ipaddress import IPv4Address
from ipaddress import IPv4Network
import logging
from requests.adapters import HTTPAdapter
from requests.adapters import Retry
from requests import RequestException
from requests import Session
from requests_kerberos import DISABLED
from requests_kerberos import HTTPKerberosAuth
from urllib import urlencode
from urlparse import urlparse
from urlparse import urlunparse

LOGGER = logging.getLogger(__name__)
config = Config()

IB_SERVICES_URL = config.get("ib-services", "url")
IB_SERVICES_TIMEOUT = float(config.get("ib-services", "timeout"))
CA_CHAIN = config.get("ib-services", "ca_chain")


class IBServiceGroup(object):
    """This class facilitates rollback of IB commands where needed"""

    def __init__(self):
        self.functions = []

    def add(self, f, r=None):
        self.functions.append((f, r))
        return self

    def commit_or_rollback(self):
        rollbacks = []
        try:
            # Iterate through the functions, pull off any rollbacks.
            for (f, r) in self.functions:
                if r:
                    rollbacks.append(r)
                f()
            self.functions = []
        except (ArgumentError, RequestException) as e:
            LOGGER.warning("Error calling Infoblox service: {0}".format(str(e)))
            # Reverse the rollbacks to start from the last, and run them.
            rollbacks.reverse()
            for f in rollbacks:
                f()
            raise e


class IBServices(object):

    def __init__(self):
        self.ib_service_url = IB_SERVICES_URL
        self.session = Session()
        if CA_CHAIN:
            self.session.auth = HTTPKerberosAuth(mutual_authentication=DISABLED, force_preemptive=True)
            self.session.verify = CA_CHAIN
        retries = Retry(total=3, status_forcelist=(500, 501, 502, 503, 504))
        self.session.mount(self.ib_service_url, HTTPAdapter(max_retries=retries))

    def assert_ip(self, ip):
        if not isinstance(ip, IPv4Address):
            raise ArgumentError("IP address should be an IPv4Address object")

    def assert_dns_environment(self, environment):
        if environment == 'internal':
            return True
        else:
            LOGGER.warning('DNS environment {} has not been integrated with Infoblox yet'.format(environment))

    def generate_url_from_params(self, url, params):
        parse = urlparse(url)._replace(query=urlencode(params))
        return urlunparse(parse)

    def host_url(self, ip):
        return self.ib_service_url + "/hosts/ipv4addr/" + str(ip)

    @with_timer
    def remove_host_dns_entries(self, ip):
        self.assert_ip(ip)

        url = self.ib_service_url + "/legacy/aq/remove-dns-entries/" + str(ip)
        response = self.session.delete(url, timeout=IB_SERVICES_TIMEOUT)
        if response.status_code == httplib.NO_CONTENT:
            LOGGER.info("Remove dns entries for {} successful".format(ip))
        else:
            raise ArgumentError(response.text)

    def build_a_ptr_payload(self, name, ip, assign_ptr_to_fqdn, ttl):
        payload = dict()
        if name:
            payload["name"] = name
        if ip:
            self.assert_ip(ip)
            payload["address"] = str(ip)
        if assign_ptr_to_fqdn:
            payload["assign_ptr_to_fqdn"] = assign_ptr_to_fqdn
        if ttl:
            payload["ttl"] = ttl
        return payload

    @with_timer
    def add_a_ptr(self, name, ip, assign_ptr_to_fqdn=None, ttl=None, create_ptr=True):
        # fixme
        if not isinstance(ip, IPv4Address):
            LOGGER.warning("add_a_ptr only supports IPv4Address {}".format(str(ip)))
            return
        self.assert_ip(ip)

        payload = self.build_a_ptr_payload(name, ip, assign_ptr_to_fqdn, ttl)
        payload['create_ptr'] = create_ptr
        url = self.ib_service_url + "/dns/a_ptr"
        LOGGER.info("Invoking {} with payload: {}".format(url, payload))
        response = self.session.post(url, json=payload, timeout=IB_SERVICES_TIMEOUT)
        if response.status_code == httplib.CREATED:
            LOGGER.info("A/PTR added to Infoblox")
        else:
            # BAD_REQUEST is returned if there is an error creating the A/PTR records
            raise ArgumentError(response.text)

    @with_timer
    def update_a_ptr(self, name, ip, new_ip=None, assign_ptr_to_fqdn=None, ttl=None, update_ptr=True):
        # fixme
        if not isinstance(ip, IPv4Address):
            LOGGER.warning("update_a_ptr only supports IPv4Address {}".format(str(ip)))
            return
        self.assert_ip(ip)

        assert new_ip or assign_ptr_to_fqdn or ttl, "new_ip, assign_ptr_to_fqdn and ttl all None"

        payload = self.build_a_ptr_payload(None, new_ip, assign_ptr_to_fqdn, ttl)
        payload["create_if_doesnt_exist"] = True
        payload['update_ptr'] = update_ptr
        url = self.ib_service_url + "/dns/a_ptr/{}/{}".format(name, ip)
        LOGGER.info("Invoking {} with payload: {}".format(url, payload))
        response = self.session.patch(url, json=payload, timeout=IB_SERVICES_TIMEOUT)
        if response.status_code == httplib.NO_CONTENT:
            LOGGER.info("A/PTR updated in Infoblox")
        else:
            # BAD_REQUEST is returned if there is an error updating the A/PTR records
            raise ArgumentError(response.text)

    @with_timer
    def delete_a_ptr(self, name, ip, delete_ptr=True):
        # fixme
        if not isinstance(ip, IPv4Address):
            LOGGER.warning("update_a_ptr only supports IPv4Address {}".format(str(ip)))
            return
        self.assert_ip(ip)

        params = {'delete_ptr': str(delete_ptr).lower()}
        url = self.ib_service_url + "/dns/a_ptr/{}/{}".format(str(name), ip)
        url = self.generate_url_from_params(url, params)
        response = self.session.delete(url, timeout=IB_SERVICES_TIMEOUT)
        if response.status_code == httplib.NO_CONTENT:
            LOGGER.info("Matching A records removed from Infoblox")
            LOGGER.info("Matching PTR records removed from Infoblox") if delete_ptr else None
            return True
        else:
            # BAD_REQUEST is returned if there is an error deleting A/PTR records
            raise ArgumentError(response.text)

    @with_timer
    def add_dns_alias(self, name, target, ttl=None):
        url = self.ib_service_url + '/dns/aliases'
        payload = {
            'name': name,
            'target': target
        }
        if ttl:
            payload["ttl"] = ttl
        LOGGER.info("Invoking {} with payload: {}".format(url, payload))
        response = self.session.post(url=url, json=payload, timeout=IB_SERVICES_TIMEOUT)
        if response.status_code == httplib.CREATED:
            LOGGER.info("DNS alias added to Infoblox")
        else:
            # BAD_REQUEST is returned if there is an error creating the alias in Infoblox grids
            raise ArgumentError(response.text)

    @with_timer
    def del_dns_alias(self, name):
        url = self.ib_service_url + '/dns/aliases/' + name
        response = self.session.delete(url=url, timeout=IB_SERVICES_TIMEOUT)
        if response.status_code == httplib.NO_CONTENT:
            LOGGER.info('Matching CNAME removed from Infoblox')
        else:
            raise ArgumentError(response.text)

    @with_timer
    def update_dns_alias(self, name, new_target=None, ttl=None):

        payload = {}
        if new_target is not None:
            payload['target'] = new_target
        if ttl is not None:
            payload['ttl'] = ttl
        url = '{}/dns/aliases/{}'.format(self.ib_service_url, name)
        LOGGER.info("Invoking {} with payload: {}".format(url, payload))

        response = self.session.patch(url=url, json=payload, timeout=IB_SERVICES_TIMEOUT)
        if response.status_code == httplib.NO_CONTENT:
            LOGGER.info('CNAME has been updated in Infoblox')
        else:
            raise ArgumentError(response.text)
