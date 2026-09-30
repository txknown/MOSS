def run(memory, payload, runner=None):
    parent_id = payload.get("parent_id")
    child_id = payload.get("child_id")
    direction = payload.get("direction")
    reference_id = payload.get("reference_id")
    position = payload.get("position")
    if not parent_id:
        raise ValueError("move_child requires parent_id")
    if not child_id:
        raise ValueError("move_child requires child_id")
    before = list(memory.load_meta(parent_id).get("children", []))
    if direction in {"up", "down"}:
        parent = memory.move_child(parent_id, child_id, direction)
        movement = direction
    elif position in {"before", "after"}:
        if not reference_id:
            raise ValueError("move_child requires reference_id")
        parent = memory.move_child_relative(parent_id, child_id, reference_id, position)
        movement = f"{position} {memory.clean_id(reference_id)}"
    elif position in {"top", "bottom"}:
        if reference_id:
            raise ValueError("move_child does not use reference_id for top or bottom")
        parent = memory.move_child_to_edge(parent_id, child_id, position)
        movement = f"to {position}"
    else:
        raise ValueError("move requires up/down, top/bottom, or before/after")
    if parent.get("children", []) == before:
        raise ValueError(f"{memory.clean_id(child_id)} is already in that position")

    return {
        "parent_id": memory.clean_id(parent_id),
        "child_id": memory.clean_id(child_id),
        "direction": direction,
        "position": position,
        "reference_id": memory.clean_id(reference_id) if reference_id else None,
        "log": f"moved {memory.clean_id(child_id)} {movement} in {memory.clean_id(parent_id)}",
    }
