from ipaddress import IPv4Address
from requests import Session, Timeout
from requests_kerberos import DISABLED, HTTPKerberosAuth
import re
from urllib.parse import urlencode, urlparse, urlunparse, quote

from aquilon.aqdb.model import ARecord, Machine
from aquilon.config import Config
from aquilon.exceptions_ import ProcessException
from aquilon.utils import with_timer


class IBServiceGroup:
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


class IBServices:
    """An interface to the IB Services API, which is an Infoblox wrapper"""

    config = Config()

    enabled = config.getboolean("ib-services", "enable")
    transactional = config.getboolean("ib-services", "transactional")
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
            payload["name"] = str(name)
        if ip:
            payload["address"] = str(ip)
        if assign_ptr_to_fqdn:
            payload["assign_ptr_to_fqdn"] = assign_ptr_to_fqdn
        if ttl:
            payload["ttl"] = ttl
        return payload

    @with_timer
    def add_a_ptr(self, name, ip, assign_ptr_to_fqdn=None, ttl=None, create_ptr=True):
        return self.update_a_ptr(name, ip,
            new_ip=ip, # We have to specify this again to force creation.
            assign_ptr_to_fqdn=assign_ptr_to_fqdn,
            ttl=ttl,
            create_ptr=create_ptr,
            update_ptr=False,
        )

    @with_timer
    def update_a_ptr(self, name, ip, new_ip=None, assign_ptr_to_fqdn=None, ttl=None, update_ptr=True, create_ptr=False):
        if not self._assert_ip(ip):
            return

        payload = self._build_a_ptr_payload(None, new_ip, assign_ptr_to_fqdn, ttl)
        payload["create_if_doesnt_exist"] = True
        payload["create_ptr"] = create_ptr
        payload["update_ptr"] = update_ptr
        url = f"/dns/a_ptr/{name}/{ip}"

        return self._http_request("PATCH", url, payload)

    @with_timer
    def delete_a_ptr(self, name, ip, delete_ptr=True):
        if not self._assert_ip(ip):
            return
        params = {
            "delete_ptr": str(delete_ptr).lower(),
            "eonid":      self.eonid,
        }
        url = f"/dns/a_ptr/{str(name)}/{str(ip)}"
        url = self._generate_url_from_params(url, params)

        return self._http_request("DELETE", url)

    @with_timer
    def show_a_ptr(self, name, ip):
        params = {
            "name":    str(name),
            "address": str(ip),
        }
        url = "/dns/a_ptr"
        url = self._generate_url_from_params(url, params)

        return self._http_request("GET", url)

    def snapshot_hw_a_records(self, dbhw_ent):
        hwdata = {}

        for addr in dbhw_ent.all_addresses():
            if not addr.network.is_internal:
                continue
            if not addr.fqdns:
                continue
            if addr.is_shared:
                continue
            if not isinstance(addr.ip, IPv4Address):
                continue

            dns_record = addr.dns_records[0]

            if not isinstance(dns_record, ARecord):
                continue

            fqdn = str(dns_record.fqdn)
            ptr = str(dns_record.reverse_ptr) if dns_record.reverse_ptr else None

            hwdata[fqdn] = {
                "ip":  str(addr.ip),
                "ptr": ptr,
                "ttl": dns_record.ttl,
            }

        # The primary address of Zebra hosts needs extra care. Here, we cheat a
        # bit - we do not check if the primary name is a service address, but
        # instead check if it has an IP address and it was not handled above.
        if (dbhw_ent.primary_ip and str(dbhw_ent.primary_name.fqdn) not in hwdata):
            ptr = str(dbhw_ent.primary_name.reverse_ptr) if dbhw_ent.primary_name.reverse_ptr else None

            hwdata[str(dbhw_ent.primary_name)] = {
                "ip":  str(dbhw_ent.primary_ip),
                "ptr": ptr,
                "ttl": dbhw_ent.primary_name.ttl,
            }

        return hwdata

    def bulk_change_a_ptr(self, old_hwdata, new_hwdata):
        self.log.info(f"bulk_update_a_ptr(): data before change = {old_hwdata}, data after change = {new_hwdata}")

        for fqdn in old_hwdata:
            # Things to delete
            if fqdn not in new_hwdata:
                self._delete_a_ptr_from_hwdata(fqdn, old_hwdata, new_hwdata)

            # Things to update
            elif old_hwdata[fqdn] != new_hwdata[fqdn]:
                self._update_a_ptr_from_hwdata(fqdn, old_hwdata, new_hwdata)
 
        # Things to add
        for fqdn in new_hwdata:
            if fqdn not in old_hwdata:
                self._add_a_ptr_from_hwdata(fqdn, old_hwdata, new_hwdata)

    def _add_a_ptr_from_hwdata(self, fqdn, old_hwdata, new_hwdata):
        ip, new_ptr, new_ttl = (new_hwdata[fqdn][key] for key in ["ip", "ptr", "ttl"])
        kwargs = {}

        if new_ptr:
            kwargs["assign_ptr_to_fqdn"] = new_ptr
        if new_ttl:
            kwargs["ttl"] = new_ttl

        self.group.add_action(
            lambda fqdn=fqdn, ip=ip, kwargs=kwargs:
                self.add_a_ptr(fqdn, ip, **kwargs),
            lambda fqdn=fqdn, ip=ip:
                self.delete_a_ptr(fqdn, ip)
        )
        self.log.info(f"add_a_ptr({fqdn}, {ip}, {kwargs}), rollback delete_a_ptr({fqdn}, {ip})")

    def _update_a_ptr_from_hwdata(self, fqdn, old_hwdata, new_hwdata):
        old_ip, old_ptr, old_ttl = (old_hwdata[fqdn][key] for key in ["ip", "ptr", "ttl"])
        new_ip, new_ptr, new_ttl = (new_hwdata[fqdn][key] for key in ["ip", "ptr", "ttl"])
        kwargs = {}
        rollback_kwargs = {}

        if old_ptr != new_ptr:
            kwargs["assign_ptr_to_fqdn"] = new_ptr
            rollback_kwargs["assign_ptr_to_fqdn"] = old_ptr
        if old_ttl != new_ttl:
            kwargs["ttl"] = new_ttl
            rollback_kwargs["ttl"] = old_ttl

        self.group.add_action(
            lambda fqdn=fqdn, old_ip=old_ip, kwargs=kwargs:
                self.update_a_ptr(fqdn, old_ip, **kwargs),
            lambda fqdn=fqdn, new_ip=new_ip, rollback_kwargs=rollback_kwargs:
                self.update_a_ptr(fqdn, new_ip, **rollback_kwargs)
        )
        self.log.info(f"update_a_ptr({fqdn}, {old_ip}, {kwargs}), rollback update_a_ptr({fqdn}, {new_ip}, {rollback_kwargs})")

    def _delete_a_ptr_from_hwdata(self, fqdn, old_hwdata, new_hwdata):
        ip, ptr, ttl = (old_hwdata[fqdn][key] for key in ["ip", "ptr", "ttl"])
        rollback_kwargs = { "ptr": ptr, "ttl": ttl }

        self.group.add_action(
            lambda fqdn=fqdn, ip=ip:
                self.delete_a_ptr(fqdn, ip),
            lambda fqdn=fqdn, ip=ip, rollback_kwargs=rollback_kwargs:
                self.add_a_ptr(fqdn, ip, **rollback_kwargs)
        )
        self.log.info(f"delete_a_ptr({fqdn}, {ip}), rollback add_a_ptr({fqdn}, {ip}, {rollback_kwargs})")

    @with_timer
    def add_dns_alias(self, name, target, ttl=None):
        args = {
            "new_target": target,
        }
        if ttl:
            args["ttl"] = ttl

        return self.update_dns_alias(name, **args)

    @with_timer
    def delete_dns_alias(self, name):
        params = { "eonid": self.eonid }
        url = f"/dns/aliases/{str(name)}"
        url = self._generate_url_from_params(url, params)

        return self._http_request("DELETE", url)

    @with_timer
    def update_dns_alias(self, name, new_target=None, ttl=None):
        payload = {"eonid": self.eonid, "create_if_doesnt_exist": True}
        if new_target is not None:
            payload["target"] = new_target
        if ttl is not None:
            payload["ttl"] = ttl
        url = f"/dns/aliases/{name}"

        return self._http_request("PATCH", url, payload)

    @with_timer
    def add_dynamic_range(self, name, start_address, end_address):
        payload = {
            "eonid":         self.eonid,
            "name":          name,
            "start_address": str(start_address),
            "end_address":   str(end_address),
        }
        url = "/ranges"

        self._http_request("POST", url, payload, ignore_statuses=[409])

    @with_timer
    def delete_dynamic_range(self, start_address, end_address):
        params = { "eonid": self.eonid }
        url = f"/ranges/{start_address}/{end_address}"
        url = self._generate_url_from_params(url, params)

        self._http_request("DELETE", url)

    @with_timer
    def show_dynamic_range(self, start_address, end_address):
        url = f"/ranges/{str(start_address)}/{str(end_address)}"

        return self._http_request("GET", url)

    def add_network(self, network, name, compartment=None, side=None, sysloc=None):
        url = "/networks/{}".format(quote(network, safe=''))

        payload = {
            "name": name,
            "compartment": compartment,
            "side": side,
            "sysloc": sysloc,
        }

        self._http_request("POST", url, payload)

    def show_network(self, network):
        url = "/networks/{}".format(quote(network, safe=''))

        return self._http_request("GET", url, ignore_statuses=[404])

    def delete_network(self, network):
        url = "/networks/{}".format(quote(network, safe=''))

        self._http_request("DELETE", url)

    def add_zone(self, fqdn, city=None):
        url = "/dns/zones/"
        payload = {"fqdn": fqdn, "city": city, "eonid": self.eonid}
        self._http_request("POST", url, payload)

    def show_zone(self, fqdn):
        url = "/dns/zones/{}".format(fqdn)

        return self._http_request("GET", url, ignore_statuses=[404])

    def delete_zone(self, fqdn):
        url = "/dns/zones/{}".format(fqdn)
        self._http_request("DELETE", url)

    def _http_request(self, http_cmd, url, data=None, ignore_statuses=[]):
        if not self.enabled:
            return

        response = None
        full_url = ""

        try:
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

            if response is not None:
                response_str = "{} {}".format(response.status_code, response.reason)

                if response.ok or response.status_code in ignore_statuses:
                    self.log.info("Successful response from Infoblox: got {} for {} {} {})".format(
                                     response_str, http_cmd, full_url, data))
                    return response
                else:
                    error_msg = ""
                    try:
                        error_msg = response.json().get("message")
                    except ValueError:
                        # Probably a JSON decode error.  Fall back to showing whole body of response.
                        error_msg = response.text

                    message = "Infoblox error: '{}' ({}) for {} {} {})".format(
                              error_msg, response_str, http_cmd, full_url, data)
                    raise ProcessException(message)
            else:
                raise ProcessException("Infoblox returned errors or no Infoblox servers could be reached, aborting change")

        except Exception as e:
            if self.transactional:
                raise e
            else:
                self.log.warning("{} (but proceeding with change as non-transactional mode is set).".format(e))


    def feature_enabled(self, name):
        enabled = False

        if self.enabled:
            enabled = name in re.split(r"\s*,\s*", self.config.get("ib-services", "enabled_features"))

        return enabled

