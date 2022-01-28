<%namespace name="dns_common" file="/dns_common.mako"/>\
{
    "record_type": "address_alias",
    ${dns_common.dns_record_head(record)}\
    "target": "${(record.target.fqdn + " [" + str(record.target_ip) + ("" if record.fqdn.dns_environment == record.target.dns_environment else ", environment: " + record.target.dns_environment.name) + "]").split(" ")[0]}",
    "ip": "${(record.target.fqdn + " [" + str(record.target_ip) + ("" if record.fqdn.dns_environment == record.target.dns_environment else ", environment: " + record.target.dns_environment.name) + "]").split(" ")[1].strip("[]")}",
    ${dns_common.dns_record_tail(record)}\
}
