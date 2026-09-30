def run(memory, payload, runner=None):
    version = str(payload.get("version") or "").strip()
    if not version:
        raise ValueError("update_core_version requires a version")

    settings = memory._load_json_file(memory.system / "settings.json", default={})
    if settings.get("core_version") == version:
        return {"changed": False, "log": None}

    settings["core_version"] = version
    memory._write_json_file(memory.system / "settings.json", settings)
    return {"changed": True, "log": f"updated core to {version}"}
