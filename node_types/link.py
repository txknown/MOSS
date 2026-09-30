from core.node_schema import module_contract
from core.urls import safe_web_url
from node_types import pad


(
    ALLOWED_ATTRIBUTES,
    ATTRIBUTE_DEFAULTS,
    ATTRIBUTE_TYPES,
    SYSTEM_MANAGED_ATTRIBUTES,
) = module_contract("link")


def render(memory, meta, indent=0, render_child=None):
    title = meta.get("title") or meta["id"]
    url = safe_web_url(meta.get("url")) or "(invalid or missing URL)"
    return f"{pad(indent)}{title}\n{pad(indent + 1)}{url}"
