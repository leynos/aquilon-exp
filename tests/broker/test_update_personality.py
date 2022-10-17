#!/usr/bin/env python
# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2009-2017,2021  Contributor
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
"""Module for testing the update personality command."""

import unittest

if __name__ == "__main__":
    from broker import utils
    utils.import_depends()

from broker.brokertest import TestBrokerCommand
from broker.grntest import VerifyGrnsMixin
from broker.personalitytest import PersonalityTestMixin
from broker.utils import MockHub


class TestUpdatePersonality(VerifyGrnsMixin, PersonalityTestMixin,
                            TestBrokerCommand):
    def test_100_update_capacity(self):
        command = ["update_personality", "--personality", "vulcan-10g-server-prod",
                   "--archetype", "esx_cluster",
                   "--vmhost_capacity_function", "{'memory': (memory - 1500) * 0.94}"] + self.valid_just_tcm
        self.noouttest(command)

    def test_115_verify_update_capacity(self):
        command = ["show_personality", "--personality", "vulcan-10g-server-prod",
                   "--archetype", "esx_cluster"]
        out = self.commandtest(command)
        self.matchoutput(out,
                         "VM host capacity function: {'memory': (memory - 1500) * 0.94}",
                         command)

    def test_120_update_basic_attributes(self):
        command = ["promote", "--personality", "utunused/dev",
                   "--archetype=aquilon"]
        self.successtest(command)

        command = ["update_personality", "--personality", "utunused/dev",
                   "--archetype=aquilon",
                   "--cluster_required",
                   "--noconfig_override",
                   "--unstaged",
                   "--comments", "New personality comments"]
        self.successtest(command)

    def test_121_verify_updates(self):
        command = ["show_personality", "--personality=utunused/dev",
                   "--archetype=aquilon"]
        out = self.commandtest(command)

        self.matchoutput(out, "Personality: utunused/dev Archetype: aquilon",
                         command)
        self.matchoutput(out, "Comments: New personality comments", command)
        self.matchoutput(out, "Requires clustered hosts", command)
        self.matchclean(out, "override", command)

        self.verifycatpersonality("aquilon", "utunused/dev")

    def test_125_restore_utunused_dev(self):
        # Well, except the comments, which are removed
        command = ["update_personality", "--personality", "utunused/dev",
                   "--archetype=aquilon",
                   "--nocluster_required",
                   "--config_override",
                   "--comments", ""]
        self.successtest(command)

    def test_126_verify_utunused_dev(self):
        command = ["show_personality", "--personality=utunused/dev",
                   "--archetype=aquilon"]
        out = self.commandtest(command)
        self.matchclean(out, "Comments", command)
        self.matchclean(out, "Requires clustered hosts", command)
        self.matchoutput(out, "Config override: enabled", command)

        self.verifycatpersonality("aquilon", "utunused/dev",
                                  config_override=True)

    def test_135_setup_hosts(self):
        hosts = ['unittest20.aqd-unittest.ms.com',
                 'server1.aqd-unittest.ms.com']
        for host in hosts:
            command = ["reconfigure", "--hostname", host,
                       "--archetype", "aquilon",
                       "--personality", "unixeng-test"]
            self.successtest(command)

    def test_140_update_owner_grn(self):
        command = ["update_personality", "--personality", "compileserver",
                   "--archetype", "aquilon", "--grn", "grn:/ms/ei/aquilon/ut2"]
        # Some hosts may emit warnings if 'aq make' was not run on them
        self.successtest(command)

    def test_141_verify_show_personality(self):
        command = ["show_personality", "--personality", "compileserver"]
        out = self.commandtest(command)
        self.matchoutput(out, "Owned by GRN: grn:/ms/ei/aquilon/ut2", command)

    def test_141_verify_show_unittest02(self):
        # Different owner, should not be updated
        command = ["show_host", "--hostname", "unittest02.one-nyp.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out, "Personality: compileserver", command)
        self.searchoutput(out, r"^  Owned by GRN: grn:/ms/ei/aquilon/aqd", command)

    def test_141_verify_show_unittest21(self):
        # Owner is the same as the personality - should be updated
        command = ["show_host", "--hostname", "unittest21.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out, "Personality: compileserver", command)
        self.searchoutput(out, r"^  Owned by GRN: grn:/ms/ei/aquilon/ut2", command)

    def test_141_verify_cat_personality(self):
        command = ["cat", "--personality", "compileserver"]
        out = self.commandtest(command)
        self.searchoutput(out, r'"/system/personality/owner_eon_id" = %d;' %
                          self.grns["grn:/ms/ei/aquilon/ut2"], command)

    def test_141_verify_cat_unittest02(self):
        # Different owner, should not be updated
        command = ["cat", "--hostname", "unittest02.one-nyp.ms.com", "--data"]
        out = self.commandtest(command)
        self.searchoutput(out, r'"system/owner_eon_id" = %d;' %
                          self.grns["grn:/ms/ei/aquilon/aqd"], command)

    def test_141_verify_cat_unittest22(self):
        # Inherited - should be updated
        command = ["cat", "--hostname", "unittest22.aqd-unittest.ms.com",
                   "--data"]
        out = self.commandtest(command)
        self.searchoutput(out, r'"system/owner_eon_id" = %d;' %
                          self.grns["grn:/ms/ei/aquilon/ut2"], command)

    def test_141_verify_cat_unittest21(self):
        # Owner is the same as the personality - should be updated
        command = ["cat", "--hostname", "unittest21.aqd-unittest.ms.com", "--data"]
        out = self.commandtest(command)
        self.searchoutput(out, r'"system/owner_eon_id" = %d;' %
                          self.grns["grn:/ms/ei/aquilon/ut2"], command)

    def test_142_update_owner_grn_nohosts(self):
        command = ["update_personality", "--personality", "compileserver",
                   "--archetype", "aquilon", "--grn", "grn:/ms/ei/aquilon/unittest",
                   "--leave_existing"]
        self.statustest(command)

    def test_143_verify_show_personality(self):
        command = ["show_personality", "--personality", "compileserver"]
        out = self.commandtest(command)
        self.matchoutput(out, "Owned by GRN: grn:/ms/ei/aquilon/unittest", command)

    def test_143_verify_show_unittest02(self):
        command = ["show_host", "--hostname", "unittest02.one-nyp.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out, "Personality: compileserver", command)
        self.searchoutput(out, r"^  Owned by GRN: grn:/ms/ei/aquilon/aqd", command)

    def test_143_verify_show_unittest21(self):
        command = ["show_host", "--hostname", "unittest21.aqd-unittest.ms.com"]
        out = self.commandtest(command)
        self.matchoutput(out, "Personality: compileserver", command)
        self.searchoutput(out, r"^  Owned by GRN: grn:/ms/ei/aquilon/ut2", command)

    def test_144_verify_cat_personality(self):
        command = ["cat", "--personality", "compileserver"]
        out = self.commandtest(command)
        self.searchoutput(out, r'"/system/personality/owner_eon_id" = %d;' %
                          self.grns["grn:/ms/ei/aquilon/unittest"], command)

    def test_144_verify_cat_unittest02(self):
        # Different owner, should not be updated
        command = ["cat", "--hostname", "unittest02.one-nyp.ms.com", "--data"]
        out = self.commandtest(command)
        self.searchoutput(out, r'"system/owner_eon_id" = %d;' %
                          self.grns["grn:/ms/ei/aquilon/aqd"], command)

    def test_144_verify_cat_unittest20(self):
        # Inherited, should be updated
        command = ["cat", "--hostname", "unittest20.aqd-unittest.ms.com", "--data"]
        out = self.commandtest(command)
        self.searchoutput(out, r'"system/owner_eon_id" = %d;' %
                          self.grns["grn:/ms/ei/aquilon/unittest"], command)

    def test_144_verify_cat_unittest21(self):
        # Should not be updated due to --leave_existing
        command = ["cat", "--hostname", "unittest21.aqd-unittest.ms.com", "--data"]
        out = self.commandtest(command)
        self.searchoutput(out, r'"system/owner_eon_id" = %d;' %
                          self.grns["grn:/ms/ei/aquilon/ut2"], command)

    def test_170_make_staged(self):
        self.check_plenary_gone("aquilon", "personality",
                                "compileserver+next", "config")
        self.noouttest(["update_personality", "--personality", "compileserver",
                        "--archetype", "aquilon", "--staged",
                        "--vmhost_capacity_function",
                        "{'memory': (memory - 1500) * 0.94}"])
        self.check_plenary_exists("aquilon", "personality",
                                  "compileserver+next", "config")

    def test_171_show_current(self):
        command = ["show_personality", "--personality", "compileserver",
                   "--archetype", "aquilon"]
        out = self.commandtest(command)
        self.matchoutput(out, "Stage: current", command)

    def test_171_cat_current(self):
        self.verifycatpersonality("aquilon", "compileserver", stage="current")

    def test_172_show_next(self):
        command = ["show_personality", "--personality", "compileserver",
                   "--archetype", "aquilon", "--personality_stage", "next"]
        out = self.commandtest(command)
        self.matchoutput(out, "Stage: next", command)

    def test_172_cat_next(self):
        self.verifycatpersonality("aquilon", "compileserver", stage="next")

    def test_174_delete_next(self):
        self.noouttest(["del_personality", "--personality", "compileserver",
                        "--archetype", "aquilon", "--personality_stage", "next"])

    def test_175_verify_next_gone(self):
        command = ["show_personality", "--personality", "compileserver",
                   "--archetype", "aquilon", "--personality_stage", "next"]
        out = self.notfoundtest(command)
        self.matchoutput(out, "Personality aquilon/compileserver does not have "
                         "stage next.", command)
        self.check_plenary_gone("aquilon", "personality",
                                "compileserver+next", "config")

    def test_176_create_next_again(self):
        self.noouttest(["update_personality", "--personality", "compileserver",
                        "--vmhost_capacity_function",
                        "{'memory': (memory - 1500) * 0.94}",
                        "--archetype", "aquilon"] + self.valid_just_tcm)

    def test_178_make_unstaged(self):
        self.check_plenary_exists("aquilon", "personality",
                                  "compileserver+next", "config")
        self.noouttest(["update_personality", "--personality", "compileserver",
                        "--archetype", "aquilon", "--unstaged"])
        self.check_plenary_gone("aquilon", "personality",
                                "compileserver+next", "config")

    def test_179_verify_unstaged(self):
        command = ["show_personality", "--personality", "compileserver",
                   "--archetype", "aquilon"]
        out = self.commandtest(command)
        self.matchclean(out, "Stage:", command)

    def test_179_cat_unstaged(self):
        self.verifycatpersonality("aquilon", "compileserver")

    def test_200_invalid_function(self):
        """ Verify that the list of built-in functions is restricted """
        command = ["update_personality", "--personality", "vulcan-10g-server-prod",
                   "--archetype", "esx_cluster",
                   "--vmhost_capacity_function", "locals()"] + self.valid_just_tcm
        out = self.badrequesttest(command)
        self.matchoutput(out, "name 'locals' is not defined", command)

    def test_200_invalid_type(self):
        command = ["update_personality", "--personality", "vulcan-10g-server-prod",
                   "--archetype", "esx_cluster",
                   "--vmhost_capacity_function", "memory - 100"] + self.valid_just_tcm
        out = self.badrequesttest(command)
        self.matchoutput(out, "The function should return a dictonary.", command)

    def test_200_invalid_dict(self):
        command = ["update_personality", "--personality", "vulcan-10g-server-prod",
                   "--archetype", "esx_cluster",
                   "--vmhost_capacity_function", "{'memory': 'bar'}"] + self.valid_just_tcm
        out = self.badrequesttest(command)
        self.matchoutput(out,
                         "The function should return a dictionary with all "
                         "keys being strings, and all values being numbers.",
                         command)

    def test_200_missing_memory(self):
        command = ["update_personality", "--personality", "vulcan-10g-server-prod",
                   "--archetype", "esx_cluster",
                   "--vmhost_capacity_function", "{'foo': 5}"] + self.valid_just_tcm
        out = self.badrequesttest(command)
        self.matchoutput(out,
                         "The memory constraint is missing from the returned "
                         "dictionary.", command)

    def test_200_update_cluster_inuse(self):
        command = ["update_personality", "--personality=vulcan-10g-server-prod",
                   "--archetype=esx_cluster",
                   "--cluster"] + self.valid_just_tcm
        out = self.badrequesttest(command)
        self.matchoutput(out, "Personality esx_cluster/vulcan-10g-server-prod is in use", command)

    def test_200_missing_personality(self):
        command = ["update_personality", "--archetype", "aquilon",
                   "--personality", "personality-does-not-exist"]
        out = self.notfoundtest(command)
        self.matchoutput(out, "Personality personality-does-not-exist, "
                         "archetype aquilon not found.", command)

    def test_200_missing_personality_stage(self):
        command = ["update_personality", "--archetype", "aquilon",
                   "--personality", "nostage",
                   "--personality_stage", "previous"]
        out = self.notfoundtest(command)
        self.matchoutput(out,
                         "Personality aquilon/nostage does not have stage "
                         "previous.",
                         command)

    def test_200_change_environment(self):
        command = ["update_personality", "--personality=utunused/dev",
                   "--archetype=aquilon", "--host_environment=infra"]
        out = self.badrequesttest(command)
        self.matchoutput(out,
                         "Personality aquilon/utunused/dev already has "
                         "its environment set to dev, and cannot be updated.",
                         command)

    # Test that update personality does not unecessarly create a next stage
    def test_300_update_personality_without_stage(self):
        mh = MockHub(engine=self)
        command = ['update_personality',
                   '--personality', mh.default_personality,
                   '--archetype', mh.default_archetype]
        self.noouttest(command)
        command = ['search_personality',
                   '--personality', mh.default_personality,
                   '--personality_stage', 'next']
        self.noouttest(command)
        mh.delete()

    # Test that update personality creates a next stage when necessary
    def test_300_update_personality_with_stage(self):
        mh = MockHub(engine=self)
        command = ['update_personality',
                   '--personality', mh.default_personality,
                   '--archetype', mh.default_archetype,
                   '--vmhost_capacity_function',
                   "{'memory': (memory - 1500) * 0.94}"]
        self.noouttest(command)
        command = ['search_personality',
                   '--personality', mh.default_personality,
                   '--personality_stage', 'next']
        out = self.commandtest(command)
        self.matchoutput(
                out,
                mh.default_archetype + '/' + mh.default_personality + '@next',
                command)
        mh.delete()

    def test_400_update_personality(self):
        mh = MockHub(engine=self, default_archetype='cannot_change_grn')
        mh.add_personality(mh.default_personality,
                           mh.default_grn_change_unrestricted_archetype)

        test_cases = {
            'changegrn': {
                'expected_failures': [
                    mh.default_archetype + '__ready__None__dl360g9'
                ]
            }
        }

        for archetype in [mh.default_grn_change_unrestricted_archetype,
                          mh.default_archetype]:
            for build_status in ['build', 'ready']:
                # status 'build' is configured to allow grn changes
                # status 'ready' is configured to restrict grn changes

                for original_grn in [
                  None,
                  'grn:/ms/ei/aquilon/unittest',
                  'grn:/ms/ei/aquilon/unittest_can_change_grn',
                  'grn:/ms/ei/aquilon/ut2'
                ]:
                    for vendor_model in ['hs21', 'dl360g9']:
                        # model hs21 has vendor 'ibm' to which
                        # grn change restrictions do not apply
                        # model dl360g9 has vendor 'hp' to which
                        # grn change restrictions do apply

                        test_key = archetype + '__' + build_status + '__' + \
                                str(original_grn) + '__' + vendor_model

                        for test_case in test_cases.keys():

                            command = [
                                'update_personality',
                                '--personality', mh.default_personality,
                                '--archetype', archetype,
                                '--grn', 'grn:/ms/ei/aquilon/ut2']

                            mh.delete_hosts()
                            mh.add_host(
                                archetype=archetype,
                                grn=original_grn,
                                personality=mh.default_personality,
                                build_status=build_status,
                                model=vendor_model
                            )

                        if test_key in \
                           test_cases[test_case]['expected_failures']:
                            (out, err) = self.failuretest(command, 4)
                            self.matchoutput(err,
                                             'Changing grn of Personality',
                                             command)
                        else:
                            (out, err) = self.successtest(command)
                            self.assertEmptyOut(out, command)
        mh.delete()

    # Test that grn change restrictions do not prevent update_personality from
    # updating the grn of hosts that have the same grn as their personality
    def test_410_update_personality(self):
        mh = MockHub(engine=self, default_archetype='cannot_change_grn')
        personality = mh.add_personality('test_410_update_personality',
                                         mh.default_archetype,
                                         grn='grn:/ms/ei/aquilon/ut2')

        hostname = mh.add_host(
            personality=personality[0],
            archetype=personality[1],
            grn='grn:/ms/ei/aquilon/ut2',
            build_status='ready'
        )

        command = [
            'update_personality',
            '--personality', personality[0],
            '--archetype', personality[1],
            '--grn', 'grn:/ms/ei/aquilon/aqd']

        self.noouttest(command)

        (out, err) = self.failuretest(['reconfigure',
                                       '--hostname', hostname,
                                       '--cleargrn'], 4)
        self.matchoutput(err, 'because it would change the host effective grn',
                         command)

        mh.delete()

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUpdatePersonality)
    unittest.TextTestRunner(verbosity=2).run(suite)
