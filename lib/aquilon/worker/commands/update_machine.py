#!/usr/bin/env python
# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2008-2018,2021  Contributor
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
"""Contains the logic for `aq update machine`."""

import re

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import and_

from aquilon.exceptions_ import ArgumentError, ProcessException
from aquilon.aqdb.model import (
    ARecord,
    BundleResource,
    Chassis,
    Filesystem,
    Machine,
    MachineChassisSlot,
    Model,
    Network,
    Resource,
    Share,
)
from aquilon.aqdb.types import CpuType
from aquilon.worker.broker import BrokerCommand
from aquilon.worker.dbwrappers.dns import update_address
from aquilon.worker.dbwrappers.hardware_entity import update_primary_ip
from aquilon.worker.dbwrappers.interface import (
    generate_ip,
    next_ip,
    set_port_group,
)
from aquilon.worker.dbwrappers.location import get_location
from aquilon.worker.dbwrappers.resources import (find_resource,
                                                 get_resource_holder)
from aquilon.worker.templates import (PlenaryHostData,
                                      PlenaryServiceInstanceToplevel)
from aquilon.worker.processes import DSDBRunner
from aquilon.worker.dbwrappers.change_management import ChangeManagement
from aquilon.worker.commands.update_interface_machine import CommandUpdateInterfaceMachine
from aquilon.worker.ib_services import IBServices
from aquilon.utils import force_mac, validate_json

_disk_map_re = re.compile(r'^([^/]+)/(?:([^/]+)/)?([^/]+):([^/]+)/(?:([^/]+)/)?([^/]+)$')


def parse_remap_disk(old_vmholder, new_vmholder, remap_disk):
    result = {}
    if not remap_disk:
        return result

    maps = remap_disk.split(",")

    for map in maps:
        res = _disk_map_re.match(map)
        if not res:
            raise ArgumentError("Invalid disk backend remapping "
                                "specification: '%s'" % map)
        src_type, src_rg, src_name, dst_type, dst_rg, dst_name = res.groups()
        src_cls = Resource.polymorphic_subclass(src_type,
                                                "Invalid resource type")
        dst_cls = Resource.polymorphic_subclass(dst_type,
                                                "Invalid resource type")
        if dst_cls not in (Share, Filesystem):
            raise ArgumentError("%s is not a valid virtual disk backend "
                                "resource type." % dst_type)

        src_backend = find_resource(src_cls, old_vmholder, src_rg, src_name)
        dst_backend = find_resource(dst_cls, new_vmholder, dst_rg, dst_name)
        result[src_backend] = dst_backend

    return result


def get_metacluster(holder):
    if hasattr(holder, "metacluster"):
        return holder.metacluster

    # vmhost
    if hasattr(holder, "cluster") and holder.cluster:
        return holder.cluster.metacluster
    else:
        # TODO vlocal still has clusters, so this case not tested yet.
        return None


def update_disk_backing_stores(dbmachine, old_holder, new_holder, remap_disk):
    if not old_holder:
        old_holder = dbmachine.vm_container.holder.holder_object
    if not new_holder:
        new_holder = old_holder

    disk_mapping = parse_remap_disk(old_holder, new_holder, remap_disk)

    for dbdisk in dbmachine.disks:
        old_bstore = dbdisk.backing_store
        if isinstance(old_bstore.holder, BundleResource):
            resourcegroup = old_bstore.holder.resourcegroup.name
        else:
            resourcegroup = None

        if old_bstore in disk_mapping:
            new_bstore = disk_mapping[old_bstore]
        else:
            new_bstore = find_resource(old_bstore.__class__, new_holder,
                                       resourcegroup, old_bstore.name,
                                       error=ArgumentError)
        dbdisk.backing_store = new_bstore


