"""Canonical, Python-owned schema for every built-in MOSS node type.

The objects in this module describe domain rules and the small amount of inert
editor metadata that the web client needs.  Node modules, actions, storage, and
the web API all derive their view of a node type from this registry.
"""

from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
from typing import Any


Choice = tuple[str, str]
CONTENT_MAX_LENGTH = 250_000


@dataclass(frozen=True)
class EditorSpec:
    label: str
    input_type: str = "text"
    placeholder: str = ""
    rows: int | None = None
    required: bool = False
    minimum: int | None = None
    step: int | None = None
    pattern: str = ""
    title: str = ""
    choices: tuple[Choice, ...] = ()
    suggestions: tuple[Choice, ...] = ()


@dataclass(frozen=True)
class AttributeSchema:
    name: str
    value_type: str
    has_default: bool = False
    default: Any = None
    system_managed: bool = False
    required: bool = False
    top_level_only: bool = False
    max_length: int | None = None
    editor: EditorSpec | None = None


@dataclass(frozen=True)
class ContentSchema:
    label: str = "Content"
    rows: int = 7
    placeholder: str = ""
    max_length: int = CONTENT_MAX_LENGTH


@dataclass(frozen=True)
class NodeSchema:
    name: str
    attributes: tuple[AttributeSchema, ...] = ()
    content: ContentSchema | None = None
    allowed_child_types: tuple[str, ...] = ()
    child_creation_types: tuple[str, ...] | None = None
    manages_children: bool = False
    relationship_editable: bool = True
    navigation: bool = False
    expand_children: bool = False
    description: str = ""  # Type reference text; never stored on individual nodes.

    def attribute(self, name: str) -> AttributeSchema | None:
        return next((item for item in self.attributes if item.name == name), None)

    def generic_child_types(self) -> tuple[str, ...]:
        if self.child_creation_types is None:
            return self.allowed_child_types
        return self.child_creation_types


def _attribute(
    name: str,
    value_type: str,
    *,
    default: Any = None,
    has_default: bool = False,
    system_managed: bool = False,
    required: bool = False,
    top_level_only: bool = False,
    max_length: int | None = None,
    editor: EditorSpec | None = None,
) -> AttributeSchema:
    return AttributeSchema(
        name=name,
        value_type=value_type,
        has_default=has_default,
        default=default,
        system_managed=system_managed,
        required=required,
        top_level_only=top_level_only,
        max_length=max_length,
        editor=editor,
    )


TITLE = _attribute(
    "title",
    "string",
    top_level_only=True,
    max_length=160,
    editor=EditorSpec("Title"),
)
TEXT_PRESENTATION = (
    _attribute(
        "size",
        "string",
        max_length=80,
        editor=EditorSpec(
            "Size",
            placeholder="18px, 1.2rem, or large",
            suggestions=(("15px", "Small"), ("18px", "Medium"), ("24px", "Large")),
        ),
    ),
    _attribute(
        "font",
        "string",
        max_length=160,
        editor=EditorSpec(
            "Font",
            placeholder="serif, sans, monospace, or a font name",
            suggestions=(
                ("serif", "MOSS serif"),
                ("sans", "MOSS sans serif"),
                ("monospace", "Monospace"),
            ),
        ),
    ),
    _attribute(
        "align",
        "string",
        max_length=80,
        editor=EditorSpec(
            "Alignment",
            input_type="select",
            choices=(("", "Default"), ("left", "Left"), ("center", "Center"), ("right", "Right")),
        ),
    ),
    _attribute(
        "color",
        "string",
        max_length=80,
        editor=EditorSpec("Color"),
    ),
)
DAY_CHOICES = (
    ("1", "Monday"),
    ("2", "Tuesday"),
    ("3", "Wednesday"),
    ("4", "Thursday"),
    ("5", "Friday"),
    ("6", "Saturday"),
    ("7", "Sunday"),
)


