"""Pure validation and read-only inspection for MOSS memory snapshots."""

from __future__ import annotations

import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any


SNAPSHOT_NAME_PATTERN = re.compile(r"^[a-z0-9_]{1,80}$")
MANIFEST_MAX_BYTES = 64_000


def validate_snapshot_name(value: Any) -> str:
    name = str(value or "").strip()
    if not name:
        raise ValueError("Use: snapshot <snapshot_name>")
    if not SNAPSHOT_NAME_PATTERN.fullmatch(name):
        raise ValueError(
            "Snapshot names may contain up to 80 lowercase letters, numbers, and underscores."
        )
    return name


def snapshot_archive_path(project_root: str | Path, snapshot_name: Any) -> Path:
    name = validate_snapshot_name(snapshot_name)
    snapshots_root = Path(project_root).resolve() / "snapshots"
    return snapshots_root / f"{name}.zip"


def list_snapshot_records(project_root: str | Path) -> list[dict[str, Any]]:
    """Inspect snapshot ZIP metadata without extracting or modifying archives."""
    snapshots_root = Path(project_root).resolve() / "snapshots"
    if not snapshots_root.is_dir():
        return []

    records = []
    for path in snapshots_root.iterdir():
        if path.is_symlink() or not path.is_file() or path.suffix.casefold() != ".zip":
            continue
        name = path.stem
        if not SNAPSHOT_NAME_PATTERN.fullmatch(name):
            continue
        records.append(_snapshot_record(path, name))
    records.sort(key=lambda item: (item["modified"], item["name"]), reverse=True)
    return records


def _snapshot_record(path: Path, name: str) -> dict[str, Any]:
    stat = path.stat()
    record: dict[str, Any] = {
        "name": name,
        "created": None,
        "modified": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(
            timespec="seconds"
        ),
        "moss_version": None,
        "size_bytes": stat.st_size,
        "file_count": 0,
        "node_count": 0,
        "status": "ready",
    }
    try:
        with zipfile.ZipFile(path) as archive:
            files = [item for item in archive.infolist() if not item.is_dir()]
            record["file_count"] = len(files)
            record["node_count"] = sum(
                item.filename.startswith("memory/nodes/")
                and item.filename.endswith("/node.json")
                for item in files
            )
            manifest = archive.getinfo("SNAPSHOT.txt")
            if manifest.file_size > MANIFEST_MAX_BYTES:
                raise ValueError("Snapshot manifest is too large.")
            text = archive.read(manifest).decode("utf-8")
            fields = {}
            for line in text.splitlines():
                key, separator, value = line.partition(":")
                if separator:
                    fields[key.strip().casefold()] = value.strip()
            record["created"] = fields.get("created") or None
            record["moss_version"] = fields.get("moss version") or None
    except (KeyError, OSError, UnicodeError, ValueError, zipfile.BadZipFile):
        record["status"] = "unreadable"
    return record
