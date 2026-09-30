from node_types import content, indent_text
from core.node_schema import module_contract


(
    ALLOWED_ATTRIBUTES,
    ATTRIBUTE_DEFAULTS,
    ATTRIBUTE_TYPES,
    SYSTEM_MANAGED_ATTRIBUTES,
) = module_contract("text")


def render(memory, meta, indent=0, render_child=None):
    body = content(memory, meta) or "(empty text)"
    align = meta.get("align")
    color = meta.get("color")
    font = meta.get("font")
    size = meta.get("size")

    labels = []
    if size:
        labels.append(str(size))
    if font:
        labels.append(str(font))
    if align in {"left", "center", "right"}:
        labels.append(align)
    if color:
        labels.append(str(color))

    if labels:
        body = f"[{', '.join(labels)}]\n{body}"

    return indent_text(body, indent) if indent else body
