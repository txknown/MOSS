def run(memory, payload, runner=None):
    parent_id = payload.get("parent_id")
    child_id = payload.get("child_id")
    direction = payload.get("direction")
    if not parent_id:
        raise ValueError("move_child requires parent_id")
    if not child_id:
        raise ValueError("move_child requires child_id")
    if direction not in {"up", "down"}:
        raise ValueError("direction must be up or down")

    memory.move_child(parent_id, child_id, direction)
    return {
        "parent_id": memory.clean_id(parent_id),
        "child_id": memory.clean_id(child_id),
        "direction": direction,
        "log": f"moved {memory.clean_id(child_id)} {direction} in {memory.clean_id(parent_id)}",
    }
