# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2015,2018  Contributor
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
"""Contains the logic for `aq update interface` for simple devices."""

from aquilon.exceptions_ import ArgumentError, ProcessException, UnimplementedError
from aquilon.aqdb.types import NicType
from aquilon.aqdb.model import Interface, Model
from aquilon.worker.broker import BrokerCommand
from aquilon.worker.dbwrappers.hardware_entity import get_hardware
from aquilon.worker.dbwrappers.interface import (rename_interface,
                                                update_netdev_iftype)
from aquilon.worker.ib_services import IBServices
from aquilon.worker.processes import DSDBRunner
from aquilon.worker.dbwrappers.change_management import ChangeManagement


class CommandUpdateInterface(BrokerCommand):

    requires_plenaries = True
    required_parameters = ["interface"]
    invalid_parameters = ['autopg', 'pg', 'boot']

    def get_plenaries(self, dbhw_ent, plenaries):
        pass

    def render(self, session, logger, plenaries, interface, mac, model, vendor,
               comments, rename_to, iftype, user, justification, reason, **arguments):
        dbhw_ent = get_hardware(session, **arguments)
        dbinterface = Interface.get_unique(session, hardware_entity=dbhw_ent,
                                           name=interface, compel=True)


        # Validate ChangeManagement
        cm = ChangeManagement(session, user, justification, reason, logger, self.command, **arguments)
        cm.consider(dbhw_ent)
        cm.validate()

        for arg in self.invalid_parameters:
            if arguments.get(arg) is not None:
                raise UnimplementedError("Argument --%s is not allowed for %s." %
                                         (arg, dbhw_ent._get_class_label(True)))

        oldinfo = DSDBRunner.snapshot_hw(dbhw_ent)
        ib_services = IBServices(logger)
        ib_old_snapshot = ib_services.snapshot_hw_a_records(dbhw_ent)

        if iftype:
            dbinterface = update_netdev_iftype(session, dbinterface, iftype)
            dbhw_ent = dbinterface.hardware_entity
        if comments is not None:
            dbinterface.comments = comments
        if mac is not None:
            q = session.query(Interface).filter_by(mac=mac)
            other = q.first()
            if other and other != dbinterface:
                raise ArgumentError("MAC address {0} is already in use by "
                                    "{1:l}.".format(mac, other))
            dbinterface.mac = mac
        if model:
            if not dbinterface.model_allowed:
                raise ArgumentError("Model/vendor can not be set for a {0:lc}."
                                    .format(dbinterface))

            dbmodel = Model.get_unique(session, name=model, vendor=vendor,
                                       model_type=NicType.Nic, compel=True)
            dbinterface.model = dbmodel
        if rename_to:
            rename_interface(session, dbinterface, rename_to)

        session.flush()

        self.get_plenaries(dbhw_ent, plenaries)

        with plenaries.transaction():
            dsdb_runner = DSDBRunner(logger=logger)
            dsdb_runner.update_host(dbhw_ent, oldinfo)
            dsdb_runner.commit_or_rollback("Could not update entry in DSDB")

            if ib_old_snapshot is not None and ib_services.feature_enabled("interface"):
                    ib_services.bulk_change_a_ptr(ib_old_snapshot, ib_services.snapshot_hw_a_records(dbhw_ent))

                    try:
                        ib_services.group.commit_or_rollback()
                    except ProcessException as e:
                        if dsdb_runner:
                            dsdb_runner.rollback()
                        raise e

        return
