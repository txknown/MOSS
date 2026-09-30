from datetime import date, timedelta

from node_types import pad
from core.node_schema import module_contract


(
    ALLOWED_ATTRIBUTES,
    ATTRIBUTE_DEFAULTS,
    ATTRIBUTE_TYPES,
    SYSTEM_MANAGED_ATTRIBUTES,
) = module_contract("week")


def render(memory, meta, indent=0, render_child=None):
    title = meta.get("title") or _date_range(meta.get("start_date")) or meta["id"]
    lines = [f"{pad(indent)}{title}"]
    children = meta.get("children", [])
    if children and render_child:
        for child_id in children:
            try:
                child = memory.load_meta(child_id)
            except FileNotFoundError:
                lines.append(f"{pad(indent + 1)}- Missing event node.")
                continue
            if child.get("type") == "event":
                lines.append(render_child(child_id, indent + 1))
    if len(lines) == 1:
        lines.append(f"{pad(indent + 1)}(no events)")
    return "\n".join(lines)


def _date_range(value):
    try:
        start = date.fromisoformat(str(value))
    except ValueError:
        return ""
    end = start + timedelta(days=6)
    if start.year == end.year:
        return f"Week of {start.strftime('%b')} {start.day} – {end.strftime('%b')} {end.day}, {end.year}"
    return f"Week of {start.strftime('%b')} {start.day}, {start.year} – {end.strftime('%b')} {end.day}, {end.year}"
