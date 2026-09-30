from core.logs import safe_log_answers, safe_log_prompts
from core.node_schema import module_contract
from node_types import pad


(
    ALLOWED_ATTRIBUTES,
    ATTRIBUTE_DEFAULTS,
    ATTRIBUTE_TYPES,
    SYSTEM_MANAGED_ATTRIBUTES,
) = module_contract("log_entry")


def render(memory, meta, indent=0, render_child=None):
    prompts = safe_log_prompts(meta.get("prompts"))
    answers = safe_log_answers(prompts, meta.get("answers"))
    title = meta.get("entry_date") or meta["id"]
    lines = [f"{pad(indent)}{title}"]
    for prompt in prompts:
        value = answers.get(prompt["id"], "")
        lines.append(f"{pad(indent + 1)}{prompt['label']}: {value or '—'}")
    return "\n".join(lines)
