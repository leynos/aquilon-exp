import re
from urllib import urlencode
from urlparse import urlparse, urlunparse

from aquilon.config import Config
from aquilon.exceptions_ import ProcessException
from aquilon.utils import with_timer
from ipaddress import IPv4Address
from requests.adapters import HTTPAdapter, Retry
from requests import Session, Timeout
from requests_kerberos import DISABLED, HTTPKerberosAuth


class IBServiceGroup(object):
    """This class facilitates rollback of IB commands where needed"""

    def __init__(self):
        self.functions = []

    def add_action(self, action, rollback=None):
        self.functions.append((action, rollback))
        return self

    def commit_or_rollback(self):
        rollbacks = []
        try:
            # Iterate through the functions, pull off any rollbacks.
            for (action, rollback) in self.functions:
                action()
                if rollback:
                    rollbacks.append(rollback)
            self.functions = []
        except ProcessException as e:
            # Reverse the rollbacks to start from the last, and run them.
            rollbacks.reverse()
            for rollback in rollbacks:
                rollback()
            raise e


class IBServices(object):
    """An interface to the IB Services API, which is an Infoblox wrapper"""

    config = Config()

    enabled = config.getboolean("ib-services", "enable")
    urls = re.split(r"\s*,\s*", config.get("ib-services", "urls"))
    timeout = float(config.get("ib-services", "timeout"))
    ca_chain = config.get("ib-services", "ca_chain")
    eonid = config.get("broker", "aqd_eonid")

    def __init__(self, logger):
        self.log = logger
        self.group = IBServiceGroup()

        self.session = Session()
        if self.ca_chain:
            self.session.auth = HTTPKerberosAuth(mutual_authentication=DISABLED, force_preemptive=True)
            self.session.verify = self.ca_chain
        retries = Retry(total=1, status_forcelist=(500, 501, 502, 503, 504))
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

    def _assert_ip(self, ip):
        if not ip or isinstance(ip, IPv4Address) or (isinstance(ip, str) and re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip)):
            return True
        self.log.warning("IP not valid for IBServices:  if supplied, it must be an IPv4Address object or correctly formatted IPv4 string.")
        return False

    def assert_dns_environment(self, environment):
        return environment == "internal"

    def _generate_url_from_params(self, url, params):
        parse = urlparse(url)._replace(query=urlencode(params))
        return urlunparse(parse)

    def _build_a_ptr_payload(self, name, ip, assign_ptr_to_fqdn, ttl):
        payload = { "eonid": self.eonid }
        if name:
            payload["name"] = name
        if ip:
            payload["address"] = str(ip)
        if assign_ptr_to_fqdn:
            payload["assign_ptr_to_fqdn"] = assign_ptr_to_fqdn
        if ttl:
            payload["ttl"] = ttl
        return payload

    @with_timer
    def add_a_ptr(self, name, ip, assign_ptr_to_fqdn=None, ttl=None, create_ptr=True):
        if not self._assert_ip(ip):
            return
        payload = self._build_a_ptr_payload(name, ip, assign_ptr_to_fqdn, ttl)
        payload["create_ptr"] = create_ptr
        url = "/dns/a_ptr"

        self._http_request("POST", url, payload)

    @with_timer
    def update_a_ptr(self, name, ip, new_ip=None, assign_ptr_to_fqdn=None, ttl=None, update_ptr=True):
        assert new_ip or assign_ptr_to_fqdn or ttl, "new_ip, assign_ptr_to_fqdn and ttl all None"
        if not self._assert_ip(ip):
            return

        payload = self._build_a_ptr_payload(None, new_ip, assign_ptr_to_fqdn, ttl)
        payload["create_if_doesnt_exist"] = True
        payload["update_ptr"] = update_ptr
        url = "/dns/a_ptr/{}/{}".format(name, ip)

        self._http_request("PATCH", url, payload)

    @with_timer
    def delete_a_ptr(self, name, ip, delete_ptr=True):
        if not self._assert_ip(ip):
            return
        params = {
            "delete_ptr": str(delete_ptr).lower(),
            "eonid":      self.eonid,
        }
        url = "/dns/a_ptr/{}/{}".format(str(name), str(ip))
        url = self._generate_url_from_params(url, params)

        self._http_request("DELETE", url)

    @with_timer
    def add_dns_alias(self, name, target, ttl=None):
        url = "/dns/aliases"
        payload = {
            "eonid":  self.eonid,
            "name":   name,
            "target": target,
        }
        if ttl:
            payload["ttl"] = ttl

        self._http_request("POST", url, payload)

    @with_timer
    def del_dns_alias(self, name):
        params = { "eonid": self.eonid }
        url = "/dns/aliases/{}".format(str(name))
        url = self._generate_url_from_params(url, params)

        self._http_request("DELETE", url)

    @with_timer
    def update_dns_alias(self, name, new_target=None, ttl=None):
        payload = { "eonid": self.eonid }
        if new_target is not None:
            payload["target"] = new_target
        if ttl is not None:
            payload["ttl"] = ttl
        url = "/dns/aliases/{}".format(name)

        self._http_request("PATCH", url, payload)

    def _http_request(self, http_cmd, url, data=None):
        if not self.enabled:
            return

        response = None
        full_url = ""

        for base_url in self.urls:
            full_url = base_url + url

            try:
                log_msg = "Sending request {} {}".format(http_cmd, full_url)
                if data:
                    log_msg += " with data {}".format(data)
                self.log.info(log_msg)

                response = self.session.request(http_cmd, full_url, json=data, timeout=self.timeout)
            except Timeout:
                self.log.warning("Request to {} timed out after {}s.".format(full_url, self.timeout))

            # There are several possible other exception types.  Not all possibilities are known.
            # In all cases, the logic depends on another pass through the loop to try any remaining URLs.
            except Exception as e:
                self.log.warning("Request to {} failed with exception {}".format(full_url, e))

            # Stop trying URLs if there was no exception.
            else:
                break

        if response is None:
            raise ProcessException("Infoblox returned errors or no Infoblox servers could be reached, aborting change")

        response_str = "{} {}".format(response.status_code, response.reason)

        if response.ok:
            self.log.info("Successful response from Infoblox: got {} for {} {} {})".format(response_str, http_cmd, full_url, data))
            if http_cmd == "GET":
                return response
        else:
            error_msg = ""
            try:
                error_msg = response.json().get("message")
            except ValueError:
                # Probably a JSON decode error.  Fall back to showing whole body of response.
                error_msg = response.text

            message = "Infoblox error: '{}' ({}) for {} {} {})".format(error_msg, response_str, http_cmd, full_url, data)
            raise ProcessException(message)

    def feature_enabled(self, name):
        enabled = False

        if self.enabled:
            enabled = name in re.split(r"\s*,\s*", self.config.get("ib-services", "enabled_features"))

        return enabled

