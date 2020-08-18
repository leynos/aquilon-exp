#!/usr/bin/env python
# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2020  Contributor
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
"""Module for testing the show issue command."""

import unittest

if __name__ == "__main__":
    import utils
    utils.import_depends()

from brokertest import TestBrokerCommand


class TestShowIssue(TestBrokerCommand):

    def test_105_show_issue(self):
        command = "show issue --tracker unixops-000"
        out = self.commandtest(command.split(" "))
        self.matchoutput(out, "unixops-000", command)
        self.matchoutput(out, "Category: ctos", command)
        self.matchoutput(out, "State: open", command)
        self.matchoutput(out, "Description: some issue description", command)

    def test_106_show_issue_fail_tracker(self):
        command = "show issue --tracker unixops-999"
        out = self.notfoundtest(command.split(" "))
        self.matchoutput(out, "Not Found: "
                              "Issue tracker unixops-999 not found.",
                         command)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestShowIssue)
    unittest.TextTestRunner(verbosity=2).run(suite)