def update_interface_bindings(session, logger, dbmachine, autoip,
                              autopg, pg, ib_services):
    for dbinterface in dbmachine.interfaces:
        old_pg = dbinterface.port_group
        if not old_pg:
            continue

        old_net = old_pg.network

        # Suppress the warning about PG mismatch - we'll update the addresses
        # later
        if autopg:
            set_port_group(session, logger, dbinterface, 'user',
                           check_pg_consistency=False)
        elif pg:
            set_port_group(session, logger, dbinterface, pg,
                           check_pg_consistency=False)
        else:
            set_port_group(session, logger, dbinterface, old_pg.name,
                           check_pg_consistency=False)
        logger.info("Updated {0:l} to use {1:l}.".format(dbinterface,
                                                         dbinterface.port_group))
        new_net = dbinterface.port_group.network

        if new_net == old_net or not autoip:
            dbinterface.check_pg_consistency(logger=logger)
            continue

        for addr in dbinterface.assignments:
            if addr.network != old_net:
                continue

            new_ip = generate_ip(session, logger, dbinterface, autoip=True,
                                 network_environment=old_net.network_environment)
            for dbdns_rec in addr.dns_records:
                dbdns_rec.network = new_net
                dbdns_rec.ip = new_ip

            old_ip = addr.ip
            addr.ip = new_ip
            addr.network = new_net
            logger.info("Changed {0:l} IP address from {1!s} to {2!s}."
                        .format(dbinterface, old_ip, new_ip))

            fqdn = str(dbinterface.hardware_entity.primary_name.fqdn)
            ib_services.group.add_action(
                lambda: ib_services.update_a_ptr(fqdn, old_ip, new_ip=new_ip),
                lambda: ib_services.update_a_ptr(fqdn, new_ip, new_ip=old_ip)
            )

        dbinterface.check_pg_consistency(logger=logger)


def move_vm(session, logger, dbmachine, resholder, remap_disk,
            allow_metacluster_change, autoip, plenaries,
            autopg=False, pg=None, ib_services=None):
    old_holder = dbmachine.vm_container.holder.holder_object
    if resholder:
        new_holder = resholder.holder_object
    else:
        new_holder = old_holder

    if new_holder != old_holder:
        old_mc = get_metacluster(old_holder)
        new_mc = get_metacluster(new_holder)
        if old_mc != new_mc and not allow_metacluster_change:
            raise ArgumentError("Moving VMs between metaclusters is "
                                "disabled by default.  Use the "
                                "--allow_metacluster_change option to "
                                "override.")

        plenaries.add(old_holder)
        plenaries.add(new_holder)

        dbmachine.vm_container.holder = resholder

    if new_holder != old_holder or remap_disk:
        update_disk_backing_stores(dbmachine, old_holder, new_holder, remap_disk)

    if new_holder != old_holder or autoip:
        update_interface_bindings(session, logger, dbmachine, autoip, autopg, pg, ib_services)

    if hasattr(new_holder, 'location_constraint'):
        dbmachine.location = new_holder.location_constraint
    else:
        dbmachine.location = new_holder.hardware_entity.location


def validate_recipe(config, recipe):
    validate_json(config, recipe, "interface_update", "recipe")

    # Type conversions not covered by the schema
    if "interfaces" in recipe:
        for iface, params in recipe["interfaces"].items():
            if "mac" in params:
                params["mac"] = force_mac("MAC address of " + iface,
                                          params["mac"])


