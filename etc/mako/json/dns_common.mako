<%def name="dns_record_head(record)">\
"${'fqdn": "{0.fqdn!s}'.format(record)}",
    "dns_environment": "${record.fqdn.dns_environment.name}",
%if record.hardware_entity:
    "primary_name_of": "${record.hardware_entity._get_class_label()}" "${record.hardware_entity.label}",
%endif
## The alias_cnt property can be loaded eagerly, so use it to check the
## presence of aliases before trying to query the alias table itself
%if record.alias_cnt:
    "aliases": ${(",".join(str(a.fqdn) + ("" if a.fqdn.dns_environment == record.fqdn.dns_environment else "[environment: " + a.fqdn.dns_environment.name + "]") for a in record.all_aliases)).split(",")},
%endif
%if record.address_alias_cnt:
    "address_aliases": ${(",".join(str(a.fqdn) + ("" if a.fqdn.dns_environment == record.fqdn.dns_environment else "[environment: " + a.fqdn.dns_environment.name + "]") for a in record.all_address_aliases)).split(",")},
%endif
%if record.ttl:
    "ttl": ${record.ttl},
%endif
%if record.owner_grn:
    "eon_id": ${record.owner_eon_id},
%endif
</%def>
<%def name="dns_record_tail(record)">\
%if record.comments:
"comments": "${record.comments | trim}"
%endif
</%def>
