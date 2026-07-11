from node_types import content, pad


def render(memory, meta, indent=0, render_child=None):
    mark = "[x]" if meta.get("checked") else "[ ]"
    text = content(memory, meta) or meta.get("title") or meta["id"]
    return f"{pad(indent)}{mark} {text}"
