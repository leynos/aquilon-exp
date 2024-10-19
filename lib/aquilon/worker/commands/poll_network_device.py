# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018  Contributor
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
"""Contains the logic for `aq poll network_device`."""

import fcntl
import logging
import os
import time
from collections import defaultdict
from datetime import datetime
from json import JSONDecoder

from aquilon.aqdb.model import NetworkDevice, ObservedMac, Rack
from aquilon.aqdb.types import MACAddress
from aquilon.config import Config
from aquilon.exceptions_ import ArgumentError, NotFoundException, ProcessException, UnimplementedError
from aquilon.utils import validate_json
from aquilon.worker.broker import BrokerCommand
from aquilon.worker.dbwrappers.network_device import determine_helper_args, determine_helper_hostname
from aquilon.worker.dbwrappers.observed_mac import update_or_create_observed_mac
from aquilon.worker.locks import ExternalKey
from aquilon.worker.processes import run_command


class CommandPollNetworkDevice(BrokerCommand):
    required_parameters = ["rack"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.active_locks = 0
        logging.basicConfig(level=logging.INFO)
        self.config = Config()
        self.user_locks = defaultdict(int)
        self.lock_dir = self.config.get("broker", "poll_switch_lock_dir")
        self.max_switches = int(self.config.get("broker", "max_switches"))
        self.lock_expiration = int(self.config.get("broker", "lock_expiration_minutes")) * 60

    def render(self, session, logger, rack, type, clear, vlan, **_):
        if vlan:
            raise UnimplementedError("vlan argument is no longer available")
        dblocation = Rack.get_unique(session, rack, compel=True)
        NetworkDevice.check_type(type)
        q = session.query(NetworkDevice)
        q = q.filter_by(location=dblocation)
        if type:
            q = q.filter_by(switch_type=type)
        netdevs = q.all()
        if not netdevs:
            raise NotFoundException("No network device found.")
        return self.poll(session, logger, netdevs, clear, vlan)

    def poll(self, session, logger, netdevs, clear, vlan):
        now = datetime.now()
        default_ssh_args = determine_helper_args(self.config)
        for netdev in netdevs:
            if clear:
                self.clear(session, netdev)
            hostname = determine_helper_hostname(session, logger, self.config, netdev)
            if hostname:
                ssh_args = default_ssh_args[:]
                ssh_args.append(hostname)
            else:
                ssh_args = []

            with ExternalKey("poll_network_device", [netdev], logger=logger):
                self.poll_mac(session, netdev, now, ssh_args)

    def acquire_lock(self, lock_name, lock_dir):
        if not os.path.exists(lock_dir):
            os.umask(0)
            os.makedirs(lock_dir, mode=0o777)
        lock_file = os.path.join(lock_dir, lock_name)
        switch_name = lock_name.split("lock_")[1]
        if os.path.exists(lock_file):
            lock_age = time.time() - os.path.getmtime(lock_file)
            if lock_age < self.lock_expiration:
                raise RuntimeError("Lock file exists and is not expired.")
            else:
                os.remove(lock_file)
                logging.info(f"Expired lock file removed: {lock_name}")
        if self.active_locks >= self.max_switches:
            raise RuntimeError(
                f"Maximum number of switches {self.max_switches} "
                f"which can be polled at the same time "
                f"has reached. Please retry later"
            )
        if self.active_locks == 1:
            raise RuntimeError(
                f"Poll switch for switch {switch_name} is already running, "
                f"only one poll switch can be run per switch."
            )
        self.lock_file = os.path.join(lock_dir, lock_name)
        fd = os.open(self.lock_file, os.O_CREAT | os.O_RDWR)
        fcntl.flock(fd, fcntl.LOCK_EX)
        self.active_locks += 1
        logging.info(f"Lock acquired: {lock_name}")
        return fd

    def release_lock(self, fd, lock_name):
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
        if os.path.exists(self.lock_file):
            os.remove(self.lock_file)
        self.active_locks -= 1
        logging.info(f"Lock released: {lock_name}")

    def poll_mac(self, session, netdev, now, ssh_args):
        importer = self.config.lookup_tool("get-camtable")
        if not netdev.primary_name:
            hostname = netdev.label
        elif netdev.primary_name.fqdn.dns_domain.name == 'ms.com':
            hostname = netdev.primary_name.fqdn.name
        else:
            hostname = netdev.fqdn
        args = []

        if ssh_args:
            args.extend(ssh_args)
        args.extend([importer, "--debug", hostname])
        lock_name = f"lock_{hostname}"
        fd = self.acquire_lock(lock_name, self.lock_dir)
        try:
            out = run_command(args)
        except ProcessException as err:
            if os.path.exists(self.lock_file):
                os.remove(self.lock_file)
            raise ArgumentError(f"Failed to run network device discovery: {err}") from err
        else:
            self.release_lock(fd, lock_name)
        macports = JSONDecoder().decode(out)
        validate_json(self.config, macports, "discovered_macs", "discovered MACs")
        for mac, port in macports:
            update_or_create_observed_mac(session, netdev, port, MACAddress(mac), now)

    def clear(self, session, netdev):
        session.query(ObservedMac).filter_by(network_device=netdev).delete()
        session.flush()
