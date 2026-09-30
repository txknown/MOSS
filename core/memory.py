import json
import re
import shutil
from datetime import datetime
from pathlib import Path

from core.node_normalization import normalize_node_meta
from core.node_schema import attribute_defaults


class Memory:
    def __init__(self, project_root=None, initialize=True):
        self.project_root = Path(project_root).resolve() if project_root else Path(__file__).resolve().parents[1]
        self.root = self.project_root / "memory"
        self.nodes = self.root / "nodes"
        self.materials = self.root / "materials"
        self.system = self.root / "system"
        self.logs = self.root / "logs"

        if initialize:
            self._ensure_directories()
            self.bootstrap()

    def _ensure_directories(self):
        for path in (self.nodes, self.materials, self.system, self.logs):
            path.mkdir(parents=True, exist_ok=True)

    def now(self):
        return datetime.now().astimezone().isoformat(timespec="minutes")

    def clean_id(self, text):
        text = str(text or "").strip().lower()
        text = re.sub(r"[^a-z0-9]+", "_", text)
        text = re.sub(r"_+", "_", text).strip("_")
        return text

    def node_path(self, node_id):
        return self.nodes / self.clean_id(node_id)

    def meta_path(self, node_id):
        return self.node_path(node_id) / "node.json"

    def content_path(self, node_id):
        return self.node_path(node_id) / "content.txt"

    def node_exists(self, node_id):
        return self.meta_path(node_id).exists()

    def _load_counters(self):
        path = self.system / "counters.json"
        return self._load_json_file(path, default={})

    def _save_counters(self, counters):
        self._write_json_file(self.system / "counters.json", counters)

    def _load_json_file(self, path, default=None):
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_json_file(self, path, value):
        path.write_text(json.dumps(value, indent=2), encoding="utf-8")

    def next_node_id(self, node_type):
        counters = self._load_counters()
        counter = int(counters.get(node_type, 0))
        while True:
            counter += 1
            node_id = f"{node_type}_{counter:03d}"
            if not self.node_exists(node_id):
                counters[node_type] = counter
                self._save_counters(counters)
                return node_id

    def create_node(self, node_type, node_id=None, content=""):
        node_type = self.clean_id(node_type)
        from core.registry import load_node_type

        load_node_type(node_type)
        node_id = self.clean_id(node_id) if node_id else self.next_node_id(node_type)
        if not node_id:
            raise ValueError("Node ID is empty.")
        if self.node_exists(node_id):
            raise FileExistsError(f"Node already exists: {node_id}")

        path = self.node_path(node_id)
        path.mkdir(parents=True, exist_ok=False)
        current_time = self.now()
        meta = {
            "id": node_id,
            "type": node_type,
            "children": [],
            "files": ["content.txt"],
            "created": current_time,
            "updated": current_time,
        }
        for field, default in attribute_defaults(node_type).items():
            meta[field] = default

        self.save_meta(node_id, meta, touch=False)
        self.content_path(node_id).write_text(content or "", encoding="utf-8")
        self.rebuild_registry()
        return self.load_meta(node_id)

    def ensure_node(self, node_id, node_type, content="", **fields):
        if self.node_exists(node_id):
            return self.load_meta(node_id)
        meta = self.create_node(node_type, node_id=node_id, content=content)
        changed = False
        for key, value in fields.items():
            if value is not None:
                meta[key] = value
                changed = True
        if changed:
            self.save_meta(node_id, meta)
        return self.load_meta(node_id)

    def load_meta(self, node_id):
        node_id = self.clean_id(node_id)
        path = self.meta_path(node_id)
        meta = json.loads(path.read_text(encoding="utf-8"))
        meta = normalize_node_meta(meta, node_id)
        current_time = self.now()
        meta.setdefault("created", current_time)
        meta.setdefault("updated", current_time)

        return meta

    def save_meta(self, node_id, meta, touch=True):
        node_id = self.clean_id(node_id)
        meta["id"] = node_id
        if "created" not in meta:
            meta["created"] = self.now()
        if touch:
            meta["updated"] = self.now()
        elif "updated" not in meta:
            meta["updated"] = self.now()

        self.node_path(node_id).mkdir(parents=True, exist_ok=True)
        self.meta_path(node_id).write_text(json.dumps(meta, indent=2), encoding="utf-8")

    def read_content(self, node_id):
        path = self.content_path(node_id)
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def write_content(self, node_id, text):
        node_id = self.clean_id(node_id)
        self.node_path(node_id).mkdir(parents=True, exist_ok=True)
        self.content_path(node_id).write_text(text, encoding="utf-8")
        meta = self.load_meta(node_id)
        self.save_meta(node_id, meta)
        self.rebuild_registry()

    def add_content(self, node_id, text):
        node_id = self.clean_id(node_id)
        self.node_path(node_id).mkdir(parents=True, exist_ok=True)
        current = self.read_content(node_id).strip()
        prefix = "\n" if current else ""
        with self.content_path(node_id).open("a", encoding="utf-8") as file:
            file.write(f"{prefix}{text}\n")
        meta = self.load_meta(node_id)
        self.save_meta(node_id, meta)
        self.rebuild_registry()

    def set_attribute(self, node_id, field, value):
        meta = self.load_meta(node_id)
        meta[field] = value
        self.save_meta(meta["id"], meta)
        self.rebuild_registry()
        return meta

    def list_nodes(self):
        items = []
        for path in self.nodes.iterdir():
            meta_path = path / "node.json"
            if path.is_dir() and meta_path.exists():
                items.append(self.load_meta(path.name))
        return sorted(items, key=lambda meta: (meta.get("type", ""), meta.get("title", ""), meta["id"]))

    def add_child(self, parent_id, child_id):
        parent_id = self.clean_id(parent_id)
        child_id = self.clean_id(child_id)
        parent = self.load_meta(parent_id)
        if not self.node_exists(child_id):
            raise FileNotFoundError(child_id)
        if child_id not in parent.get("children", []):
            parent["children"].append(child_id)
            self.save_meta(parent_id, parent)
        self.rebuild_registry()
        return parent

    def remove_child(self, parent_id, child_id):
        parent_id = self.clean_id(parent_id)
        child_id = self.clean_id(child_id)
        parent = self.load_meta(parent_id)
        parent["children"] = [current_id for current_id in parent.get("children", []) if current_id != child_id]
        self.save_meta(parent_id, parent)
        self.rebuild_registry()
        return parent

    def rename_node(self, node_id, new_node_id):
        """Rename one node and every structured reference to it, with rollback."""
        node_id = self.clean_id(node_id)
        new_node_id = self.clean_id(new_node_id)
        source = self.node_path(node_id)
        target = self.node_path(new_node_id)
        if source.is_symlink() or not source.is_dir():
            raise FileNotFoundError(node_id)
        if target.exists():
            raise FileExistsError(f"Node already exists: {new_node_id}")

        own_path = source / "node.json"
        own_bytes = own_path.read_bytes()
        own_meta = json.loads(own_bytes)
        reference_updates = []
        for path in self.nodes.iterdir():
            meta_path = path / "node.json"
            if path == source or path.is_symlink() or not meta_path.is_file():
                continue
            raw_bytes = meta_path.read_bytes()
            meta = json.loads(raw_bytes)
            changed = False
            children = meta.get("children")
            if isinstance(children, list) and node_id in children:
                meta["children"] = [
                    new_node_id if child_id == node_id else child_id
                    for child_id in children
                ]
                changed = True
            if meta.get("log_id") == node_id:
                meta["log_id"] = new_node_id
                changed = True
            if meta.get("target_id") == node_id:
                meta["target_id"] = new_node_id
                changed = True
            if changed:
                meta["updated"] = self.now()
                reference_updates.append((meta_path, raw_bytes, meta))

        own_meta["id"] = new_node_id
        if isinstance(own_meta.get("children"), list):
            own_meta["children"] = [
                new_node_id if child_id == node_id else child_id
                for child_id in own_meta["children"]
            ]
        if own_meta.get("log_id") == node_id:
            own_meta["log_id"] = new_node_id
        if own_meta.get("target_id") == node_id:
            own_meta["target_id"] = new_node_id
        own_meta["updated"] = self.now()

        source.rename(target)
        try:
            self._write_json_file(target / "node.json", own_meta)
            for meta_path, _raw_bytes, meta in reference_updates:
                self._write_json_file(meta_path, meta)
            self.rebuild_registry()
        except Exception:
            for meta_path, raw_bytes, _meta in reference_updates:
                meta_path.write_bytes(raw_bytes)
            if target.exists() and not source.exists():
                target.rename(source)
            (source / "node.json").write_bytes(own_bytes)
            self.rebuild_registry()
            raise
        return self.load_meta(new_node_id)

    def move_child(self, parent_id, child_id, direction):
        parent_id = self.clean_id(parent_id)
        child_id = self.clean_id(child_id)
        parent = self.load_meta(parent_id)
        children = list(parent.get("children", []))
        if child_id not in children:
            raise ValueError(f"{child_id} is not a child of {parent_id}")

        index = children.index(child_id)
        new_index = index - 1 if direction == "up" else index + 1
        if new_index < 0 or new_index >= len(children):
            return parent

        children[index], children[new_index] = children[new_index], children[index]
        parent["children"] = children
        self.save_meta(parent_id, parent)
        self.rebuild_registry()
        return parent

    def move_child_relative(self, parent_id, child_id, reference_id, position):
        parent_id = self.clean_id(parent_id)
        child_id = self.clean_id(child_id)
        reference_id = self.clean_id(reference_id)
        if position not in {"before", "after"}:
            raise ValueError("position must be before or after")
        if child_id == reference_id:
            raise ValueError("A node cannot be moved relative to itself.")

        parent = self.load_meta(parent_id)
        children = list(parent.get("children", []))
        if child_id not in children:
            raise ValueError(f"{child_id} is not a child of {parent_id}")
        if reference_id not in children:
            raise ValueError(f"{reference_id} is not a child of {parent_id}")

        children.remove(child_id)
        reference_index = children.index(reference_id)
        insert_at = reference_index if position == "before" else reference_index + 1
        children.insert(insert_at, child_id)
        if children != parent.get("children", []):
            parent["children"] = children
            self.save_meta(parent_id, parent)
            self.rebuild_registry()
        return parent

    def move_child_to_bottom(self, parent_id, child_id):
        parent_id = self.clean_id(parent_id)
        child_id = self.clean_id(child_id)
        parent = self.load_meta(parent_id)
        children = list(parent.get("children", []))
        if child_id not in children or children[-1:] == [child_id]:
            return False

        parent["children"] = [current_id for current_id in children if current_id != child_id]
        parent["children"].append(child_id)
        self.save_meta(parent_id, parent)
        self.rebuild_registry()
        return True

    def move_child_to_edge(self, parent_id, child_id, position):
        parent_id = self.clean_id(parent_id)
        child_id = self.clean_id(child_id)
        if position not in {"top", "bottom"}:
            raise ValueError("position must be top or bottom")
        parent = self.load_meta(parent_id)
        children = list(parent.get("children", []))
        if child_id not in children:
            raise ValueError(f"{child_id} is not a child of {parent_id}")

        children.remove(child_id)
        if position == "top":
            children.insert(0, child_id)
        else:
            children.append(child_id)
        if children != parent.get("children", []):
            parent["children"] = children
            self.save_meta(parent_id, parent)
            self.rebuild_registry()
        return parent

    def parent_metas_for(self, child_id):
        child_id = self.clean_id(child_id)
        return [meta for meta in self.list_nodes() if child_id in meta.get("children", [])]

    def trash_node(self, node_id):
        node_id = self.clean_id(node_id)
        if node_id == "home":
            raise ValueError("Cannot trash home.")
        if not node_id or not self.node_exists(node_id):
            raise FileNotFoundError(f"Node not found: {node_id or '(empty node ID)'}")

        # Children are deliberately left intact; only references to this node are removed.
        for parent in self.parent_metas_for(node_id):
            parent["children"] = [child_id for child_id in parent.get("children", []) if child_id != node_id]
            self.save_meta(parent["id"], parent)

        shutil.rmtree(self.node_path(node_id))
        self.rebuild_registry()

    def rebuild_registry(self):
        registry = []
        for meta in self.list_nodes():
            registry.append(
                {
                    "id": meta["id"],
                    "type": meta["type"],
                    "path": str(self.node_path(meta["id"]).relative_to(self.project_root)),
                }
            )
        (self.system / "registry.json").write_text(json.dumps(registry, indent=2), encoding="utf-8")
        return registry

    def bootstrap(self):
        self._ensure_system_files()
        self.ensure_node("home", "page", title="Home")
        self.rebuild_registry()

    def _ensure_system_files(self):
        settings_path = self.system / "settings.json"
        if not settings_path.exists():
            settings_path.write_text(json.dumps({}, indent=2), encoding="utf-8")

        counters_path = self.system / "counters.json"
        if not counters_path.exists():
            counters_path.write_text(json.dumps({}, indent=2), encoding="utf-8")

        action_log_path = self.logs / "action_log.txt"
        if not action_log_path.exists():
            action_log_path.write_text("", encoding="utf-8")
