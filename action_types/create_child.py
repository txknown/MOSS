"""Create and link a child node as one MOSS action."""

from core.node_schema import attribute_defaults, get_node_schema_or_none
from core.node_validation import validate_attribute_values, validate_content


def run(memory, payload, runner=None):
    if runner is None:
        raise RuntimeError("create_child must run through ActionRunner")
    if not isinstance(payload, dict):
        raise ValueError("create_child requires an object")
    unknown = sorted(set(payload) - {"parent_id", "type", "id", "content", "attributes"})
    if unknown:
        raise ValueError(f"Unknown child field: {', '.join(unknown)}")

    parent_id = memory.clean_id(payload.get("parent_id"))
    if not parent_id or not memory.node_exists(parent_id):
        raise FileNotFoundError(f"Parent not found: {parent_id or '(empty node ID)'}")
    parent = memory.load_meta(parent_id)
    parent_schema = get_node_schema_or_none(parent.get("type"))
    allowed_types = set(parent_schema.generic_child_types()) if parent_schema else set()
    node_type = memory.clean_id(payload.get("type"))
    if node_type not in allowed_types:
        allowed_text = ", ".join(sorted(allowed_types)) if allowed_types else "(none)"
        raise ValueError(
            f"Cannot create {node_type or '(empty type)'} inside {parent.get('type', 'node')}. "
            f"Allowed child types: {allowed_text}"
        )

    content = validate_content(payload.get("content", ""))

    prospective = {
        "type": node_type,
        **attribute_defaults(node_type),
    }
    attributes = validate_attribute_values(prospective, payload.get("attributes", {}))
    node_schema = get_node_schema_or_none(node_type)
    missing_required = [
        item.name
        for item in node_schema.attributes
        if item.required and item.name not in attributes and not item.has_default
    ]
    if missing_required:
        raise ValueError(f"Required child attributes: {', '.join(missing_required)}")
    requested_id = payload.get("id")
    if requested_id is not None and not isinstance(requested_id, str):
        raise ValueError("id must be text")

    node_id = None
    try:
        node_id = runner.run(
            "create_node",
            {"type": node_type, "id": requested_id, "content": content},
            log=False,
        )["node_id"]
        for field, value in attributes.items():
            runner.run(
                "set_attribute",
                {"node_id": node_id, "field": field, "value": value},
                log=False,
            )
        runner.run(
            "link_node",
            {"parent_id": parent_id, "child_id": node_id},
            log=False,
        )
    except Exception:
        if node_id and memory.node_exists(node_id):
            runner.run("trash_node", {"node_id": node_id}, log=False)
        raise

    return {
        "node_id": node_id,
        "parent_id": parent_id,
        "log": f"created {node_type} {node_id} in {parent_id}",
    }
