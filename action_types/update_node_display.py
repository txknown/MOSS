"""Save a node's presentation choices without altering its durable content."""
from core.display_styles import validate_node_styles
from core.ui_settings import read_ui_file, write_ui_file


def run(memory, payload, runner=None):
    node_id, selection = validate_node_styles(memory, payload)
    selections = read_ui_file(memory, "node_display.json")
    if all(value == "default" for value in selection.values()):
        selections.pop(node_id, None)
    else:
        selections[node_id] = selection
    write_ui_file(memory, "node_display.json", selections)
    return {"node_id": node_id, "styles": selection,
            "log": f"updated display styles for {node_id}"}
