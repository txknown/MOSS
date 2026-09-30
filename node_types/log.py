from core.node_schema import module_contract
from node_types import pad


(
    ALLOWED_ATTRIBUTES,
    ATTRIBUTE_DEFAULTS,
    ATTRIBUTE_TYPES,
    SYSTEM_MANAGED_ATTRIBUTES,
) = module_contract("log")


def render(memory, meta, indent=0, render_child=None):
    title = meta.get("title") or meta["id"]
    description = meta.get("description", "")
    prompts = meta.get("prompts") if isinstance(meta.get("prompts"), list) else []
    entries = meta.get("children", [])
    lines = [f"{pad(indent)}{title}"]
    if description:
        lines.append(f"{pad(indent + 1)}{description}")
    lines.append(f"{pad(indent + 1)}{len(prompts)} prompts · {len(entries)} entries")
    return "\n".join(lines)
