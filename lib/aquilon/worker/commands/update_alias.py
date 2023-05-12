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
"""Contains the logic for `aq update alias`."""

from aquilon.exceptions_ import ArgumentError, NotFoundException
from aquilon.aqdb.model import Alias, DnsEnvironment
from aquilon.worker.broker import BrokerCommand
from aquilon.worker.dbwrappers.dns import (create_target_if_needed,
                                           delete_target_if_needed)
from aquilon.worker.dbwrappers.grn import lookup_grn
from aquilon.worker.processes import DSDBRunner, IBServices
from aquilon.worker.dbwrappers.change_management import ChangeManagement

from requests import RequestException


class CommandUpdateAlias(BrokerCommand):

    required_parameters = ["fqdn"]

    def render(self, session, logger, fqdn, dns_environment, target,
               target_environment, ttl, clear_ttl, grn, eon_id, clear_grn,
               comments, exporter, user, justification, reason, **arguments):
        dbdns_env = DnsEnvironment.get_unique_or_default(session,
                                                         dns_environment)

        if target_environment:
            dbtgt_env = DnsEnvironment.get_unique_or_default(session,
                                                             target_environment)
        else:
            dbtgt_env = dbdns_env

        dbalias = Alias.get_unique(session, fqdn=fqdn,
                                   dns_environment=dbdns_env, compel=True)

        if dns_environment is not None and dns_environment != 'internal' \
                and justification is None:
            raise ArgumentError("Please provide valid justification "
                                "number")

        # Validate ChangeManagement
        cm = ChangeManagement(session, user, justification, reason, logger, self.command, **arguments)
        cm.consider(dbalias.target)
        cm.validate()

        old_target_fqdn = str(dbalias.target.fqdn)
        old_comments = dbalias.comments

        if grn or eon_id:
            dbgrn = lookup_grn(session, grn, eon_id, logger=logger,
                               config=self.config)
            dbalias.owner_grn = dbgrn
        elif clear_grn:
            dbalias.owner_grn = None

        old_target = None
        if target or target_environment:
            if target == fqdn:
                raise ArgumentError("Cannot alias {0} to itself"
                                    .format(fqdn))

            old_target = dbalias.target

            # see if the new target is an alias: if so, check we're not
            # creating a loop
            try:
                ntalias = Alias.get_unique(session, fqdn=target,
                                           dns_environment=dbdns_env, compel=True)
            except NotFoundException:
                ntalias = None

            if ntalias is not None:
                if fqdn in ntalias.get_alias_targets():
                    raise ArgumentError("Cannot alias {0} to {1}, as that "
                                        "is an alias of {0}"
                                        .format(fqdn, target))
                # Ensure max alias depth requirement not breached
                if ntalias.alias_depth + 1 > Alias.MAX_ALIAS_DEPTH:
                    raise ArgumentError("Maximum alias depth would be exceeded - "
                                        "new target is an alias.")
                if any([al.alias_depth + ntalias.alias_depth >
                        Alias.MAX_ALIAS_DEPTH for al in dbalias.all_aliases]):
                    raise ArgumentError("Maximum alias depth would be exceeded - "
                                        "new target is an alias.")
            dbalias.target = create_target_if_needed(session, logger, target, dbtgt_env)

            # TODO: at some day we should verify that the new target is also
            # bound as a server, and modify the ServiceInstanceServer bindings
            # accordingly
            for srv in dbalias.services_provided:
                if srv.host or srv.cluster:
                    provider = srv.host or srv.cluster
                    logger.client_info("Warning: {0} provides {1:l}, and is "
                                       "bound to {2:l}. Updating the target of "
                                       "the alias may leave that server "
                                       "binding in an inconsistent state."
                                       .format(dbalias, srv.service_instance,
                                               provider))

            if dbalias.target.dns_domain.restricted != \
                    old_target.dns_domain.restricted:
                raise ArgumentError("Cannot update alias {0} because the "
                                    "value of the restricted flag does not "
                                    "match between old and new DNS domains"
                                    .format(fqdn))

            if dbalias.target != old_target:
                delete_target_if_needed(session, old_target)

        if ttl is not None:
            dbalias.ttl = ttl
        elif clear_ttl:
            dbalias.ttl = None

        if comments is not None:
            dbalias.comments = comments

        if exporter:
            exporter.update(dbalias.fqdn)

        session.flush()

        dsdb_runner = None
        if dbdns_env.is_default and dbalias.fqdn.dns_domain.name == "ms.com"\
                and not dbalias.target.dns_domain.restricted:
            dsdb_runner = DSDBRunner(logger=logger)
            dsdb_runner.update_alias(fqdn, dbalias.target.fqdn,
                                     dbalias.comments, old_target_fqdn,
                                     old_comments)
            dsdb_runner.commit_or_rollback("Could not update alias in DSDB")

        if self.config.infoblox_feature_enabled("update_alias"):
            try:
                ib_services = IBServices()
                if ib_services.assert_dns_environment(dbalias.fqdn.dns_environment.name) and \
                        (not old_target or ib_services.assert_dns_environment(old_target.dns_environment.name)) and \
                        ib_services.assert_dns_environment(dbalias.target.dns_environment.name):
                    ib_services.update_dns_alias(str(dbalias.fqdn), str(dbalias.target), ttl)
            except (ArgumentError, RequestException) as e:
                logger.warning("Error calling Infoblox update_dns_alias: {0}".format(str(e)))
                if dsdb_runner:
                    logger.warning("Rolling back DSDB transaction ...")
                    dsdb_runner.rollback()
                raise e
        return
