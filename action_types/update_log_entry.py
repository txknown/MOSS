"""Correct an existing entry against its original prompt snapshot."""

from core.logs import entry_date_for, validate_log_answers, validate_log_prompts


def run(memory, payload, runner=None):
    if runner is None:
        raise RuntimeError("update_log_entry must run through ActionRunner")
    if not isinstance(payload, dict):
        raise ValueError("update_log_entry requires an object")
    unknown = sorted(set(payload) - {"node_id", "answers"})
    if unknown:
        raise ValueError(f"Unknown log entry field: {', '.join(unknown)}")

    node_id = memory.clean_id(payload.get("node_id"))
    if not node_id or not memory.node_exists(node_id):
        raise FileNotFoundError(f"Log entry not found: {node_id or '(empty entry ID)'}")
    meta = memory.load_meta(node_id)
    if meta.get("type") != "log_entry":
        raise ValueError(f"Log entry answers can only be set on log entry nodes: {node_id}")

    prompts = validate_log_prompts(meta.get("prompts"))
    answers = validate_log_answers(prompts, payload.get("answers"))
    entry_date = entry_date_for(prompts, answers)
    if meta.get("answers") == answers and meta.get("entry_date", "") == entry_date:
        return {"node_id": node_id, "changed": False, "log": None}
    meta["answers"] = answers
    meta["entry_date"] = entry_date
    memory.save_meta(node_id, meta)
    memory.rebuild_registry()
    return {
        "node_id": node_id,
        "changed": True,
        "log": f"updated log entry {node_id}",
    }
