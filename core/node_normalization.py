"""Pure node metadata normalization shared by storage and read APIs."""

from __future__ import annotations

from typing import Any

from core.node_schema import attribute_defaults, get_node_schema_or_none


CORE_DEFAULTS = {
    "type": "text",
    "children": [],
    "files": ["content.txt"],
}


def normalize_node_meta(raw: dict[str, Any], node_id: str) -> dict[str, Any]:
    """Return a normalized copy without writing or mutating ``raw``."""
    meta = dict(raw)
    meta["id"] = node_id
    for key, value in CORE_DEFAULTS.items():
        if key not in meta:
            meta[key] = list(value) if isinstance(value, list) else value

    schema = get_node_schema_or_none(meta.get("type"))
    if schema is not None:
        for field, default in attribute_defaults(schema.name).items():
            if field not in meta:
                meta[field] = default
    return meta


def schema_default(node_type: str, field: str, fallback: Any = None) -> Any:
    schema = get_node_schema_or_none(node_type)
    attribute = schema.attribute(field) if schema is not None else None
    return attribute.default if attribute is not None and attribute.has_default else fallback
