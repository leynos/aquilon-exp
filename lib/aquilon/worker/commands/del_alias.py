# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2008,2009,2010,2011,2012,2013,2016,2017  Contributor
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
"""Contains the logic for `aq del alias`."""

from aquilon.aqdb.model import DnsEnvironment, Alias
from aquilon.exceptions_ import ArgumentError, ProcessException
from aquilon.worker.broker import BrokerCommand
from aquilon.worker.dbwrappers.change_management import ChangeManagement
from aquilon.worker.dbwrappers.dns import delete_dns_record
from aquilon.worker.dbwrappers.service_instance import check_no_provided_service
from aquilon.worker.ib_services import IBServices
from aquilon.worker.processes import DSDBRunner



class CommandDelAlias(BrokerCommand):

    required_parameters = ["fqdn"]

    def render(self, session, logger, fqdn, dns_environment,
               exporter, user, justification, reason, **arguments):
        requestid = arguments.get("requestid")
        dbdns_env = DnsEnvironment.get_unique_or_default(session,
                                                         dns_environment)
        dbdns_rec = Alias.get_unique(session, fqdn=fqdn,
                                     dns_environment=dbdns_env, compel=True)

        if dns_environment is not None and dns_environment != 'internal' \
                and justification is None:
            raise ArgumentError("Please provide valid justification "
                                "number")

        # Validate ChangeManagement
        cm = ChangeManagement(session, user, justification, reason, logger, self.command, **arguments)
        cm.consider(dbdns_rec.target)
        cm.validate()

        domain = dbdns_rec.fqdn.dns_domain.name

        check_no_provided_service(dbdns_rec)

        old_target_fqdn = str(dbdns_rec.target)
        old_comments = dbdns_rec.comments
        target_is_restricted = dbdns_rec.target.dns_domain.restricted
        delete_dns_record(dbdns_rec, exporter=exporter)

        session.flush()

        dsdb_runner = None
        if dbdns_env.is_default and domain == "ms.com" and not target_is_restricted:
            dsdb_runner = DSDBRunner(logger=logger)
            dsdb_runner.del_alias(fqdn, old_target_fqdn, old_comments)
            dsdb_runner.commit_or_rollback("Could not delete alias from DSDB")

        ib_services = IBServices(logger, requestid)
        if ib_services.feature_enabled("alias"):
            try:
                if ib_services.assert_dns_environment(dbdns_rec.fqdn.dns_environment.name):
                    ib_services.delete_dns_alias(str(dbdns_rec))
            except ProcessException as e:
                if dsdb_runner:
                    dsdb_runner.rollback()
                raise e