class CommandUpdateMachine(BrokerCommand):
    requires_plenaries = True

    required_parameters = ["machine"]

    def render(self, session, logger, plenaries, machine, model, vendor, serial, uuid,
               clear_uuid, chassis, slot, clearchassis, multislot, vmhost,
               cluster, metacluster, allow_metacluster_change, cpuname,
               cpuvendor, cpucount, memory, recipe, ip, autoip, swap_ip, uri,
               remap_disk, comments, user, justification, reason, **arguments):
        dsdb_runner = DSDBRunner(logger=logger)
        dbmachine = Machine.get_unique(session, machine, compel=True)
        oldinfo = DSDBRunner.snapshot_hw(dbmachine)
        old_location = dbmachine.location

        ib_services = IBServices(logger)

        # Validate ChangeManagement
        cm = ChangeManagement(session, user, justification, reason, logger, self.command, **arguments)
        cm.consider(dbmachine)
        cm.validate()

        plenaries.add(dbmachine)
        if dbmachine.vm_container:
            plenaries.add(dbmachine.vm_container)
        if dbmachine.host:
            # Using PlenaryHostData directly, to avoid warnings if the host has
            # not been configured yet
            plenaries.add(dbmachine.host, cls=PlenaryHostData)

        if clearchassis:
            del dbmachine.chassis_slot[:]

        if chassis:
            dbchassis = Chassis.get_unique(session, chassis, compel=True)
            dbmachine.location = dbchassis.location
            if slot is None:
                raise ArgumentError("Option --chassis requires --slot "
                                    "information.")
            self.adjust_slot(session, logger,
                             dbmachine, dbchassis, slot, multislot)
        elif slot is not None:
            dbchassis = None
            for dbslot in dbmachine.chassis_slot:
                if dbchassis and dbslot.chassis != dbchassis:
                    raise ArgumentError("Machine in multiple chassis, please "
                                        "use --chassis argument.")
                dbchassis = dbslot.chassis
            if not dbchassis:
                raise ArgumentError("Option --slot requires --chassis "
                                    "information.")
            self.adjust_slot(session, logger,
                             dbmachine, dbchassis, slot, multislot)

        dblocation = get_location(session, **arguments)
        if dblocation:
            loc_clear_chassis = False
            for dbslot in dbmachine.chassis_slot:
                dbcl = dbslot.chassis.location
                if dbcl != dblocation:
                    if chassis or slot is not None:
                        raise ArgumentError("{0} conflicts with chassis {1!s} "
                                            "location {2}."
                                            .format(dblocation, dbslot.chassis,
                                                    dbcl))
                    else:
                        loc_clear_chassis = True
            if loc_clear_chassis:
                del dbmachine.chassis_slot[:]
            dbmachine.location = dblocation

        if model:
            # If overriding model, should probably overwrite default
            # machine specs as well.
            dbmodel = Model.get_unique(session, name=model, vendor=vendor,
                                       compel=True)
            if not dbmodel.model_type.isMachineType():
                raise ArgumentError("The update_machine command cannot update "
                                    "machines of type %s." %
                                    dbmodel.model_type)
            # We probably could do this by forcing either cluster or
            # location data to be available as appropriate, but really?
            # Failing seems reasonable.
            if dbmodel.model_type != dbmachine.model.model_type and \
                (dbmodel.model_type.isVirtualMachineType() or
                 dbmachine.model.model_type.isVirtualMachineType()):
                raise ArgumentError("Cannot change machine from %s to %s." %
                                    (dbmachine.model.model_type,
                                     dbmodel.model_type))

            old_nic_model = dbmachine.model.nic_model
            new_nic_model = dbmodel.nic_model
            if old_nic_model != new_nic_model:
                for iface in dbmachine.interfaces:
                    if iface.model == old_nic_model:
                        iface.model = new_nic_model

            dbmachine.model = dbmodel

        if cpuname or cpuvendor:
            dbcpu = Model.get_unique(session, name=cpuname, vendor=cpuvendor,
                                     model_type=CpuType.Cpu, compel=True)
            dbmachine.cpu_model = dbcpu

        if cpucount is not None:
            dbmachine.cpu_quantity = cpucount
        if memory is not None:
            dbmachine.memory = memory
        if serial is not None:
            dbmachine.serial_no = serial
        if comments is not None:
            dbmachine.comments = comments

        if uuid:
            q = session.query(Machine)
            q = q.filter_by(uuid=uuid)
            existing = q.first()
            if existing:
                raise ArgumentError("{0} is already using UUID {1!s}."
                                    .format(existing, uuid))
            dbmachine.uuid = uuid
        elif clear_uuid:
            dbmachine.uuid = None

        if uri and not dbmachine.model.model_type.isVirtualMachineType():
            raise ArgumentError("URI can be specified only for virtual "
                                "machines and the model's type is %s" %
                                dbmachine.model.model_type)

        if uri is not None:
            dbmachine.uri = uri

        # Will be set to True if pg in recipe will be used if below
        # conditions apply.
        pg_used = False

        # FIXME: For now, if a machine has its interface(s) in a portgroup
        # this command will need to be followed by an update_interface to
        # re-evaluate the portgroup for overflow.
        # It would be better to have --pg and --autopg options to let it
        # happen at this point.
        if cluster or vmhost or metacluster:
            if not dbmachine.vm_container:
                raise ArgumentError("Cannot convert a physical machine to "
                                    "virtual.")

            resholder = get_resource_holder(session, logger, hostname=vmhost,
                                            cluster=cluster,
                                            metacluster=metacluster,
                                            compel=False)

            # For now the autopg on the interface is allowed for only instance

            # Existing update_machine will still do move_vm for zebra vm which
            # have multiple interfaces but the issues may occur where pg's are
            # not available when doing metacluster change.

            # Next Steps: Extend this logic for multiple interfaces which need
            # checking for the available pg on source & dest cluster as well
            # as count to be same.

            if recipe and len(recipe.get('interface').split()) == 1 and \
                    recipe.get("autopg"):
                move_vm(session, logger, dbmachine, resholder, remap_disk,
                        allow_metacluster_change, autoip, plenaries,
                        autopg=recipe.get("autopg"), ib_services=ib_services)
            elif recipe and len(recipe.get('interface').split()) == 1 and \
                    recipe.get("pg"):
                move_vm(session, logger, dbmachine, resholder, remap_disk,
                        allow_metacluster_change, autoip, plenaries,
                        pg=recipe.get("pg"), ib_services=ib_services)
                pg_used = True
            else:
                move_vm(session, logger, dbmachine, resholder, remap_disk,
                        allow_metacluster_change, autoip, plenaries, ib_services=ib_services)
        elif remap_disk:
            update_disk_backing_stores(dbmachine, None, None, remap_disk)

        # FIXED: If a machine has its interface(s) in a portgroup
        # this command will need to be followed by an update_interface to
        # re-evaluate the portgroup for overflow.
        # It would be better to have --pg and --autopg options to let it
        # happen at this point.
        if recipe:
            validate_recipe(self.config, recipe)

            # This will handle edge cases where the port-group is not
            # associated with a VM and will use the autopg passed inside
            # recipe if no metacluster change is involved. 


            old_pg = []
            # This will check to ensure only single pg is currently being
            # updated as multiple interface will be done in next phase
            for dbinterface in dbmachine.interfaces:
                old_pg.append(dbinterface.port_group)
            if recipe.get("autopg") and len(old_pg) == 1 \
                    and None not in old_pg:
                new_pg = False
            else:
                new_pg = recipe.get("autopg")

            # This will check to ensure if pg is already set and will
            # not be set again in update_interface code.
            if recipe.get("pg") and pg_used:
                target_pg = None
            else:
                target_pg = recipe.get("pg")

            if len(recipe.get('interface').split()) == 1:
                int_update = CommandUpdateInterfaceMachine()
                int_update.update_interface_machine(session, logger, plenaries,
                                                    recipe.get("interface"), machine,
                                                    mac=recipe.get("mac", None),
                                                    model=recipe.get("model", None),
                                                    vendor=recipe.get("vendor", None),
                                                    boot=recipe.get("boot", None),
                                                    pg=target_pg,
                                                    autopg=new_pg,
                                                    comments=recipe.get("comments", None),
                                                    master=recipe.get("master", None),
                                                    clear_master=recipe.get("clear_master", None),
                                                    default_route=recipe.get("default_route", None),
                                                    rename_to=recipe.get("rename_to", None),
                                                    bus_address=recipe.get("bus_address", None),
                                                    **arguments)
            else:
                logger.warning("Warning:Please run update_interface to change "
                               "mutiple interfaces on the host")

        swap_addr = None
