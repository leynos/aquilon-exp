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
"""Contains the logic for `aq del chassis`."""

from aquilon.exceptions_ import ArgumentError, ProcessException
from aquilon.worker.broker import BrokerCommand
from aquilon.aqdb.model import Chassis, ARecord
from aquilon.worker.dbwrappers.dns import delete_dns_record
from aquilon.worker.dbwrappers.hardware_entity import check_only_primary_ip
from aquilon.worker.ib_services import IBServices
from aquilon.worker.processes import DSDBRunner


class CommandDelChassis(BrokerCommand):

    required_parameters = ["chassis"]

    def render(self, session, logger, chassis, clear_slots, exporter, **arguments):
        dbchassis = Chassis.get_unique(session, chassis, compel=True)

        check_only_primary_ip(dbchassis)

        dsdb_runner = DSDBRunner(logger=logger)
        oldinfo = DSDBRunner.snapshot_hw(dbchassis)
        dsdb_runner.update_host(None, oldinfo)
        dsdb_runner.delete_chassis(dbchassis)

        if dbchassis.not_empty_slots and not clear_slots:
            raise ArgumentError("{0} is still in use by {1} machines or network devices. Use "
                                "--clear_slots if you really want to delete "
                                "it.".format(dbchassis, len(dbchassis.not_empty_slots)))

        # Order matters here
        dbdns_rec = dbchassis.primary_name
        session.delete(dbchassis)
        if dbdns_rec:
            delete_dns_record(dbdns_rec, exporter=exporter)

        session.flush()

        dsdb_runner.commit_or_rollback("Could not remove chassis from DSDB")

        # chassis may not hve a primary interface assigned
        ip = dbchassis.primary_name.ip if type(dbchassis.primary_name) == ARecord else None
        ib_services = IBServices(logger, **arguments)
        if ib_services.feature_enabled("chassis") and ip:
            try:
                ib_services.group.add_action(
                    lambda name=str(dbchassis.primary_name.fqdn), ip=ip: ib_services.delete_a(name, ip=ip),
                    lambda name=str(dbchassis.primary_name.fqdn), ip=ip: ib_services.add_a(name, ip=ip)
                )
                ib_services.group.add_action(
                    lambda ip=ip: ib_services.delete_ptr(ip=ip),
                    lambda name=str(dbchassis.primary_name.fqdn), ip=ip: ib_services.add_ptr(name, ip=ip)
                )
                ib_services.group.commit_or_rollback()
            except ProcessException as e:
                dsdb_runner.rollback()
                raise e
