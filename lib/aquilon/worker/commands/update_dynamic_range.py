# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2009,2010,2011,2012,2013,2014,2015,2016,2017,2023  Contributor
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

from ipaddress import ip_address, IPv4Network
from sqlalchemy.orm import joinedload

from aquilon.exceptions_ import ArgumentError, NotFoundException, ProcessException, UnimplementedError
from aquilon.aqdb.model import DynamicStub, DnsEnvironment
from aquilon.aqdb.model.network_environment import get_net_dns_env
from aquilon.aqdb.model.network import get_net_id_from_ip
from aquilon.worker.broker import BrokerCommand
from aquilon.worker.ib_services import IBServices
from aquilon.worker.dbwrappers.change_management import ChangeManagement


class CommandUpdateDynamicRange(BrokerCommand):
    required_parameters = ["ip", "range_class"]

    def render(self, session, logger, ip,
               range_class, exporter, user, justification,
               reason, **arguments):

        dbnetwork, dbstubs, startip, endip, old_range_class = self.fetch_range_details(session, ip)

        if old_range_class == range_class:
            raise ArgumentError("The range class of this range is already {}".format(range_class))

        ib_services = IBServices(logger, justification=justification, **arguments)
        if ib_services.feature_enabled("dynamic_range") and old_range_class == "infoblox_managed":
            self._check_range_is_in_ib(ib_services, dbstubs, startip, endip)

        cm = ChangeManagement(session, user, justification, reason, logger, self.command, **arguments)
        cm.consider(dbnetwork)
        cm.validate()

        self._update_dynamic_range(logger, session, ib_services, dbstubs, old_range_class, range_class)

    def fetch_range_details(self, session, ip):
        dbdns_env = DnsEnvironment.get_unique_or_default(session, None)

        dbnetwork = get_net_id_from_ip(session, ip)
        dbdns_rec = session.query(DynamicStub).filter_by(ip=ip, network=dbnetwork).first()

        start = int(ip)
        end = int(ip)

        if not dbdns_rec:
            raise NotFoundException("{} is not part of a dynamic range".format(ip))

        range_class = dbdns_rec.range_class

        q = session.query(DynamicStub)
        q = q.filter_by(network=dbnetwork, range_class=range_class)
        dbstubs = list(q)
        ips = [int(stub.ip) for stub in dbstubs]

        while start > int(dbnetwork.network_address) and start - 1 in ips:
            start = start - 1

        while end < int(dbnetwork.broadcast_address) and end + 1 in ips:
            end = end + 1

        return dbnetwork, dbstubs, ip_address(start), ip_address(end), range_class

    def _check_range_is_in_ib(self, ib_services, dbstubs, startip, endip):
        startip = str(startip)
        endip = str(endip)

        response = None
        try:
            response = ib_services.show_dynamic_range(startip, endip)
        except ProcessException as e:
            if response and response.status_code == 404:
                raise ArgumentException("Dynamic range {} to {} was not found in Infoblox, cannot update"
                                        .format(startip, endip))
            else:
                raise e

    def _update_dynamic_range(self, logger, session, ib_services, dbstubs, old_range_class, range_class):
        prefix = str(dbstubs[0]).split("-", 1)[0]
        startip = str(dbstubs[0].ip)
        endip = str(dbstubs[-1].ip)

        with session.no_autoflush:
            for stub in dbstubs:
                stub.range_class = range_class

        session.flush()

        if ib_services.feature_enabled("dynamic_range"):
            # Delete the range in IB as it's no longer needed there
            if old_range_class == "infoblox_managed":
                ib_services.delete_dynamic_range(startip, endip),

            # Add the range to IB as we now want it to be managed there
            elif range_class == "infoblox_managed":
                ib_services.add_dynamic_range("{}-{}-{}".format(prefix, startip, endip), startip, endip)
