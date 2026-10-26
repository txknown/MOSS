"""Explicit, atomic updates to presentation preferences."""
from core.ui_settings import validate_settings, write_ui_file


def run(memory, payload, runner=None):
    settings = validate_settings(memory, payload)
    write_ui_file(memory, "ui_settings.json", settings)
    return {"settings": settings, "log": "updated MOSS UI settings"}
