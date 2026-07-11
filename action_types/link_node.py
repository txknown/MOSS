def run(memory, payload, runner=None):
    parent_id = payload.get("parent_id")
    child_id = payload.get("child_id")
    if not parent_id:
        raise ValueError("link requires a parent node")
    if not child_id:
        raise ValueError("link requires a child node")

    parent_id = memory.clean_id(parent_id)
    child_id = memory.clean_id(child_id)
    memory.add_child(parent_id, child_id)
    return {
        "parent_id": parent_id,
        "child_id": child_id,
        "log": f"linked {child_id} to {parent_id}",
    }
