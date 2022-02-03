<%namespace name="dns_common" file="/dns_common.mako"/>\
{
    "record_type": "dns_record",
    ${dns_common.dns_record_head(record)}\
    ${dns_common.dns_record_tail(record)}\
}
