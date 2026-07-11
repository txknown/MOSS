from core import registry


def render_node(memory, node_id, indent=0):
    try:
        meta = memory.load_meta(node_id)
    except FileNotFoundError:
        return f"{'  ' * indent}- Missing node."

    node_type = meta.get("type", "text")
    try:
        module = registry.load_node_type(node_type)
    except KeyError:
        return _render_fallback(memory, meta, indent)

    return module.render(
        memory,
        meta,
        indent=indent,
        render_child=lambda child_id, child_indent=indent: render_node(memory, child_id, child_indent),
    )


def _render_fallback(memory, meta, indent):
    pad = "  " * indent
    content = memory.read_content(meta["id"]).strip()
    title = meta.get("title") or meta.get("id", "node")
    lines = [f"{pad}{title}"]
    if content:
        lines.append(_indent_text(content, indent))
    return "\n".join(lines)


def _indent_text(text, indent):
    pad = "  " * indent
    return "\n".join(f"{pad}{line}" for line in text.splitlines())
