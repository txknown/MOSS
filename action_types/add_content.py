def run(memory, payload, runner=None):
    node_id = payload.get("node_id")
    text = payload.get("text")
    if not node_id:
        raise ValueError("add requires a selected node")
    if text is None:
        raise ValueError("add requires text")

    memory.add_content(node_id, text)
    return {
        "node_id": memory.clean_id(node_id),
        "log": f"added content to {memory.clean_id(node_id)}",
    }
