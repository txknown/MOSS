"""File-backed presentation preferences, separate from node content."""
import json
import re
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from core.system_views import SYSTEM_TARGETS

DEFAULT_NAVIGATION = [{"label": "Home", "target": "home"}] + [
    {"label": SYSTEM_TARGETS[target][0], "target": target}
    for target in ("system:search", "system:node-types", "system:action-types",
                   "system:snapshots", "system:tree", "system:action-log", "system:change-log")
]
DEFAULTS = {"scheme": "moss-light", "home_style": "node", "home_node_id": "home",
            "navigation": DEFAULT_NAVIGATION}
PALETTE_KEYS = {
    "color-canvas", "color-surface", "color-surface-soft", "color-text",
    "color-muted", "color-faint", "color-accent", "color-accent-strong",
    "color-accent-soft", "color-border", "color-border-strong",
    "color-danger-soft", "color-danger",
}


def saved_schemes():
    schemes = json.loads(Path(__file__).with_name("ui_schemes.json").read_text(encoding="utf-8"))
    seen = set()
    for scheme in schemes:
        if set(scheme) != {"id", "name", "mode", "colors"}:
            raise ValueError("Invalid saved color scheme")
        if not isinstance(scheme["id"], str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", scheme["id"]) or scheme["id"] in seen:
            raise ValueError("Invalid or duplicate scheme ID")
        seen.add(scheme["id"])
        if not isinstance(scheme["name"], str) or not 1 <= len(scheme["name"]) <= 80 or scheme["mode"] not in ("light", "dark"):
            raise ValueError("Invalid scheme name or mode")
        if set(scheme["colors"]) != PALETTE_KEYS or any(not isinstance(v, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", v) for v in scheme["colors"].values()):
            raise ValueError("Scheme colors must be complete six-digit hex colors")
    if DEFAULTS["scheme"] not in seen:
        raise ValueError("The default light scheme must exist")
    return schemes


def read_settings(memory):
    """Use defaults for missing/stale preferences; never repair files during reads."""
    result = deepcopy(DEFAULTS)
    raw = read_ui_file(memory, "ui_settings.json")
    if raw.get("scheme") in [s["id"] for s in saved_schemes()]:
        result["scheme"] = raw["scheme"]
    if raw.get("home_style") in ("node", "top-down"):
        result["home_style"] = raw["home_style"]
    node_id = raw.get("home_node_id")
    if isinstance(node_id, str) and node_id == memory.clean_id(node_id) and memory.node_exists(node_id):
        result["home_node_id"] = node_id
    try:
        if "navigation" in raw:
            result["navigation"] = validate_navigation(memory, raw["navigation"], require_existing=False)
    except ValueError:
        pass
    return result


def validate_settings(memory, payload):
    if not isinstance(payload, dict) or not payload or set(payload) - set(DEFAULTS):
        raise ValueError("Provide scheme, home_style, home_node_id, or navigation")
    result = read_settings(memory)
    if "scheme" in payload and payload["scheme"] not in [s["id"] for s in saved_schemes()]:
        raise ValueError("Select an existing saved color scheme")
    if "home_style" in payload and payload["home_style"] not in ("node", "top-down"):
        raise ValueError("Home style must be node or top-down")
    if "home_node_id" in payload:
        node_id = payload["home_node_id"]
        if not isinstance(node_id, str) or not node_id or node_id != memory.clean_id(node_id) or not memory.node_exists(node_id):
            raise ValueError("Home node must be an existing node ID")
    if "navigation" in payload:
        validate_navigation(memory, payload["navigation"])
    result.update(payload)
    return result


def navigation_catalog():
    """Built-in destinations; node destinations remain ordinary node references."""
    return [{"target": "home", "label": "Home", "url": None}] + [
        {"target": target, "label": label, "url": url}
        for target, (label, url) in SYSTEM_TARGETS.items()
    ]


def validate_navigation(memory, entries, require_existing=True):
    if not isinstance(entries, list) or len(entries) > 30:
        raise ValueError("Choose up to 30 top-bar links")
    previous = read_ui_file(memory, "ui_settings.json").get("navigation", [])
    previous_targets = [item.get("target") for item in previous if isinstance(item, dict)] if isinstance(previous, list) else []
    result = []
    for item in entries:
        if not isinstance(item, dict) or set(item) != {"label", "target"}:
            raise ValueError("Each navigation link needs a label and target")
        label, target = item["label"], item["target"]
        if not isinstance(label, str) or not label.strip() or len(label) > 80:
            raise ValueError("Navigation labels must contain 1–80 characters")
        if not isinstance(target, str) or target == "system:ui":
            raise ValueError("MOSS UI is always available as a fixed link")
        if target != "home" and target not in SYSTEM_TARGETS:
            node_id = target.removeprefix("node:")
            if node_id != memory.clean_id(node_id) or not target.startswith("node:") or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", node_id):
                raise ValueError("Choose a built-in view or a valid node ID")
            if require_existing and not memory.node_exists(node_id) and target not in previous_targets:
                raise ValueError(f"Navigation node does not exist: {node_id}")
        result.append({"label": label, "target": target})
    return result


def read_ui_file(memory, filename):
    try:
        value = json.loads((memory.system / filename).read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (FileNotFoundError, ValueError):
        return {}


def write_ui_file(memory, filename, value):
    """Atomic persistence, called only from an explicit action."""
    memory.system.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".ui-", dir=memory.system)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(value, file, indent=2)
            file.write("\n")
        os.replace(temporary, memory.system / filename)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def renamed_presentation_records(memory, old_id, new_id):
    """Join Memory.rename_node's existing rollback for presentation references."""
    updates = []
    for filename in ("ui_settings.json", "node_display.json"):
        path = memory.system / filename
        value = read_ui_file(memory, filename)
        original = deepcopy(value)
        if filename == "node_display.json" and old_id in value:
            value[new_id] = value.pop(old_id)
        if filename == "ui_settings.json":
            if value.get("home_node_id") == old_id:
                value["home_node_id"] = new_id
            navigation = value.get("navigation", [])
            for item in navigation if isinstance(navigation, list) else []:
                if isinstance(item, dict) and item.get("target") == f"node:{old_id}":
                    item["target"] = f"node:{new_id}"
        if value != original:
            updates.append((path, path.read_bytes(), value))
    return updates
