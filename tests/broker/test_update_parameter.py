#!/usr/bin/env python
# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2016  Contributor
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
"""Module for testing the update parameter command."""

import unittest

if __name__ == "__main__":
    from broker import utils
    utils.import_depends()

from broker.brokertest import TestBrokerCommand


class TestUpdateParameter(TestBrokerCommand):

    def check_match(self, out, expected, command):
        out = ' '.join(out.split())
        self.matchoutput(out, expected, command)

    def test_100_update_existing_leaf_path(self):
        self.noouttest(["update_parameter", "--personality", "utpers-dev",
                        "--archetype", "aquilon",
                        "--path", "actions/testaction/user",
                        "--value", "user2"])

        command = ["show_parameter", "--personality", "utpers-dev",
                   "--archetype", "aquilon", "--personality_stage", "next"]
        out = self.commandtest(command)
        expected = 'testaction: { "command": "/bin/testaction", "user": "user2" }'
        self.check_match(out, expected, command)

    def test_109_upd_existing_path_fail(self):
        command = ["update_parameter", "--personality", "utpers-dev",
                   "--archetype", "aquilon",
                   "--path", "espinfo/function", "--value",
                   [[{"frequency":"0 0 * * * *","user":"itsdoop",
                      "name":"itsdoop_ticket_refresh",
                      "command":"source /etc/systemvars.ksh && "
                                "/ms/dist/aurora/bin/krun -id itsdoop -- "
                                "/usr/bin/maprlogin kerberos -duration 1800000"},
                     {"frequency":"1 0 * * * *","user":"itsacvut",
                      "name":"itsacvut_ticket_refresh",
                      "command":"source /etc/systemvars.ksh && /ms/dist/aurora/bin/krun "
                                "-id itsacvut -- /usr/bin/maprlogin kerberos -duration 1800000"},
                     {"frequency":"6 0 * * * *","user":"itsskyhd","name":"itsskyhd_ticket_refresh",
                      "command":"source /etc/systemvars.ksh && /ms/dist/aurora/bin/krun -id "
                                "itsskyhd -- /usr/bin/maprlogin kerberos -duration 1800000"},
                     {"frequency":"7 0 * * * *","user":"itsskyhp","name":"itsskyhp_ticket_refresh",
                      "command":"source /etc/systemvars.ksh && /ms/dist/aurora/bin/krun -id "
                                "itsskyhp -- /usr/bin/maprlogin kerberos -duration 1800000"},
                     {"frequency":"9 0 * * * *","user":"itsterm","name":"itsterm_ticket_refresh",
                      "command":"source /etc/systemvars.ksh && /ms/dist/aurora/bin/krun -id "
                                "itsterm -- /usr/bin/maprlogin kerberos -duration 1800000"},
                     {"frequency":"8 0 * * * *","user":"itspal","name":"itspal_ticket_refresh",
                      "command":"source /etc/systemvars.ksh && /ms/dist/aurora/bin/krun -id "
                                "itspal -- /usr/bin/maprlogin kerberos -duration 1800000"},
                     {"frequency":"10 0 * * * *","user":"itsvpsec","name":"itsvpsec_ticket_refresh",
                      "command":"source /etc/systemvars.ksh && /ms/dist/aurora/bin/krun -id "
                                "itsvpsec -- /usr/bin/maprlogin kerberos -duration 1800000"},
                     {"frequency":"12 0 * * * *","user":"vaultui","name":"vaultui_ticket_refresh",
                      "command":"source /etc/systemvars.ksh && /ms/dist/aurora/bin/krun -id "
                                "vaultui -- /usr/bin/maprlogin kerberos -duration 1800000"},
                     {"frequency":"13 0 * * * *","user":"root","name":"root_ticket_refresh",
                      "command":"cp /opt/mapr/conf/mapruserticket /tmp/maprticket_0"},
                     {"frequency":"18 0 * * * *","user":"itsdlpp","name":"itsdlpp_ticket_refresh",
                      "command":"source /etc/systemvars.ksh && /ms/dist/aurora/bin/krun -id "
                                "itsdlpp -- /usr/bin/maprlogin kerberos -duration 1800000"},
                     {"frequency":"19 0 * * * *","user":"itsmalintel","name":"itsmalintel_ticket_refresh",
                      "command":"source /etc/systemvars.ksh && /ms/dist/aurora/bin/krun -id "
                                "itsmalintel -- /usr/bin/maprlogin kerberos -duration 1800000"},
                     {"frequency":"21 0 * * * *","user":"fwlss","name":"fwlss_ticket_refresh",
                      "command":"source /etc/systemvars.ksh && /ms/dist/aurora/bin/krun -id "
                                "fwlss -- /usr/bin/maprlogin kerberos -duration 1800000"},
                     {"frequency":"22 0 * * * *","user":"casprkp","name":"casprkp_ticket_refresh",
                      "command":"source /etc/systemvars.ksh && /ms/dist/aurora/bin/krun -id "
                                "casprkp -- /usr/bin/maprlogin kerberos -duration 1800000"},
                     {"frequency":"22 0 * * * *","user":"itsqdoop","name":"itsqdoop_ticket_refresh",
                      "command":"source /etc/systemvars.ksh && /ms/dist/aurora/bin/krun -id "
                                "itsqdoop -- /usr/bin/maprlogin kerberos -duration 1800000"}]]]
        out = self.commandtest(command)
        self.matchoutput(out, "The character count in value is beyond the permitted "
                              "value. Please specify argument value less than 2600",
                         command)

    def test_110_upd_existing_path(self):
        self.noouttest(["update_parameter", "--personality", "utpers-dev",
                        "--archetype", "aquilon",
                        "--path", "espinfo/function", "--value", "production"])

    def test_200_upd_nonexisting_leaf_path(self):
        command = ["update_parameter", "--personality", "utpers-dev",
                   "--archetype", "aquilon",
                   "--path", "actions/testaction/badpath", "--value", "badvalue"]
        err = self.notfoundtest(command)
        self.matchoutput(err,
                         "No parameter of path=testaction/badpath defined.",
                         command)

    def test_200_upd_nonexisting_path(self):
        command = ["update_parameter", "--personality", "utpers-dev",
                   "--archetype", "aquilon",
                   "--path", "espinfo/badpath", "--value", "badvalue"]
        err = self.notfoundtest(command)
        self.matchoutput(err,
                         "Path espinfo/badpath does not match any parameter "
                         "definitions of archetype aquilon.",
                         command)

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUpdateParameter)
    unittest.TextTestRunner(verbosity=2).run(suite)
