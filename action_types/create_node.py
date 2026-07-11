from core.registry import known_node_types


def run(memory, payload, runner=None):
    node_type = payload.get("type")
    node_id = payload.get("id")
    if not node_type:
        raise ValueError("new requires a node type")
    if node_type not in known_node_types():
        raise ValueError(f"Unknown node type: {node_type}")

    meta = memory.create_node(node_type, node_id=node_id, content=payload.get("content", ""))
    return {
        "node_id": meta["id"],
        "log": f"created node {meta['id']}",
    }
