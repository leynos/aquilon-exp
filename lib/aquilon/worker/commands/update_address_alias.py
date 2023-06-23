# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2015,2016,2017  Contributor
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
"""Contains the logic for `aq update address alias`."""

from aquilon.aqdb.model import Fqdn, AddressAlias
from aquilon.worker.broker import BrokerCommand
from aquilon.worker.dbwrappers.grn import lookup_grn
from aquilon.exceptions_ import ArgumentError
from aquilon.worker.dbwrappers.change_management import ChangeManagement
from aquilon.worker.ib_services import IBServices

from requests import RequestException


class CommandUpdateAddressAlias(BrokerCommand):

    required_parameters = ["fqdn"]

    def render(self, session, logger, fqdn, target, ttl, clear_ttl, comments,
               dns_environment, target_environment, grn, eon_id, clear_grn,
               exporter, user, justification, reason, **arguments):
        if not target_environment:
            target_environment = dns_environment

        dbfqdn = Fqdn.get_unique(session, fqdn=fqdn,
                                 dns_environment=dns_environment,
                                 compel=True)

        dbdns_records = []
        if target:
            dbtarget = Fqdn.get_unique(session, fqdn=target,
                                       dns_environment=target_environment,
                                       compel=True)

            dbaddr_alias = AddressAlias.get_unique(session, fqdn=dbfqdn,
                                                   target=dbtarget, compel=True)
            dbdns_records.append(dbaddr_alias)
        else:
            dbdns_records = [rec for rec in dbfqdn.dns_records if isinstance(rec, AddressAlias)]
            if len(dbdns_records) == 0:
                raise ArgumentError("No address alias record found.")

        dbgrn = None
        update_grn = False
        if grn or eon_id:
            dbgrn = lookup_grn(session, grn, eon_id, logger=logger,
                               config=self.config)
            update_grn = True
        elif clear_grn:
            update_grn = True

        # Validate ChangeManagement
        cm = ChangeManagement(session, user, justification, reason, logger, self.command, **arguments)
        for dbaddr_alias in dbdns_records:
            cm.consider(dbaddr_alias.target)

            if ttl is not None:
                dbaddr_alias.ttl = ttl
            elif clear_ttl:
                dbaddr_alias.ttl = None

            if update_grn:
                dbaddr_alias.owner_grn = dbgrn

            if comments is not None:
                dbaddr_alias.comments = comments

        cm.validate()

        ib_services = IBServices(logger)
        if ib_services.feature_enabled('update_address_alias') and ttl:
            try:
                for dns_rec in dbdns_records:
                    if ib_services.assert_dns_environment(dns_rec.fqdn.dns_environment.name):
                        ib_services.update_a_ptr(str(dns_rec), dns_rec.target_ip, ttl=ttl, update_ptr=False)
            except (ArgumentError, RequestException) as e:
                raise e


        if exporter:
            exporter.update(dbfqdn)

        session.flush()
        return
