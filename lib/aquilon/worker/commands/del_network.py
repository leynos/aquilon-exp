# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2008,2009,2010,2011,2012,2013,2014,2015,2016,2017  Contributor
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

from aquilon.exceptions_ import ArgumentError
from aquilon.aqdb.model import DnsDomain, Network, NetworkEnvironment
from aquilon.worker.broker import BrokerCommand
from aquilon.worker.dbwrappers.dns import delete_dns_record
from aquilon.worker.ib_services import IBServices
from aquilon.worker.processes import DSDBRunner


class CommandDelNetwork(BrokerCommand):
    requires_plenaries = True

    required_parameters = ["ip"]

    def render(self, session, plenaries, dbuser, ip,
               network_environment, exporter, user, justification, reason, logger, **arguments):
        dbnet_env = NetworkEnvironment.get_unique_or_default(session,
                                                             network_environment)
        self.az.check_network_environment(dbuser, dbnet_env)

        dbnetwork = Network.get_unique(session, network_environment=dbnet_env,
                                       ip=ip, compel=True)

        plenaries.add(dbnetwork)

        # Lock order: DNS domain(s), network
        DnsDomain.lock_rows(set(rec.fqdn.dns_domain
                                for rtr in dbnetwork.routers
                                for rec in rtr.dns_records))
        dbnetwork.lock_row()

        # Delete the routers so they don't trigger the checks below
        ib_services = IBServices(logger, justification=justification, **arguments)
        for dbrouter in dbnetwork.routers:
            for dns_rec in dbrouter.dns_records:
                delete_dns_record(dns_rec, locked=True, exporter=exporter, ib_services=ib_services)
        dbnetwork.routers = []
        session.flush()

        if dbnetwork.dns_records:
            raise ArgumentError("{0} is still in use by DNS entries and "
                                "cannot be deleted.".format(dbnetwork))
        if dbnetwork.assignments:
            raise ArgumentError("{0} is still in use by hosts and "
                                "cannot be deleted.".format(dbnetwork))
        
        dsdb_runner = None
        if dbnetwork.send_to_dsdb:
            dsdb_runner = DSDBRunner(logger=logger)
            dsdb_runner.delete_network(dbnetwork)
            dsdb_runner.commit_or_rollback("Could not delete network in DSDB")

        if ib_services.feature_enabled("network"):
            try:
                ib_services.group.commit_or_rollback()
            except ProcessException as e:
                if dsdb_runner:
                    dsdb_runner.rollback()
                raise e

        session.delete(dbnetwork)
        session.flush()
        plenaries.write()

        return
