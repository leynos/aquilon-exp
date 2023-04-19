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
"""Contains the logic for `aq del address alias`."""

from aquilon.exceptions_ import NotFoundException, ArgumentError
from aquilon.aqdb.model import Fqdn, AddressAlias
from aquilon.worker.broker import BrokerCommand
from aquilon.worker.dbwrappers.dns import delete_dns_record
from aquilon.worker.dbwrappers.change_management import ChangeManagement
from aquilon.worker.processes import IBServices

from requests import RequestException

class CommandDelAddressAlias(BrokerCommand):

    required_parameters = ["fqdn"]

    def render(self, session, fqdn, target, dns_environment, target_environment,
               exporter, user, justification, reason, logger, **arguments):

        if not target_environment:
            target_environment = dns_environment

        dbfqdn = Fqdn.get_unique(session, fqdn=fqdn,
                                 dns_environment=dns_environment)

        if target:
            dbtarget = Fqdn.get_unique(session, fqdn=target,
                                       dns_environment=target_environment,
                                       compel=True)
        else:
            dbtarget = None

        rrs = []
        if dbfqdn:
            for rr in dbfqdn.dns_records:
                if not isinstance(rr, AddressAlias):
                    continue
                if dbtarget and rr.target != dbtarget:
                    continue
                rrs.append(rr)

        if not rrs:
            if dbtarget:
                msg = ", with target %s" % dbtarget.fqdn
            else:
                msg = ""
            raise NotFoundException("%s %s%s not found." %
                                    (AddressAlias._get_class_label(), fqdn,
                                     msg))

        # Validate ChangeManagement
        cm = ChangeManagement(session, user, justification, reason, logger, self.command, **arguments)
        for dns_rec in rrs:
            delete_dns_record(dns_rec, exporter=exporter)
            cm.consider(dns_rec.target)

        cm.validate()

        if self.config.infoblox_feature_enabled('del_address_alias'):
            try:
                ib_services = IBServices()
                for dns_rec in rrs:
                    if ib_services.assert_dns_environment(dns_rec.fqdn.dns_environment.name) and \
                            ib_services.assert_dns_environment(dns_rec.target.dns_environment.name):
                        ib_services.delete_a_ptr(str(dns_rec), dns_rec.target_ip, delete_ptr=False)
            except (ArgumentError, RequestException) as e:
                logger.warning("Error calling Infoblox delete_a_ptr: {0}".format(str(e)))
                raise e

        session.flush()

        return
