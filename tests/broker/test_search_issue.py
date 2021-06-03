# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2020-2021  Contributor
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
"""Module for testing the search issue command."""

import unittest

if __name__ == "__main__":
    import utils
    utils.import_depends()

from brokertest import TestBrokerCommand


class TestSearchIssue(TestBrokerCommand):

    @classmethod
    def setUpClass(cls):
        super(TestSearchIssue, cls).setUpClass()

        cls.proto = cls.protocols['aqdsystems_pb2']
        desc = cls.proto.Issue.DESCRIPTOR
        cls.state_type = desc.fields_by_name["state"].enum_type

    # link os and/or model for unittest15.aqd-unittest.ms.com
    def test_180_link_issues(self):
        # unixops-100: model
        self.noouttest(["add_issue", "--tracker", "unixops-100",
                        "--category", "ctos",
                        "--description", "Some issue description"])
        command = ["update_issue", "--tracker", "unixops-100",
                   "--model", "dl360g9", "--vendor", "hp"]
        self.noouttest(command)

        # unixops-101: os
        self.noouttest(["add_issue", "--tracker", "unixops-101",
                        "--category", "hw",
                        "--description", "Some issue description"])

        osver = self.config.get("unittest", "linux_version_curr")
        command = ["update_issue", "--tracker", "unixops-101", "--osname",
                   "linux", "--archetype", "aquilon", "--osversion", osver]
        self.noouttest(command)

        # unixops-102: model&os
        self.noouttest(["add_issue", "--tracker", "unixops-102",
                        "--category", "hw",
                        "--description", "Some issue description"])
        command = ["update_issue", "--tracker", "unixops-102",
                   "--model", "dl360g9", "--vendor", "hp"]
        self.noouttest(command)

        command = ["update_issue", "--tracker", "unixops-102",
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

    def test_190_search_osissues(self):
        osver = self.config.get("unittest", "linux_version_curr")
        command = ["search", "issue", "--osversion", osver]
        out = self.commandtest(command)
        self.matchoutput(out, "unixops-101", command)
        self.matchoutput(out, "unixops-102", command)

    def test_199_search_firmwareissues(self):
        command = ["search", "issue", "--model", "dl360g9",
                   "--vendor", "hp"]
        out = self.commandtest(command)
        self.matchoutput(out, "unixops-100", command)
        self.matchoutput(out, "unixops-102", command)

    def test_199_search_issues_os_category(self):
        command = ["search", "issue", "--hostname",
                   "unittest15.aqd-unittest.ms.com", "--category", "ctos",
                   "--state_all"]
        out = self.commandtest(command)
        self.matchoutput(out, "unixops-100", command)

    def test_199_search_issues_firmware_category(self):
        command = ["search", "issue", "--hostname",
                   "unittest15.aqd-unittest.ms.com", "--category", "hw"]
        out = self.commandtest(command)
        self.matchoutput(out, "unixops-101", command)
        self.matchoutput(out, "unixops-102", command)

    def test_199_search_issue_state(self):
        command = ["update_issue", "--tracker", "unixops-100",
                   "--state", "closed"]
        self.noouttest(command)
        command = ["search", "issue", "--hostname",
                   "unittest15.aqd-unittest.ms.com",
                   "--state", "closed", "--category", "ctos"]
        out = self.commandtest(command)
        self.matchoutput(out, "unixops-100", command)
        command = ["update_issue", "--tracker", "unixops-100",
                   "--state", "open"]
        self.noouttest(command)

    def test_199_search_issue_state_all(self):
        command = ["update_issue", "--tracker", "unixops-101",
                   "--state", "closed"]
        self.noouttest(command)
        command = ["search", "issue", "--hostname",
                   "unittest15.aqd-unittest.ms.com",
                   "--state_all", "--category", "hw"]
        out = self.commandtest(command)
        self.matchoutput(out, "unixops-101", command)
        self.matchoutput(out, "unixops-102", command)

        command = ["update_issue", "--tracker", "unixops-101",
                   "--state", "open"]
        self.noouttest(command)

    def test_199_search_issue_fullinfo(self):
        command = ["update_issue", "--tracker", "unixops-100",
                   "--state", "closed"]
        self.noouttest(command)

        command = ["search", "issue", "--hostname",
                   "unittest15.aqd-unittest.ms.com",
                   "--state", "closed", "--category", "ctos", "--fullinfo"]
        out = self.commandtest(command)
        self.matchoutput(out, "unixops-100", command)
        self.matchoutput(out, "Category: ctos", command)
        self.matchoutput(out, "State: closed", command)
        self.matchoutput(out, "Description: some issue description", command)
        self.matchoutput(out, "Model: dl360g9", command)
        self.matchoutput(out, "Vendor: hp", command)
        command = ["update_issue", "--tracker", "unixops-100",
                   "--state", "open"]
        self.noouttest(command)

    def test_199_search_issues_os(self):
        osver = self.config.get("unittest", "linux_version_curr")
        command = ["search", "issue", "--osversion", osver, "--state_all"]
        out = self.commandtest(command)
        self.matchoutput(out, "unixops-101", command)
        self.matchoutput(out, "unixops-102", command)

    def test_199_search_issues_os_state(self):
        osver = self.config.get("unittest", "linux_version_curr")
        command = ["search", "issue", "--osversion", osver,
                   "--state", "closed"]
        self.noouttest(command)

    def test_199_search_issues_os_state_fullinfo(self):
        osver = self.config.get("unittest", "linux_version_curr")
        command = ["search", "issue", "--osversion", osver,
                   "--state", "open", "--fullinfo"]
        out = self.commandtest(command)
        self.matchoutput(out, "unixops-101", command)
        self.matchoutput(out, "unixops-102", command)
        self.matchoutput(out, "Category: hw", command)
        self.matchoutput(out, "State: open", command)
        self.matchoutput(out, "Description: some issue description", command)
        self.matchoutput(out, "Operating System: linux", command)
        self.matchoutput(out, "Version: 6.1-x86_64", command)

    def test_199_search_issues_model(self):
        command = ["search", "issue", "--model", "dl360g9", "--state_all"]
        out = self.commandtest(command)
        self.matchoutput(out, "unixops-100", command)
        self.matchoutput(out, "unixops-102", command)

    def test_199_search_issues_model_state(self):
        command = ["update_issue", "--tracker", "unixops-100",
                   "--state", "closed"]
        self.noouttest(command)
        command = ["search", "issue", "--model", "dl360g9",
                   "--state", "closed"]
        out = self.commandtest(command)
        self.matchoutput(out, "unixops-100", command)

    def test_199_search_issues_model_state_fullinfo(self):
        command = ["search", "issue", "--model", "dl360g9", "--vendor", "hp",
                   "--state", "open", "--fullinfo"]
        out = self.commandtest(command)
        self.matchoutput(out, "unixops-102", command)
        self.matchoutput(out, "Category: hw", command)
        self.matchoutput(out, "State: open", command)
        self.matchoutput(out, "Description: some issue description", command)
        self.matchoutput(out, "Vendor: hp", command)
        self.matchoutput(out, "Model: dl360g9", command)
        self.matchoutput(out, "Model Type: rackmount", command)
        self.matchoutput(out, "Operating System: linux", command)
        self.matchoutput(out, "Version: 6.1-x86_64", command)
        self.matchoutput(out, "Lifecycle: early_prod", command)

    def test_200_show_issue_all(self):
        # revert previous tracker change
        command = ["update", "issue", "--tracker", "unixops-222",
                   "--new_tracker", "unixops-000"]
        self.noouttest(command)

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
        command = ["search_issue", "--list", scratchfile, "--fullinfo",
                   "--state_all"]
        out = self.commandtest(command)

        self.matchoutput(out, "unixops-000", command)
        self.matchoutput(out, "unixops-001", command)
        self.matchoutput(out, "unixops-100", command)
        self.matchoutput(out, "unixops-101", command)
        self.matchoutput(out, "unixops-102", command)

    # filter model
    def test_400_host_list_filter_vendor(self):
        hosts = ["unittest15.aqd-unittest.ms.com", "unittest02.one-nyp.ms.com"]
        scratchfile = self.writescratch("search_issue_list", "\n".join(hosts))
        command = ["search_issue", "--list", scratchfile, "--vendor", "hp"]
        out = self.commandtest(command)

        self.matchoutput(out, "unixops-102", command)

    def test_470_host_list_filter_category(self):
        hosts = ["unittest15.aqd-unittest.ms.com", "unittest02.one-nyp.ms.com"]
        scratchfile = self.writescratch("search_issue_list", "\n".join(hosts))
        command = ["search_issue", "--list", scratchfile, "--category", "ctos",
                   "--state_all"]
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
        # osver = self.config.get("unittest", "linux_version_curr")
        command = ["search_issue", "--list", scratchfile,
                   "--category", "hw", "--state", "open"]

        out = self.commandtest(command)
        self.matchoutput(out, "unixops-102", command)

    def test_500_verify_fullinfo(self):
        hosts = ["unittest15.aqd-unittest.ms.com", "unittest02.one-nyp.ms.com"]
        scratchfile = self.writescratch("search_issue_list", "\n".join(hosts))

        command = ["update_issue", "--tracker", "unixops-102",
                   "--model", "hs21-8853", "--vendor", "ibm"]
        self.noouttest(command)

        osver_prev = self.config.get("unittest", "linux_version_prev")
        command = ["update_issue", "--tracker", "unixops-102",
                   "--osname", "linux",
                   "--archetype", "aquilon", "--osversion", osver_prev]
        self.noouttest(command)

        osver_curr = self.config.get("unittest", "linux_version_curr")
        command = ["update_issue", "--tracker", "unixops-102",
                   "--osname", "linux",
                   "--archetype", "aquilon", "--osversion", osver_curr]
        self.noouttest(command)

        command = ["search_issue", "--list", scratchfile,
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

    def test_500_host_list_filter_all_test(self):
        hosts = ["unittest15.aqd-unittest.ms.com", "unittest02.one-nyp.ms.com"]
        scratchfile = self.writescratch("search_issue_list", "\n".join(hosts))
        # osver = self.config.get("unittest", "linux_version_curr")
        command = ["search_issue", "--list", scratchfile,
                   "--category", "hw", "--state", "open", "--fullinfo"]

        out = self.commandtest(command)
        self.matchoutput(out, "unixops-101", command)

    def test_500_verify_proto(self):
        command = ["update_issue", "--tracker", "unixops-001",
                   "--state", "closed"]
        self.noouttest(command)
        command = ["update_issue", "--tracker", "unixops-101",
                   "--state", "closed"]
        self.noouttest(command)
        hosts = ["unittest15.aqd-unittest.ms.com", "unittest02.one-nyp.ms.com"]
        scratchfile = self.writescratch("search_issue_list", "\n".join(hosts))
        osver_prev = self.config.get("unittest", "linux_version_prev")
        osver_curr = self.config.get("unittest", "linux_version_curr")

        command = ["search_issue", "--format", "proto", "--list", scratchfile,
                   "--category", "hw", "--state", "open"]
        issue = self.protobuftest(command, expect=1)[0]
        self.assertEqual(issue.tracker, "unixops-102")
        state = "open"
        val = self.state_type.values_by_name[state.upper()]
        self.assertEqual(issue.state, val.number)
        self.assertEqual(issue.category, "hw")
        self.assertEqual(issue.description, "some issue description")
        expected_models = set([("dl360g9", "hp"), ("hs21-8853", "ibm")])
        actual_models = set()
        self.assertEqual(len(issue.models), len(expected_models))
        for model in issue.models:
            actual_models.add((model.name, model.vendor))
        self.assertTrue(expected_models == actual_models)
        expected_osversions = set([osver_curr, osver_prev])
        actual_osversions = set()
        self.assertEqual(len(issue.os), len(expected_osversions))
        for osversion in issue.os:
            actual_osversions.add(osversion.version)
        self.assertTrue(expected_osversions == actual_osversions)

    def test_500_host_list_filter_all_fail(self):
        # no issue correspond to filter --> no output
        hosts = ["unittest15.aqd-unittest.ms.com", "unittest02.one-nyp.ms.com"]
        scratchfile = self.writescratch("search_issue_list", "\n".join(hosts))
        osver = self.config.get("unittest", "linux_version_curr")
        command = ["search_issue", "--list", scratchfile,
                   "--category", "hw", "--state", "discarded"]
        self.noouttest(command)

    def test_501_host_list_filter_os_fail(self):
        hosts = ["unittest15.aqd-unittest.ms.com", "unittest02.one-nyp.ms.com"]
        scratchfile = self.writescratch("search_issue_list", "\n".join(hosts))
        command = ["search_issue", "--list", scratchfile,
                   "--category", "hw", "--state", "discarded"]
        self.noouttest(command)

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSearchIssue)
    unittest.TextTestRunner(verbosity=2).run(suite)
