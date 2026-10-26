from core.node_schema import module_contract
from node_types import pad

(ALLOWED_ATTRIBUTES, ATTRIBUTE_DEFAULTS, ATTRIBUTE_TYPES,
 SYSTEM_MANAGED_ATTRIBUTES) = module_contract("scratchpad")


def render(memory, meta, indent=0, render_child=None):
    lines = [f"{pad(indent)}{meta.get('title') or meta['id']}"]
    for child_id in reversed(meta.get("children", [])):
        if render_child:
            lines.append(render_child(child_id, indent + 1))
    if len(lines) == 1:
        lines.append(f"{pad(indent + 1)}(no jots yet)")
    return "\n\n".join(lines)
