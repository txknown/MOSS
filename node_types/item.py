from core.items import safe_item_fields, safe_item_values
from core.node_schema import module_contract
from node_types import pad


(
    ALLOWED_ATTRIBUTES,
    ATTRIBUTE_DEFAULTS,
    ATTRIBUTE_TYPES,
    SYSTEM_MANAGED_ATTRIBUTES,
) = module_contract("item")


def render(memory, meta, indent=0, render_child=None):
    title = meta.get("title") or meta["id"]
    parents = [parent for parent in memory.parent_metas_for(meta["id"]) if parent.get("type") == "item_list"]
    fields = safe_item_fields(parents[0].get("fields")) if len(parents) == 1 else []
    values = safe_item_values(fields, meta.get("values"))
    details = ", ".join(
        f"{field['label']}: {values[field['id']]}"
        for field in fields
        if values[field["id"]] != ""
    )
    return f"{pad(indent)}- {title}{f' — {details}' if details else ''}"
