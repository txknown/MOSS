from node_types import content, pad


def render(memory, meta, indent=0, render_child=None):
    source = content(memory, meta) or meta.get("source") or "No image source yet."
    title = meta.get("title") or "Image"
    return f"{pad(indent)}{title}\n{pad(indent)}{source}"
