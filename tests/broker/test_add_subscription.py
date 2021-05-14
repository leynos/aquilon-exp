#!/usr/bin/env python
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
"""Module for testing the add subscription command."""

import getpass
import unittest

if __name__ == "__main__":
    import utils
    utils.import_depends()

from brokertest import TestBrokerCommand


class TestAddSubscription(TestBrokerCommand):

    def test_100_add_subscription(self):
        user_name = getpass.getuser()
        command = ["add_subscription",
                   "--hostname=server1.aqd-unittest.ms.com",
                   "--username={}".format(user_name),
                   "--mode=test",
                   "--environment=uat",
                   "--subscription=/dev/app/localdisk/data/uat"]
        self.successtest(command)

    def test_110_show_subscription(self):
        user_name = getpass.getuser()
        command = ["show_subscription",
                   "--hostname=server1.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.output_equals(out, """
            Subscription
              Bound to: Host server1.aqd-unittest.ms.com
              Mode: test
              Environment: uat
              User: {}
              Subscription: /dev/app/localdisk/data/uat
            """.format(user_name), command)

    def test_110_badhostname(self):
        user_name = getpass.getuser()
        command = ["add_subscription",
                   "--hostname=host.ms.com",
                   "--username={}".format(user_name),
                   "--mode=test",
                   "--environment=uat",
                   "--subscription=/dev/app/localdisk/data/uat"]
        out = self.notfoundtest(command)
        self.matchoutput(out, "Not Found: Host host.ms.com not found.",
                         command)

    def test_120_show_all(self):
        command = ["show_subscription", "--all"]
        out = self.commandtest(command)
        self.searchoutput(out, "Subscription$", command)

    def test_120_show_host(self):
        command = ["show_host", "--hostname=server1.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out, "Subscription: /dev/app/localdisk/data/uat",
                         command)

    def test_200_add_existing(self):
        user_name = getpass.getuser()
        command = ["add_subscription",
                   "--hostname=server1.aqd-unittest.ms.com",
                   "--username={}".format(user_name),
                   "--mode=test",
                   "--environment=uat",
                   "--subscription=/dev/app/localdisk/data/uat"]
        out = self.badrequesttest(command)
        self.matchoutput(out, "already exists", command)

    def test_200_notfound(self):
        command = ["show_subscription", "--hostname", "invalidhost.ms.com"]
        self.notfoundtest(command)

    def test_200_search_subscription(self):
        command = ["search_subscription",
                   "--hostname=server1.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out, "Subscription: /dev/app/localdisk/data/uat",
                         command)

    def test_200_search_subscription_user(self):
        user_name = getpass.getuser()
        command = ["search_subscription",
                   "--username={}".format(user_name)]
        out = self.commandtest(command)
        self.matchoutput(out, "Subscription: /dev/app/localdisk/data/uat",
                         command)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAddSubscription)
    unittest.TextTestRunner(verbosity=2).run(suite)
