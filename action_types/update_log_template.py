"""Replace a log's future prompt template without touching prior entries."""

from core.logs import validate_log_prompts


def run(memory, payload, runner=None):
    if runner is None:
        raise RuntimeError("update_log_template must run through ActionRunner")
    if not isinstance(payload, dict):
        raise ValueError("update_log_template requires an object")
    unknown = sorted(set(payload) - {"node_id", "prompts"})
    if unknown:
        raise ValueError(f"Unknown log template field: {', '.join(unknown)}")

    node_id = memory.clean_id(payload.get("node_id"))
    if not node_id or not memory.node_exists(node_id):
        raise FileNotFoundError(f"Log not found: {node_id or '(empty log ID)'}")
    meta = memory.load_meta(node_id)
    if meta.get("type") != "log":
        raise ValueError(f"Log templates can only be set on log nodes: {node_id}")

    prompts = validate_log_prompts(payload.get("prompts"))
    if meta.get("prompts") == prompts:
        return {"node_id": node_id, "changed": False, "log": None}
    meta["prompts"] = prompts
    memory.save_meta(node_id, meta)
    memory.rebuild_registry()
    return {
        "node_id": node_id,
        "changed": True,
        "log": f"updated log template {node_id}",
    }
