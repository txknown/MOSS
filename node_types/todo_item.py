from node_types import content, pad
from core.node_schema import module_contract


(
    ALLOWED_ATTRIBUTES,
    ATTRIBUTE_DEFAULTS,
    ATTRIBUTE_TYPES,
    SYSTEM_MANAGED_ATTRIBUTES,
) = module_contract("todo_item")


def render(memory, meta, indent=0, render_child=None):
    checked = meta.get("checked")
    is_checked = checked is True or (isinstance(checked, str) and checked.lower() in {"true", "1"})
    mark = "[x]" if is_checked else "[ ]"
    text = content(memory, meta) or meta.get("title") or meta["id"]
    lines = [f"{pad(indent)}{mark} {text}"]
    if render_child:
        for child_id in meta.get("children", []):
            try:
                child = memory.load_meta(child_id)
            except FileNotFoundError:
                lines.append(f"{pad(indent + 1)}- Missing child todo.")
                continue
            if child.get("type") == "todo_item":
                lines.append(render_child(child_id, indent + 1))
    return "\n".join(lines)
