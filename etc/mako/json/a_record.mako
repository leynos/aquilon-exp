<%namespace name="dns_common" file="/dns_common.mako"/>\
{
    "record_type": "a_record",
    ${dns_common.dns_record_head(record)}\
    "ip": "${record.ip}",
%if record.network:
    "network": "${str(record.network).split(" ")[0]}",
    "netmask": "${str(record.network).split(" ")[1].strip("[]")}",
%endif
    "network_environment": "${record.network.network_environment.name}",
%if record.assignments:
    "assigned_to": "${','.join('%s/%s' % (addr.interface.hardware_entity.label, addr.interface.name) for addr in record.assignments)}",
%endif
%if record.service_addresses:
% for service_address in record.service_addresses:
    "provides": "${format(service_address)}",
    "bound_to": "${format(service_address.holder)}",
% endfor
%endif
%if record.reverse_ptr:
    "reverse_ptr": "${str(record.reverse_ptr)}",
%endif
    ${dns_common.dns_record_tail(record)}\
}
