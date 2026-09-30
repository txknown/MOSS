from datetime import datetime

from core.node_validation import validate_attribute_values


def run(memory, payload, runner=None):
    node_id = payload.get("node_id")
    field = payload.get("field")
    value = payload.get("value")
    if not node_id:
        raise ValueError("setattr requires a selected node")
    if not field:
        raise ValueError("setattr requires a field")

    meta = memory.load_meta(node_id)
    field = str(field).strip().lower()
    value = validate_attribute_values(meta, {field: value})[field]
    if meta.get("type") == "internal_link" and field == "target_id":
        if not memory.node_exists(value):
            raise FileNotFoundError(f"Internal link target not found: {value}")

    was_checked = meta.get("checked", False) is True
    completed_now = field == "checked" and value is True and not was_checked
    if field == "checked":
        if completed_now:
            meta["date_completed"] = datetime.now().astimezone().strftime("%Y-%m-%d")
        elif value is False:
            meta["date_completed"] = None

    prospective = dict(meta)
    prospective[field] = value
    if prospective.get("type") == "event":
        start_time = prospective.get("start_time")
        end_time = prospective.get("end_time")
        if start_time and end_time and end_time <= start_time:
            raise ValueError("end_time must be later than start_time")

    meta[field] = value
    memory.save_meta(meta["id"], meta)
    memory.rebuild_registry()
    moved_to = []
    if field == "checked" and value is True:
        for parent in memory.parent_metas_for(meta["id"]):
            if parent.get("type") == "todo_list" and memory.move_child_to_bottom(parent["id"], meta["id"]):
                moved_to.append(parent["id"])

    display_value = str(value).lower() if isinstance(value, bool) else value
    message = f"completed {meta['id']}" if completed_now else f"set {field} of {meta['id']} to {display_value}"
    if moved_to:
        moves = "; ".join(f"moved completed {meta['id']} to bottom of {parent_id}" for parent_id in moved_to)
        message = f"{message}; {moves}"
    return {
        "node_id": meta["id"],
        "field": field,
        "log": message,
    }
