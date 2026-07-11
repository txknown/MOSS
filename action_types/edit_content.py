import os
import subprocess


def run(memory, payload, runner=None):
    node_id = payload.get("node_id")
    if not node_id:
        raise ValueError("edit requires a selected node")

    path = memory.content_path(node_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("", encoding="utf-8")

    editor = os.environ.get("EDITOR")
    if editor:
        before = path.read_text(encoding="utf-8")
        subprocess.run([editor, str(path)], check=False)
        after = path.read_text(encoding="utf-8")
        if before != after:
            meta = memory.load_meta(node_id)
            memory.save_meta(meta["id"], meta)
            return {"path": str(path), "log": f"edited {memory.clean_id(node_id)}"}

    return {"path": str(path), "log": f"opened {memory.clean_id(node_id)} for editing"}
