def pad(indent):
    return "  " * indent


def indent_text(text, indent):
    prefix = pad(indent)
    return "\n".join(f"{prefix}{line}" for line in text.splitlines())


def content(memory, meta):
    return memory.read_content(meta["id"]).strip()
