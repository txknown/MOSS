import random

from node_types import pad
from core.node_schema import module_contract


(
    ALLOWED_ATTRIBUTES,
    ATTRIBUTE_DEFAULTS,
    ATTRIBUTE_TYPES,
    SYSTEM_MANAGED_ATTRIBUTES,
) = module_contract("randomizer")


def render(memory, meta, indent=0, render_child=None):
    # Deduplicating preserves source order while guaranteeing distinct phrases.
    phrases = list(dict.fromkeys(line.strip() for line in memory.read_content(meta["id"]).splitlines() if line.strip()))
    count = meta.get("count", 1)
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        count = 1

    if count >= len(phrases):
        selected = phrases
    else:
        selected = random.sample(phrases, count)
    title = meta.get("title")
    lines = []
    if indent == 0 or (title and meta.get("title_visible", False) is True):
        lines.append(f"{pad(indent)}{title or meta['id']}")
    if selected:
        lines.extend(f"{pad(indent)}{phrase}" for phrase in selected)
    else:
        lines.append(f"{pad(indent)}(empty randomizer)")
    return "\n".join(lines)
