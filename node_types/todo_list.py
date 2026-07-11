from node_types import pad


def render(memory, meta, indent=0, render_child=None):
    lines = [f"{pad(indent)}{meta.get('title') or meta['id']}"]
    children = meta.get("children", [])
    if children and render_child:
        for child_id in children:
            lines.append(render_child(child_id, indent + 1))
    else:
        lines.append(f"{pad(indent + 1)}(empty todo list)")
    return "\n".join(lines)
