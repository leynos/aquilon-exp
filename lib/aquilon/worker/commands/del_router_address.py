# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2009,2010,2011,2012,2013,2014,2015,2016,2017  Contributor
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
"""Contains the logic for `aq del router address`."""

from aquilon.exceptions_ import ArgumentError, NotFoundException
from aquilon.aqdb.model import ARecord, NetworkEnvironment
from aquilon.aqdb.model.network import get_net_id_from_ip
from aquilon.worker.broker import BrokerCommand
from aquilon.worker.dbwrappers.dns import delete_dns_record
from aquilon.worker.dbwrappers.change_management import ChangeManagement
from aquilon.worker.processes import IBServices
from requests import RequestException


class CommandDelRouterAddress(BrokerCommand):
    requires_plenaries = True

    required_parameters = []

    def render(self, session, plenaries, dbuser, ip, fqdn,
               network_environment, exporter, user, justification, reason, logger, **arguments):
        dbnet_env = NetworkEnvironment.get_unique_or_default(session,
                                                             network_environment)
        self.az.check_network_environment(dbuser, dbnet_env)
        if fqdn:
            dbdns_rec = ARecord.get_unique(session, fqdn=fqdn,
                                           dns_environment=dbnet_env.dns_environment,
                                           compel=True)
            ip = dbdns_rec.ip
        elif not ip:
            raise ArgumentError("Please specify either --ip or --fqdn.")

        dbnetwork = get_net_id_from_ip(session, ip, dbnet_env)

        # Validate ChangeManagement
        cm = ChangeManagement(session, user, justification, reason, logger, self.command, **arguments)
        cm.consider(dbnetwork)
        cm.validate()

        dbrouter = None
        for rtaddr in dbnetwork.routers:
            if rtaddr.ip == ip:
                dbrouter = rtaddr
                break
        if not dbrouter:
            raise NotFoundException("IP address {0} is not a router on "
                                    "{1:l}.".format(ip, dbnetwork))

        # Only remove the DNS record if its not assinged to an interface,
        # or is a service address.  (This would be easier if service
        # address were not split from assignments)
        for dns_rec in dbrouter.dns_records:
            if dns_rec.is_unused:
                delete_dns_record(dns_rec, verify_assignments=True,
                                  exporter=exporter)

        dbnetwork.routers.remove(dbrouter)
        session.flush()

        with plenaries.transaction():
            # TODO: update the templates of Zebra hosts on the network
            plenaries.add(dbnetwork)

            if self.config.infoblox_feature_enabled("del_router_address"):
                # If FQDN not passed then look it up from the DNS records associated with the router
                if not fqdn:
                    for r in dbrouter.dns_records:
                        if r.ip == ip:
                            fqdn = r.fqdn
                if not fqdn:
                    logger.warning("Unable to determine FQDN from IP {} and can not remove A/PTR from Infoblox"
                                   .format(ip))
                try:
                    IBServices().delete_a_ptr(fqdn, ip)
                except (ArgumentError,RequestException) as e:
                    logger.warning("Error calling Infoblox delete_a_ptr: {0}".format(str(e)))
                    logger.warning("Rolling back DSDB transaction ...")
                    raise e
