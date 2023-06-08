# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018  Contributor
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
"""Contains the logic for `aq add address`."""

from aquilon.aqdb.model.network_environment import get_net_dns_env
from aquilon.exceptions_ import ArgumentError, ProcessException
from aquilon.worker.broker import BrokerCommand
from aquilon.worker.dbwrappers.dns import (grab_address,
                                           set_reverse_ptr)
from aquilon.worker.dbwrappers.grn import lookup_grn
from aquilon.worker.dbwrappers.interface import generate_ip
from aquilon.worker.dbwrappers.change_management import ChangeManagement
from aquilon.worker.ib_services import IBServices
from aquilon.worker.processes import DSDBRunner
from requests import RequestException


class CommandAddAddress(BrokerCommand):

    required_parameters = ["fqdn"]

    def render(self, session, logger, fqdn, dns_environment, grn, eon_id,
               network_environment, reverse_ptr, ttl, comments, exporter, user,
               justification, reason, **arguments):
        dbnet_env, dbdns_env = get_net_dns_env(session, network_environment,
                                               dns_environment)
        audit_results = []
        ip = generate_ip(session, logger, compel=True, dbinterface=None,
                         network_environment=dbnet_env,
                         audit_results=audit_results, **arguments)

        dbgrn = None
        if grn or eon_id:
            dbgrn = lookup_grn(session, grn, eon_id, logger=logger,
                               config=self.config)
        # TODO: add allow_multi=True
        dbdns_rec, _ = grab_address(session, fqdn, ip, dbnet_env, dbdns_env,
                                    comments=comments, preclude=True,
                                    exporter=exporter, grn=dbgrn)

        # Validate ChangeManagement
        cm = ChangeManagement(session, user, justification, reason, logger, self.command, **arguments)
        cm.consider(dbdns_rec.fqdn)
        cm.validate()

        if reverse_ptr:
            set_reverse_ptr(session, logger, dbdns_rec, reverse_ptr)

        if ttl is not None:
            dbdns_rec.ttl = ttl

        session.flush()

        dsdb_runner = None
        if dbdns_rec.fqdn.dns_environment.is_default:
            dsdb_runner = DSDBRunner(logger=logger)
            dsdb_runner.add_host_details(dbdns_rec.fqdn, ip, comments=comments)
            dsdb_runner.commit_or_rollback("Could not add address to DSDB")

        for name, value in audit_results:
            self.audit_result(session, name, value, **arguments)

        if self.config.infoblox_feature_enabled("add_address"):
            try:
                IBServices().add_a_ptr(str(dbdns_rec.fqdn), ip, reverse_ptr, ttl)
            except (ArgumentError,RequestException) as e:
                logger.warning("Error calling Infoblox add_a_ptr: {0}".format(str(e)))
                if dsdb_runner:
                    logger.warning("Rolling back DSDB transaction ...")
                    dsdb_runner.rollback()
                raise e
