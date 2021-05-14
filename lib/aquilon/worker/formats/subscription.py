# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2021  Contributor
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
"""Subscription Resource formatter."""

from aquilon.aqdb.model import Subscription
from aquilon.worker.formats.formatters import ObjectFormatter
from aquilon.worker.formats.resource import ResourceFormatter


class SubscriptionFormatter(ResourceFormatter):

    suppress_name = True

    def extra_details(self, subs, indent=""):
        details = []
        details.append(indent + "  Mode: %s" % subs.configmode)
        details.append(indent + "  Environment: %s" % subs.environment)
        details.append(indent + "  User: %s" % subs.username)
        details.append(indent + "  Subscription: %s" % subs.subscription)
        return details

    def csv_fields(self, subs):
        hostname = "{0}".format(subs.holder)
        yield (hostname, subs.configmode, subs.environment,
               subs.username, subs.subscription)


ObjectFormatter.handlers[Subscription] = SubscriptionFormatter()
