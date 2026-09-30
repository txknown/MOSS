from node_types import content, indent_text, pad
from core.node_schema import module_contract


(
    ALLOWED_ATTRIBUTES,
    ATTRIBUTE_DEFAULTS,
    ATTRIBUTE_TYPES,
    SYSTEM_MANAGED_ATTRIBUTES,
) = module_contract("note")


def render(memory, meta, indent=0, render_child=None):
    title = meta.get("title") or meta["id"]
    body = content(memory, meta)
    lines = [f"{pad(indent)}{title}"]
    if body:
        labels = []
        if meta.get("size"):
            labels.append(str(meta["size"]))
        if meta.get("font"):
            labels.append(str(meta["font"]))
        if meta.get("align") in {"left", "center", "right"}:
            labels.append(meta["align"])
        if meta.get("color"):
            labels.append(str(meta["color"]))
        if labels:
            body = f"[{', '.join(labels)}]\n{body}"
        lines.extend(["", indent_text(body, indent)])
    return "\n".join(lines)
