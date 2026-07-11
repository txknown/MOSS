from node_types import content, indent_text, pad


def render(memory, meta, indent=0, render_child=None):
    title = meta.get("title") or meta["id"]
    lines = [
        f"{pad(indent)}{title}",
        f"{pad(indent)}{'=' * max(len(title), 4)}",
    ]

    body = content(memory, meta)
    if body:
        lines.append("")
        lines.append(indent_text(body, indent))

    children = meta.get("children", [])
    if children and render_child:
        lines.append("")
        for child_id in children:
            try:
                child = memory.load_meta(child_id)
            except FileNotFoundError:
                lines.append(f"{pad(indent)}- Missing child node.")
                continue

            if child.get("type") == "page":
                lines.append(f"{pad(indent)}[page] {child.get('title') or child['id']}")
            else:
                lines.append(render_child(child_id, indent))

    return "\n".join(lines).rstrip()
