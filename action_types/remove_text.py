"""Permanently delete a confirmed scratchpad text child."""


def run(memory, payload, runner=None):
    if runner is None:
        raise RuntimeError("remove_text must run through ActionRunner")
    if not isinstance(payload, dict) or set(payload) - {"parent_id", "node_id", "confirm_id"}:
        raise ValueError("remove_text requires parent_id, node_id, and confirm_id")
    parent_id = memory.clean_id(payload.get("parent_id"))
    node_id = memory.clean_id(payload.get("node_id"))
    if not node_id or payload.get("confirm_id") != node_id:
        raise ValueError("Confirm the exact text node ID")
    if not memory.node_exists(parent_id) or not memory.node_exists(node_id):
        raise ValueError("Text or parent node is missing")
    if memory.load_meta(node_id).get("type") != "text":
        raise ValueError("Only text nodes can be removed with remove_text")
    if memory.load_meta(parent_id).get("type") != "scratchpad":
        raise ValueError("Jot deletion requires a scratchpad parent")
    if node_id not in memory.load_meta(parent_id).get("children", []):
        raise ValueError("Text is not a child of this parent")
    runner.run("trash_node", {"node_id": node_id}, log=False)
    operation = "deleted"
    return {"parent_id": parent_id, "removed_id": node_id, "operation": operation,
            "log": f"{operation} text {node_id} from {parent_id}"}
