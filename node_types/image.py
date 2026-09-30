from node_types import content, pad
from core.node_schema import module_contract


(
    ALLOWED_ATTRIBUTES,
    ATTRIBUTE_DEFAULTS,
    ATTRIBUTE_TYPES,
    SYSTEM_MANAGED_ATTRIBUTES,
) = module_contract("image")


def render(memory, meta, indent=0, render_child=None):
    source = content(memory, meta) or meta.get("source") or "(no image source)"
    title = meta.get("title") or meta["id"]
    return f"{pad(indent)}{title}: {source}"