#        old_ip = dbmachine.primary_name.ip if (dbmachine.primary_name and hasattr(dbmachine.primary_name, "ip")) else None
        old_ip = None
        if (dbmachine.primary_name and hasattr(dbmachine.primary_name, "ip")):
            old_ip = dbmachine.primary_name.ip

        temp_ip = None
        if swap_ip:
            if not dbmachine.primary_name:
                raise ArgumentError("Cannot swap IP with a machine that "
                                    "has no primary name.")
            dbnetwork = dbmachine.primary_name.network
            q = session.query(ARecord)
            q = q.filter_by(ip=swap_ip)
            q = q.outerjoin(Network)
            q = q.filter(and_(Network.network_environment ==
                              dbnetwork.network_environment))
            try:
                swap_addr = q.one()
            except NoResultFound:
                raise ArgumentError(
                    "IP address {0} is not assigned to a DNS entry. You can "
                    "only swap IPs with unused DNS records added via "
                    "add_address".format(swap_ip),
                )
            swap_addr.network.lock_row()
            dbmachine.primary_name.network.lock_row()
            temp_ip = next_ip(session, swap_addr.network, ipalgorithm=None)
            dsdb_runner.update_host_details(swap_addr.fqdn,
                                            old_ip=swap_addr.ip,
                                            new_ip=temp_ip)
            update_address(session, swap_addr, temp_ip, swap_addr.network)
            session.flush()

            fqdn = str(swap_addr.fqdn)
            ib_services.group.add_action(
                lambda: ib_services.update_a_ptr(fqdn, swap_addr.ip, new_ip=temp_ip),
                lambda: ib_services.update_a_ptr(fqdn, temp_ip,      new_ip=swap_addr.ip)
            )

        if (ip or swap_ip):
            target_ip = ip if ip else swap_ip
            if dbmachine.host:
                for srv in dbmachine.host.services_provided:
                    si = srv.service_instance
                    plenaries.add(si, cls=PlenaryServiceInstanceToplevel)
            update_primary_ip(session, logger, dbmachine, target_ip)

            fqdn = str(dbmachine.primary_name.fqdn)
            ib_services.group.add_action(
                lambda: ib_services.update_a_ptr(fqdn, old_ip,    new_ip=target_ip),
                lambda: ib_services.update_a_ptr(fqdn, target_ip, new_ip=old_ip)
            )

        if swap_ip:
            update_address(session, swap_addr, old_ip, swap_addr.network)

            fqdn = str(swap_addr.fqdn)
            ib_services.group.add_action(
                lambda: ib_services.update_a_ptr(fqdn, temp_ip, new_ip=old_ip),
                lambda: ib_services.update_a_ptr(fqdn, old_ip,  new_ip=temp_ip)
            )

        if dbmachine.location != old_location and dbmachine.host:
            for vm in dbmachine.host.virtual_machines:
                plenaries.add(vm)
                vm.location = dbmachine.location

        session.flush()

        # Check if the changed parameters still meet cluster capacity
        # requiremets
        if dbmachine.cluster:
            dbmachine.cluster.validate()
            if allow_metacluster_change and dbmachine.cluster.metacluster:
                dbmachine.cluster.metacluster.validate()
        if dbmachine.host and dbmachine.host.cluster:
            dbmachine.host.cluster.validate()

        for dbinterface in dbmachine.interfaces:
            dbinterface.check_pg_consistency(logger=logger)

        # The check to make sure a plenary file is not written out for
        # dummy aurora hardware is within the call to write().  This way
        # it is consistent without altering (and forgetting to alter)
        # all the calls to the method.
        with plenaries.transaction():
            if dbmachine.host and dbmachine.host.archetype.name == 'aurora':
                try:
                    dsdb_runner.show_host(dbmachine.fqdn)
                except ValueError as e:
                    raise ArgumentError("Could not find host in DSDB: "
                                        "%s" % e)
            else:
                dsdb_runner.update_host(dbmachine, oldinfo)
                if swap_ip:
                    dsdb_runner.update_host_details(swap_addr.fqdn,
                                                    old_ip=temp_ip,
                                                    new_ip=old_ip)
                dsdb_runner.commit_or_rollback("Could not update machine in DSDB")

        try:
            ib_services.group.commit_or_rollback()
        except Exception as e:
            dsdb_runner.rollback()
            raise e

        return

    def adjust_slot(self, session, logger,
                    dbmachine, dbchassis, slot, multislot):
        for dbslot in dbmachine.chassis_slot:
            # This update is a noop, ignore.
            # Technically, this could be a request to trim the list down
            # to just this one slot - in that case --clearchassis will be
            # required.
            if dbslot.chassis == dbchassis and dbslot.slot_number == slot:
                return
            if dbslot.chassis != dbchassis and multislot:
                raise ArgumentError("Machine cannot be in multiple chassis. "
                                    "Use --clearchassis to remove "
                                    "current chassis slot information.")

        if len(dbmachine.chassis_slot) > 1 and not multislot:
            raise ArgumentError("Use --multislot to support a machine in more "
                                "than one slot, or --clearchassis to remove "
                                "current chassis slot information.")
        if not multislot:
            slots = ", ".join(str(dbslot.slot_number) for dbslot in
                              dbmachine.chassis_slot)
            logger.info("Clearing {0:l} out of {1:l} slot(s) "
                        "{2}".format(dbmachine, dbchassis, slots))
            del dbmachine.chassis_slot[:]
        q = session.query(MachineChassisSlot)
        q = q.filter_by(chassis=dbchassis, slot_number=slot)
        dbslot = q.first()
        if dbslot:
            if dbslot.machine:
                raise ArgumentError("{0} slot {1} already has machine "
                                    "{2}.".format(dbchassis, slot,
                                                  dbslot.machine.label))
        else:
            dbslot = MachineChassisSlot(chassis=dbchassis, slot_number=slot)
        dbmachine.chassis_slot.append(dbslot)

        return
