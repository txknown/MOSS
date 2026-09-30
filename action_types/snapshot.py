import zipfile
from datetime import datetime

from core.snapshots import snapshot_archive_path, validate_snapshot_name


def run(memory, payload, runner=None):
    snapshot_name = validate_snapshot_name(payload.get("name"))

    snapshots_dir = memory.project_root / "snapshots"
    target = snapshot_archive_path(memory.project_root, snapshot_name)
    if target.exists():
        raise FileExistsError(f"Snapshot already exists: {snapshot_name}")

    snapshots_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now().astimezone()
    version_path = memory.project_root / "version.txt"
    version_text = version_path.read_text(encoding="utf-8")
    first_line = version_text.splitlines()[0] if version_text.splitlines() else "MOSS"
    version = first_line.removeprefix("MOSS ").strip() or "(unknown)"
    snapshot_text = "\n".join(
        [
            f"Snapshot: {snapshot_name}",
            f"Created: {now.strftime('%B')} {now.day}, {now.year}, {now.strftime('%H:%M')}",
            f"MOSS version: {version}",
            "",
        ]
    )

    created_target = False
    try:
        archive = zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED)
        created_target = True
        with archive:
            archive.writestr("SNAPSHOT.txt", snapshot_text)
            archive.write(version_path, "version.txt")
            _write_tree(archive, memory.root, memory.project_root)
    except Exception:
        if created_target:
            target.unlink(missing_ok=True)
        raise

    return {
        "name": snapshot_name,
        "path": str(target),
        "log": f"created snapshot {snapshot_name}",
    }


def _write_tree(archive, root, project_root):
    archive.write(root, str(root.relative_to(project_root)))
    for path in sorted(root.rglob("*")):
        archive.write(path, str(path.relative_to(project_root)))
