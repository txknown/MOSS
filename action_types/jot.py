"""Save a scratchpad jot as an ordinary text child, preserving exact wording."""
from core.node_validation import validate_content


def run(memory, payload, runner=None):
    if runner is None:
        raise RuntimeError("jot must run through ActionRunner")
    if not isinstance(payload, dict) or set(payload) - {"parent_id", "content"}:
        raise ValueError("jot requires parent_id and content")
    parent_id = memory.clean_id(payload.get("parent_id"))
    if not memory.node_exists(parent_id) or memory.load_meta(parent_id).get("type") != "scratchpad":
        raise ValueError("Jots require a scratchpad parent")
    content = validate_content(payload.get("content"))
    if not content.strip():
        raise ValueError("Write something before saving a jot")
    result = runner.run("create_child", {
        "parent_id": parent_id, "type": "text", "content": content,
    }, log=False)
    return {**result, "log": f"saved jot {result['node_id']} in {parent_id}"}
