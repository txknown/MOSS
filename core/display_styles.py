"""Inert presentation catalog and pure per-node display selection reads."""
from core.node_schema import NODE_SCHEMAS
from core.ui_settings import read_ui_file

CONTEXTS = ("parent", "open")
STYLE_CATALOG = {
    node_type: {context: [{"id": "default", "name": "Default", "description": "Use the standard node display."}]
                for context in CONTEXTS}
    for node_type in NODE_SCHEMAS
}
STYLE_CATALOG["calendar"]["parent"].append({
    "id": "current-week", "name": "Current week",
    "description": "Show the existing week containing today, with its events and day items. Uses this computer's local date; creates no weeks.",
})


def safe_styles(node_type, selection):
    selection = selection if isinstance(selection, dict) else {}
    catalog = STYLE_CATALOG.get(node_type, {})
    return {context: selection.get(context) if selection.get(context) in
            [style["id"] for style in catalog.get(context, [])] else "default"
            for context in CONTEXTS}


def read_node_styles(memory):
    result = {}
    for node_id, selection in read_ui_file(memory, "node_display.json").items():
        if node_id != memory.clean_id(node_id) or not memory.node_exists(node_id):
            continue
        try:
            result[node_id] = safe_styles(memory.load_meta(node_id)["type"], selection)
        except (ValueError, KeyError, FileNotFoundError):
            continue
    return result


def validate_node_styles(memory, payload):
    if not isinstance(payload, dict) or set(payload) != {"node_id", "parent", "open"}:
        raise ValueError("Provide node_id, parent, and open display styles")
    node_id = payload["node_id"]
    if not isinstance(node_id, str) or node_id != memory.clean_id(node_id) or not memory.node_exists(node_id):
        raise ValueError("Select an existing node")
    node_type = memory.load_meta(node_id)["type"]
    selection = {context: payload[context] for context in CONTEXTS}
    if selection != safe_styles(node_type, selection):
        raise ValueError("Choose an available display style for this node type and context")
    return node_id, selection
