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
"""Contains the logic for `aq search subscription`."""

from aquilon.aqdb.model import Subscription
from aquilon.worker.broker import BrokerCommand  # noqa
from aquilon.worker.commands.search_resource import CommandSearchResource


class CommandSearchSubscription(CommandSearchResource):

    resource_class = Subscription

    def filter_by(self, q, mode=None, environment=None, username=None,
                  subscription=None, **kwargs):
        if mode:
            q = q.filter_by(configmode=mode)
        if environment:
            q = q.filter_by(environment=environment)
        if username:
            q = q.filter_by(username=username)
        if subscription:
            q = q.filter_by(subscription=subscription)

        return q
