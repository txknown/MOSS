"""Pure, read-only access to MOSS memory for the web renderer."""

from __future__ import annotations

import json
import random
import re
from collections import deque
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote

from core.logs import safe_log_answers, safe_log_prompts
from core.items import safe_item_fields, safe_item_values
from core.node_normalization import normalize_node_meta, schema_default
from core.node_schema import NODE_SCHEMAS, get_node_schema_or_none, public_schema
from core.snapshots import list_snapshot_records, snapshot_archive_path
from core.urls import safe_web_url

NODE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
NAVIGATION_TYPES = {
    node_type for node_type, schema in NODE_SCHEMAS.items() if schema.navigation
}
EXPANDABLE_CHILD_TYPES = {
    node_type for node_type, schema in NODE_SCHEMAS.items() if schema.expand_children
}
SYSTEM_API_ATTRIBUTES = ("created", "updated")


class ReadServiceError(Exception):
    """Base class for errors that can be returned without repairing memory."""


class NodeNotFoundError(ReadServiceError):
    """Raised when a requested node does not exist."""


class MalformedNodeError(ReadServiceError):
    """Raised when a node cannot be safely interpreted."""


class UnsafeMaterialPathError(ReadServiceError):
    """Raised when a material path does not stay inside memory/materials."""


class MaterialNotFoundError(ReadServiceError):
    """Raised when a safe material path does not name a file."""