NODE_SCHEMAS: dict[str, NodeSchema] = {
    "page": NodeSchema(
        name="page",
        description="A home for related nodes, with an optional description. Use pages to organize projects, topics, or areas of life.",
        attributes=(
            TITLE,
            _attribute(
                "description",
                "string",
                default="",
                has_default=True,
                top_level_only=True,
                max_length=10_000,
                editor=EditorSpec("Description", input_type="textarea", rows=4),
            ),
            _attribute(
                "description_visible",
                "boolean",
                default=True,
                has_default=True,
                top_level_only=True,
                editor=EditorSpec("Show description", input_type="checkbox"),
            ),
        ),
        allowed_child_types=(
            "page",
            "text",
            "note",
            "item_list",
            "todo_list",
            "image",
            "randomizer",
            "calendar",
            "log",
            "link",
            "internal_link",
        ),
        manages_children=True,
        navigation=True,
    ),
    "text": NodeSchema(
        name="text",
        description="A block of text displayed directly on its parent page, useful for headings, reminders, or short passages.",
        attributes=TEXT_PRESENTATION,
        content=ContentSchema(),
    ),
    "note": NodeSchema(
        name="note",
        description="A note that opens on its own and shows a short preview on its parent page. Useful for ideas, recipes, and longer writing.",
        attributes=(TITLE, *TEXT_PRESENTATION),
        content=ContentSchema(),
        navigation=True,
    ),
    "item_list": NodeSchema(
        name="item_list",
        description="An ordered collection of items that share the same fields. Use it for inventories, collections, or lists of concepts.",
        attributes=(
            TITLE,
            _attribute(
                "fields",
                "item_fields",
                default=[],
                has_default=True,
                system_managed=True,
                top_level_only=True,
            ),
        ),
        allowed_child_types=("item",),
        child_creation_types=(),
        manages_children=True,
        navigation=True,
        expand_children=True,
    ),
    "item": NodeSchema(
        name="item",
        description="One entry in an item list, with a title and values for the fields defined by that list.",
        attributes=(
            _attribute(
                "title",
                "string",
                required=True,
                top_level_only=True,
                max_length=160,
                editor=EditorSpec("Title", required=True),
            ),
            _attribute(
                "values",
                "item_values",
                default={},
                has_default=True,
                system_managed=True,
                top_level_only=True,
            ),
        ),
        navigation=True,
    ),
    "todo_list": NodeSchema(
        name="todo_list",
        description="A collection of tasks you can check off, useful for project work, errands, or a wishlist.",
        attributes=(TITLE,),
        allowed_child_types=("todo_item",),
        manages_children=True,
        navigation=True,
        expand_children=True,
    ),
    "todo_item": NodeSchema(
        name="todo_item",
        description="A task you can check off, with an automatically recorded completion date. Tasks can contain subtasks.",
        attributes=(
            _attribute(
                "checked",
                "boolean",
                default=False,
                has_default=True,
                top_level_only=True,
                editor=EditorSpec("Completed", input_type="checkbox"),
            ),
            _attribute(
                "date_completed",
                "date_or_null",
                default=None,
                has_default=True,
                system_managed=True,
                top_level_only=True,
            ),
        ),
        content=ContentSchema(),
        allowed_child_types=("todo_item",),
        manages_children=True,
        expand_children=True,
    ),
    "image": NodeSchema(
        name="image",
        description="An image from your local materials, displayed at a chosen size with an optional title.",
        attributes=(
            TITLE,
            _attribute("source", "string", top_level_only=True, max_length=1_000),
            _attribute(
                "size",
                "string",
                default="large",
                has_default=True,
                max_length=80,
                editor=EditorSpec(
                    "Display size",
                    placeholder="320px, 60%, 32rem, or large",
                    suggestions=(
                        ("small", "Small · 320px"),
                        ("medium", "Medium · 560px"),
                        ("large", "Large · full width"),
                    ),
                ),
            ),
        ),
        content=ContentSchema(label="Image name", rows=1, placeholder="example.png"),
    ),
    "randomizer": NodeSchema(
        name="randomizer",
        description="A fresh selection from a list of phrases or prompts, with one entry per line. Choose how many to display at a time.",
        attributes=(
            TITLE,
            _attribute(
                "title_visible",
                "boolean",
                default=False,
                has_default=True,
                editor=EditorSpec("Show title on parent page", input_type="checkbox"),
            ),
            _attribute(
                "count",
                "positive_integer",
                default=1,
                has_default=True,
                top_level_only=True,
                editor=EditorSpec("Selection count", input_type="number", minimum=1, step=1),
            ),
            _attribute(
                "display_mode",
                "randomizer_display",
                default="list",
                has_default=True,
                max_length=20,
                editor=EditorSpec(
                    "Display",
                    input_type="select",
                    choices=(("list", "List"), ("text", "Text")),
                ),
            ),
            *TEXT_PRESENTATION,
        ),
        content=ContentSchema(rows=10),
    ),
    "calendar": NodeSchema(
        name="calendar",
        description="A collection of weekly schedules for organizing events and reviewing upcoming or past weeks.",
        attributes=(
            _attribute(
                "title",
                "string",
                default="Calendar",
                has_default=True,
                top_level_only=True,
                max_length=160,
                editor=EditorSpec("Title"),
            ),
        ),
        allowed_child_types=("week",),
        manages_children=True,
        navigation=True,
        expand_children=True,
    ),
    "week": NodeSchema(
        name="week",
        description="A schedule running from Monday through Sunday. Holds events and can be marked complete to move it into past weeks.",
        attributes=(
            _attribute(
                "title",
                "string",
                default="",
                has_default=True,
                top_level_only=True,
                max_length=160,
                editor=EditorSpec("Title"),
            ),
            _attribute(
                "start_date",
                "monday_date",
                default="",
                has_default=True,
                editor=EditorSpec("Monday", input_type="date", required=True),
            ),
            _attribute(
                "completed",
                "boolean",
                default=False,
                has_default=True,
                top_level_only=True,
                editor=EditorSpec("Completed (move to past)", input_type="checkbox"),
            ),
        ),
        allowed_child_types=("event",),
        child_creation_types=(),
        manages_children=True,
        navigation=True,
        expand_children=True,
    ),
    "event": NodeSchema(
        name="event",
        description="An entry on a weekly schedule, with a day, optional start and end times, and notes.",
        attributes=(
            _attribute(
                "title",
                "string",
                default="",
                has_default=True,
                top_level_only=True,
                max_length=160,
                editor=EditorSpec("Title"),
            ),
            _attribute(
                "description",
                "string",
                default="",
                has_default=True,
                top_level_only=True,
                max_length=10_000,
                editor=EditorSpec("Notes", input_type="textarea", rows=4),
            ),
            _attribute(
                "day",
                "day_number",
                default=1,
                has_default=True,
                editor=EditorSpec("Day", input_type="select", choices=DAY_CHOICES),
            ),
            _attribute(
                "start_time",
                "clock_time_or_blank",
                default="",
                has_default=True,
                editor=EditorSpec(
                    "Starts",
                    placeholder="HH:MM",
                    pattern="(?:[01][0-9]|2[0-3]):[0-5][0-9]",
                    title="Use 24-hour time in HH:MM format",
                ),
            ),
            _attribute(
                "end_time",
                "clock_time_or_blank",
                default="",
                has_default=True,
                editor=EditorSpec(
                    "Ends",
                    placeholder="HH:MM",
                    pattern="(?:[01][0-9]|2[0-3]):[0-5][0-9]",
                    title="Use 24-hour time in HH:MM format",
                ),
            ),
        ),
    ),
    "log": NodeSchema(
        name="log",
        description="A reusable set of prompts for check-ins, reflections, or routines. Each submission creates a separate log entry.",
        attributes=(
            TITLE,
            _attribute(
                "description",
                "string",
                default="",
                has_default=True,
                top_level_only=True,
                max_length=10_000,
                editor=EditorSpec(
                    "Description",
                    input_type="textarea",
                    rows=4,
                    placeholder="What this log is for",
                ),
            ),
            _attribute("prompts", "log_prompts", top_level_only=True),
        ),
        allowed_child_types=("log_entry",),
        child_creation_types=(),
        manages_children=True,
        relationship_editable=False,
        navigation=True,
    ),
    "log_entry": NodeSchema(
        name="log_entry",
        description="A saved response to a log, keeping the prompts as they were when submitted so later template changes do not alter its meaning.",
        attributes=(
            _attribute("log_id", "string", system_managed=True, top_level_only=True),
            _attribute("entry_date", "date_or_blank", system_managed=True, top_level_only=True),
            _attribute("submitted_at", "string", system_managed=True, top_level_only=True),
            _attribute("prompts", "log_prompts", system_managed=True, top_level_only=True),
            _attribute("answers", "log_answers", system_managed=True, top_level_only=True),
        ),
    ),
    "link": NodeSchema(
        name="link",
        description="A named link to a website or web resource.",
        attributes=(
            _attribute(
                "title",
                "string",
                required=True,
                top_level_only=True,
                max_length=160,
                editor=EditorSpec("Name", required=True),
            ),
            _attribute(
                "url",
                "web_url",
                required=True,
                max_length=2_048,
                editor=EditorSpec(
                    "URL",
                    input_type="url",
                    placeholder="https://example.com",
                    required=True,
                ),
            ),
        ),
    ),
    "internal_link": NodeSchema(
        name="internal_link",
        description="A shortcut to another node in MOSS, leaving it in its original place. If the target goes missing, the shortcut stays visible as broken.",
        attributes=(
            _attribute(
                "title",
                "string",
                required=True,
                top_level_only=True,
                max_length=160,
                editor=EditorSpec("Name", required=True),
            ),
            _attribute(
                "target_id",
                "node_id",
                required=True,
                max_length=160,
                editor=EditorSpec(
                    "Target node ID",
                    placeholder="actions_i_desire",
                    required=True,
                    pattern="[a-z0-9]+(?:_[a-z0-9]+)*",
                    title="Use a lowercase MOSS node ID",
                ),
            ),
        ),
    ),
}


