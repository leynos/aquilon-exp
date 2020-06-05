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

    @classmethod
    def setUpClass(cls):
        super(TestAddIssue, cls).setUpClass()

        cls.proto = cls.protocols['aqdsystems_pb2']
        desc = cls.proto.Issue.DESCRIPTOR
        cls.state_type = desc.fields_by_name["state"].enum_type

    # --------------------------------------------------------------------------------
    # add
    def test_100_add_issue(self):
        self.noouttest(["add_issue", "--tracker", "unixops-000",
                        "--category", "ctos",
                        "--description", "Some issue description"])

    def test_101_add_issue_duplicate_fail(self):
        # Test fail to use --ipfromtype for hosts not in bunker
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

    # --------------------------------------------------------------------------------
    # show
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

    # --------------------------------------------------------------------------------
    # update
    def test_110_update_issue(self):
        command = ["update", "issue", "--tracker", "unixops-000",
                   "--new_description", "New description"]
        self.noouttest(command)

    def test_115_verify_update(self):
        command = "show issue --tracker unixops-000"
        out = self.commandtest(command.split(" "))
        self.matchoutput(out, "unixops-000", command)
        self.matchoutput(out, "Category: ctos", command)
        self.matchoutput(out, "State: open", command)
        self.matchoutput(out, "Description: new description", command)

    def test_116_update_fail(self):
        command = ["update", "issue", "--tracker", "unixops-999",
                   "--new_description", "New description"]
        out = self.notfoundtest(command)
        self.matchoutput(out, "Not Found: "
                              "Issue tracker unixops-999 not found.",
                         command)

    # --------------------------------------------------------------------------------
    # close
    def test_120_close_issue(self):
        command = ["close", "issue", "--tracker", "unixops-000"]
        self.noouttest(command)

    def test_125_verify_close(self):
        command = "show issue --tracker unixops-000"
        out = self.commandtest(command.split(" "))
        self.matchoutput(out, "unixops-000", command)
        self.matchoutput(out, "Category: ctos", command)
        self.matchoutput(out, "State: closed", command)
        self.matchoutput(out, "Description: new description", command)

    def test_126_close_fail(self):
        command = ["close", "issue", "--tracker", "unixops-999"]
        out = self.notfoundtest(command)
        self.matchoutput(out, "Not Found: "
                              "Issue tracker unixops-999 not found.",
                         command)

    # --------------------------------------------------------------------------------
    # discard
    def test_130_discard_issue(self):
        command = ["discard", "issue", "--tracker", "unixops-000"]
        self.noouttest(command)

    def test_135_verify_discard(self):
        command = "show issue --tracker unixops-000"
        out = self.commandtest(command.split(" "))
        self.matchoutput(out, "unixops-000", command)
        self.matchoutput(out, "Category: ctos", command)
        self.matchoutput(out, "State: disc", command)
        self.matchoutput(out, "Description: new description", command)

    def test_136_discard_fail(self):
        command = ["discard", "issue", "--tracker", "unixops-999"]
        out = self.notfoundtest(command)
        self.matchoutput(out, "Not Found: "
                              "Issue tracker unixops-999 not found.",
                         command)

    # --------------------------------------------------------------------------------
    # link model for host unittest02.one-nyp.ms.com
    def test_140_link_issue_model(self):
        command = ["link_issue_model", "--tracker", "unixops-000",
                   "--model", "hs21-8853", "--vendor", "ibm"]
        self.noouttest(command)

    def test_150_link_model_fail_tracker_not_found(self):
        command = ["link_issue_model", "--tracker", "unixops-999",
                   "--model", "hs21-8853", "--vendor", "ibm"]
        out = self.notfoundtest(command)
        self.matchoutput(out, "Not Found: "
                              "Issue tracker unixops-999 not found.",
                         command)

    def test_150_link_model_fail_model_not_found(self):
        command = ["link_issue_model", "--tracker", "unixops-000",
                   "--model", "test", "--vendor", "ibm"]
        out = self.notfoundtest(command)
        self.matchoutput(out, "Not Found: "
                              "Model test, vendor ibm not found.",
                         command)

    def test_150_link_model_fail_vendor_not_found(self):
        command = ["link_issue_model", "--tracker", "unixops-000",
                   "--model", "hs21-8853", "--vendor", "test"]
        out = self.notfoundtest(command)
        self.matchoutput(out, "Not Found: "
                              "Vendor test not found.",
                         command)

    def test_151_link_model_fail_duplicate(self):
        command = ["link_issue_model", "--tracker", "unixops-000",
                   "--model", "hs21-8853", "--vendor", "ibm"]
        err = self.internalerrortest(command)
        self.matchoutput(err, "Internal Server Error: "
                              "Issue with same tracker and model "
                              "already in database", command)

    def test_160_search_issue_model(self):
        command = ["search", "issue", "--hostname",
                   "unittest02.one-nyp.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out, "unixops-000", command)

    # --------------------------------------------------------------------------------
    # link os for host unittest02.one-nyp.ms.com
    def test_170_link_issue_os(self):
        self.noouttest(["add_issue", "--tracker", "unixops-001",
                        "--category", "hw",
                        "--description", "Some issue description"])
        osver = self.config.get("unittest", "linux_version_prev")
        command = ["link_issue_os", "--tracker", "unixops-001", "--osname",
                   "linux", "--archetype", "aquilon", "--osversion", osver]
        self.noouttest(command)

    def test_171_search_issue_model_os(self):
        command = ["search", "issue",
                   "--hostname", "unittest02.one-nyp.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out, "unixops-000", command)
        self.matchoutput(out, "unixops-001", command)

    # --------------------------------------------------------------------------------
    # link os and/or model for unittest15.aqd-unittest.ms.com
    def test_180_link_issues(self):
        # unixops-100: model
        self.noouttest(["add_issue", "--tracker", "unixops-100",
                        "--category", "ctos",
                        "--description", "Some issue description"])
        command = ["link_issue_model", "--tracker", "unixops-100",
                   "--model", "dl360g9", "--vendor", "hp"]
        self.noouttest(command)

        # unixops-101: os
        self.noouttest(["add_issue", "--tracker", "unixops-101",
                        "--category", "hw",
                        "--description", "Some issue description"])

        osver = self.config.get("unittest", "linux_version_curr")
        command = ["link_issue_os", "--tracker", "unixops-101", "--osname",
                   "linux", "--archetype", "aquilon", "--osversion", osver]
        self.noouttest(command)

        # unixops-102: model&os
        self.noouttest(["add_issue", "--tracker", "unixops-102",
                        "--category", "hw",
                        "--description", "Some issue description"])
        command = ["link_issue_model", "--tracker", "unixops-102",
                   "--model", "dl360g9", "--vendor", "hp"]
        self.noouttest(command)
        command = ["link_issue_os", "--tracker", "unixops-102",
                   "--osname", "linux", "--archetype", "aquilon",
                   "--osversion", osver]
        self.noouttest(command)

    # search for previously linked issues
    def test_190_search_issues(self):
        command = ["search", "issue", "--hostname",
                   "unittest15.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out, "unixops-100", command)
        self.matchoutput(out, "unixops-101", command)
        self.matchoutput(out, "unixops-102", command)

    def test_200_show_issue_all(self):
        command = "show issue --all"
        out = self.commandtest(command.split(" "))
        self.matchoutput(out, "unixops-000", command)
        self.matchoutput(out, "unixops-001", command)
        self.matchoutput(out, "unixops-100", command)
        self.matchoutput(out, "unixops-101", command)
        self.matchoutput(out, "unixops-102", command)

    # --------------------------------------------------------------------------------
    # search --list
    def test_300_host_list_filter_model(self):
        hosts = ["unittest15.aqd-unittest.ms.com", "unittest02.one-nyp.ms.com"]
        scratchfile = self.writescratch("search_issue_list", "\n".join(hosts))
        command = ["search_issue", "--list", scratchfile]
        out = self.commandtest(command)

        self.matchoutput(out, "unixops-000", command)
        self.matchoutput(out, "unixops-001", command)
        self.matchoutput(out, "unixops-100", command)
        self.matchoutput(out, "unixops-101", command)
        self.matchoutput(out, "unixops-102", command)

    # filter model
    def test_400_host_list_filter_model(self):
        hosts = ["unittest15.aqd-unittest.ms.com", "unittest02.one-nyp.ms.com"]
        scratchfile = self.writescratch("search_issue_list", "\n".join(hosts))
        command = ["search_issue", "--list", scratchfile, "--model", "dl360g9"]
        out = self.commandtest(command)

        self.matchoutput(out, "unixops-100", command)
        self.matchoutput(out, "unixops-102", command)

    # filter os
    def test_450_host_list_filter_os(self):
        hosts = ["unittest15.aqd-unittest.ms.com", "unittest02.one-nyp.ms.com"]
        scratchfile = self.writescratch("search_issue_list", "\n".join(hosts))
        osver = self.config.get("unittest", "linux_version_curr")
        command = ["search_issue", "--list", scratchfile, "--osversion", osver]
        out = self.commandtest(command)

        self.matchoutput(out, "unixops-101", command)
        self.matchoutput(out, "unixops-102", command)

    # various filters
    def test_460_host_list_filter_model_os(self):
        hosts = ["unittest15.aqd-unittest.ms.com", "unittest02.one-nyp.ms.com"]
        scratchfile = self.writescratch("search_issue_list", "\n".join(hosts))
        osver = self.config.get("unittest", "linux_version_curr")
        command = ["search_issue", "--list", scratchfile, "--osversion",
                   osver, "--model", "dl360g9"]
        out = self.commandtest(command)

        self.matchoutput(out, "unixops-102", command)

    def test_470_host_list_filter_category(self):
        hosts = ["unittest15.aqd-unittest.ms.com", "unittest02.one-nyp.ms.com"]
        scratchfile = self.writescratch("search_issue_list", "\n".join(hosts))
        command = ["search_issue", "--list", scratchfile, "--category", "ctos"]
        out = self.commandtest(command)

        self.matchoutput(out, "unixops-000", command)
        self.matchoutput(out, "unixops-100", command)

    def test_480_host_list_filter_state(self):
        hosts = ["unittest15.aqd-unittest.ms.com", "unittest02.one-nyp.ms.com"]
        scratchfile = self.writescratch("search_issue_list", "\n".join(hosts))
        command = ["search_issue", "--list", scratchfile,
                   "--state", "discarded"]
        out = self.commandtest(command)

        self.matchoutput(out, "unixops-000", command)

    def test_500_host_list_filter_all(self):
        hosts = ["unittest15.aqd-unittest.ms.com", "unittest02.one-nyp.ms.com"]
        scratchfile = self.writescratch("search_issue_list", "\n".join(hosts))
        osver = self.config.get("unittest", "linux_version_curr")
        command = ["search_issue", "--list", scratchfile, "--osversion", osver,
                   "--model", "dl360g9", "--category", "hw", "--state", "open"]
        out = self.commandtest(command)

        self.matchoutput(out, "unixops-102", command)

    def test_500_verify_fullinfo(self):
        hosts = ["unittest15.aqd-unittest.ms.com", "unittest02.one-nyp.ms.com"]
        scratchfile = self.writescratch("search_issue_list", "\n".join(hosts))

        command = ["link_issue_model", "--tracker", "unixops-102",
                   "--model", "hs21-8853", "--vendor", "ibm"]
        self.noouttest(command)

        osver_prev = self.config.get("unittest", "linux_version_prev")
        command = ["link_issue_os", "--tracker", "unixops-102",
                   "--osname", "linux",
                   "--archetype", "aquilon", "--osversion", osver_prev]
        self.noouttest(command)

        osver_curr = self.config.get("unittest", "linux_version_curr")
        command = ["search_issue", "--list", scratchfile,
                   "--osversion", osver_curr, "--model", "dl360g9",
                   "--category", "hw", "--state", "open", "--fullinfo"]
        out = self.commandtest(command)

        self.matchoutput(out, "unixops-102", command)
        self.matchoutput(out, "Category: hw", command)
        self.matchoutput(out, "State: open", command)
        self.matchoutput(out, "Description: some issue description", command)
        self.matchoutput(out, "Model: dl360g9", command)
        self.matchoutput(out, "Vendor: hp", command)
        self.matchoutput(out, "Model: hs21-8853", command)
        self.matchoutput(out, "Vendor: ibm", command)
        self.matchoutput(out, "Version: 6.1-x86_64", command)
        self.matchoutput(out, "Lifecycle: early_prod", command)
        self.matchoutput(out, "Version: 5.1-x86_64", command)

    def test_500_verify_proto(self):
        hosts = ["unittest15.aqd-unittest.ms.com", "unittest02.one-nyp.ms.com"]
        scratchfile = self.writescratch("search_issue_list", "\n".join(hosts))
        osver_prev = self.config.get("unittest", "linux_version_prev")
        osver_curr = self.config.get("unittest", "linux_version_curr")

        command = ["search_issue", "--format", "proto", "--list", scratchfile,
                   "--osversion", osver_curr, "--model", "dl360g9",
                   "--category", "hw", "--state", "open"]
        issue = self.protobuftest(command, expect=1)[0]
        self.assertEqual(issue.tracker, "unixops-102")
        state = "open"
        val = self.state_type.values_by_name[state.upper()]
        self.assertEqual(issue.state, val.number)
        self.assertEqual(issue.category, "hw")
        self.assertEqual(issue.description, "some issue description")
        self.assertEqual(issue.models[1].name, "dl360g9")
        self.assertEqual(issue.models[1].vendor, "hp")
        self.assertEqual(issue.models[0].name, "hs21-8853")
        self.assertEqual(issue.models[0].vendor, "ibm")
        self.assertEqual(issue.os[0].version, osver_curr)
        self.assertEqual(issue.os[1].version, osver_prev)

    def test_500_host_list_filter_all_fail(self):
        # no issue correspond to filter --> no output
        hosts = ["unittest15.aqd-unittest.ms.com", "unittest02.one-nyp.ms.com"]
        scratchfile = self.writescratch("search_issue_list", "\n".join(hosts))
        osver = self.config.get("unittest", "linux_version_curr")
        command = ["search_issue", "--list", scratchfile, "--osversion", osver,
                   "--model", "dl360g9", "--category", "hw",
                   "--state", "discarded"]
        self.noouttest(command)

    def test_501_host_list_filter_os_fail(self):
        hosts = ["unittest15.aqd-unittest.ms.com", "unittest02.one-nyp.ms.com"]
        scratchfile = self.writescratch("search_issue_list", "\n".join(hosts))
        command = ["search_issue", "--list", scratchfile, "--osname", "linux",
                   "--model", "dl360g9", "--category", "hw",
                   "--state", "discarded"]
        err = self.badrequesttest(command)
        self.matchoutput(err, "Bad Request: "
                              "Operating System linux is not unique.",
                         command)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAddIssue)
    unittest.TextTestRunner(verbosity=2).run(suite)
