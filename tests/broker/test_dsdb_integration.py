#!/usr/bin/env python
# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2024  Contributor
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
"""Test integration with DSDB"""

import unittest

if __name__ == "__main__":
    from broker import utils
    utils.import_depends()

try:
    import ms.version
except ImportError:
    pass
else:
    ms.version.addpkg('ms.dsdb', '6.1.7')

from copy import copy
from ipaddress import ip_network, IPv4Network
import logging as log
import ms.dsdb.depends
import ms.dsdb.client
import os
from pathlib import Path
import pwd
import socket
import subprocess
import sys

from aquilon import config
from broker.brokertest import TestBrokerCommand
from broker.networktest import NetworkInfo


class TestDSDBIntegration(TestBrokerCommand):
    @classmethod
    def setUpClass(cls):
        super(TestDSDBIntegration, cls).setUpClass()

        cls.config = config.Config()
        cls._checkout_dsdb_code()
        cls._setup_dsdb_broker()

        hostname = socket.getfqdn()
        os.environ["DSDB_BROKER_URL"] = f"http://{hostname}:8088"
        dsdb_plant = cls.config.get("dsdb", "dsdb_use_testdb")

        cls.dsdb = ms.dsdb.client.DSDB(plant=dsdb_plant)

    @classmethod
    def _checkout_dsdb_code(cls):
        cls.user = pwd.getpwuid(os.getuid())[0]
        cls.dsdb_dir = cls.config.get("unittest", "dsdb_integration_location")

        # Make a directory for a git checkout of DSDB's main repo
        path = Path(cls.dsdb_dir)
        path.mkdir(parents=True, exist_ok=True)
        cls.assertTrue(path.exists(), "DSDB checkout dir exists")

        # We unfortunately need to change directory in a possible `git fetch` below.  Keep 
        # track of where we started.
        cls.orig_pwd = os.getcwd()

        # Do a git clone/fetch depending on whether we already have a local copy of the repo.
        repo = f"http://{cls.user}@stashblue.ms.com/atlassian-stash/scm/aurora_dsdb/dsdb.git"
        git_cmd = cls.config.get("tool_locations", "git")

        if path.joinpath("fcgi-bin").exists():
            os.chdir(cls.dsdb_dir)
            cmd = [git_cmd, "fetch"]
        else:
            cmd = [git_cmd, "clone", repo, cls.dsdb_dir]

        cls.diag(f"Running {cmd}")
        retval = subprocess.run(cmd)

        cls.assertTrue(retval.returncode == 0, "git command returns success")

        # Go back to our original dir
        os.chdir(cls.orig_pwd)


    @classmethod
    def _setup_dsdb_broker(cls):
        dsdb_test_dir = Path(cls.dsdb_dir) / "tests"
        os.chdir(dsdb_test_dir)

        # Option --norecreate_schema could be used if you're certain the schema for NYT_DSDB_15
        # is already correct.  That will save 10 minutes or more.
        cmd = ["./aq_dsdb_integration_setup"]

        cls.diag(f"Running {cmd} in dir {dsdb_test_dir}")
        retval = subprocess.run(cmd)

        cls.assertTrue(retval.returncode == 0, "DSDB initialise command returns success")
        os.chdir(cls.orig_pwd)


    @classmethod
    def tearDownClass(cls):
        os.chdir(cls.orig_pwd)


    @classmethod
    def diag(self, msg):
        print(msg, file=sys.stderr)


    def _run_dsdb_commands(self, commands):
        for command in commands:
            fn = getattr(self.dsdb, command["cmd"])
            try:
                self.diag(f"Running dsdb {command['cmd']} {command['args']}")
                fn(**command["args"])
            except Exception as e:
                self.diag(f"dsdb {command['cmd']} {command['args']} threw exception {e}")


    def _delete_dsdb_network(self, ip):
        try:
            self.dsdb.delete_network(network_ip_address=ip)
        except Exception as e:
            self.diag(f"dsdb delete_network --network_ip_address={ip} threw exception {e}")


    def test_000_initialise_dsdb_data(self):
        """Initialise DSDB location and other data"""
        for network in self.net:
            if (network.autocreate and network.is_ipv4) \
                or network.name == "netuc_netmgmt_1a" or network.name == "netuc_netmgmt_1b":
                self._delete_dsdb_network(network.ip)

        commands = [
            { "cmd": "delete_bucket", "args": { "bucket": "bucket2" }},
            { "cmd": "delete_bucket", "args": { "bucket": "nyb10" }},
            { "cmd": "delete_bucket", "args": { "bucket": "zebrabucket" }},
            { "cmd": "delete_building_aq", "args": { "building": "bu" }},
            { "cmd": "delete_building_aq", "args": { "building": "np" }},
            { "cmd": "delete_building_aq", "args": { "building": "ut" }},
            { "cmd": "delete_city_aq", "args": { "city": "ny" }},
            { "cmd": "add_country", "args": { "country_symbol": "us", "country_name": "USA", "continent": "na" }},
            { "cmd": "add_network_type", "args": { "network_type": "localvip" }},
            { "cmd": "add_network_type", "args": { "network_type": "management" }},
            { "cmd": "add_network_type", "args": { "network_type": "tor_net" }},
            { "cmd": "add_network_type", "args": { "network_type": "tor_net2" }},
            { "cmd": "add_network_type", "args": { "network_type": "transit" }},
            { "cmd": "add_network_type", "args": { "network_type": "unknown" }},
            { "cmd": "add_network_type", "args": { "network_type": "vip" }},
            { "cmd": "add_network_type", "args": { "network_type": "vm_storage_net" }},
            { "cmd": "add_network_type", "args": { "network_type": "vpls" }},
        ]
        self._run_dsdb_commands(commands)

    def test_002_initialise_aq_locations(self):
        commands = [
            ["add_organization", "--organization", "ms"],
            ["add_hub", "--hub", "ny"],
            ["add_continent", "--continent", "na", "--hub", "ny"],
            ["add_country", "--country", "us", "--continent", "na"],
            ["add_city", "--city", "ny", "--timezone", "America/New_York", "--country", "us"],
            ["add_building", "--building", "bu", "--address", "bu", "--city", "ny"],
            ["add_building", "--building", "np", "--address", "np", "--city", "ny"],
            ["add_building", "--building", "ut", "--address", "ut", "--city", "ny"],
            ["add_bunker", "--bunker", "bucket2.np", "--building", "np"],
            ["add_bunker", "--bunker", "nyb10.np", "--building", "np"],
            ["add_bunker", "--bunker", "bucket2.ut", "--building", "ut"],
            ["add_bunker", "--bunker", "zebrabucket.ut", "--building", "ut"],
        ]

        for command in commands:
            self.diag(f"Running aq {command}")
            p, out, err = self.aq.runcommand(command)
            if p.returncode:
                self.diag(f"Command returned p={p}, out={out}, err={err}")


    def test_003_initialise_more_dsdb_locations(self):
        """Initialise more DSDB location data. This is after some aq commands have created data in DSDB."""
        commands = [
            {"cmd": "add_bucket", "args": { "bucket": "bucket2" }},
            {"cmd": "add_bucket", "args": { "bucket": "nyb10" }},
            {"cmd": "add_bucket", "args": { "bucket": "zebrabucket" }},
        ]

        self._run_dsdb_commands(commands)


    def _check_dsdb_network_data(self, network, voicevlan=None):
        actual = None

        # This is what we expect in the data structure returned by DSDB:
        expected = {
            "IP_address": str(network.ip),
            "network_name": network.name,
            "netmask": str(IPv4Network(f"{network.ip}/{network.prefixlen}").netmask),
            "network_type": network.nettype,
            "side": network.side,
        }

        if network.comments:
            expected["comments"] = network.comments

        if voicevlan is not None:
            expected["voice_vlan"] = voicevlan

        if network.network_tags:
            expected["network_tags"] = network.network_tags
        else:
            expected["network_tags"] = {}

        building = None
        if network.loc_type == "building":
            building = network.loc_name
        elif network.loc_type == "bunker":
            bucket, building = network.loc_name.split(".")
            expected["bucket_name"] = bucket
        expected["location_name"] = f"{building}.ny.na"

        success = True
        try:
            actual = self.dsdb.show_network(ip_address=expected["IP_address"], show_network_tags=1).results()
            if isinstance(actual, list):
                actual = actual[0]
            else:
                actual = {}
        except Exception as e:
            self.diag(f"Error fetching network {expected['IP_address']} from DSDB: {e}")
            success = False

        self.diag(f"dsdb show_network returned {actual}")

        for key in expected:
            if expected[key] == actual.get(key):
                self.diag(f"Network {expected['IP_address']}: match for key {key}: {expected[key]}")
            else:
                self.diag(f"Network {expected['IP_address']}: NO match: for key {key}, expected {expected[key]}, " +
                      f"but got {actual[key]}")
                success = False

        self.assertTrue(success, f"All tested fields for network {network.ip} match in AQ and DSDB")
        

    def _check_network_missing_in_dsdb(self, ip):
        result = self.dsdb.show_network(ip_address=ip).results()

        self.diag(f"Network {ip} is no longer present in DSDB")
        self.assertEqual(len(result), 0, f"Network {ip} is now missing in DSDB")


    def test_100_add_network(self):
        for network in self.net:
            if not network.autocreate or not network.is_ipv4:
                continue

            command = [
                "add_network",
                f"--network={network.name}",
                f"--ip={network.ip}",
                f"--prefixlen={network.prefixlen}",
                f"--{network.loc_type}={network.loc_name}",
                f"--type={network.nettype}",
                f"--side={network.side}"
            ]
            if network.comments:
                command.extend(["--comments", network.comments])

            tags = {
                "is_advertised_externally": "0",
                "is_advertised_to_internet": "0",
                "is_dc_hosted_desktop": "0",
                "is_gels": "0",
                "is_infra_services": "1",
                "is_network_infra": "1",
                "plant": "voice",
                "plant_type": "lab",
                "stance": "amber",
                "standard_network_environment": "nonprod",
                "virtual_ip": "none",
            }
            command.extend((f"--network_tag={tag}={tags[tag]}" for tag in tags))
            setattr(network, "network_tags", tags)

            self.diag(f"Running aq command {command}")
            self.noouttest(command)

            self._check_dsdb_network_data(network)


    def test_101_add_network_voicevlan(self):
        network = self.net["netuc_netmgmt_1a"]
        voicevlan = "4093"

        command = [
            "add_network",
            f"--network={network.name}",
            f"--ip={network.ip}",
            f"--prefixlen={network.prefixlen}",
            f"--{network.loc_type}={network.loc_name}",
            f"--type={network.nettype}",
            f"--side={network.side}",
            f"--voicevlan={voicevlan}",
        ]
        self.diag(f"Running aq command {command}")
        self.noouttest(command)

        self._check_dsdb_network_data(network, voicevlan=voicevlan)


    def test_102_add_network_with_no_tags(self):
        network = self.net["netuc_netmgmt_1b"]

        command = [
            "add_network",
            f"--network={network.name}",
            f"--ip={network.ip}",
            f"--prefixlen={network.prefixlen}",
            f"--{network.loc_type}={network.loc_name}",
            f"--type={network.nettype}",
            f"--side={network.side}"
        ]

        self.diag(f"Running aq command {command}")
        self.noouttest(command)

        self._check_dsdb_network_data(network)


    def test_200_update_network(self):
        network = self.net["ut10_eth1"]

        tags = {
            "is_advertised_externally": "0",
            "is_advertised_to_internet": "0",
            "is_dc_hosted_desktop": "0",
            "is_gels": "0",
            "is_infra_services": "1",
            "is_network_infra": "1",
            "plant": "voice",
            "plant_type": "lab",
            "stance": "amber",
            "standard_network_environment": "nonprod",
            "virtual_ip": "none",
        }
        tests = [
            { "rename_to": "ut10_eth1_updated" },
            { "building": "np" },
            { "bunker": "nyb10.np" },
            { "type": "tor_net2" },
            { "side": "b" },
            { "comments": "Some new comments" },
            { "voicevlan": "0" },
            { "network_tags": { "plant_type": "management", "version": "2" }},
            { "network_tags": { "version": "" }},
        ]
        expected = NetworkInfo(
            name=network.name,
            cidr=str(network),
            nettype=network.nettype,
            loc_type=network.loc_type,
            loc_name=network.loc_name,
            side=network.side,
            network_tags=tags,
        )

        # Map from what an 'aq' command expects to what a NetworkInfo object calls it.
        # Unspecified fields are the same.
        arg_map = {
            "rename_to": "name",
            "type":      "nettype",
            "building":  "loc_name",
            "bunker":    "loc_name",
        }
            
        for test in tests:
            command = [
                "update_network",
                "--ip", str(network.ip),
            ]
            for arg in test:
                if arg == "network_tags":
                    command.extend((f"--network_tag={tag}={test[arg][tag]}" for tag in test[arg]))
                    for tag in test[arg]:
                        if test[arg][tag] not in ("", None):
                            tags[tag] = test[arg][tag]
                        else:
                            del tags[tag]
                    setattr(expected, "network_tags", tags)
                else:
                    command.extend((f"--{arg}", test[arg]))

                    expected_arg = arg_map.get(arg, arg)
                    setattr(expected, expected_arg, test[arg])

                if arg in ("building", "bunker"):
                    setattr(expected, "loc_type", arg)
    
            self.diag(f"Running aq command {command}")
            self.noouttest(command)

            self._check_dsdb_network_data(expected)


    def test_201_update_network_invalid_voicevlan(self):
        """Confirm that DSDB issues an error when we use an out of range voicevlan value, causing the aq command to fail"""
        network = self.net["ut10_eth1"]

        command = [
            "update_network",
            "--ip", str(network.ip),
            "--voicevlan", "4096",
        ]

        self.diag(f"Running aq command {command}")

        err = self.badrequesttest(command)
        self.matchoutput(err, r"DSDB update_network Failed (-1): Invalid VOICEVLAN value", command)


    def test_300_del_network(self):
        for network in self.net:
            if (not network.autocreate or not network.is_ipv4) \
                and network.name not in ("netuc_netmgmt_1a", "netuc_netmgmt_1b"):
                continue

            command = ["del_network", f"--ip={network.ip}"]
            self.diag(f"Running aq command {command}")
            try:
                self.noouttest(command)
            except Exception as e:
                self.diag(f"Got exception {e} but continuing")

            self._check_network_missing_in_dsdb(network.ip)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDSDBIntegration)
    unittest.TextTestRunner(verbosity=2).run(suite)

