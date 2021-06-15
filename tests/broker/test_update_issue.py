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
"""Module for testing the update issue command."""

import unittest

if __name__ == "__main__":
    import utils
    utils.import_depends()

from brokertest import TestBrokerCommand


class TestUpdateIssue(TestBrokerCommand):

    # update description
    def test_110_update_issue_description(self):
        command = ["update", "issue", "--tracker", "unixops-000",
                   "--description", "New description"]
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
                   "--description", "New description"]
        out = self.notfoundtest(command)
        self.matchoutput(out, "Not Found: "
                              "Issue tracker unixops-999 not found.",
                         command)

    # update state: close
    def test_120_update_close(self):
        command = ["update", "issue", "--tracker", "unixops-000",
                   "--state", "closed"]
        self.noouttest(command)

    def test_121_verify_close(self):
        command = "show issue --tracker unixops-000"
        out = self.commandtest(command.split(" "))
        self.matchoutput(out, "unixops-000", command)
        self.matchoutput(out, "Category: ctos", command)
        self.matchoutput(out, "State: closed", command)
        self.matchoutput(out, "Description: new description", command)

    def test_122_close_fail(self):
        command = ["update", "issue", "--tracker", "unixops-000",
                   "--state", "random_string"]
        out = self.badrequesttest(command)
        self.matchoutput(out, "Bad Request: "
                              '"random_string" not a valid value. Valid values'
                              " are: ('open', 'closed', 'discarded')",
                         command)

    # update state: open
    def test_125_update_open(self):
        command = ["update", "issue", "--tracker", "unixops-000",
                   "--state", "open"]
        self.noouttest(command)

    def test_126_verify_open(self):
        command = "show issue --tracker unixops-000"
        out = self.commandtest(command.split(" "))
        self.matchoutput(out, "unixops-000", command)
        self.matchoutput(out, "Category: ctos", command)
        self.matchoutput(out, "State: open", command)
        self.matchoutput(out, "Description: new description", command)

    def test_127_open_fail(self):
        command = ["update", "issue", "--tracker", "unixops-000",
                   "--state", "random_string"]
        out = self.badrequesttest(command)
        self.matchoutput(out, "Bad Request: "
                              '"random_string" not a valid value. Valid values'
                              " are: ('open', 'closed', 'discarded')",
                         command)

    # update state: discarded
    def test_130_update_discarded(self):
        command = ["update", "issue", "--tracker", "unixops-000",
                   "--state", "discarded"]
        self.noouttest(command)

    def test_131_verify_discarded(self):
        command = "show issue --tracker unixops-000"
        out = self.commandtest(command.split(" "))
        self.matchoutput(out, "unixops-000", command)
        self.matchoutput(out, "Category: ctos", command)
        self.matchoutput(out, "State: discarded", command)
        self.matchoutput(out, "Description: new description", command)

    def test_132_discarded_fail(self):
        command = ["update", "issue", "--tracker", "unixops-000",
                   "--state", "random_string"]
        out = self.badrequesttest(command)
        self.matchoutput(out, "Bad Request: "
                              '"random_string" not a valid value. Valid values'
                              " are: ('open', 'closed', 'discarded')",
                         command)

    # update model: link model for host unittest02.one-nyp.ms.com
    def test_140_update_issue_model(self):
        command = ["update_issue", "--tracker", "unixops-000",
                   "--model", "hs21-8853", "--vendor", "ibm"]
        self.noouttest(command)

    def test_150_link_model_fail_tracker_not_found(self):
        command = ["update_issue", "--tracker", "unixops-999",
                   "--model", "hs21-8853", "--vendor", "ibm"]
        out = self.notfoundtest(command)
        self.matchoutput(out, "Not Found: "
                              "Issue tracker unixops-999 not found.",
                         command)

    def test_150_link_model_fail_model_not_found(self):
        command = ["update_issue", "--tracker", "unixops-000",
                   "--model", "test", "--vendor", "ibm"]
        out = self.notfoundtest(command)
        self.matchoutput(out, "Not Found: "
                              "Model test, vendor ibm not found.",
                         command)

    def test_150_link_model_fail_vendor_not_unique(self):
        command = ["update_issue", "--tracker", "unixops-000",
                   "--vendor", "aurora_vendor"]
        err = self.badrequesttest(command)
        self.matchoutput(err, "Bad Request: "
                              "Model vendor aurora_vendor is not unique.",
                         command)

    def test_150_link_model_fail_vendor_not_found(self):
        command = ["update_issue", "--tracker", "unixops-000",
                   "--model", "hs21-8853", "--vendor", "test"]
        out = self.notfoundtest(command)
        self.matchoutput(out, "Not Found: "
                              "Vendor test not found.",
                         command)

    def test_160_search_issue_model(self):
        command = ["search", "issue", "--hostname",
                   "unittest02.one-nyp.ms.com", "--state_all"]
        out = self.commandtest(command)
        self.matchoutput(out, "unixops-000", command)

    # update os: link os for host unittest02.one-nyp.ms.com
    def test_167_update_issue_os(self):
        self.noouttest(["add_issue", "--tracker", "unixops-001",
                        "--category", "hw",
                        "--description", "Some issue description"])
        osver = self.config.get("unittest", "linux_version_prev")
        command = ["update_issue", "--tracker", "unixops-001", "--osname",
                   "linux", "--archetype", "aquilon", "--osversion", osver]
        self.noouttest(command)

    def test_168_search_issue_model_os(self):
        command = ["search", "issue",
                   "--hostname", "unittest02.one-nyp.ms.com", "--state_all"]
        out = self.commandtest(command)
        self.matchoutput(out, "unixops-000", command)
        self.matchoutput(out, "unixops-001", command)

    def test_169_update_issue_os_not_unique(self):
        command = ["update_issue", "--tracker", "unixops-001", "--osname",
                   "linux"]
        err = self.badrequesttest(command)
        self.matchoutput(err, "Bad Request: "
                              "Operating System linux is not unique.",
                         command)

    # update tracker
    def test_172_update_issue_description(self):
        command = ["update", "issue", "--tracker", "unixops-000",
                   "--new_tracker", "unixops-222"]
        self.noouttest(command)

    def test_173_verify_update(self):
        command = "show issue --tracker unixops-222"
        out = self.commandtest(command.split(" "))
        self.matchoutput(out, "unixops-222", command)
        self.matchoutput(out, "Category: ctos", command)
        self.matchoutput(out, "State: discarded", command)
        self.matchoutput(out, "Description: new description", command)

    def test_174_update_tracker_fail(self):
        command = ["update", "issue", "--tracker", "unixops-222",
                   "--new_tracker", "unixops-001"]
        err = self.badrequesttest(command)
        self.matchoutput(err, "Bad Request: "
                              "Issue tracker unixops-001 already exists.",
                         command)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUpdateIssue)
    unittest.TextTestRunner(verbosity=2).run(suite)
