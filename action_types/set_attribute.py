def run(memory, payload, runner=None):
    node_id = payload.get("node_id")
    field = payload.get("field")
    value = payload.get("value")
    if not node_id:
        raise ValueError("setattr requires a selected node")
    if not field:
        raise ValueError("setattr requires a field")

    meta = memory.set_attribute(node_id, field, value)
    return {
        "node_id": meta["id"],
        "field": field,
        "log": f"set {field} of {meta['id']} to {str(value).lower() if isinstance(value, bool) else value}",
    }
