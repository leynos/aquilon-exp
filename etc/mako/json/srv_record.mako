<%namespace name="dns_common" file="/dns_common.mako"/>\
{
    "record_type": "srv_record",
    ${dns_common.dns_record_head(record)}\
    "service": "${record.service}",
    "protocol": "${record.protocol}",
    "priority": "${record.priority}",
    "weight": ${record.weight},
    "target": "${record.target.fqdn + ("" if record.fqdn.dns_environment == record.target.dns_environment else " [environment: " + record.target.dns_environment.name + "]")}",
    "port": "${record.port}",
    ${dns_common.dns_record_tail(record)}\
}
