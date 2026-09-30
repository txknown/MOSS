import os
import platform
import shlex
import shutil
import subprocess


def run(memory, payload, runner=None):
    node_id = payload.get("node_id")
    if not node_id:
        raise ValueError("edit requires a selected node")

    path = memory.content_path(node_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("", encoding="utf-8")

    before = _read(path)
    editor = os.environ.get("EDITOR")
    if editor:
        command = shlex.split(editor) + [str(path)]
        try:
            result = subprocess.run(command, check=False)
            after = _read(path)
            return _edit_result(memory, node_id, path, before, after, result.returncode == 0)
        except OSError:
            pass

    if platform.system() == "Darwin":
        try:
            subprocess.Popen(["open", "-a", "TextEdit", str(path)])
            return {"path": str(path), "log": f"opened {memory.clean_id(node_id)} for editing", "opened": True}
        except OSError:
            pass

    code = shutil.which("code")
    if code:
        try:
            result = subprocess.run([code, "-w", str(path)], check=False)
            after = _read(path)
            return _edit_result(memory, node_id, path, before, after, result.returncode == 0)
        except OSError:
            pass

    return {"path": str(path), "log": None, "opened": False}


def _read(path):
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _edit_result(memory, node_id, path, before, after, opened):
    clean_id = memory.clean_id(node_id)
    if before is not None and after is not None and before != after:
        meta = memory.load_meta(node_id)
        memory.save_meta(meta["id"], meta)
        return {"path": str(path), "log": f"edited {clean_id}", "opened": opened}
    if opened:
        return {"path": str(path), "log": f"opened {clean_id} for editing", "opened": True}
    return {"path": str(path), "log": None, "opened": False}
