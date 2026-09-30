from node_types import pad
from core.node_schema import module_contract


(
    ALLOWED_ATTRIBUTES,
    ATTRIBUTE_DEFAULTS,
    ATTRIBUTE_TYPES,
    SYSTEM_MANAGED_ATTRIBUTES,
) = module_contract("todo_list")


def render(memory, meta, indent=0, render_child=None):
    lines = [f"{pad(indent)}{meta.get('title') or meta['id']}"]
    children = meta.get("children", [])
    if children and render_child:
        for child_id in children:
            try:
                child = memory.load_meta(child_id)
            except FileNotFoundError:
                lines.append(f"{pad(indent + 1)}- Missing child node.")
                continue
            if child.get("type") == "todo_item":
                lines.append(render_child(child_id, indent + 1))
    return "\n".join(lines)
