"""Create and link one event as a single logged MOSS action."""

from core.node_schema import get_node_schema
from core.node_validation import validate_attribute_value


def run(memory, payload, runner=None):
    if runner is None:
        raise RuntimeError("create_event must run through ActionRunner")

    allowed_fields = {
        "week_id",
        "title",
        "description",
        "day",
        "start_time",
        "end_time",
    }
    unknown_fields = sorted(set(payload) - allowed_fields)
    if unknown_fields:
        raise ValueError(f"Unknown event field: {', '.join(unknown_fields)}")

    week_id = memory.clean_id(payload.get("week_id"))
    if not week_id or not memory.node_exists(week_id):
        raise FileNotFoundError(f"Week not found: {week_id or '(empty week ID)'}")
    week = memory.load_meta(week_id)
    if week.get("type") != "week":
        raise ValueError(f"Events can only be created inside a week: {week_id}")
    week_schema = get_node_schema("week")
    if "event" not in week_schema.allowed_child_types:
        raise RuntimeError("The week schema does not permit event children.")

    title = payload.get("title")
    description = payload.get("description", "")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Event title is required")
    title = title.strip()
    event_schema = get_node_schema("event")
    title_limit = event_schema.attribute("title").max_length
    if title_limit and len(title) > title_limit:
        raise ValueError(f"Event title must be {title_limit} characters or fewer")
    if not isinstance(description, str):
        raise ValueError("Event notes must be text")
    description = description.strip()
    description_limit = event_schema.attribute("description").max_length
    if description_limit and len(description) > description_limit:
        raise ValueError(
            f"Event notes must be {description_limit} characters or fewer"
        )

    day = validate_attribute_value(
        "day", payload.get("day"), event_schema.attribute("day").value_type
    )
    start_time = validate_attribute_value(
        "start_time",
        payload.get("start_time"),
        event_schema.attribute("start_time").value_type,
    )
    end_time = validate_attribute_value(
        "end_time",
        payload.get("end_time"),
        event_schema.attribute("end_time").value_type,
    )
    if not start_time or not end_time:
        raise ValueError("Event start and end times are required")
    if end_time <= start_time:
        raise ValueError("Event end time must be later than its start time")

    event_id = None
    try:
        event_id = runner.run(
            "create_node",
            {"type": "event"},
            log=False,
        )["node_id"]
        for field, value in (
            ("title", title),
            ("description", description),
            ("day", day),
            ("start_time", start_time),
            ("end_time", end_time),
        ):
            runner.run(
                "set_attribute",
                {"node_id": event_id, "field": field, "value": value},
                log=False,
            )
        runner.run(
            "link_node",
            {"parent_id": week_id, "child_id": event_id},
            log=False,
        )
    except Exception:
        if event_id and memory.node_exists(event_id):
            runner.run("trash_node", {"node_id": event_id}, log=False)
        raise

    return {
        "node_id": event_id,
        "week_id": week_id,
        "log": f"created event {event_id} in {week_id}: {title} (day {day}, {start_time}–{end_time})",
    }
