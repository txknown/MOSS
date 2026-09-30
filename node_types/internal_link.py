from core.node_schema import module_contract
from node_types import pad


(
    ALLOWED_ATTRIBUTES,
    ATTRIBUTE_DEFAULTS,
    ATTRIBUTE_TYPES,
    SYSTEM_MANAGED_ATTRIBUTES,
) = module_contract("internal_link")


def render(memory, meta, indent=0, render_child=None):
    title = meta.get("title") or meta["id"]
    target_id = meta.get("target_id") or "(missing target)"
    return f"{pad(indent)}{title} → {target_id}"
