{
    "host": "${record.holder.holder_name}",
    "bound_to": "${record.holder.holder_type}",
    "type": "${record.resource_type}",
% if record.reason:
    "reason": "${record.reason | trim}",
% endif
    "start_date": "${record.start_date}",
    "expiry_date": "${record.expiry_date}"
}