def node_type_names() -> tuple[str, ...]:
    return tuple(NODE_SCHEMAS)


def get_node_schema(node_type: str) -> NodeSchema:
    normalized = str(node_type).strip().lower()
    try:
        return NODE_SCHEMAS[normalized]
    except KeyError:
        raise KeyError(f"Unknown node type: {node_type}") from None


def get_node_schema_or_none(node_type: Any) -> NodeSchema | None:
    if not isinstance(node_type, str):
        return None
    return NODE_SCHEMAS.get(node_type.strip().lower())


def validate_node_schemas() -> None:
    """Raise when the canonical registry contains an inconsistent contract."""
    editor_input_types = {"checkbox", "date", "number", "select", "text", "textarea", "url"}
    for node_type, schema in NODE_SCHEMAS.items():
        if schema.name != node_type:
            raise ValueError(f"Schema key {node_type} does not match name {schema.name}.")
        names = [item.name for item in schema.attributes]
        if len(names) != len(set(names)):
            raise ValueError(f"Schema {node_type} contains duplicate attributes.")
        unknown_children = sorted(set(schema.allowed_child_types) - set(NODE_SCHEMAS))
        if unknown_children:
            raise ValueError(
                f"Schema {node_type} names unknown child types: {', '.join(unknown_children)}."
            )
        invalid_creation_types = sorted(
            set(schema.generic_child_types()) - set(schema.allowed_child_types)
        )
        if invalid_creation_types:
            raise ValueError(
                f"Schema {node_type} offers disallowed child types: "
                f"{', '.join(invalid_creation_types)}."
            )
        if (schema.allowed_child_types or schema.generic_child_types()) and not schema.manages_children:
            raise ValueError(f"Schema {node_type} has child rules but cannot manage children.")
        for attribute in schema.attributes:
            editor = attribute.editor
            if attribute.system_managed and editor is not None:
                raise ValueError(
                    f"Schema {node_type}.{attribute.name} is system-managed but editable."
                )
            if editor is None:
                continue
            if editor.input_type not in editor_input_types:
                raise ValueError(
                    f"Schema {node_type}.{attribute.name} has an unknown editor input."
                )
            if editor.input_type == "select" and not editor.choices:
                raise ValueError(
                    f"Schema {node_type}.{attribute.name} select has no choices."
                )


