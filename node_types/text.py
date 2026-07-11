from node_types import content, indent_text


def render(memory, meta, indent=0, render_child=None):
    body = content(memory, meta) or "(empty text)"
    align = meta.get("align")
    color = meta.get("color")
    size = meta.get("size")

    labels = []
    if size in {"small", "medium", "large"}:
        labels.append(size)
    if align in {"left", "center", "right"}:
        labels.append(align)
    if color:
        labels.append(str(color))

    if labels:
        body = f"[{', '.join(labels)}]\n{body}"

    return indent_text(body, indent) if indent else body
