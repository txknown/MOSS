"""Validate, snapshot, create, and link one log entry atomically."""

from core.logs import entry_date_for, validate_log_answers, validate_log_prompts
from core.node_schema import get_node_schema


def run(memory, payload, runner=None):
    if runner is None:
        raise RuntimeError("submit_log_entry must run through ActionRunner")
    if not isinstance(payload, dict):
        raise ValueError("submit_log_entry requires an object")
    unknown = sorted(set(payload) - {"log_id", "answers"})
    if unknown:
        raise ValueError(f"Unknown log entry field: {', '.join(unknown)}")

    log_id = memory.clean_id(payload.get("log_id"))
    if not log_id or not memory.node_exists(log_id):
        raise FileNotFoundError(f"Log not found: {log_id or '(empty log ID)'}")
    log_meta = memory.load_meta(log_id)
    if log_meta.get("type") != "log":
        raise ValueError(f"Entries can only be started from a log node: {log_id}")
    if "log_entry" not in get_node_schema("log").allowed_child_types:
        raise RuntimeError("The log schema does not permit log entry children.")

    prompts = validate_log_prompts(log_meta.get("prompts"))
    answers = validate_log_answers(prompts, payload.get("answers"))
    entry_date = entry_date_for(prompts, answers)
    entry_id = None
    try:
        entry_id = runner.run("create_node", {"type": "log_entry"}, log=False)["node_id"]
        entry_meta = memory.load_meta(entry_id)
        entry_meta.update(
            {
                "log_id": log_id,
                "entry_date": entry_date,
                "submitted_at": memory.now(),
                "prompts": prompts,
                "answers": answers,
            }
        )
        memory.save_meta(entry_id, entry_meta)
        runner.run(
            "link_node",
            {"parent_id": log_id, "child_id": entry_id},
            log=False,
        )
    except Exception:
        if entry_id and memory.node_exists(entry_id):
            runner.run("trash_node", {"node_id": entry_id}, log=False)
        raise

    entry_label = entry_date or entry_id
    return {
        "node_id": entry_id,
        "parent_id": log_id,
        "log": f"submitted {log_id} entry {entry_id}: {entry_label}",
    }