class ReadService:
    """Read MOSS files without invoking bootstrap or mutation-capable code."""

    def __init__(self, project_root: str | Path | None = None):
        self.project_root = (
            Path(project_root).resolve()
            if project_root is not None
            else Path(__file__).resolve().parents[1]
        )
        self.memory_root = self.project_root / "memory"
        self.nodes_root = self.memory_root / "nodes"
        self.materials_root = self.memory_root / "materials"
        self.logs_root = self.memory_root / "logs"

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok" if self.nodes_root.is_dir() else "error",
            "read_only": True,
            "memory_available": self.nodes_root.is_dir(),
        }

    def get_schema(self) -> dict[str, Any]:
        return public_schema()

    def get_snapshots(self) -> dict[str, Any]:
        snapshots = list_snapshot_records(self.project_root)
        for snapshot in snapshots:
            snapshot["download_url"] = f"/snapshots/{snapshot['name']}.zip"
        return {"snapshots": snapshots}

    def resolve_snapshot_request(self, snapshot_name: str) -> Path:
        path = snapshot_archive_path(self.project_root, snapshot_name)
        if path.is_symlink() or not path.is_file():
            raise FileNotFoundError(f"Snapshot not found: {snapshot_name}")
        return path

    def get_node(self, node_id: str) -> dict[str, Any]:
        index, errors = self._load_index()
        requested_id = self._validate_node_id(node_id)
        if requested_id not in index:
            direct = self._load_meta(requested_id)
            index[requested_id] = direct

        parents = self._parent_index(index)
        node = self._normalize(index[requested_id], index, parents)
        node["child_nodes"] = self._child_details(
            index[requested_id],
            index,
            parents,
            remaining_depth=3,
            active_ids={requested_id},
        )
        node["path"] = self._path_from_home(requested_id, index)
        if errors:
            node["read_warnings"] = errors
        return node

    def get_tree(self) -> dict[str, Any]:
        index, errors = self._load_index()
        if "home" not in index:
            raise NodeNotFoundError("Home node was not found.")

        seen: set[str] = set()

        def build(node_id: str) -> dict[str, Any]:
            if node_id not in index:
                return {
                    "id": node_id,
                    "title": node_id,
                    "type": "missing",
                    "missing": True,
                    "children": [],
                }

            meta = index[node_id]
            item = self._tree_summary(meta)
            if node_id in seen:
                item["repeated_reference"] = True
                item["children"] = []
                return item

            seen.add(node_id)
            item["repeated_reference"] = False
            item["children"] = []
            for child_id in meta["children"]:
                child = index.get(child_id)
                if child is None:
                    item["children"].append(build(child_id))
                elif child["type"] in NAVIGATION_TYPES:
                    item["children"].append(build(child_id))
            return item

        reachable = self._reachable_from_home(index)
        unlinked_pages = [
            self._tree_summary(meta)
            for node_id, meta in index.items()
            if meta["type"] == "page" and node_id != "home" and node_id not in reachable
        ]
        unlinked_pages.sort(key=self._summary_sort_key)
        orphaned_nodes = [
            self._tree_summary(meta)
            for node_id, meta in index.items()
            if node_id != "home" and node_id not in reachable
        ]
        orphaned_nodes.sort(key=self._summary_sort_key)

        return {
            "root": build("home"),
            "unlinked_pages": unlinked_pages,
            "orphaned_nodes": orphaned_nodes,
            "read_warnings": errors,
        }

    def search(self, query: str) -> dict[str, Any]:
        clean_query = str(query or "").strip()
        if not clean_query:
            return {"query": "", "results": []}

        needle = clean_query.casefold()
        index, errors = self._load_index()
        results = []
        for meta in index.values():
            content = self._read_content(meta["id"])
            description = self._as_text(meta.get("description"))
            prompts = safe_log_prompts(meta.get("prompts"))
            answers = safe_log_answers(prompts, meta.get("answers"))
            structured_log_text = " ".join(
                [
                    *(prompt["label"] for prompt in prompts),
                    *(str(value) for value in answers.values()),
                ]
            )
            item_fields = safe_item_fields(meta.get("fields"))
            item_values = safe_item_values(item_fields, meta.get("values"))
            structured_item_text = " ".join(
                [
                    *(field["label"] for field in item_fields),
                    *(str(value) for value in item_values.values()),
                ]
            )
            fields = (
                meta["id"],
                meta["type"],
                self._as_text(meta.get("title")),
                description,
                self._as_text(meta.get("start_date")),
                self._as_text(meta.get("start_time")),
                self._as_text(meta.get("end_time")),
                content,
                structured_log_text,
                structured_item_text,
                self._as_text(meta.get("url")),
            )
            if not any(needle in field.casefold() for field in fields):
                continue

            snippet = None
            if needle in description.casefold():
                snippet = self._matching_snippet(description, clean_query)
            elif needle in content.casefold():
                snippet = self._matching_snippet(content, clean_query)

            results.append(
                {
                    "id": meta["id"],
                    "type": meta["type"],
                    "title": self._display_title(meta),
                    "snippet": snippet,
                    "path": self._path_from_home(meta["id"], index),
                }
            )

        results.sort(key=self._summary_sort_key)
        response: dict[str, Any] = {"query": clean_query, "results": results}
        if errors:
            response["read_warnings"] = errors
        return response

    def get_pages(self) -> dict[str, Any]:
        index, errors = self._load_index()
        parents = self._parent_index(index)
        ordered_ids = self._breadth_first_ids(index)
        linked_ids = {
            node_id
            for node_id in ordered_ids
            if node_id in index and index[node_id]["type"] == "page"
        }

        page_ids = [
            node_id
            for node_id in ordered_ids
            if node_id in index and index[node_id]["type"] == "page"
        ]
        page_ids.extend(
            sorted(
                (
                    node_id
                    for node_id, meta in index.items()
                    if meta["type"] == "page" and node_id not in linked_ids
                ),
                key=lambda node_id: (
                    self._display_title(index[node_id]).casefold(),
                    node_id,
                ),
            )
        )

        pages = []
        for node_id in page_ids:
            item = self._normalize(index[node_id], index, parents, include_content=False)
            item["path"] = self._path_from_home(node_id, index)
            item["linked_from_home"] = node_id in linked_ids
            pages.append(item)

        response: dict[str, Any] = {"pages": pages}
        if errors:
            response["read_warnings"] = errors
        return response

    def get_change_log(self) -> dict[str, Any]:
        """Read release notes shipped with the code, independently of memory."""
        path = self.project_root / "change_log.json"
        try:
            entries = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            entries = []
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ReadServiceError("MOSS change log could not be read.") from error
        if not isinstance(entries, list) or any(
            not isinstance(entry, dict)
            or not isinstance(entry.get("version"), str)
            or not isinstance(entry.get("date"), str)
            or not isinstance(entry.get("changes"), list)
            or any(not isinstance(change, str) for change in entry["changes"])
            for entry in entries
        ):
            raise ReadServiceError("MOSS change log has an invalid format.")
        return {
            "current_version": entries[0]["version"] if entries else None,
            "entries": entries,
        }

    def get_action_log(self, limit: int = 250) -> dict[str, Any]:
        """Return recent action-log lines without invoking Memory or changing the log."""
        path = self.logs_root / "action_log.txt"
        if not path.exists():
            return {"entries": [], "total": 0}
        if not path.is_file():
            raise ReadServiceError("MOSS action log is not a file.")
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError) as error:
            raise ReadServiceError("MOSS action log could not be read.") from error

        clean_limit = max(1, min(int(limit), 1000))
        start = max(0, len(lines) - clean_limit)
        entries = []
        for offset, raw_line in enumerate(lines[start:], start=start + 1):
            timestamp, separator, action = raw_line.partition(" — ")
            clean_action = action if separator else raw_line
            verb, kind = self._classify_action(clean_action)
            entries.append(
                {
                    "line": offset,
                    "timestamp": timestamp if separator else None,
                    "action": clean_action,
                    "verb": verb,
                    "kind": kind,
                }
            )
        entries.reverse()
        return {"entries": entries, "total": len(lines)}

    @staticmethod
    def _classify_action(action: str) -> tuple[str, str]:
        """Give log records a small display category without changing their text."""
        first_word = str(action or "").strip().partition(" ")[0].casefold().strip(":")
        if first_word in {"created", "imported", "restored"}:
            kind = "create"
        elif first_word in {"linked", "moved", "reordered"}:
            kind = "link"
        elif first_word in {"trashed", "deleted", "removed", "unlinked"}:
            kind = "remove"
        elif first_word in {"started", "ended"}:
            kind = "session"
        elif first_word in {
            "added",
            "set",
            "updated",
            "edited",
            "opened",
            "completed",
            "reopened",
        }:
            kind = "change"
        else:
            kind = "other"
        return first_word or "record", kind

    def resolve_material_request(self, material_path: str) -> Path:
        return self._resolve_material_path(material_path, request_path=True)

    def _load_index(self) -> tuple[dict[str, dict[str, Any]], list[str]]:
        if not self.nodes_root.is_dir():
            raise ReadServiceError(f"MOSS nodes directory was not found: {self.nodes_root}")

        index: dict[str, dict[str, Any]] = {}
        errors: list[str] = []
        try:
            paths = sorted(self.nodes_root.iterdir(), key=lambda path: path.name.casefold())
        except OSError as error:
            raise ReadServiceError("MOSS nodes could not be listed.") from error

        for path in paths:
            if not path.is_dir() or not (path / "node.json").is_file():
                continue
            try:
                node_id = self._validate_node_id(path.name)
                index[node_id] = self._load_meta(node_id)
            except ReadServiceError as error:
                errors.append(str(error))
        return index, errors

    def _load_meta(self, node_id: str) -> dict[str, Any]:
        clean_id = self._validate_node_id(node_id)
        path = self.nodes_root / clean_id / "node.json"
        if not path.is_file():
            raise NodeNotFoundError(f"Node not found: {clean_id}")

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise MalformedNodeError(f"Node {clean_id} has an unreadable node.json.") from error
        if not isinstance(raw, dict):
            raise MalformedNodeError(f"Node {clean_id} node.json must contain an object.")

        stored_id = raw.get("id", clean_id)
        if stored_id != clean_id:
            raise MalformedNodeError(
                f"Node {clean_id} has a mismatched id in node.json."
            )

        node_type = raw.get("type", "text")
        if not isinstance(node_type, str) or not node_type.strip():
            raise MalformedNodeError(f"Node {clean_id} has an invalid type.")

        children = raw.get("children", [])
        if not isinstance(children, list):
            raise MalformedNodeError(f"Node {clean_id} has an invalid children list.")
        clean_children = []
        for child_id in children:
            if not isinstance(child_id, str):
                raise MalformedNodeError(
                    f"Node {clean_id} contains a non-text child reference."
                )
            try:
                clean_children.append(self._validate_node_id(child_id))
            except MalformedNodeError as error:
                raise MalformedNodeError(
                    f"Node {clean_id} contains an unsafe child reference."
                ) from error

        meta = normalize_node_meta(raw, clean_id)
        meta["type"] = node_type.strip()
        meta["children"] = clean_children
        return meta

    def _read_content(self, node_id: str) -> str:
        clean_id = self._validate_node_id(node_id)
        path = self.nodes_root / clean_id / "content.txt"
        if not path.exists():
            return ""
        if not path.is_file():
            raise MalformedNodeError(f"Node {clean_id} content.txt is not a file.")
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise MalformedNodeError(f"Node {clean_id} has unreadable content.") from error

    def _normalize(
        self,
        meta: dict[str, Any],
        index: dict[str, dict[str, Any]],
        parents: dict[str, list[str]],
        *,
        include_content: bool = True,
    ) -> dict[str, Any]:
        node_id = meta["id"]
        node_type = meta["type"]
        raw_content = self._read_content(node_id) if include_content else ""
        event_day = self._day_number(
            meta.get("day"),
            default=schema_default(node_type, "day", 1),
        )
        schema = get_node_schema_or_none(node_type)
        safe_attribute_names = SYSTEM_API_ATTRIBUTES
        if schema is not None:
            safe_attribute_names = (
                *safe_attribute_names,
                *(item.name for item in schema.attributes if not item.top_level_only),
            )
        result: dict[str, Any] = {
            "id": node_id,
            "type": node_type,
            "title": self._nullable_text(meta.get("title")),
            "display_title": self._display_title(meta),
            "description": self._as_text(meta.get("description")),
            "description_visible": self._as_bool(
                meta.get("description_visible"),
                default=schema_default(node_type, "description_visible", True),
            ),
            "content": raw_content,
            "children": list(meta["children"]),
            "parents": list(parents.get(node_id, [])),
            "checked": self._as_bool(
                meta.get("checked"),
                default=schema_default(node_type, "checked", False),
            ),
            "date_completed": self._nullable_text(meta.get("date_completed")),
            "completed": self._as_bool(
                meta.get("completed"),
                default=schema_default(node_type, "completed", False),
            ),
            "start_date": self._nullable_text(meta.get("start_date")),
            "day": event_day,
            "start_time": self._nullable_text(meta.get("start_time")),
            "end_time": self._nullable_text(meta.get("end_time")),
            "count": self._positive_integer(
                meta.get("count"),
                default=schema_default(node_type, "count", 1),
            ),
            "log_id": self._nullable_text(meta.get("log_id")),
            "entry_date": self._nullable_text(meta.get("entry_date")),
            "submitted_at": self._nullable_text(meta.get("submitted_at")),
            "target_id": self._nullable_text(meta.get("target_id")),
            "prompts": safe_log_prompts(meta.get("prompts")),
            "attributes": {
                key: meta[key]
                for key in safe_attribute_names
                if key in meta and self._is_safe_json_scalar(meta[key])
            },
        }
        result["answers"] = safe_log_answers(result["prompts"], meta.get("answers"))
        result["fields"] = safe_item_fields(meta.get("fields")) if node_type == "item_list" else []
        result["item_list_id"] = None
        result["values"] = {}
        if node_type == "item":
            item_list_ids = [
                parent_id
                for parent_id in parents.get(node_id, [])
                if index.get(parent_id, {}).get("type") == "item_list"
            ]
            if len(item_list_ids) == 1:
                result["item_list_id"] = item_list_ids[0]
                result["fields"] = safe_item_fields(index[item_list_ids[0]].get("fields"))
            result["values"] = safe_item_values(result["fields"], meta.get("values"))

        if node_type == "link":
            result["url"] = safe_web_url(meta.get("url"))
            if result["url"] is None:
                result["attributes"].pop("url", None)
            else:
                result["attributes"]["url"] = result["url"]
        else:
            result["url"] = None

        result["internal_target"] = None
        if node_type == "internal_link" and result["target_id"]:
            target = index.get(result["target_id"])
            if target is not None:
                result["internal_target"] = {
                    "id": target["id"],
                    "type": target["type"],
                    "title": self._display_title(target),
                }

        if node_type == "randomizer":
            phrases = list(
                dict.fromkeys(
                    line.strip() for line in raw_content.splitlines() if line.strip()
                )
            )
            count = result["count"]
            result["random_selection"] = (
                phrases
                if count >= len(phrases)
                else random.sample(phrases, count)
            )
        else:
            result["random_selection"] = []

        if node_type == "image":
            source_value = raw_content.strip() or meta.get("source")
            result.update(self._material_information(source_value))
        else:
            result.update(
                {
                    "source": None,
                    "material_url": None,
                    "material_exists": False,
                    "material_status": "not_applicable",
                }
            )
        return result

    def _child_details(
        self,
        meta: dict[str, Any],
        index: dict[str, dict[str, Any]],
        parents: dict[str, list[str]],
        *,
        remaining_depth: int,
        active_ids: set[str],
    ) -> list[dict[str, Any]]:
        details = []
        encountered: set[str] = set()
        for child_id in meta["children"]:
            if child_id in encountered or child_id in active_ids:
                repeated = self._missing_child(child_id)
                if child_id in index:
                    repeated = self._normalize(index[child_id], index, parents)
                repeated["repeated_reference"] = True
                details.append(repeated)
                continue
            encountered.add(child_id)

            child = index.get(child_id)
            if child is None:
                details.append(self._missing_child(child_id))
                continue

            item = self._normalize(child, index, parents)
            item["repeated_reference"] = False
            if remaining_depth > 0 and child["type"] in EXPANDABLE_CHILD_TYPES:
                item["child_nodes"] = self._child_details(
                    child,
                    index,
                    parents,
                    remaining_depth=remaining_depth - 1,
                    active_ids={*active_ids, child_id},
                )
            details.append(item)
        return details

    def _material_information(self, source: Any) -> dict[str, Any]:
        if not isinstance(source, str) or not source.strip():
            return {
                "source": None,
                "material_url": None,
                "material_exists": False,
                "material_status": "not_configured",
            }
        try:
            path = self._resolve_material_path(source, require_file=False)
        except UnsafeMaterialPathError:
            return {
                "source": None,
                "material_url": None,
                "material_exists": False,
                "material_status": "blocked",
            }

        relative = path.relative_to(self.materials_root.resolve()).as_posix()
        encoded = "/".join(quote(part, safe="") for part in relative.split("/"))
        exists = path.is_file()
        return {
            "source": relative,
            "material_url": f"/materials/{encoded}" if exists else None,
            "material_exists": exists,
            "material_status": "ready" if exists else "missing",
        }

    def _resolve_material_path(
        self,
        source: str,
        *,
        request_path: bool = False,
        require_file: bool = True,
    ) -> Path:
        if not isinstance(source, str):
            raise UnsafeMaterialPathError("Material path must be text.")
        value = source.strip()
        if not value or "\x00" in value or "\\" in value:
            raise UnsafeMaterialPathError("Material path is invalid.")

        materials_root = self.materials_root.resolve()
        if request_path:
            if value.startswith("/") or "://" in value:
                raise UnsafeMaterialPathError("Material path must be relative.")
            candidate = materials_root / value
        elif value.startswith("/materials/"):
            candidate = materials_root / value.removeprefix("/materials/")
        else:
            supplied = Path(value)
            if supplied.is_absolute():
                candidate = supplied
            else:
                parts = supplied.parts
                if parts[:2] == ("memory", "materials"):
                    supplied = Path(*parts[2:])
                elif parts[:1] == ("materials",):
                    supplied = Path(*parts[1:])
                candidate = materials_root / supplied

        resolved = candidate.resolve(strict=False)
        try:
            resolved.relative_to(materials_root)
        except ValueError as error:
            raise UnsafeMaterialPathError(
                "Material path is outside memory/materials."
            ) from error
        if require_file and not resolved.is_file():
            raise MaterialNotFoundError("Material was not found.")
        return resolved

    def _parent_index(
        self,
        index: dict[str, dict[str, Any]],
    ) -> dict[str, list[str]]:
        parents: dict[str, list[str]] = {}
        for parent_id, meta in index.items():
            for child_id in meta["children"]:
                parents.setdefault(child_id, []).append(parent_id)
        for values in parents.values():
            values.sort()
        return parents

    def _path_from_home(
        self,
        target_id: str,
        index: dict[str, dict[str, Any]],
    ) -> list[dict[str, str]]:
        if target_id == "home" and "home" in index:
            return [self._breadcrumb(index["home"])]
        if "home" not in index or target_id not in index:
            return []

        queue: deque[tuple[str, list[str]]] = deque([("home", ["home"])])
        seen = {"home"}
        while queue:
            node_id, path = queue.popleft()
            for child_id in index[node_id]["children"]:
                if child_id not in index or child_id in seen:
                    continue
                child_path = [*path, child_id]
                if child_id == target_id:
                    return [self._breadcrumb(index[current]) for current in child_path]
                seen.add(child_id)
                queue.append((child_id, child_path))

        return [self._breadcrumb(index["home"]), self._breadcrumb(index[target_id])]

    def _reachable_from_home(self, index: dict[str, dict[str, Any]]) -> set[str]:
        return set(self._breadth_first_ids(index))

    def _breadth_first_ids(self, index: dict[str, dict[str, Any]]) -> list[str]:
        if "home" not in index:
            return []
        ordered = []
        queue = deque(["home"])
        seen = {"home"}
        while queue:
            node_id = queue.popleft()
            ordered.append(node_id)
            for child_id in index[node_id]["children"]:
                if child_id in index and child_id not in seen:
                    seen.add(child_id)
                    queue.append(child_id)
        return ordered

    def _tree_summary(self, meta: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": meta["id"],
            "type": meta["type"],
            "title": self._display_title(meta),
        }

    def _breadcrumb(self, meta: dict[str, Any]) -> dict[str, str]:
        return {
            "id": meta["id"],
            "type": meta["type"],
            "title": self._display_title(meta),
        }

    def _missing_child(self, node_id: str) -> dict[str, Any]:
        return {
            "id": node_id,
            "type": "missing",
            "title": node_id,
            "display_title": node_id,
            "missing": True,
            "children": [],
            "child_nodes": [],
        }

    def _validate_node_id(self, node_id: Any) -> str:
        if not isinstance(node_id, str) or not NODE_ID_PATTERN.fullmatch(node_id):
            raise MalformedNodeError("Node ID is invalid.")
        return node_id

    def _display_title(self, meta: dict[str, Any]) -> str:
        title = self._nullable_text(meta.get("title"))
        if title:
            return title
        if meta.get("type") == "week":
            try:
                start = date.fromisoformat(str(meta.get("start_date", "")))
            except ValueError:
                pass
            else:
                end = start + timedelta(days=6)
                return f"{start.strftime('%b')} {start.day} – {end.strftime('%b')} {end.day}, {end.year}"
        if meta.get("type") == "log_entry":
            entry_date = self._nullable_text(meta.get("entry_date"))
            if entry_date:
                return entry_date
        return meta["id"]

    @staticmethod
    def _as_text(value: Any) -> str:
        return value if isinstance(value, str) else ""

    @staticmethod
    def _nullable_text(value: Any) -> str | None:
        return value if isinstance(value, str) and value else None

    @staticmethod
    def _as_bool(value: Any, *, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            if value.casefold() in {"true", "1"}:
                return True
            if value.casefold() in {"false", "0"}:
                return False
        return default

    @staticmethod
    def _positive_integer(value: Any, *, default: int) -> int:
        if isinstance(value, int) and not isinstance(value, bool) and value > 0:
            return value
        return default

    @staticmethod
    def _day_number(value: Any, *, default: int) -> int:
        if isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 7:
            return value
        if isinstance(value, str):
            try:
                parsed = int(value)
            except ValueError:
                return default
            if 1 <= parsed <= 7:
                return parsed
        return default

    @staticmethod
    def _is_safe_json_scalar(value: Any) -> bool:
        return value is None or isinstance(value, (str, int, float, bool))

    @staticmethod
    def _matching_snippet(text: str, query: str, radius: int = 70) -> str:
        compact = re.sub(r"\s+", " ", text).strip()
        index = compact.casefold().find(query.casefold())
        if index < 0:
            return compact[: radius * 2]
        start = max(0, index - radius)
        end = min(len(compact), index + len(query) + radius)
        prefix = "…" if start else ""
        suffix = "…" if end < len(compact) else ""
        return f"{prefix}{compact[start:end].strip()}{suffix}"

    @staticmethod
    def _summary_sort_key(item: dict[str, Any]) -> tuple[str, str]:
        title = item.get("title") or item.get("display_title") or item.get("id", "")
        return str(title).casefold(), str(item.get("id", ""))
