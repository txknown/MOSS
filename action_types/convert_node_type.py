"""Explicitly convert a node while retaining its stable identity."""

from core.node_schema import attribute_defaults, get_node_schema, get_node_schema_or_none


def run(memory, payload, runner=None):
    if runner is None:
        raise RuntimeError("convert_node_type must run through ActionRunner")
    if not isinstance(payload, dict):
        raise ValueError("convert_node_type requires an object")
    unknown = sorted(set(payload) - {"node_id", "type"})
    if unknown:
        raise ValueError(f"Unknown conversion field: {', '.join(unknown)}")

    node_id = memory.clean_id(payload.get("node_id"))
    new_type = memory.clean_id(payload.get("type"))
    if not node_id or not memory.node_exists(node_id):
        raise FileNotFoundError(f"Node not found: {node_id or '(empty node ID)'}")
    try:
        new_schema = get_node_schema(new_type)
    except KeyError:
        raise ValueError(f"Unknown node type: {new_type or '(empty type)'}") from None

    meta = memory.load_meta(node_id)
    old_type = meta.get("type", "")
    if old_type == new_type:
        return {"node_id": node_id, "old_type": old_type, "type": new_type, "changed": False, "log": None}

    child_types = []
    for child_id in meta.get("children", []):
        if not memory.node_exists(child_id):
            raise ValueError(f"Cannot convert {node_id} while child {child_id} is missing")
        child_types.append(memory.load_meta(child_id).get("type"))
    disallowed = sorted({item for item in child_types if item not in new_schema.allowed_child_types})
    if disallowed:
        raise ValueError(
            f"Cannot convert {node_id} to {new_type} while it contains: {', '.join(disallowed)}"
        )
    if new_schema.content is None and memory.read_content(node_id):
        raise ValueError(f"Cannot convert {node_id} to {new_type} while it has content")

    old_schema = get_node_schema_or_none(old_type)
    new_attribute_names = {item.name for item in new_schema.attributes}
    if old_schema is not None:
        for attribute in old_schema.attributes:
            if attribute.name not in new_attribute_names:
                meta.pop(attribute.name, None)
    meta["type"] = new_type
    for field, default in attribute_defaults(new_type).items():
        meta.setdefault(field, default)
    memory.save_meta(node_id, meta)
    memory.rebuild_registry()
    return {
        "node_id": node_id,
        "old_type": old_type,
        "type": new_type,
        "changed": True,
        "log": f"converted {node_id} from {old_type} to {new_type}",
    }
