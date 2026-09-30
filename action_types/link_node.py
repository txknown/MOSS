from core.node_schema import get_node_schema_or_none


def run(memory, payload, runner=None):
    parent_id = payload.get("parent_id")
    child_id = payload.get("child_id")
    if not parent_id:
        raise ValueError("link requires a parent node")
    if not child_id:
        raise ValueError("link requires a child node")

    parent_id = memory.clean_id(parent_id)
    child_id = memory.clean_id(child_id)
    parent = memory.load_meta(parent_id)
    child = memory.load_meta(child_id)
    parent_schema = get_node_schema_or_none(parent.get("type"))
    if parent_schema is not None and child.get("type") not in parent_schema.allowed_child_types:
        allowed = ", ".join(parent_schema.allowed_child_types) or "(none)"
        raise ValueError(
            f"Cannot link {child.get('type', 'node')} inside {parent.get('type', 'node')}. "
            f"Allowed child types: {allowed}"
        )
    if child.get("type") == "item" and parent.get("type") == "item_list":
        existing_lists = [
            item["id"]
            for item in memory.parent_metas_for(child_id)
            if item.get("type") == "item_list" and item["id"] != parent_id
        ]
        if existing_lists:
            raise ValueError(
                f"Item {child_id} already belongs to item list {existing_lists[0]}"
            )
    if child_id in parent.get("children", []):
        raise ValueError(f"{child_id} is already linked to {parent_id}")
    memory.add_child(parent_id, child_id)
    return {
        "parent_id": parent_id,
        "child_id": child_id,
        "log": f"linked {child_id} to {parent_id}",
    }
