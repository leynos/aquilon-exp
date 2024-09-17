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
"""Network formatter."""

from collections import defaultdict
from ipaddress import IPv4Network
from operator import attrgetter

from sqlalchemy.orm import object_session, subqueryload
from sqlalchemy.orm.attributes import set_committed_value

from aquilon.aqdb.model import HardwareEntity, Network
from aquilon.utils import chunk
from aquilon.worker.formats.formatters import ObjectFormatter
from aquilon.worker.formats.list import ListFormatter
from aquilon.worker.formats.service_address import ServiceAddressFormatter


def summarize_ranges(addrlist):
    """ Convert a list like [1,2,3,5] to ["1-3", "5"], but with IP addresses """
    ranges = []
    start = None
    prev_range_class = None
    for addr in addrlist:
        if start is None:
            start = addr.ip
            end = addr.ip
            prev_range_class = addr.range_class
            continue
        if addr.range_class == prev_range_class:
            if int(addr.ip) == int(end) + 1:
                end = addr.ip
                prev_range_class = addr.range_class
                continue
        if start == end:
            ranges.append(f"{start} ({prev_range_class})")
        else:
            ranges.append(f"{start}-{end} ({prev_range_class})")
        start = end = addr.ip
        prev_range_class = addr.range_class
    if start is not None:
        if start == end:
            ranges.append(f"{start} ({prev_range_class})")
        else:
            ranges.append(f"{start}-{end} ({prev_range_class})")

    return ranges


def possible_mac_addresses(interface):
    """ Return the list of MAC addresses the DHCP server should accept.

    There are a couple of cases to consider:

    - 801.q VLANs: the MAC address of the physical interface may appear on
      multiple networks that belong to the different VLANs configured on the
      interface.

    - Bonding devices: during PXE, the bonding is not configured yet, and the
      DHCP server should accept the MAC address of the physical interface(s).
      If the bonding device has a dedicated MAC address configured, then that
      should also be accepted if the host configures the interface using DHCP.
    """

    mac_addrs = []

    # In case of VLANs, just grab the parent interface
    if interface.interface_type == 'vlan':
        interface = interface.parent

    # Bonding/bridge: append the MACs of the physical interfaces
    # TODO: drop the public/bootable check once we decide how to send the extra
    # information to clients
    for slave in interface.all_slaves():
        if slave.mac and (slave.interface_type != "public" or slave.bootable):
            mac_addrs.append(slave.mac)

    # Handle physical interfaces, and bonding with a dedicated MAC
    # TODO: drop the public/bootable check once we decide how to send the extra
    # information to clients
    if interface.mac and (interface.interface_type != "public" or interface.bootable):
        mac_addrs.append(interface.mac)

    return mac_addrs


