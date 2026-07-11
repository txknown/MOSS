import json
import re
from datetime import datetime
from pathlib import Path


class Memory:
    def __init__(self, project_root=None):
        self.project_root = Path(project_root).resolve() if project_root else Path(__file__).resolve().parents[1]
        self.root = self.project_root / "memory"
        self.nodes = self.root / "nodes"
        self.materials = self.root / "materials"
        self.system = self.root / "system"
        self.logs = self.root / "logs"

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
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_counters(self, counters):
        (self.system / "counters.json").write_text(json.dumps(counters, indent=2), encoding="utf-8")

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
        if node_type == "todo_item":
            meta["checked"] = False

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
        changed = False
        current_time = self.now()

        defaults = {
            "id": node_id,
            "type": "text",
            "children": [],
            "files": ["content.txt"],
            "created": current_time,
            "updated": current_time,
        }
        for key, value in defaults.items():
            if key not in meta:
                meta[key] = value
                changed = True

        if meta.get("type") == "todo_item" and "checked" not in meta:
            meta["checked"] = False
            changed = True

        if meta["id"] != node_id:
            meta["id"] = node_id
            changed = True

        if changed:
            self.save_meta(node_id, meta)

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
