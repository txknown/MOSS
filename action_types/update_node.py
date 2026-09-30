"""Update one node through a single, meaningful MOSS action."""

from core.node_schema import CONTENT_MAX_LENGTH
from core.node_validation import validate_attribute_values, validate_content


MAX_CONTENT_LENGTH = CONTENT_MAX_LENGTH
def run(memory, payload, runner=None):
    if runner is None:
        raise RuntimeError("update_node must run through ActionRunner")
    if not isinstance(payload, dict):
        raise ValueError("update_node requires an object")
    unknown = sorted(set(payload) - {"node_id", "attributes", "content"})
    if unknown:
        raise ValueError(f"Unknown update field: {', '.join(unknown)}")

    node_id = memory.clean_id(payload.get("node_id"))
    if not node_id or not memory.node_exists(node_id):
        raise FileNotFoundError(f"Node not found: {node_id or '(empty node ID)'}")
    meta = memory.load_meta(node_id)
    attributes = validate_attribute_values(meta, payload.get("attributes", {}))

    has_content = "content" in payload
    content = payload.get("content")
    if has_content:
        content = validate_content(content)

    changed_attributes = {
        field: value
        for field, value in attributes.items()
        if meta.get(field) != value
    }
    content_changed = has_content and memory.read_content(node_id) != content
    if not changed_attributes and not content_changed:
        return {"node_id": node_id, "changed": [], "log": None}

    if content_changed:
        runner.run(
            "set_content",
            {"node_id": node_id, "text": content},
            log=False,
        )

    ordered_fields = list(changed_attributes)
    if meta.get("type") == "event" and {"start_time", "end_time"}.issubset(changed_attributes):
        ordered_fields = [
            field for field in ordered_fields if field not in {"start_time", "end_time"}
        ]
        if changed_attributes["start_time"] < (meta.get("end_time") or ""):
            ordered_fields.extend(["start_time", "end_time"])
        else:
            ordered_fields.extend(["end_time", "start_time"])

    for field in ordered_fields:
        runner.run(
            "set_attribute",
            {"node_id": node_id, "field": field, "value": changed_attributes[field]},
            log=False,
        )

    changed = (["content"] if content_changed else []) + list(changed_attributes)
    if changed == ["checked"]:
        message = f"{'completed' if changed_attributes['checked'] else 'reopened'} {node_id}"
    else:
        message = f"updated {node_id}: {', '.join(changed)}"
    return {"node_id": node_id, "changed": changed, "log": message}