class NetworkFormatter(ObjectFormatter):
    def format_raw(self, network, indent="", embedded=True,
                   indirect_attrs=True):
        sysloc = network.location.sysloc()
        details = [indent + f"{network:c}: {network.name}"]
        details.append(indent + f"  {network.network_environment:c}: {network.network_environment.name}")
        details.append(indent + f"  IP: {network.network_address}")
        if isinstance(network.network, IPv4Network):
            details.append(indent + f"  Netmask: {network.netmask}")
        else:
            details.append(indent + "  Prefix: %d" % network.cidr)
        details.append(indent + f"  Sysloc: {sysloc}")
        details.append(self.redirect_raw(network.location, indent + "  "))
        details.append(indent + f"  Side: {network.side}")
        details.append(indent + f"  Network Type: {network.network_type}")
        if network.network_compartment:
            details.append(indent + f"  {network.network_compartment:c}: {network.network_compartment.name}")
        if network.comments:
            details.append(indent + f"  Comments: {network.comments}")

        if network.routers:
            routers = ", ".join(sorted(f"{rtr.ip} ({rtr.location})" for rtr in network.routers))
            details.append(indent + f"  Routers: {routers}")

        if network.port_group:
            details.append(indent + f"  Port Group: {network.port_group.name}")

        # Look for dynamic DHCP ranges
        ranges = summarize_ranges(network.dynamic_stubs)
        if ranges:
            details.append(indent + "  Dynamic Ranges: {}".format(", ".join(ranges)))

        for route in sorted(network.static_routes,
                            key=attrgetter('destination', 'gateway_ip')):
            details.append(indent + f"  {route:c}: {route.destination} gateway {route.gateway_ip}")
            if route.personality_stage:
                details.append(
                    indent
                    + f"    {route.personality_stage.personality:c}: {route.personality_stage.personality.name} {route.personality_stage.archetype:c}: {route.personality_stage.archetype.name}"
                )

                if route.personality_stage.staged:
                    details.append(indent + f"      Stage: {route.personality_stage.name}")
            if route.comments:
                details.append(indent + f"    Comments: {route.comments}")

        return "\n".join(details)

    def csv_fields(self, network):
        yield (network.name, network.network_address, network.netmask,
               network.location.sysloc(), network.location.country,
               network.side, network.network_type, network.comments)

    def format_json(self, network, embedded=True, indirect_attrs=True):
        details = {
            "name": network.name,
            "network_type": network.network_type,
            "ip": str(network.network_address) if network.network_address else None,
            "netmask": str(network.netmask) if network.netmask else None,
            "cidr": network.cidr,
            "broadcast_address": str(network.broadcast_address) if network.broadcast_address else None,
            "side": network.side,
            "sysloc": network.location.sysloc(),
            "comments": network.comments,
        }
        if indirect_attrs:
            details.update({"location": self.redirect_json(network.location, embedded=embedded, indirect_attrs=False)})
        return details

    def fill_proto(self, net, skeleton, embedded=True, indirect_attrs=True):
        skeleton.name = net.name
        skeleton.ip = str(net.network_address)
        skeleton.cidr = net.cidr
        skeleton.bcast = str(net.broadcast_address)
        if isinstance(net.network, IPv4Network):
            skeleton.netmask = str(net.netmask)
        if net.side:
            skeleton.side = net.side

        sysloc = net.location.sysloc()
        if sysloc:
            skeleton.sysloc = sysloc

        self.redirect_proto(net.location, skeleton.location,
                            indirect_attrs=False)
        skeleton.type = net.network_type
        skeleton.env_name = net.network_environment.name

        skeleton.routers.extend(str(router.ip) for router in net.routers)
        if net.network_compartment:
            skeleton.compartment = net.network_compartment.name

        for route in sorted(net.static_routes,
                            key=attrgetter('destination', 'gateway_ip')):
            map = skeleton.static_routes.add()
            map.destination = str(route.destination)
            map.gateway_ip = str(route.gateway_ip)
            if route.personality_stage:
                self.redirect_proto(route.personality_stage, map.personality)

        # Look for dynamic DHCP ranges
        range_msg = None
        last_ip = None
        last_range_class = None
        for dynhost in net.dynamic_stubs:
            if not last_ip or dynhost.ip != last_ip + 1 or \
               dynhost.range_class != last_range_class:
                if last_ip:
                    range_msg.end = str(last_ip)
                range_msg = skeleton.dynamic_ranges.add()
                range_msg.start = str(dynhost.ip)
                if dynhost.range_class:
                    range_msg.range_class = str(dynhost.range_class)
            last_ip = dynhost.ip
            last_range_class = dynhost.range_class
        if last_ip:
            range_msg.end = str(last_ip)

ObjectFormatter.handlers[Network] = NetworkFormatter()


class NetworkHostList(list):
    """Holds a list of networks for which a host list will be formatted
    """


