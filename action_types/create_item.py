"""Create one item whose values follow its parent item list's fields."""

from core.items import safe_item_fields, validate_item_values


def run(memory, payload, runner=None):
    if runner is None:
        raise RuntimeError("create_item must run through ActionRunner")
    if not isinstance(payload, dict):
        raise ValueError("create_item requires an object")
    unknown = sorted(set(payload) - {"parent_id", "id", "title", "values"})
    if unknown:
        raise ValueError(f"Unknown item field: {', '.join(unknown)}")

    parent_id = memory.clean_id(payload.get("parent_id"))
    if not parent_id or not memory.node_exists(parent_id):
        raise FileNotFoundError(f"Item list not found: {parent_id or '(empty node ID)'}")
    parent = memory.load_meta(parent_id)
    if parent.get("type") != "item_list":
        raise ValueError(f"Items can only be created in item lists: {parent_id}")

    title = payload.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Item title is required")
    title = title.strip()
    if len(title) > 160:
        raise ValueError("Item title must be 160 characters or fewer")
    fields = safe_item_fields(parent.get("fields"))
    values = validate_item_values(fields, payload.get("values", {}))

    node_id = None
    try:
        node_id = runner.run(
            "create_node",
            {"type": "item", "id": payload.get("id"), "content": ""},
            log=False,
        )["node_id"]
        meta = memory.load_meta(node_id)
        meta["title"] = title
        meta["values"] = values
        memory.save_meta(node_id, meta)
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
        "log": f"created item {node_id} in {parent_id}",
    }
