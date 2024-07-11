import re
from ipaddress import IPv4Address
from urllib.parse import quote, urlencode, urlparse, urlunparse

from requests import Session, Timeout
from requests_kerberos import DISABLED, HTTPKerberosAuth

from aquilon.aqdb.model import Alias, ARecord, DnsRecord, Fqdn, HardwareEntity, SrvRecord
from aquilon.config import Config
from aquilon.exceptions_ import ArgumentError, ProcessException
from aquilon.utils import with_timer

xstr = lambda s: None if s is None else str(s)

class IBServiceGroup:
    """This class facilitates rollback of IB commands where needed"""

    def __init__(self):
        self.functions = []

    def add_action(self, action, rollback=None):
        self.functions.append((action, rollback))
        return self

    @with_timer
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

    transaction_id_header = "X-MS-Unique-ID"

    def __init__(self, logger, justification=None, **kwargs):
        self.log = logger
        self.requestid = kwargs.get("requestid")
        self.group = IBServiceGroup()

        if justification is None or justification.lower() == "emergency":
            self.justification = None
        else:
            self.justification = justification

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

    def _assert_dns_environment(self, fqdn):
        assert(isinstance(fqdn, Fqdn))
        return fqdn.dns_environment.is_default

    def _assert_archetype(self, dbdns_rec):
        # TODO, what happens if someone runs `aq add address` (which syncs the address to infoblox), then assigns that address to an aurora host.
        #  Do we need to delete the address from infoblox at that point ?  Does it matter ?
        assert(isinstance(dbdns_rec, DnsRecord))
        return dbdns_rec.hardware_entity is None or dbdns_rec.hardware_entity.host is None or dbdns_rec.hardware_entity.host.archetype.name != "aurora"  # TODO, not sure archetype name should be hardcoded here.

    def _wants_infoblox_sync(self, dbdns_rec):
        assert(isinstance(dbdns_rec, DnsRecord))
        return self._assert_dns_environment(dbdns_rec.fqdn) and self._assert_archetype(dbdns_rec)

    def _generate_url_from_params(self, url, params):
        parse = urlparse(url)._replace(query=urlencode(params))
        return urlunparse(parse)


    def add_a_ptr(self, dbdns_rec):
        if not self._wants_infoblox_sync(dbdns_rec):
            return

        args = dbdns_rec.get_dns_args()


        if not dbdns_rec.fqdn.dns_domain.restricted:
            self.group.add_action(
                lambda name=str(args["name"]), ip=str(args["ip"]), ttl=int(args["ttl"]): self._add_a(name=name, ip=ip, ttl=ttl),
                lambda name=str(args["name"]), ip=str(args["ip"]): self._del_a(name=name, ip=ip),
            )

            if args["reverse_ptr"] is not None:
                self.group.add_action(
                    lambda name=str(args["reverse_ptr"]), ip=str(args["ip"]), ttl=int(args["ttl"]): self._add_ptr(name=name, ip=ip, ttl=ttl),
                    lambda ip=str(args["ip"]): self._del_ptr(ip=ip),
                )

    def update_a_ptr(self, dbdns_rec, _from):
        if not self._wants_infoblox_sync(dbdns_rec):
            return

        _to = dbdns_rec.get_dns_args()

        if _from["name"] != _to["name"]:
            raise ProcessException("Updating name of a-record not implemented")

        if _from["ip"] != _to["ip"] or _from["ttl"] != _to["ttl"]:
            if self._assert_dns_environment(_from["name"]):
                self.group.add_action(
                    lambda name=str(_from["name"]), ip=str(_from["ip"]), new_ip=str(_to["ip"]), new_ttl=int(_to["ttl"]): self._update_a(name=name, ip=ip, new_ip=new_ip, new_ttl=new_ttl),
                    lambda name=str(_to["name"]), ip=str(_to["ip"]), new_ip=str(_from["ip"]), new_ttl=int(_from["ttl"]): self._update_a(name=name, ip=ip, new_ip=new_ip, new_ttl=new_ttl),
                )

            for r in dbdns_rec.address_aliases:
                if self._assert_dns_environment(r.fqdn):
                    self.group.add_action(
                        lambda name=str(r.fqdn), ip=str(_from["ip"]), new_ip=str(_to["ip"]), new_ttl=int(_to["ttl"]): self._update_a(name=name, ip=ip, new_ip=new_ip, new_ttl=new_ttl),
                        lambda name=str(r.fqdn), ip=str(_to["ip"]), new_ip=str(_from["ip"]), new_ttl=int(_from["ttl"]): self._update_a(name=name, ip=ip, new_ip=new_ip, new_ttl=new_ttl),
                    )

        #TODO, this is a bit complicated, need to check different permutations of dns env
        # _from.fqdn internal _to.fqdn internal # update as is
        # _from.fqdn internal _to.fqdn external # delete the _from PTR record from IB
        # _from.fqdn external _to.fqdn internal # add the _to PTR  record to IB
        # _from.fqdn external _to.fqdn external # Don't update anything

        # If the reverse ptr exists, we need to update it
        if _from["reverse_ptr"] is not None:
            # then check if the ip changed, in which case the reverse ptr needs to be deleted and re-created
            if _from["ip"] != _to["ip"]:
                self.group.add_action(
                    lambda ip=str(_from["ip"]): self._del_ptr(ip=ip),
                    lambda name=str(_from["reverse_ptr"]), ip=str(_from["ip"]), ttl=int(_from["ttl"]): self._add_ptr(name=name, ip=ip, ttl=ttl),
                )
                self.group.add_action(
                    lambda name=str(_to["reverse_ptr"]), ip=str(_to["ip"]), ttl=int(_to["ttl"]): self._add_ptr(name=name, ip=ip, ttl=ttl),
                    lambda ip=str(_to["ip"]): self._del_ptr(ip=ip),
                )
            else:
                # else if the ip didn't change, the reverse_ptr and/or ttl might need updating
                if _from["reverse_ptr"] != _to["reverse_ptr"] or _from["ttl"] != _to["ttl"]:
                    self.group.add_action(
                        lambda ip=str(_to["ip"]), new_name=xstr(_to["reverse_ptr"]), new_ttl=int(_to["ttl"]): self._update_ptr(ip=ip, new_name=new_name, new_ttl=new_ttl),
                        lambda ip=str(_to["ip"]), new_name=str(_from["reverse_ptr"]), new_ttl=int(_from["ttl"]): self._update_ptr(ip=ip, new_name=new_name, new_ttl=new_ttl),
                    )
        else: # If the reverse ptr did not exist before, we need to create it
            if _to["reverse_ptr"] is not None:
                self.group.add_action(
                    lambda ip=str(_to["ip"]), name=str(_to["reverse_ptr"]), ttl=int(_to["ttl"]): self._add_ptr(name=name, ip=ip, ttl=ttl),
                    lambda ip=str(_to["ip"]): self._del_ptr(ip=ip),
                )

    def del_a_ptr(self, dbdns_rec):
        if not self._wants_infoblox_sync(dbdns_rec):
            return

        args = dbdns_rec.get_dns_args()

        if not dbdns_rec.fqdn.dns_domain.restricted:
            self.group.add_action(
                lambda name=str(args["name"]), ip=str(args["ip"]): self._del_a(name=name, ip=ip),
                lambda name=str(args["name"]), ip=str(args["ip"]), ttl=int(args["ttl"]): self._add_a(name=name, ip=ip, ttl=ttl)
            )

        if args["reverse_ptr"] is not None and self._assert_dns_environment(args["reverse_ptr"]):
            self.group.add_action(
                lambda ip=str(args["ip"]): self._del_ptr(ip=ip),
                lambda name=str(args["reverse_ptr"]), ip=str(args["reverse_ptr"]), ttl=int(args["ttl"]): self._add_ptr(name=name, ip=ip, ttl=ttl)
            )

            if not dbdns_rec.fqdn.dns_domain.restricted:
                # Update any PTR records that point to the A record being deleted
                for reverse_entry in dbdns_rec.fqdn.reverse_entries:
                    ib_rollback = reverse_entry.get_dns_args()

                    self.group.add_action(
                        lambda ip=str(reverse_entry.ip), new_name=str(reverse_entry.fqdn), new_ttl=-1 if reverse_entry.ttl is None else reverse_entry.ttl: self._update_ptr(ip=ip, new_name=new_name, new_ttl=new_ttl),
                        lambda ip=str(reverse_entry.ip), new_name=str(dbdns_rec.fqdn), new_ttl=-1 if dbdns_rec.ttl is None else dbdns_rec.ttl: self._update_ptr(ip=ip, new_name=new_name, new_ttl=new_ttl),
                    )

    def add_hardware_entity(self, dbhw_ent):
        assert(isinstance(dbhw_ent, HardwareEntity))

        for address in dbhw_ent.all_addresses():
            for rec in address.dns_records:
                self.add_a_ptr(rec)

    def del_hardware_entity(self, dbhw_ent):
        assert(isinstance(dbhw_ent, HardwareEntity))

        for address in dbhw_ent.all_addresses():
            for rec in address.dns_records:
                self.del_a_ptr(rec)

    @with_timer
    def _add_ptr(self, name, ip, ttl=None):
        assert(isinstance(name, str))
        assert(isinstance(ip, str))
        if ttl is not None:
            assert(isinstance(ttl, int))
        if not self._assert_ip(ip):
            return
        if not name:
            raise ArgumentError("Required argument 'name' is missing")
        payload = {"name": name, "address": ip}
        if ttl is not None and ttl != -1:
            payload['ttl'] = ttl
        if (self.justification is not None):
            payload["cm_token"] = self.justification
        r = self._http_request("POST", "/dns/a_ptr/ptr", payload, ignore_statuses=[409])
        if r is not None and r.status_code == 409:
            return self._update_ptr(ip, new_name=name, new_ttl=ttl)
        return r

    @with_timer
    def _update_ptr(self, ip, new_name, new_ttl=None):
        assert(isinstance(ip, str))
        if new_name is None:
            raise ArgumentError("new_name parameter is required")
        assert(isinstance(new_name, str))
        if new_ttl is not None:
            assert(isinstance(new_ttl, int))
        if not self._assert_ip(ip):
            return
        if new_name is None and new_ttl is None:
            return

        payload = {}
        if (self.justification is not None):
            payload["cm_token"] = self.justification
        if new_name is not None:
            payload['name'] = new_name
        if new_ttl is not None:
            payload['ttl'] = new_ttl

        url = "/dns/a_ptr/ptr/{}".format(ip)
        r = self._http_request("PATCH", url, payload, ignore_statuses=[404])
        if r is not None and r.status_code == 404:
            if new_name is None:
                raise ArgumentError("Required argument 'new_name is missing")
            payload['name'] = new_name
            payload['address'] = ip
            if payload.get('ttl'):
                if payload['ttl'] == -1:
                    del payload['ttl']
            return self._http_request("POST", "/dns/a_ptr/ptr", payload)
        else:
            return r

    @with_timer
    def _del_ptr(self, ip):
        assert(isinstance(ip, str))
        if not self._assert_ip(ip):
            return
        params = {}
        if self.justification is not None:
            params["cm_token"] = self.justification
        url = "/dns/a_ptr/ptr/{}".format(ip)
        url = self._generate_url_from_params(url, params)

        return self._http_request("DELETE", url, ignore_statuses=[404])

    @with_timer
    def _add_a(self, name, ip, ttl=None):
        assert(isinstance(name, str))
        assert(isinstance(ip, str))
        if ttl is not None:
            assert(isinstance(ttl, int))
        if not self._assert_ip(ip):
            return
        if not self._is_domain_authoritative(name):
            return

        payload = {"name": name, "address": ip}
        if ttl is not None and ttl != -1:
            payload['ttl'] = ttl
        if (self.justification is not None):
            payload["cm_token"] = self.justification
        r = self._http_request("POST", "/dns/a_ptr/a", payload, ignore_statuses=[409])
        if r is not None and r.status_code == 409:
            r = self._update_a(name, ip, new_ip=ip, new_ttl=ttl)
        return r

    @with_timer
    def _update_a(self, name, ip, new_ip, new_ttl=None):
        assert(isinstance(name, str))
        assert(isinstance(ip, str))
        if new_ip is None:
            raise ArgumentException("Required parameter ip missing")
        assert(isinstance(new_ip, str))
        if new_ttl is not None:
            assert(isinstance(new_ttl, int))
        if not self._assert_ip(ip):
            return
        if new_ip is None and new_ttl is None:
            return
        if not self._is_domain_authoritative(name):
            return

        payload = {}
        if (self.justification is not None):
            payload["cm_token"] = self.justification
        if new_ip is not None:
            payload['address'] = new_ip
        if new_ttl is not None:
            payload['ttl'] = new_ttl

        url = "/dns/a_ptr/a/{}/{}".format(name, ip)
        r = self._http_request("PATCH", url, payload, ignore_statuses=[404])
        if r is not None and r.status_code == 404:
            if new_ip is None:
                raise ArgumentError(f"Required argument '{new_ip}' is missing")
            payload['name'] = name
            payload['address'] = new_ip
            if payload.get('ttl'):
                if payload['ttl'] == -1:
                    del payload['ttl']
            return self._http_request("POST", "/dns/a_ptr/a", payload)
        else:
            return r

    @with_timer
    def _del_a(self, name, ip):
        assert(isinstance(name, str))
        assert(isinstance(ip, str))
        if not self._assert_ip(ip):
            return
        if not self._is_domain_authoritative(name):
            return
        params = {}
        if self.justification is not None:
            params["cm_token"] = self.justification
        url = "/dns/a_ptr/a/{}/{}".format(name, ip)
        url = self._generate_url_from_params(url, params)

        return self._http_request("DELETE", url, ignore_statuses=[404])

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

            dns_record = addr.dns_records[0] #  TODO odd, can there be more than one dns record ?

            if not self._assert_archetype(dns_record):
                continue

            if not isinstance(dns_record, ARecord):
                continue

            fqdn = str(dns_record.fqdn)
            ptr = str(dns_record.reverse_ptr) if dns_record.reverse_ptr else None

            hwdata[fqdn] = {
                "ip":  str(addr.ip),
                "ptr": ptr,
                "ttl": dns_record.ttl,
                "restricted_dns_domain": dns_record.fqdn.dns_domain.restricted,
                "default_dns_environment": dns_record.fqdn.dns_environment.is_default,
            }

        # The primary address of Zebra hosts needs extra care. Here, we cheat a
        # bit - we do not check if the primary name is a service address, but
        # instead check if it has an IP address and it was not handled above.
        if (dbhw_ent.primary_ip and str(dbhw_ent.primary_name.fqdn) not in hwdata):
            ptr = str(dbhw_ent.primary_name.reverse_ptr) if dbhw_ent.primary_name.reverse_ptr else None

            hwdata[str(dbhw_ent.primary_name.fqdn)] = {
                "ip":  str(dbhw_ent.primary_ip),
                "ptr": ptr,
                "ttl": dbhw_ent.primary_name.ttl,
                "restricted_dns_domain": dbhw_ent.primary_name.fqdn.dns_domain.restricted,
                "default_dns_environment": dbhw_ent.primary_name.fqdn.dns_environment.is_default,
            }

        return hwdata

    def bulk_change_a_ptr(self, old_hwdata, new_hwdata):
        self.log.debug(f"bulk_change_a_ptr(): data before change = {old_hwdata}, data after change = {new_hwdata}")

        # TODO don't send data if it's an aurora host and if it's a restricted domain, send only PTR records
        # I think these tests can be done in the snapshot function where we have the db objects

        for fqdn in old_hwdata:
            # Things to delete
            if fqdn not in new_hwdata:
                self._delete_a_ptr_from_hwdata(fqdn, old_hwdata, new_hwdata)

            # Things to update
            elif old_hwdata[fqdn] != new_hwdata[fqdn]:
                #TODO, if fqdn belongs to an ARecord that is a target of an AddressAlias, all the AddressAliases need updating too
                self._update_a_ptr_from_hwdata(fqdn, old_hwdata, new_hwdata)

        # Things to add
        for fqdn in new_hwdata:
            if fqdn not in old_hwdata:
                self._add_a_ptr_from_hwdata(fqdn, old_hwdata, new_hwdata)

    def _add_a_ptr_from_hwdata(self, fqdn, old_hwdata, new_hwdata):
        ip, new_ptr, new_ttl, restricted_dns_domain, default_dns_environment = (new_hwdata[fqdn][key] for key in ["ip", "ptr", "ttl", "restricted_dns_domain", "default_dns_environment"])

        if default_dns_environment:
            if not restricted_dns_domain:
                self.group.add_action(
                    lambda fqdn=fqdn, ip=ip, ttl=-1 if new_ttl is None else new_ttl:
                        self._add_a(fqdn, ip, ttl),
                    lambda fqdn=fqdn, ip=ip:
                        self._del_a(fqdn, ip)
                )

            self.group.add_action(
                lambda fqdn=fqdn if new_ptr is None else new_ptr, ip=ip, ttl=-1 if new_ttl is None else new_ttl:
                    self._add_ptr(fqdn, ip, ttl),
                lambda ip=ip:
                    self._del_ptr(ip)
            )

    def _update_a_ptr_from_hwdata(self, fqdn, old_hwdata, new_hwdata):
        old_ip, old_ptr, old_ttl, old_restricted_dns_domain, old_default_dns_environment = (old_hwdata[fqdn][key] for key in ["ip", "ptr", "ttl", "restricted_dns_domain", "default_dns_environment"])
        new_ip, new_ptr, new_ttl, new_restricted_dns_domain, new_default_dns_environment = (new_hwdata[fqdn][key] for key in ["ip", "ptr", "ttl", "restricted_dns_domain", "default_dns_environment"])

        if old_default_dns_environment:
            if not old_restricted_dns_domain:
                if old_ip != new_ip or old_ttl != new_ttl:
                        self.group.add_action(
                            lambda name=fqdn, ip=old_ip, new_ip=new_ip, ttl=-1 if new_ttl is None else new_ttl: self._update_a(name=name, ip=ip, new_ip=new_ip, new_ttl=ttl),
                            lambda name=fqdn, ip=new_ip, new_ip=old_ip, ttl=-1 if old_ttl is None else old_ttl: self._update_a(name=name, ip=ip, new_ip=new_ip, new_ttl=ttl),
                        )

            if old_ip != new_ip:
                self.group.add_action(
                    lambda ip=old_ip: self._del_ptr(ip),
                    lambda name=fqdn, ip=old_ip, ttl=old_ttl: self._add_ptr(name, ip, ttl=-1 if ttl is None else ttl)
                )
                self.group.add_action(
                    lambda name=fqdn, ip=new_ip, ttl=new_ttl: self._add_ptr(name, ip, ttl=-1 if ttl is None else ttl),
                    lambda ip=new_ip: self._del_ptr(ip),
                )
            else:
                if old_ptr != new_ptr or old_ttl != new_ttl:
                    self.group.add_action(
                        lambda ip=old_ip:
                            self._update_ptr(ip, new_name=fqdn if new_ptr is None else new_ptr, new_ttl=-1 if new_ttl is None else new_ttl),
                        lambda ip=old_ip:
                            self._update_ptr(ip, new_name=fqdn if old_ptr is None else old_ptr, new_ttl=-1 if old_ttl is None else old_ttl)
                    )

    def _delete_a_ptr_from_hwdata(self, fqdn, old_hwdata, new_hwdata):
        ip, ptr, ttl, restricted_dns_domain, default_dns_environment = (old_hwdata[fqdn][key] for key in ["ip", "ptr", "ttl", "restricted_dns_domain", "default_dns_environment"])

        if default_dns_environment:
            if not restricted_dns_domain:
                self.group.add_action(
                    lambda fqdn=fqdn, ip=ip:
                        self._del_a(fqdn, ip),
                    lambda fqdn=fqdn, ip=ip, ttl=ttl:
                        self._add_a(fqdn, ip, ttl)
                )
            self.group.add_action(
                lambda ip=ip: self._del_ptr(ip),
                lambda fqdn=fqdn if ptr is None else ptr, ip=ip, ttl=ttl:
                    self._add_ptr(fqdn, ip, ttl)
            )

    def add_dns_alias(self, dbdns_rec):
        assert(isinstance(dbdns_rec, Alias))
        if not self._wants_infoblox_sync(dbdns_rec):
            return
        args = dbdns_rec.get_dns_args()
        self.group.add_action(
            lambda name=str(args["name"]), target=str(args["target"]), ttl=int(args["ttl"]): self._add_dns_alias(name=name, target=target, ttl=ttl),
            lambda name=str(args["name"]): self._del_dns_alias(name=name),
        )

    def del_dns_alias(self, dbdns_rec):
        assert(isinstance(dbdns_rec, Alias))
        if not self._wants_infoblox_sync(dbdns_rec):
            return

        args = dbdns_rec.get_dns_args()
        self.group.add_action(
            lambda name=str(args["name"]): self._del_dns_alias(name=name),
            lambda name=str(args["name"]), target=str(args["target"]), ttl=int(args["ttl"]): self._add_dns_alias(name=name, target=target, ttl=ttl),
        )

    def update_dns_alias(self, dbdns_rec, _from):
        assert(isinstance(dbdns_rec, Alias))
        if not self._wants_infoblox_sync(dbdns_rec):
            return
        _to = dbdns_rec.get_dns_args()
        self.group.add_action(
            lambda name=str(_to["name"]), new_target=str(_to["target"]), new_ttl=int(_to["ttl"]): self._update_dns_alias(name=name, new_target=new_target, ttl=new_ttl),
            lambda name=str(_to["name"]), new_target=str(_from["target"]), new_ttl=int(_from["ttl"]): self._update_dns_alias(name=name, new_target=new_target, ttl=new_ttl),
        )


    @with_timer
    def _add_dns_alias(self, name, target, ttl=None):
        assert(isinstance(name, str))
        assert(isinstance(target, str))
        if ttl is not None:
            assert(isinstance(ttl, int))
        payload = {"name": name, "target": target}
        if ttl is not None and ttl != -1:
            payload["ttl"] = ttl
        if self.justification is not None:
            payload["cm_token"] = self.justification
        url = f"/dns/aliases/"

        r = self._http_request("POST", url, payload, ignore_statuses=[409])
        if r is not None and r.status_code == 409:
            return self._update_dns_alias(name, new_target=target, ttl=ttl)
        else:
            return r

    @with_timer
    def _del_dns_alias(self, name):
        assert(isinstance(name, str))
        params = {}
        if self.justification is not None:
            params["cm_token"] = self.justification
        url = f"/dns/aliases/{name}"
        url = self._generate_url_from_params(url, params)

        return self._http_request("DELETE", url, ignore_statuses=[404])

    @with_timer
    def _update_dns_alias(self, name, new_target=None, ttl=None):
        assert(isinstance(name, str))
        if new_target is not None:
            assert(isinstance(new_target, str))
        if ttl is not None:
            assert(isinstance(ttl, int))
        payload = {}
        if new_target is not None:
            payload["target"] = new_target
        if ttl is not None:
            payload["ttl"] = ttl
        if self.justification is not None:
            payload["cm_token"] = self.justification
        url = "/dns/aliases/{}".format(name)

        r = self._http_request("PATCH", url, payload, ignore_statuses=[404])
        if r is not None and r.status_code == 404:
            if new_target is None:
                raise ArgumentError("Required argument 'new_target' is missing")
            payload['name'] = name
            if payload.get('ttl'):
                if payload['ttl'] == -1:
                    del payload['ttl']
            r = self._http_request("POST", "/dns/aliases/", payload)
            return r
        else:
            return r

    @with_timer
    def add_dynamic_range(self, name, start_address, end_address):
        payload = {
            "name":          name,
            "start_address": str(start_address),
            "end_address":   str(end_address),
        }
        if self.justification is not None:
            payload["cm_token"] = self.justification
        url = "/ranges"

        self._http_request("POST", url, payload, ignore_statuses=[409])

    @with_timer
    def delete_dynamic_range(self, start_address, end_address):
        params = {}
        if self.justification is not None:
            params["cm_token"] = self.justification
        url = f"/ranges/{start_address}/{end_address}"
        url = self._generate_url_from_params(url, params)

        self._http_request("DELETE", url, ignore_statuses=[404])

    @with_timer
    def show_dynamic_range(self, start_address, end_address):
        url = f"/ranges/{str(start_address)}/{str(end_address)}"

        return self._http_request("GET", url)

    def add_dns_srv_record(self, r):
        assert(isinstance(r, SrvRecord))

        if not self._assert_dns_environment(r.fqdn):
            return

        self.group.add_action(
            lambda service=r.service, protocol=r.protocol, dns_domain=str(r.fqdn.dns_domain), target=str(r.target.fqdn), port=r.port, priority=r.priority, weight=r.weight, ttl=r.ttl:
                self._add_dns_srv_record(service, protocol, dns_domain, target, port, priority, weight, ttl),
            lambda service=r.service, protocol=r.protocol, dns_domain=str(r.fqdn.dns_domain), target=str(r.target.fqdn), port=r.port, priority=r.priority, weight=r.weight:
                self._del_dns_srv_record(service, protocol, dns_domain, target, port, priority, weight),
        )

    @with_timer
    def _add_dns_srv_record(self, service, protocol, dns_domain, target, port, priority, weight, ttl=None):
        assert(isinstance(service, str))
        assert(isinstance(protocol, str))
        assert(isinstance(dns_domain, str))
        assert(isinstance(target, str))
        assert(isinstance(port, int))
        assert(isinstance(priority, int))
        assert(isinstance(weight, int))
        if ttl is not None:
            assert(isinstance(ttl, int))
        url = "/dns/srv"
        payload = {
            "service":  service,
            "protocol": protocol,
            "domain":   str(dns_domain),
            "target":   target,
            "port":     port,
            "priority": priority,
            "weight":   weight,
        }
        if target is not None:
            payload["target"] = str(target)
        if ttl:
            payload["ttl"] = ttl
        if self.justification is not None:
            payload["cm_token"] = self.justification

        return self._http_request("POST", url, payload, ignore_statuses=[409])

    def del_dns_srv_record(self, r):
        assert(isinstance(r, SrvRecord))

        if not self._assert_dns_environment(r.fqdn):
            return

        self.group.add_action(
            lambda service=r.service, protocol=r.protocol, dns_domain=str(r.fqdn.dns_domain), target=str(r.target.fqdn), port=r.port, priority=r.priority, weight=r.weight:
                self._del_dns_srv_record(service, protocol, dns_domain, target, port, priority, weight),
            lambda service=r.service, protocol=r.protocol, dns_domain=str(r.fqdn.dns_domain), target=str(r.target.fqdn), port=r.port, priority=r.priority, weight=r.weight, ttl=r.ttl:
                self._add_dns_srv_record(service, protocol, dns_domain, target, port, priority, weight, ttl),
        )

    @with_timer
    def _del_dns_srv_record(self, service, protocol, dns_domain, target, port, priority, weight):
        assert(isinstance(service, str))
        assert(isinstance(protocol, str))
        assert(isinstance(dns_domain, str))
        assert(isinstance(target, str))
        assert(isinstance(port, int))
        assert(isinstance(priority, int))
        assert(isinstance(weight, int))
        options = {
            "service":  service,
            "protocol": protocol,
            "domain":   str(dns_domain),
            "target":   target,
            "port":     port,
            "priority": priority,
            "weight":   weight,
            "cm_token": self.justification,
        }
        if target is not None:
            options["target"] = str(target)
        params = dict(filter(lambda item: item[1] is not None, options.items()))
        url = self._generate_url_from_params("/dns/srv", params)

        return self._http_request("DELETE", url, ignore_statuses=[404])

    def update_dns_srv_record(self, s, old):
        assert(isinstance(s, SrvRecord))
        if not self._wants_infoblox_sync(s):
            return

        new = s.get_dns_args()

        new["domain"] = str(new["domain"])
        new["target"] = str(new["target"])

        old["domain"] = str(old["domain"])
        old["target"] = str(old["target"])

        if old == new:
            return

        self.group.add_action(
            lambda old=old, new=new: self._update_dns_srv_record(old, new),
            lambda old=new, new=old: self._update_dns_srv_record(old, new),
        )

    @with_timer
    def _update_dns_srv_record(self, old, new):
        required_fields = ("service", "protocol", "domain", "port", "target", "priority", "weight")
        payload = {}

        for field in required_fields:
            if old[field] is None:
                raise ArgumentError("Required argument '{}' is missing".format(field))
            payload[field] = new[field] if field in new else old[field]

        if new.get("ttl", None):
            payload["ttl"] = new["ttl"]
        if payload.get("domain", None):
            payload["domain"] = str(payload["domain"])
        if payload.get("target", None):
            payload["target"] = str(payload["target"])
        payload["cm_token"] = self.justification

        params = dict(filter(lambda item: item[1] is not None, old.items()))
        url = self._generate_url_from_params("/dns/srv", params)

        return self._http_request("PATCH", url, payload)

    @with_timer
    def show_dns_srv_record(self, service, protocol, dns_domain, target, port=None, priority=None, weight=None):
        params = {
            "service":  service,
            "protocol": protocol,
            "domain":   str(dns_domain),
            "target":   str(target),
        }

        optional_params = {
            "port":     port,
            "priority": priority,
            "weight":   weight,
        }
        for field in optional_params:
            if optional_params[field] is not None:
                params[field] = optional_params[field]

        url = self._generate_url_from_params("/dns/srv", params)

        return self._http_request("GET", url, ignore_statuses=[404])

    @with_timer
    def _show_zone_type(self, dns_domain):
        url = f"/dns/zones/type/{dns_domain}"
        return self._http_request("GET", url)

    def _get_domain_from_fqdn(self, fqdn):
        parts = fqdn.split('.')
        if len(parts) > 2:
            return '.'.join(parts[1:])
        else:
            return fqdn

    def _is_domain_authoritative(self, fqdn):
        response = self._show_zone_type(self._get_domain_from_fqdn(fqdn))
        response_text = response.text

        if re.search("forward", response_text):
            return True
        elif re.search("delegated", response_text):
            return False

        raise ProcessException(f"Unexpected result '{response_text}' when retrieving zone type for {fqdn}")

    def _http_request(self, http_cmd, url, data=None, ignore_statuses=[]):
        if not self.enabled:
            return

        response = None
        full_url = ""

        headers = {}
        if self.requestid:
            headers[self.transaction_id_header] = str(self.requestid)
        else:
            self.log.info("No requestid found!!")

        try:
            for base_url in self.urls:
                full_url = base_url + url

                try:
                    log_msg = f"Sending request {http_cmd} {full_url}"
                    if data:
                        log_msg += f" with data {data}"
                    self.log.info(log_msg)

                    response = self.session.request(http_cmd, full_url, json=data, timeout=self.timeout,
                                                    headers=headers)
                except Timeout:
                    self.log.warning(f"Infoblox timeout error: request to {full_url} timed out after {self.timeout}s.")

                # There are several possible other exception types.  Not all possibilities are known.
                # In all cases, the logic depends on another pass through the loop to try any remaining URLs.
                except Exception as e:
                    self.log.warning(f"Infoblox request exception error: request to {full_url} failed with exception {e}")

                # Stop trying URLs if there was no exception.
                else:
                    break

            if response is not None:
                if response.ok or response.status_code in ignore_statuses:
                    self._log_ib_result("Successful response from Infoblox: ", http_cmd, full_url, data, response)
                    return response
                else:
                    error_msg = ""
                    try:
                        error_msg = response.json().get("message")
                    except ValueError:
                        # Probably a JSON decode error.  Fall back to showing whole body of response.
                        error_msg = response.text

                    msg = self._log_ib_result(f"Infoblox error: '{error_msg}'", http_cmd, full_url, data, response)
                    raise ProcessException(msg)
            else:
                raise ProcessException("Infoblox returned errors or no Infoblox servers could be reached, aborting change")

        except Exception as e:
            if self.transactional:
                raise e
            else:
                self.log.warning(f"{e} (but proceeding with change as non-transactional mode is set).")

    def _log_ib_result(self, msg, http_cmd, full_url, request_data, response):
        response_str = f"{response.status_code} {response.reason}"
        msg += f" got {response_str} for {http_cmd} {full_url}"

        if request_data:
            msg += f" (request body '{request_data}')"
        if response.text and response.text != "{}":
            msg += f" (response body '{response.text}')"
        if self.requestid:
            msg += f" (AQD request ID '{self.requestid}')"
        ib_request_id = response.headers.get(self.transaction_id_header)
        if ib_request_id:
            msg += f" (Infoblox request ID '{ib_request_id}')"
        self.log.info(msg)
        return msg

    def feature_enabled(self, name):
        enabled = False

        if self.enabled:
            enabled = name in re.split(r"\s*,\s*", self.config.get("ib-services", "enabled_features"))

        return enabled

