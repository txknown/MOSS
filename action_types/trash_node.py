def run(memory, payload, runner=None):
    if not isinstance(payload, dict):
        raise ValueError("trash_node requires an object")
    unknown = sorted(set(payload) - {"node_id"})
    if unknown:
        raise ValueError(f"Unknown delete field: {', '.join(unknown)}")
    node_id = memory.clean_id(payload.get("node_id"))
    if not node_id or not memory.node_exists(node_id):
        raise FileNotFoundError(f"Node not found: {node_id or '(empty node ID)'}")

    memory.trash_node(node_id)
    return {
        "node_id": node_id,
        "deleted": True,
        "log": f"deleted node {node_id}",
    }
