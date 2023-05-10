{
    "host": "${record.holder.holder_name}",
    "bound_to": "${record.holder.holder_type}",
    "type": "${record.resource_type}",
    "week": "${record.week}",
% if record.time:
    "time": "${record.time}",
% endif
    "day": "${record.day}"
}