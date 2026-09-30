"""Small, inert reference catalog for registered MOSS actions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ActionSpec:
    name: str
    summary: str


ACTION_SPECS = (
    ActionSpec("create_node", "Create a new unlinked node record."),
    ActionSpec("convert_node_type", "Convert a compatible node while preserving its identity."),
    ActionSpec("rename_node", "Rename a node ID and update its structured references."),
    ActionSpec("create_child", "Create a node and link it to a parent as one action."),
    ActionSpec("create_item", "Create a structured item in an item list."),
    ActionSpec("create_event", "Create and schedule an event within a week."),
    ActionSpec("submit_log_entry", "Save a new entry using a log template snapshot."),
    ActionSpec("update_log_template", "Change the prompts used by future log entries."),
    ActionSpec("update_log_entry", "Correct the saved answers in an existing log entry."),
    ActionSpec("update_item", "Update an item's title and structured values."),
    ActionSpec("update_item_list_fields", "Change the shared fields for an item list."),
    ActionSpec("update_node", "Update validated node content and attributes together."),
    ActionSpec("set_content", "Replace a node's content."),
    ActionSpec("add_content", "Append content to a node."),
    ActionSpec("edit_content", "Replace matching text within a node's content."),
    ActionSpec("set_attribute", "Set one validated node attribute."),
    ActionSpec("link_node", "Add an existing node to a parent."),
    ActionSpec("unlink_node", "Remove a node reference from a parent without deleting the node."),
    ActionSpec("move_child", "Reorder one child within a parent."),
    ActionSpec("snapshot", "Create a named ZIP archive of durable memory."),
    ActionSpec("update_core_version", "Record the current MOSS core version."),
    ActionSpec("trash_node", "Permanently delete a node after explicit confirmation."),
    ActionSpec("session_started", "Record the start of a terminal session."),
    ActionSpec("session_ended", "Record the end of a terminal session."),
)


def action_type_names() -> tuple[str, ...]:
    return tuple(spec.name for spec in ACTION_SPECS)


def public_action_types(web_actions: Iterable[str] = ()) -> dict[str, object]:
    """Return JSON-safe documentation, never action modules or callables."""
    browser_names = set(web_actions)
    return {
        "catalog_version": 1,
        "action_types": [
            {
                "name": spec.name,
                "summary": spec.summary,
                "browser_available": spec.name in browser_names,
            }
            for spec in ACTION_SPECS
        ],
    }
