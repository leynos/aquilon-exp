<%namespace name="dns_common" file="/dns_common.mako"/>\
{
    "record_type": "alias",
    ${dns_common.dns_record_head(record)}\
    "target": "${record.target.fqdn + ("" if record.fqdn.dns_environment == record.target.dns_environment else " [environment: " + record.target.dns_environment.name + "]") }",
%if record.services_provided:
%  for srv in record.services_provided:
    "provides_service": "${srv.service_instance.service.name}",
    "instance": "${srv.service_instance.name}",
%  endfor
%endif
    ${dns_common.dns_record_tail(record)}\
}
