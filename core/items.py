"""Validation and safe normalization for structured item lists."""

from __future__ import annotations

import math
import re
from typing import Any


FIELD_ID = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
MAX_FIELDS = 20
MAX_FIELD_LABEL = 120
MAX_VALUE_LENGTH = 10_000


def validate_item_fields(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise ValueError("fields must be a list")
    if len(value) > MAX_FIELDS:
        raise ValueError(f"An item list can have at most {MAX_FIELDS} fields")

    fields: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, raw in enumerate(value, start=1):
        if not isinstance(raw, dict) or set(raw) != {"id", "label"}:
            raise ValueError(f"Field {index} must contain only id and label")
        field_id = raw.get("id")
        label = raw.get("label")
        if not isinstance(field_id, str) or not FIELD_ID.fullmatch(field_id.strip()):
            raise ValueError(
                f"Field {index} ID must start with a letter and use lowercase letters, numbers, and underscores"
            )
        field_id = field_id.strip()
        if field_id in seen:
            raise ValueError(f"Duplicate item field: {field_id}")
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"Field {index} label is required")
        label = label.strip()
        if len(label) > MAX_FIELD_LABEL:
            raise ValueError(f"Field labels must be {MAX_FIELD_LABEL} characters or fewer")
        seen.add(field_id)
        fields.append({"id": field_id, "label": label})
    return fields


def safe_item_fields(value: Any) -> list[dict[str, str]]:
    try:
        return validate_item_fields(value)
    except ValueError:
        return []


def validate_item_values(
    fields: list[dict[str, str]],
    value: Any,
) -> dict[str, str | int | float | bool]:
    if not isinstance(value, dict):
        raise ValueError("values must be an object")
    field_ids = [field["id"] for field in fields]
    unknown = sorted(set(value) - set(field_ids))
    if unknown:
        raise ValueError(f"Unknown item fields: {', '.join(unknown)}")

    result: dict[str, str | int | float | bool] = {}
    for field_id in field_ids:
        raw = value.get(field_id, "")
        if raw is None:
            raw = ""
        if isinstance(raw, bool):
            result[field_id] = raw
        elif isinstance(raw, int):
            result[field_id] = raw
        elif isinstance(raw, float) and math.isfinite(raw):
            result[field_id] = raw
        elif isinstance(raw, str):
            if len(raw) > MAX_VALUE_LENGTH:
                raise ValueError(
                    f"{field_id} must be {MAX_VALUE_LENGTH} characters or fewer"
                )
            result[field_id] = raw
        else:
            raise ValueError(f"{field_id} must be text, a number, or true/false")
    return result


def safe_item_values(
    fields: list[dict[str, str]],
    value: Any,
) -> dict[str, str | int | float | bool]:
    if not isinstance(value, dict):
        value = {}
    safe_input = {key: raw for key, raw in value.items() if key in {f["id"] for f in fields}}
    try:
        return validate_item_values(fields, safe_input)
    except ValueError:
        return {field["id"]: "" for field in fields}
