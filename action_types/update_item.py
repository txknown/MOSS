"""Update an item against the shared field structure of its one item list."""

from core.items import safe_item_fields, validate_item_values


def run(memory, payload, runner=None):
    if not isinstance(payload, dict):
        raise ValueError("update_item requires an object")
    unknown = sorted(set(payload) - {"node_id", "title", "values"})
    if unknown:
        raise ValueError(f"Unknown item field: {', '.join(unknown)}")

    node_id = memory.clean_id(payload.get("node_id"))
    if not node_id or not memory.node_exists(node_id):
        raise FileNotFoundError(f"Item not found: {node_id or '(empty node ID)'}")
    meta = memory.load_meta(node_id)
    if meta.get("type") != "item":
        raise ValueError(f"Item values can only be set on item nodes: {node_id}")

    parents = [
        parent for parent in memory.parent_metas_for(node_id)
        if parent.get("type") == "item_list"
    ]
    if len(parents) != 1:
        raise ValueError(f"{node_id} must belong to exactly one item list")
    fields = safe_item_fields(parents[0].get("fields"))

    title = payload.get("title", meta.get("title"))
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Item title is required")
    title = title.strip()
    if len(title) > 160:
        raise ValueError("Item title must be 160 characters or fewer")
    values = validate_item_values(fields, payload.get("values", meta.get("values", {})))

    if meta.get("title") == title and meta.get("values") == values:
        return {"node_id": node_id, "changed": False, "log": None}
    meta["title"] = title
    meta["values"] = values
    memory.save_meta(node_id, meta)
    memory.rebuild_registry()
    return {
        "node_id": node_id,
        "changed": True,
        "log": f"updated item {node_id}",
    }
