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
"""Module for testing the add issue command."""

import unittest

if __name__ == "__main__":
    import utils
    utils.import_depends()

from brokertest import TestBrokerCommand


class TestAddIssue(TestBrokerCommand):

    def test_100_add_issue(self):
        self.noouttest(["add_issue", "--tracker", "unixops-000",
                        "--category", "ctos",
                        "--description", "Some issue description"])

    def test_101_add_issue_duplicate_fail(self):
        command = ["add_issue", "--tracker", "unixops-000", "--category", "hw",
                   "--description", "Some issue description 2"]
        err = self.badrequesttest(command)
        self.matchoutput(err, "Bad Request: "
                              "Issue tracker unixops-000 already exists.",
                         command)

    def test_102_add_too_long_tracker(self):
        cmd = ['add_issue', '--tracker',
               #         1         2         3
               's23456789012345678901234567890123456',
               "--category", "hw", "--description", "Some issue description 2"]
        out = self.badrequesttest(cmd)
        self.matchoutput(out, "is more than the maximum 32 allowed.", cmd)

    def test_102_add_too_long_category(self):
        cmd = ['add_issue', '--category',
               #         1         2         3
               's23456789012345678901234567890123456',
               "--tracker", "hw", "--description", "Some issue description 2"]
        out = self.badrequesttest(cmd)
        self.matchoutput(out, "is more than the maximum 32 allowed.", cmd)

    def test_103_add_too_long_description(self):
        cmd = ['add_issue', '--description',
               #         1         2         3         4         5         6
               's2345678901234567890123456789012345678901234567890123456789' +
               's2345678901234567890123456789012345678901234567890123456789' +
               's2345678901234567890123456789012345678901234567890123456789' +
               's2345678901234567890123456789012345678901234567890123456789' +
               's2345678901234567890123456789012345678901234567890123456789',
               "--category", "hw", "--tracker", "Some issue description 2"]
        out = self.badrequesttest(cmd)
        self.matchoutput(out, "is more than the maximum 255 allowed.", cmd)

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAddIssue)
    unittest.TextTestRunner(verbosity=2).run(suite)
