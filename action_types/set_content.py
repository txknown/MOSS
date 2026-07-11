def run(memory, payload, runner=None):
    node_id = payload.get("node_id")
    text = payload.get("text")
    if not node_id:
        raise ValueError("set requires a selected node")
    if text is None:
        raise ValueError("set requires text")

    memory.write_content(node_id, text)
    return {
        "node_id": memory.clean_id(node_id),
        "log": f"set content of {memory.clean_id(node_id)}",
    }
