#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.action_runner import ActionRunner
from core.memory import Memory


def parse_args():
    parser = argparse.ArgumentParser(description="Import a plain-text file into an existing MOSS todo_list.")
    parser.add_argument("todo_list_id")
    parser.add_argument("file_path", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def read_todos(path):
    if not path.is_file():
        raise ValueError(f"Input file not found: {path}")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise ValueError(f"Could not read input file: {error}") from error

    todos = []
    for source_line in lines:
        text = source_line.strip()
        if not text:
            continue
        if text.startswith("- "):
            text = text[2:].lstrip()
        if text.startswith("[ ] "):
            text = text[4:].lstrip()
        if text:
            todos.append(text)
    return todos


def validate_target(memory, todo_list_id):
    clean_id = memory.clean_id(todo_list_id)
    if not clean_id or not memory.node_exists(clean_id):
        raise ValueError(f"Todo list not found: {clean_id or todo_list_id}")
    meta = memory.load_meta(clean_id)
    if meta.get("type") != "todo_list":
        raise ValueError(f"Target is not a todo_list: {clean_id}")
    return clean_id


def import_todos(project_root, todo_list_id, file_path, dry_run=False):
    todos = read_todos(Path(file_path))
    readonly_memory = Memory(project_root=project_root, initialize=False)
    target_id = validate_target(readonly_memory, todo_list_id)

    if dry_run:
        return target_id, todos, []

    memory = Memory(project_root=project_root)
    runner = ActionRunner(memory)
    created_ids = []
    for text in todos:
        created = runner.run(
            "create_node",
            payload={"type": "todo_item", "content": f"{text}\n"},
            log=False,
        )
        node_id = created["node_id"]
        runner.run(
            "link_node",
            payload={"parent_id": target_id, "child_id": node_id},
            log=False,
        )
        created_ids.append(node_id)

    runner.write_log(f"imported {len(created_ids)} todo items into {target_id}")
    return target_id, todos, created_ids


def main():
    args = parse_args()
    try:
        target_id, todos, created_ids = import_todos(
            PROJECT_ROOT,
            args.todo_list_id,
            args.file_path,
            dry_run=args.dry_run,
        )
    except (ValueError, FileNotFoundError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"Dry run: {len(todos)} todo items would be imported into {target_id}")
        for text in todos:
            print(f"- {text}")
    else:
        print(f"Imported {len(created_ids)} todo items into {target_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
