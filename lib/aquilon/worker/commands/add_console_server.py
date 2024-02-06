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
"""Contains the logic for `aq add console server`."""

from aquilon.exceptions_ import ArgumentError, ProcessException
from aquilon.aqdb.types import ConsoleServerType
from aquilon.aqdb.model import ConsoleServer, Model
from aquilon.aqdb.model.network import get_net_id_from_ip
from aquilon.worker.broker import BrokerCommand
from aquilon.worker.dbwrappers.dns import grab_address
from aquilon.worker.dbwrappers.interface import (get_or_create_interface,
                                                 check_ip_restrictions,
                                                 assign_address)
from aquilon.worker.dbwrappers.location import get_location
from aquilon.worker.ib_services import IBServices
from aquilon.worker.processes import DSDBRunner


class CommandAddConsoleServer(BrokerCommand):

    required_parameters = ["console_server", "model", "ip"]

    def render(self, session, logger, console_server, label, model, ip,
               interface, user, justification, reason, mac, vendor, serial,
               comments, **arguments):
        dbmodel = Model.get_unique(session, name=model, vendor=vendor,
                                   model_type=ConsoleServerType.ConsoleServer,
                                   compel=True)

        dblocation = get_location(session, compel=True, **arguments)

        dbdns_rec, _ = grab_address(session, console_server, ip,
                                    allow_restricted_domain=True,
                                    allow_reserved=True, preclude=True,
                                    require_grn=False)
        if not label:
            label = dbdns_rec.fqdn.name
            try:
                ConsoleServer.check_label(label)
            except ArgumentError:
                raise ArgumentError("Could not deduce a valid hardware label "
                                    "from the console server name.  Please specify "
                                    "--label.")

        dbcons = ConsoleServer(label=label, location=dblocation, model=dbmodel,
                               serial_no=serial, comments=comments)
        session.add(dbcons)
        dbcons.primary_name = dbdns_rec

        # FIXME: get default name from the model
        if not interface:
            interface = "mgmt"
        dbinterface = get_or_create_interface(session, dbcons,
                                              name=interface, mac=mac,
                                              interface_type="oa")
        if ip:
            dbnetwork = get_net_id_from_ip(session, ip)
            check_ip_restrictions(dbnetwork, ip)
            assign_address(dbinterface, ip, dbnetwork)

        session.flush()

        if ip:
            dsdb_runner = DSDBRunner(logger=logger)
            dsdb_runner.update_host(dbcons, None)
            dsdb_runner.commit_or_rollback("Could not add console server to DSDB")

            # Oddly the code above assumes ip is optional but it's a required field.
            ib_services = IBServices(logger, justification=justification, **arguments)
            if ib_services.feature_enabled("console_server"):
                try:
                    ib_services.group.add_action(
                        lambda name=str(dbcons.primary_name.fqdn), ip=ip: ib_services.add_a(name=name, ip=ip),
                        lambda name=str(dbcons.primary_name.fqdn), ip=ip: ib_services.delete_a(name=name, ip=ip)
                    )
                    ib_services.group.add_action(
                        lambda name=str(dbcons.primary_name.fqdn), ip=ip: ib_services.add_ptr(name=name, ip=ip),
                        lambda ip=ip: ib_services.delete_ptr(ip=ip)
                    )
                    ib_services.group.commit_or_rollback()
                except ProcessException as e:
                    dsdb_runner.rollback()
                    raise e
