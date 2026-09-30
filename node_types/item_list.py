from core.node_schema import module_contract
from node_types import pad


(
    ALLOWED_ATTRIBUTES,
    ATTRIBUTE_DEFAULTS,
    ATTRIBUTE_TYPES,
    SYSTEM_MANAGED_ATTRIBUTES,
) = module_contract("item_list")


def render(memory, meta, indent=0, render_child=None):
    lines = [f"{pad(indent)}{meta.get('title') or meta['id']}"]
    if render_child:
        for child_id in meta.get("children", []):
            lines.append(render_child(child_id, indent + 1))
    return "\n".join(lines)