def attribute_defaults(node_type: str) -> dict[str, Any]:
    return {
        item.name: deepcopy(item.default)
        for item in get_node_schema(node_type).attributes
        if item.has_default
    }


def module_contract(node_type: str) -> tuple[tuple[str, ...], dict[str, Any], dict[str, str], tuple[str, ...]]:
    """Return legacy node-module declarations, derived from the canonical schema."""
    schema = get_node_schema(node_type)
    return (
        tuple(item.name for item in schema.attributes),
        attribute_defaults(node_type),
        {item.name: item.value_type for item in schema.attributes},
        tuple(item.name for item in schema.attributes if item.system_managed),
    )


def public_schema() -> dict[str, Any]:
    """Return the inert, JSON-safe subset of schema needed by the browser."""
    node_types: dict[str, Any] = {}
    for node_type, schema in NODE_SCHEMAS.items():
        attributes = []
        for item in schema.attributes:
            public_attribute: dict[str, Any] = {
                "name": item.name,
                "type": item.value_type,
                "system_managed": item.system_managed,
                "required": item.required,
                "editable": item.editor is not None and not item.system_managed,
            }
            if item.has_default:
                public_attribute["default"] = item.default
            if item.editor is not None and not item.system_managed:
                editor = item.editor
                public_editor: dict[str, Any] = {
                    "label": editor.label,
                    "input_type": editor.input_type,
                }
                for key, value in (
                    ("placeholder", editor.placeholder),
                    ("rows", editor.rows),
                    ("required", editor.required),
                    ("min", editor.minimum),
                    ("step", editor.step),
                    ("pattern", editor.pattern),
                    ("title", editor.title),
                ):
                    if value not in (None, "", False):
                        public_editor[key] = value
                if item.max_length is not None:
                    public_editor["max_length"] = item.max_length
                if editor.choices:
                    public_editor["choices"] = [
                        {"value": value, "label": label}
                        for value, label in editor.choices
                    ]
                if editor.suggestions:
                    public_editor["suggestions"] = [
                        {"value": value, "label": label}
                        for value, label in editor.suggestions
                    ]
                public_attribute["editor"] = public_editor
            attributes.append(public_attribute)

        content = None
        if schema.content is not None:
            content = {
                "editable": True,
                "label": schema.content.label,
                "rows": schema.content.rows,
                "placeholder": schema.content.placeholder,
                "max_length": schema.content.max_length,
            }
        node_types[node_type] = {
            "type": schema.name,
            "description": schema.description,
            "editable_content": schema.content is not None,
            "content": content,
            "attributes": attributes,
            "allowed_child_types": list(schema.allowed_child_types),
            "child_creation_types": list(schema.generic_child_types()),
            "manages_children": schema.manages_children,
            "relationship_editable": schema.relationship_editable,
        }
    return {"schema_version": 1, "node_types": node_types}


validate_node_schemas()