class NetworkHostListFormatter(ListFormatter):
    protocol = "aqdnetworks_pb2"

    def format_raw(self, netlist, indent="", embedded=True,
                   indirect_attrs=True):
        details = []

        for network in netlist:
            # we'll get the header from the existing formatter
            nfm = NetworkFormatter()
            details.append(indent + nfm.format_raw(network))

            ips_in_assignments = {}
            for addr in network.assignments:
                iface = addr.interface
                hw_ent = iface.hardware_entity
                if addr.fqdns:
                    names = ", ".join(sorted(str(fqdn) for fqdn in addr.fqdns))
                else:
                    names = "unknown"
                details.append(
                    indent + f"  {hw_ent:c}: {hw_ent.printable_name}, "
                    f"interface: {addr.logical_name}, "
                    f"MAC: {iface.mac}, IP: {addr.ip} ({names})"
                )
                ips_in_assignments[int(addr.ip)] = None

            svc_address_fqdns = list(map(lambda s: s.dns_record.fqdn.fqdn, network.service_addresses))

            for addr in network.dns_records:
                if int(addr.ip) in ips_in_assignments:
                    continue
                if addr.fqdn.fqdn in svc_address_fqdns:
                    continue
                dns_record = indent + f"  {addr._get_class_label()}: {addr.fqdn.fqdn}, IP: {addr.ip}"
                if addr.reverse_ptr is not None:
                    dns_record += f", ReversePTR: {addr.reverse_ptr.fqdn}"
                if addr.ttl is not None:
                    dns_record += f", TTL: {addr.ttl}"
                details.append(dns_record)

        return "\n".join(details)

    def format_proto(self, result, container, embedded=True, indirect_attrs=True):
        for item in result:
            skeleton = container.add()
            handler = NetworkFormatter()
            # Use the standard network formatter to fill in the non-host details
            handler.format_proto(item, skeleton, embedded=embedded,
                                 indirect_attrs=indirect_attrs)
            # Use ourself to fill in all of the assignement information
            self.fill_proto(item, skeleton, embedded=embedded,
                            indirect_attrs=indirect_attrs)

    def fill_proto(self, net, skeleton, embedded=True, indirect_attrs=True):
        # Bulk load information about anything having a network address on this
        # network
        hw_ids = {addr.interface.hardware_entity_id for addr in
                     net.assignments}
        if hw_ids:
            session = object_session(net)
            hwent_by_id = {}
            # aqd runs on 3 different db engines: oracle, postgres and sqlite.
            # The query below filters on a sql "IN" clause of HardwareEntity.id
            # Different engines impose different limits on the number of values
            # allowed inside an "IN" clause, as well as number of SQL variables
            # in a statement.
            # To work around these limits in a fashion compatible with all
            # supported db engines, we chunk the query such that the number of
            # values in the "IN" clause and number of SQL variables in this SQL
            # statement is never larger than 999.
            for hw_ids_chunk in chunk(hw_ids, 999):
                q = session.query(HardwareEntity)
                q = q.filter(HardwareEntity.id.in_(hw_ids_chunk))
                q = q.options(subqueryload('interfaces'),
                              subqueryload('host'),
                              subqueryload('host.personality_stage'),
                              subqueryload('host.operating_system'))
                for dbhwent in q:
                    hwent_by_id[dbhwent.id] = dbhwent

                    iface_by_id = {}
                    slaves_by_id = defaultdict(list)

                    # We have all the interfaces loaded already, so compute the
                    # master/slave relationships to avoid having to touch the
                    # database again
                    for iface in dbhwent.interfaces:
                        iface_by_id[iface.id] = iface
                        if iface.master_id is not None:
                            slaves_by_id[iface.master_id].append(iface)

                    for iface in dbhwent.interfaces:
                        set_committed_value(iface, "master",
                                            iface_by_id.get(
                                                iface.master_id,
                                                None))
                        set_committed_value(iface, "slaves",
                                            slaves_by_id[iface.id])

        # Add interfaces that have addresses in this network
        for addr in net.assignments:
            if not addr.dns_records:
                # hostname is a required field in the protobuf description
                continue

            hwent = addr.interface.hardware_entity

            # DHCP: we do not care about secondary IP addresses, but in some
            # cases the same IP address may show up with different MACs
            if not addr.label:
                mac_addrs = possible_mac_addresses(addr.interface)
            else:
                mac_addrs = []

            # Generate a host record even if there is no known MAC address for
            # it
            if not mac_addrs:
                mac_addrs.append(None)

            # Associating the same IP with multiple MAC addresses is
            # problematic using the current protocol. Sending multiple host
            # messages is easy for the broker, but it can confuse consumers like
            # aqdhcpd. For now just ensure it never happens, and revisit the
            # problem when we have a real world requirement.
            if len(mac_addrs) > 1:
                mac_addrs = [mac_addrs[0]]

            for mac in mac_addrs:
                host_msg = skeleton.hosts.add()

                if addr.interface.interface_type == 'management':
                    host_msg.type = 'manager'
                else:
                    host_msg.type = hwent.hardware_type
                    if hwent.host:
                        # TODO: deprecate host_msg.archetype
                        self.redirect_proto(hwent.host.archetype,
                                            host_msg.archetype,
                                            indirect_attrs=False)
                        self.redirect_proto(hwent.host.personality_stage,
                                            host_msg.personality,
                                            indirect_attrs=False)
                        self.redirect_proto(hwent.host.operating_system,
                                            host_msg.operating_system,
                                            indirect_attrs=False)
                        host_msg.status = hwent.host.status.name

                host_msg.hostname = addr.dns_records[0].fqdn.name
                host_msg.fqdn = str(addr.dns_records[0].fqdn)
                host_msg.dns_domain = addr.dns_records[0].fqdn.dns_domain.name

                host_msg.ip = str(addr.ip)

                if mac:
                    host_msg.mac = str(mac)

                host_msg.machine.name = hwent.label
                self.redirect_proto(hwent.model, host_msg.machine.model)

                # aqdhcpd uses the interface list when excluding hosts it is not
                # authoritative for
                for iface in hwent.interfaces:
                    int_msg = host_msg.machine.interfaces.add()
                    int_msg.device = iface.name
                    if iface.mac:
                        int_msg.mac = str(iface.mac)


