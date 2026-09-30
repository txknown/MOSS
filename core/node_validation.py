"""Schema-backed validation shared by MOSS actions."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from core.node_schema import CONTENT_MAX_LENGTH, get_node_schema
from core.logs import validate_log_prompts
from core.urls import validate_web_url


def validate_content(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("content must be text")
    if len(value) > CONTENT_MAX_LENGTH:
        raise ValueError(f"content must be {CONTENT_MAX_LENGTH} characters or fewer")
    return value


def validate_attribute_values(meta: dict[str, Any], attributes: Any) -> dict[str, Any]:
    if not isinstance(attributes, dict):
        raise ValueError("attributes must be an object")

    try:
        node_schema = get_node_schema(meta.get("type", ""))
    except KeyError:
        raise ValueError(
            f"Cannot set attributes for unknown node type: {meta.get('type', '(unknown)')}"
        ) from None

    allowed = tuple(item.name for item in node_schema.attributes)
    system_managed = tuple(
        item.name for item in node_schema.attributes if item.system_managed
    )
    validated: dict[str, Any] = {}
    for raw_field, raw_value in attributes.items():
        field = str(raw_field).strip().lower()
        if field not in allowed:
            allowed_text = ", ".join(allowed) if allowed else "(none)"
            raise ValueError(
                f"Unknown attribute for {meta.get('type', 'node')}: {field}\n"
                f"Allowed attributes: {allowed_text}"
            )
        if field in system_managed:
            raise ValueError(f"{field} is managed automatically and cannot be set directly.")
        attribute = node_schema.attribute(field)
        value = validate_attribute_value(field, raw_value, attribute.value_type)
        if attribute.required and isinstance(value, str) and not value.strip():
            raise ValueError(f"{field} is required")
        if attribute.max_length and isinstance(value, str) and len(value) > attribute.max_length:
            raise ValueError(
                f"{field} must be {attribute.max_length} characters or fewer"
            )
        validated[field] = value

    prospective = {**meta, **validated}
    if prospective.get("type") == "event":
        start_time = prospective.get("start_time")
        end_time = prospective.get("end_time")
        if start_time and end_time and end_time <= start_time:
            raise ValueError("end_time must be later than start_time")
    return validated


def validate_attribute_value(field: str, value: Any, value_type: str | None) -> Any:
    if value_type == "web_url":
        try:
            return validate_web_url(value)
        except ValueError as error:
            raise ValueError(str(error)) from None
    if value_type == "log_prompts":
        return validate_log_prompts(value)
    if value_type == "log_answers":
        if not isinstance(value, dict):
            raise ValueError(f"{field} must be an object")
        return value
    if value_type == "boolean":
        try:
            return _parse_boolean(value)
        except ValueError:
            raise ValueError(f"{field} must be true or false") from None
    if value_type == "string":
        if not isinstance(value, str):
            raise ValueError(f"{field} must be a string")
        return value
    if value_type == "node_id":
        if not isinstance(value, str):
            raise ValueError(f"{field} must be a node ID")
        value = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)*", value):
            raise ValueError(
                f"{field} must use lowercase letters, numbers, and underscores"
            )
        return value
    if value_type == "positive_integer":
        if isinstance(value, bool):
            raise ValueError(f"{field} must be an integer greater than zero")
        if isinstance(value, str):
            try:
                value = int(value.strip())
            except ValueError:
                raise ValueError(f"{field} must be an integer greater than zero") from None
        if not isinstance(value, int) or value < 1:
            raise ValueError(f"{field} must be an integer greater than zero")
        return value
    if value_type == "randomizer_display":
        if not isinstance(value, str) or value.strip().lower() not in {"list", "text"}:
            raise ValueError(f"{field} must be list or text")
        return value.strip().lower()
    if value_type == "monday_date":
        if not isinstance(value, str):
            raise ValueError(f"{field} must be a date in YYYY-MM-DD format")
        try:
            parsed = datetime.strptime(value.strip(), "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(f"{field} must be a date in YYYY-MM-DD format") from None
        if parsed.weekday() != 0:
            raise ValueError(f"{field} must be a Monday")
        return parsed.isoformat()
    if value_type == "date_or_blank":
        if not isinstance(value, str):
            raise ValueError(f"{field} must be a date in YYYY-MM-DD format or blank")
        value = value.strip()
        if not value:
            return ""
        try:
            return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
        except ValueError:
            raise ValueError(f"{field} must be a date in YYYY-MM-DD format or blank") from None
    if value_type == "day_number":
        if isinstance(value, bool):
            raise ValueError(f"{field} must be an integer from 1 to 7")
        if isinstance(value, str):
            try:
                value = int(value.strip())
            except ValueError:
                raise ValueError(f"{field} must be an integer from 1 to 7") from None
        if not isinstance(value, int) or not 1 <= value <= 7:
            raise ValueError(f"{field} must be an integer from 1 to 7")
        return value
    if value_type == "clock_time_or_blank":
        if not isinstance(value, str):
            raise ValueError(f"{field} must use HH:MM format or be blank")
        value = value.strip()
        if not value:
            return ""
        try:
            parsed = datetime.strptime(value, "%H:%M")
        except ValueError:
            raise ValueError(f"{field} must use HH:MM format or be blank") from None
        return parsed.strftime("%H:%M")
    return value


def _parse_boolean(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
    raise ValueError("value must be true or false")
