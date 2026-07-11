def run(memory, payload, runner=None):
    parent_id = payload.get("parent_id")
    child_id = payload.get("child_id")
    if not parent_id:
        raise ValueError("unlink requires a parent node")
    if not child_id:
        raise ValueError("unlink requires a child node")

    parent_id = memory.clean_id(parent_id)
    child_id = memory.clean_id(child_id)
    memory.remove_child(parent_id, child_id)
    return {
        "parent_id": parent_id,
        "child_id": child_id,
        "log": f"unlinked {child_id} from {parent_id}",
    }
