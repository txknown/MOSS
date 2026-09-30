from node_types import pad
from core.node_schema import module_contract


DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

(
    ALLOWED_ATTRIBUTES,
    ATTRIBUTE_DEFAULTS,
    ATTRIBUTE_TYPES,
    SYSTEM_MANAGED_ATTRIBUTES,
) = module_contract("event")


def render(memory, meta, indent=0, render_child=None):
    title = meta.get("title") or meta["id"]
    lines = [f"{pad(indent)}{title}"]
    lines.append(
        f"{pad(indent + 1)}"
        f"{_time_range(meta.get('day'), meta.get('start_time'), meta.get('end_time'))}"
    )
    description = meta.get("description")
    if description:
        lines.append(f"{pad(indent + 1)}{description}")
    return "\n".join(lines)


def _time_range(day, start_time, end_time):
    day_name = DAY_NAMES[day - 1] if isinstance(day, int) and 1 <= day <= 7 else "Day not set"
    if start_time and end_time:
        return f"{day_name}, {start_time}–{end_time}"
    if start_time:
        return f"{day_name}, starts {start_time}"
    if end_time:
        return f"{day_name}, ends {end_time}"
    return day_name
