"""Replace an item list's field definition and reshape every existing item."""

from core.items import safe_item_values, validate_item_fields


def run(memory, payload, runner=None):
    if not isinstance(payload, dict):
        raise ValueError("update_item_list_fields requires an object")
    unknown = sorted(set(payload) - {"node_id", "fields"})
    if unknown:
        raise ValueError(f"Unknown item-list field: {', '.join(unknown)}")

    node_id = memory.clean_id(payload.get("node_id"))
    if not node_id or not memory.node_exists(node_id):
        raise FileNotFoundError(f"Item list not found: {node_id or '(empty node ID)'}")
    meta = memory.load_meta(node_id)
    if meta.get("type") != "item_list":
        raise ValueError(f"Fields can only be set on item lists: {node_id}")

    fields = validate_item_fields(payload.get("fields"))
    item_metas = []
    for child_id in meta.get("children", []):
        child = memory.load_meta(child_id)
        if child.get("type") != "item":
            raise ValueError(f"Item list {node_id} contains non-item child {child_id}")
        child["values"] = safe_item_values(fields, child.get("values"))
        item_metas.append(child)

    if meta.get("fields") == fields and all(
        memory.load_meta(item["id"]).get("values") == item["values"]
        for item in item_metas
    ):
        return {"node_id": node_id, "changed": False, "log": None}

    original = {node_id: memory.meta_path(node_id).read_bytes()}
    original.update({item["id"]: memory.meta_path(item["id"]).read_bytes() for item in item_metas})
    try:
        meta["fields"] = fields
        memory.save_meta(node_id, meta)
        for item in item_metas:
            memory.save_meta(item["id"], item)
        memory.rebuild_registry()
    except Exception:
        for current_id, raw in original.items():
            memory.meta_path(current_id).write_bytes(raw)
        memory.rebuild_registry()
        raise
    return {
        "node_id": node_id,
        "changed": True,
        "log": f"updated item-list fields {node_id}",
    }