ObjectFormatter.handlers[NetworkHostList] = NetworkHostListFormatter()


class NetworkAddressAssignmentList(list):
    """Holds a list of networks for which an address assignment list will be formatted
    """


class NetworkAddressAssignmentFormatter(NetworkHostListFormatter):

    def format_raw(self, netlist, indent="", embedded=True,
                   indirect_attrs=True):
        details = []
        for network in netlist:
            details_str = super().format_raw(netlist=[network], indent=indent, embedded=embedded,
                                                                                    indirect_attrs=indirect_attrs)
            details.extend(details_str.split("\n"))

            for srv in network.service_addresses:
                handler = ServiceAddressFormatter()
                service_addr_list = handler.format_raw(srv).split("\n")
                details.append("  " + ", ".join([srv.strip() for srv in service_addr_list]))

        return "\n".join(details)


    def format_proto(self, result, container, embedded=True, indirect_attrs=True):
        for item in result:
            skeleton = container.add()
            handler = NetworkFormatter()
            # Use the standard network formatter to fill in the non-host details
            handler.format_proto(item, skeleton, embedded=embedded,
                                 indirect_attrs=indirect_attrs)
            # Use ourself to fill in all of the assignement information
            self.fill_proto(item, skeleton, embedded=embedded,
                            indirect_attrs=indirect_attrs)

            for srv in item.service_addresses:
                service_address = skeleton.service_addresses.add()
                handler = ServiceAddressFormatter()
                handler.fill_proto(srv, service_address, embedded=embedded,
                                indirect_attrs=indirect_attrs)


ObjectFormatter.handlers[NetworkAddressAssignmentList] = NetworkAddressAssignmentFormatter()


class NetworkList(list):
    """By convention, holds a list of networks to be formatted as alist"""


class NetworkListFormatter(ListFormatter):
    def format_raw(self, objects, indent="", embedded=True, indirect_attrs=True):
        def sortkey(network):
            return (1 if isinstance(network.network, IPv4Network) else 2,
                    int(network.network_address))

        return "\n".join(indent + str(network.network)
                         for network in sorted(objects, key=sortkey))

ObjectFormatter.handlers[NetworkList] = NetworkListFormatter()
