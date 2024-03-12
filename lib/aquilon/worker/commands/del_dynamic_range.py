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

from sqlalchemy.orm import joinedload

from aquilon.worker.broker import BrokerCommand
from aquilon.aqdb.model import DnsDomain, Fqdn, ARecord, NetworkEnvironment
from aquilon.aqdb.model.network import get_net_id_from_ip
from aquilon.exceptions_ import ArgumentError
from aquilon.worker.ib_services import IBServices
from aquilon.worker.processes import DSDBRunner
from aquilon.worker.dbwrappers.dns import delete_dns_record
from aquilon.worker.dbwrappers.change_management import ChangeManagement


class CommandDelDynamicRange(BrokerCommand):

    required_parameters = ["startip", "endip"]

    def render(self, session, logger, startip, endip, exporter, user,
               justification, reason, **arguments):
        dbnet_env = NetworkEnvironment.get_unique_or_default(session)
        startnet = get_net_id_from_ip(session, startip, dbnet_env)
        endnet = get_net_id_from_ip(session, endip, dbnet_env)
        if startnet != endnet:
            raise ArgumentError("IP addresses %s (%s) and %s (%s) must be "
                                "on the same subnet." %
                                (startip, startnet.network_address,
                                 endip, endnet.network_address))

        # Validate ChangeManagement
        cm = ChangeManagement(session, user, justification, reason, logger, self.command, **arguments)
        cm.consider(startnet)
        cm.validate()

        # Lock order: DNS domain(s), network
        q = session.query(DnsDomain.id)
        q = q.join(Fqdn, (ARecord, ARecord.fqdn_id == Fqdn.id))
        q = q.filter_by(network=startnet)
        q = q.order_by(DnsDomain.id)
        q = q.with_for_update()
        session.execute(q)
        startnet.lock_row()

        q = session.query(ARecord)
        q = q.filter_by(network=startnet)
        q = q.filter(ARecord.ip >= startip)
        q = q.filter(ARecord.ip <= endip)
        q = q.order_by(ARecord.ip)
        q = q.options(joinedload('fqdn'),
                      joinedload('fqdn.aliases'),
                      joinedload('fqdn.srv_records'),
                      joinedload('reverse_ptr'))
        dbstubs = q.all()
        if not dbstubs:
            raise ArgumentError("Nothing found in range.")
        if dbstubs[0].ip != startip:
            raise ArgumentError("No system found with IP address %s." % startip)
        if dbstubs[-1].ip != endip:
            raise ArgumentError("No system found with IP address %s." % endip)
        invalid = [s for s in dbstubs if s.dns_record_type != 'dynamic_stub']
        if invalid:
            raise ArgumentError("The range contains non-dynamic systems:\n" +
                                "\n".join(format(i, "a") for i in invalid))

        self.del_dynamic_stubs(session, logger, dbstubs, exporter, justification, **arguments)

    def del_dynamic_stubs(self, session, logger, dbstubs, exporter, justification, **arguments):
        range_class = dbstubs[0].range_class

        for stub in dbstubs:
            delete_dns_record(stub, locked=True, exporter=exporter)

        session.flush()

        # A second loop, so we only send data to other systems once the AQ change is
        # confirmed to be successful.
        dsdb_runner = DSDBRunner(logger=logger)
        ib_services = IBServices(logger, justification=justification, **arguments)
        for stub in dbstubs:
            fqdn = str(stub.fqdn)
            dsdb_runner.delete_host_details(fqdn, stub.ip)

            # We do this in all cases, whatever the range_class value.
            ib_services.del_a_ptr(stub)

        prefix = str(dbstubs[0]).split("-", 1)
        startip = str(dbstubs[0].ip)
        endip = str(dbstubs[-1].ip)

        if range_class == "infoblox_managed":
            ib_services.group.add_action(
                lambda startip=startip, endip=endip:
                    ib_services.delete_dynamic_range(startip, endip),
                lambda prefix=prefix, startip=startip, endip=endip:
                    ib_services.add_dynamic_range(
                        "{}-{}-{}".format(prefix, startip, endip), startip, endip
                    )
            )

        # This may take some time if the range is big, so be verbose
        dsdb_runner.commit_or_rollback(verbose=True)

        if ib_services.feature_enabled("dynamic_range"):
            try:
                ib_services.group.commit_or_rollback()
            except Exception as e:
                dsdb_runner.rollback()
                raise e
