# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2019  Contributor
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
import json
import unittest
import os

try:
    from unittest import mock
except ImportError:
    # noinspection PyUnresolvedReferences
    import mock

from aq import *


class TestAQClient(unittest.TestCase):
    def test_100_get_default_opts_config_file(self):
        auth_option = True
        conf_file = os.path.join(os.getcwd(), "tests/unit/bin/data/unittest-aq.conf")
        readonly = False
        exp_result, exp_override = \
            ({'prepare_sandbox': '/abc/def/ghi/jkl/mno/test.sh',
              'aqservice': 'stu', 'aqport': '6900', 'aqhost': 'test_vwxyz1'}, False)
        result, override = get_default_opts(auth_option, conf_file,
                                            readonly)
        self.assertEqual(override, exp_override)
        self.assertEqual(result.get('aqhost'), 'test_vwxyz1')

    def test_101_get_default_opts_aqhost_env(self):
        auth_option = True
        conf_file = None
        readonly = True
        env_host = 'test_abc_ring1.xyz.com'
        exp_result, exp_override = ({}, False)
        result, override = get_default_opts(auth_option, conf_file,
                                            readonly, env_aqhost= env_host)
        self.assertEqual(override, exp_override)
        self.assertEqual(result.get('aqhost'), None)

    def test_102_get_default_opts_aqhost_write(self):
        auth_option = True
        conf_file = None
        readonly = False
        globalopts_host = 'test_vwxyz1'
        exp_result, exp_override = \
            ({'prepare_sandbox':
                  '/abc/def/ghi/jkl/mno/test.sh',
              'aqservice': 'stu', 'aqport': '6900', 'aqhost': 'test_vwxyz1'}, False)
        result, override = get_default_opts(auth_option, conf_file,
                                            readonly, globalopts_host)
        self.assertEqual(override, exp_override)
        self.assertEqual(exp_result.get('aqhost'), globalopts_host)

    @mock.patch('aq.get_username')
    @mock.patch('aq.check_ldap_filter')
    def test_103_get_default_opts_aqbatch(self, mock_ldap, mock_username):
        auth_option = True
        conf_file = os.path.join(os.getcwd(), "tests/unit/bin/data/unittest-aq.conf")
        readonly = True
        mock_username.return_value = 'def1'
        mock_ldap.return_value = True
        exp_result, exp_override = ({'aqhost': 'test_vwxyz-batch.abc.com',
                                     'ro_users': 'abc_test1,\ndef_test1,\nghi_test1,'
                                                  '\njkl_test1',
                                     'aqservice': 'stu', 'aqport': '6900'}, True)
        result, override = get_default_opts(auth_option, conf_file,
                                            readonly)
        self.assertEqual(override, exp_override)
        self.assertEqual(result.get('aqhost'), 'test_vwxyz-batch.abc.com')

    @mock.patch('aq.get_username')
    @mock.patch('aq.check_ldap_filter')
    def test_104_get_default_opts_aqbatch_ro_host(self, mock_ldap, mock_username):
        auth_option = True
        conf_file = os.path.join(os.getcwd(), "tests/unit/bin/data/unittest-aq.conf")
        readonly = True
        globalopts_host = 'test_vwxyz-ro.abc.com'
        mock_username.return_value = 'abc1'
        mock_ldap.return_value = True
        exp_result, exp_override = ({'aqhost': 'test_vwxyz-batch.abc.com',
                                     'ro_users': 'abc_test1,\ndef_test1,\nghi_test1,'
                                                 '\njkl_test1',
                                     'aqservice': 'stu', 'aqport': '6900'}, True)
        result, override = get_default_opts(auth_option, conf_file,
                                            readonly, globalopts_host)
        self.assertEqual(override, exp_override)
        self.assertEqual(result.get('aqhost'), 'test_vwxyz-batch.abc.com')

    @mock.patch('aq.get_username')
    @mock.patch('aq.check_ldap_filter')
    def test_105_get_default_opts_aqhost_env_ro_host(self, mock_ldap, mock_username):
        auth_option = True
        conf_file = os.path.join(os.getcwd(), "tests/unit/bin/data/unittest-aq.conf")
        readonly = True
        env_host = 'test_vwxyz-ro.abc.com'
        mock_username.return_value = 'jkl1'
        mock_ldap.return_value = True
        exp_result, exp_override = ({'aqhost': 'test_vwxyz-batch.abc.com',
                                     'ro_users': 'abc_test1,\ndef_test1,\nghi_test1,'
                                                 '\njkl_test1',
                                     'aqservice': 'stu', 'aqport': '6900'}, True)
        result, override = get_default_opts(auth_option, conf_file,
                                            readonly,
                                            env_aqhost=env_host)
        self.assertEqual(override, exp_override)
        self.assertEqual(result.get('aqhost'), 'test_vwxyz-batch.abc.com')

    @mock.patch('aq.get_username')
    @mock.patch('aq.check_ldap_filter')
    def test_106_get_default_opts_aqhost_env_global(self, mock_ldap, mock_username):
        auth_option = True
        conf_file = os.path.join(os.getcwd(), "tests/unit/bin/data/unittest-aq.conf")
        readonly = True
        globalopts_host = 'test_vwxyz-ro.abc.com'
        env_host = 'test_vwxyz-ro.abc.com'
        mock_username.return_value = 'ghi1'
        mock_ldap.return_value = True
        exp_result, exp_override = ({'aqhost': 'test_vwxyz-batch.abc.com',
                                     'ro_users': 'abc_test1,\ndef_test1,\nghi_test1,'
                                                 '\njkl_test1',
                                     'aqservice': 'stu', 'aqport': '6900'}, True)
        result, override = get_default_opts(auth_option, conf_file,
                                            readonly, globalopts_host,
                                            env_host)
        self.assertEqual(override, exp_override)
        self.assertEqual(result.get('aqhost'), 'test_vwxyz-batch.abc.com')

    @mock.patch('aq.get_username')
    @mock.patch('aq.check_ldap_filter')
    def test_107_get_default_opts_aqhost_env_nonro_config(self, mock_ldap, mock_username):
        auth_option = True
        conf_file = os.path.join(os.getcwd(), "tests/unit/bin/data/unittest-aq.conf")
        readonly = True
        env_host = 'test_vwxyz-r1.abc.com'
        mock_username.return_value = 'abc_test'
        mock_ldap.return_value = True
        exp_result, exp_override = ({}, False)
        result, override = get_default_opts(auth_option, conf_file,
                                            readonly,
                                            env_aqhost=env_host)
        self.assertEqual(override, exp_override)
        self.assertEqual(result.get('aqhost'), 'test_vwxyz-ro.abc.com')

    @mock.patch('aq.get_username')
    def test_108_get_default_opts_aqhost_env_nonro_host(self, mock_username):
        auth_option = True
        conf_file = None
        readonly = True
        env_host = 'test_aqd-r1.ms.com'
        mock_username.return_value = 'abc_test'
        exp_result, exp_override = ({}, False)
        result, override = get_default_opts(auth_option, conf_file,
                                            readonly,
                                            env_aqhost=env_host)
        self.assertEqual(override, exp_override)
        self.assertEqual(result.get('aqhost'), None)

    def test_109_get_default_opts_noauth(self):
        auth_option = False
        conf_file = os.path.join(os.getcwd(), "tests/unit/bin/data/unittest-aq.conf")
        readonly = None
        globalopts_host = 'test_vwxyz-ro.abc.com'
        exp_result, exp_override = ({'aqservice': 'cdb', 'aqport': '6901',
                                     'aqhost': 'test_vwxyz1_ro'}, False)
        result, override = get_default_opts(auth_option, conf_file,
                                            readonly, globalopts_host)
        self.assertEqual(override, exp_override)
        self.assertEqual(result.get('aqhost'), 'test_vwxyz1_ro')

    @mock.patch('aq.get_username')
    @mock.patch('aq.check_ldap_filter')
    def test_110_get_default_opts_ro(self, mock_ldap, mock_username):
        auth_option = True
        conf_file = os.path.join(os.getcwd(), "tests/unit/bin/data/unittest-aq.conf")
        readonly = True
        mock_username.return_value = 'def_test1'
        mock_ldap.return_value = True
        exp_result, exp_override = ({'aqservice': 'cdb', 'aqport': '6901',
                                     'aqhost': 'test_vwxyz-ro.abc.com'}, False)
        result, override = get_default_opts(auth_option, conf_file,
                                            readonly)
        self.assertEqual(override, exp_override)
        self.assertEqual(result.get('aqhost'), 'test_vwxyz-ro.abc.com')

    @mock.patch('aq.get_username')
    @mock.patch('aq.check_ldap_filter')
    def test_111_get_default_opts_aqhost_env(self, mock_ldap, mock_username):
        auth_option = True
        conf_file = None
        readonly = True
        env_host = 'test_vwxyz-r100.abc.com'
        mock_username.return_value = 'def_test1'
        mock_ldap.return_value = True
        exp_result, exp_override = ({}, False)
        result, override = get_default_opts(auth_option, conf_file,
                                            readonly, env_aqhost= env_host)
        self.assertEqual(override, exp_override)
        self.assertEqual(result.get('aqhost'), None)

    @mock.patch('aq.get_username')
    @mock.patch('aq.check_ldap_filter')
    def test_112_get_default_opts_ro_users(self, mock_ldap, mock_username):
        auth_option = True
        conf_file = os.path.join(os.getcwd(), "tests/unit/bin/data/unittest-aq.conf")
        readonly = True
        mock_username.return_value = 'ghi_test1'
        mock_ldap.return_value = True
        exp_result, exp_override = ({'aqservice': 'cdb', 'aqport': '6900',
                                     'aqhost': 'test_vwxyz-ro.abc.com'}, False)
        result, override = get_default_opts(auth_option, conf_file,
                                            readonly)
        self.assertEqual(override, exp_override)
        self.assertEqual(result.get('aqhost'), 'test_vwxyz-ro.abc.com')

    @mock.patch('aq.get_username')
    @mock.patch('aq.check_ldap_filter')
    def test_113_get_default_opts_nobatchsection(self, mock_ldap, mock_username):
        auth_option = True
        conf_file = os.path.join(os.getcwd(), "tests/unit/bin/data/unittest1-aq.conf")
        readonly = True
        mock_username.return_value = 'def1'
        mock_ldap.return_value = True
        exp_result, exp_override = ({'aqhost': 'test_vwxyz-batch.abc.com',
                                     'ro_users': 'abc_test1,\ndef_test1,\nghi_test1,'
                                                 '\njkl_test1',
                                     'aqservice': 'stu', 'aqport': '6900'}, True)
        result, override = get_default_opts(auth_option, conf_file,
                                            readonly)
        self.assertEqual(override, exp_override)
        self.assertEqual(result.get('aqhost'), 'test_vwxyz-batch.abc.com')

    @mock.patch('aq.get_username')
    @mock.patch('aq.check_ldap_filter')
    def test_114_get_default_opts_noreadonlysection(self, mock_ldap, mock_username):
        auth_option = True
        conf_file = os.path.join(os.getcwd(), "tests/unit/bin/data/unittest2-aq.conf")
        readonly = True
        mock_username.return_value = 'def1'
        mock_ldap.return_value = True
        exp_result, exp_override = \
            ({'prepare_sandbox': '/abc/def/ghi/jkl/mno/test.sh',
              'aqservice': 'stu', 'aqport': '6900', 'aqhost': 'test_vwxyz1'}, False)
        result, override = get_default_opts(auth_option, conf_file,
                                            readonly)
        self.assertEqual(override, exp_override)
        self.assertEqual(result.get('aqhost'), 'test_vwxyz1')
        self.assertEqual(exp_result, result)
