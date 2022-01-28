{
    "record_type": "ns_record",
    "dns_domain": "${record.dns_domain.name}",
    "name_server": "${record.a_record.fqdn}",
% if record.comments:
    "comments": "${record.comments}"
% endif
}