"""Pure validation and normalization helpers for structured log data."""

from __future__ import annotations

import re
from datetime import date
from typing import Any


LOG_PROMPT_TYPES = ("text", "date", "choice")
MAX_LOG_PROMPTS = 40
MAX_PROMPT_LABEL_LENGTH = 120
MAX_TEXT_ANSWER_LENGTH = 250_000
PROMPT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


def validate_log_prompts(value: Any) -> list[dict[str, Any]]:
    """Validate an ordered log template and return a detached JSON-safe copy."""
    if not isinstance(value, list):
        raise ValueError("prompts must be a list")
    if not value:
        raise ValueError("a log must contain at least one prompt")
    if len(value) > MAX_LOG_PROMPTS:
        raise ValueError(f"a log can contain at most {MAX_LOG_PROMPTS} prompts")

    prompts: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw_prompt in enumerate(value, start=1):
        if not isinstance(raw_prompt, dict):
            raise ValueError(f"prompt {index} must be an object")
        unknown = sorted(set(raw_prompt) - {"id", "label", "type", "required", "options"})
        if unknown:
            raise ValueError(f"prompt {index} has unknown fields: {', '.join(unknown)}")

        prompt_id = raw_prompt.get("id")
        if not isinstance(prompt_id, str) or not PROMPT_ID_PATTERN.fullmatch(prompt_id):
            raise ValueError(
                f"prompt {index} id must start with a letter and use lowercase letters, numbers, or underscores"
            )
        if prompt_id in seen_ids:
            raise ValueError(f"prompt id is repeated: {prompt_id}")
        seen_ids.add(prompt_id)

        label = raw_prompt.get("label")
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"prompt {prompt_id} requires a label")
        label = label.strip()
        if len(label) > MAX_PROMPT_LABEL_LENGTH:
            raise ValueError(
                f"prompt {prompt_id} label must be {MAX_PROMPT_LABEL_LENGTH} characters or fewer"
            )

        prompt_type = raw_prompt.get("type")
        if prompt_type not in LOG_PROMPT_TYPES:
            raise ValueError(
                f"prompt {prompt_id} type must be one of: {', '.join(LOG_PROMPT_TYPES)}"
            )
        required = raw_prompt.get("required", False)
        if not isinstance(required, bool):
            raise ValueError(f"prompt {prompt_id} required must be true or false")

        prompt: dict[str, Any] = {
            "id": prompt_id,
            "label": label,
            "type": prompt_type,
            "required": required,
        }
        if prompt_type == "choice":
            options = raw_prompt.get("options")
            if not isinstance(options, list) or not 1 <= len(options) <= 24:
                raise ValueError(f"prompt {prompt_id} must have between 1 and 24 choices")
            clean_options: list[str | int] = []
            for option in options:
                if isinstance(option, bool) or not isinstance(option, (str, int)):
                    raise ValueError(f"prompt {prompt_id} choices must be text or integers")
                if isinstance(option, str):
                    option = option.strip()
                    if not option:
                        raise ValueError(f"prompt {prompt_id} choices cannot be blank")
                    if len(option) > MAX_PROMPT_LABEL_LENGTH:
                        raise ValueError(f"prompt {prompt_id} contains an overly long choice")
                if any(type(option) is type(current) and option == current for current in clean_options):
                    raise ValueError(f"prompt {prompt_id} contains a repeated choice")
                clean_options.append(option)
            prompt["options"] = clean_options
        prompts.append(prompt)
    return prompts


def validate_log_answers(
    prompts_value: Any,
    answers_value: Any,
    *,
    require_required: bool = True,
) -> dict[str, str | int]:
    """Validate answers against the exact prompt snapshot used for an entry."""
    prompts = validate_log_prompts(prompts_value)
    if not isinstance(answers_value, dict):
        raise ValueError("answers must be an object")
    prompt_ids = {prompt["id"] for prompt in prompts}
    unknown = sorted(set(answers_value) - prompt_ids)
    if unknown:
        raise ValueError(f"answers contain unknown prompts: {', '.join(unknown)}")

    answers: dict[str, str | int] = {}
    for prompt in prompts:
        prompt_id = prompt["id"]
        value = answers_value.get(prompt_id, "")
        if value is None:
            value = ""
        if prompt["type"] == "choice":
            if value == "" and not prompt["required"]:
                answers[prompt_id] = ""
                continue
            if isinstance(value, bool) or not any(
                type(value) is type(option) and value == option
                for option in prompt["options"]
            ):
                choices = ", ".join(str(option) for option in prompt["options"])
                raise ValueError(f"{prompt['label']} must be one of: {choices}")
        else:
            if not isinstance(value, str):
                raise ValueError(f"{prompt['label']} must be text")
            value = value.strip() if prompt["type"] == "date" else value
            if prompt["type"] == "date" and value:
                try:
                    value = date.fromisoformat(value).isoformat()
                except ValueError:
                    raise ValueError(f"{prompt['label']} must be a date in YYYY-MM-DD format") from None
            if len(value) > MAX_TEXT_ANSWER_LENGTH:
                raise ValueError(
                    f"{prompt['label']} must be {MAX_TEXT_ANSWER_LENGTH} characters or fewer"
                )
        if require_required and prompt["required"] and value == "":
            raise ValueError(f"{prompt['label']} is required")
        answers[prompt_id] = value
    return answers


def entry_date_for(prompts_value: Any, answers_value: Any) -> str:
    prompts = validate_log_prompts(prompts_value)
    answers = validate_log_answers(prompts, answers_value)
    for prompt in prompts:
        if prompt["type"] == "date":
            return str(answers[prompt["id"]])
    return ""


def safe_log_prompts(value: Any) -> list[dict[str, Any]]:
    try:
        return validate_log_prompts(value)
    except ValueError:
        return []


def safe_log_answers(prompts_value: Any, answers_value: Any) -> dict[str, str | int]:
    """Return only harmless scalar answers for read rendering; never repair data."""
    prompts = safe_log_prompts(prompts_value)
    if not prompts or not isinstance(answers_value, dict):
        return {}
    answers: dict[str, str | int] = {}
    for prompt in prompts:
        value = answers_value.get(prompt["id"], "")
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            value = ""
        answers[prompt["id"]] = value
    return answers
