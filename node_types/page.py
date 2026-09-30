from node_types import pad
from core.node_schema import module_contract


(
    ALLOWED_ATTRIBUTES,
    ATTRIBUTE_DEFAULTS,
    ATTRIBUTE_TYPES,
    SYSTEM_MANAGED_ATTRIBUTES,
) = module_contract("page")


def render(memory, meta, indent=0, render_child=None):
    title = meta.get("title") or meta["id"]
    heading = f"{pad(indent)}{title}"
    description = meta.get("description", "")
    if description and meta.get("description_visible", True) is True:
        heading = f"{heading}\n{pad(indent)}{description}"
    blocks = [heading]

    children = meta.get("children", [])
    if children and render_child:
        for child_id in children:
            try:
                child = memory.load_meta(child_id)
            except FileNotFoundError:
                blocks.append(f"{pad(indent + 1)}- Missing child node.")
                continue

            if child.get("type") == "page":
                card = f"{pad(indent + 1)}[page] {child.get('title') or child['id']}"
                child_description = child.get("description", "")
                if child_description and child.get("description_visible", True) is True:
                    card = f"{card}\n{pad(indent + 2)}{child_description}"
                blocks.append(card)
            elif child.get("type") == "note":
                blocks.append(f"{pad(indent + 1)}[note] {child.get('title') or child['id']}")
            else:
                blocks.append(render_child(child_id, indent + 1))

    return "\n\n".join(blocks).rstrip()
