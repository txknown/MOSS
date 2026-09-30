import hashlib
import json
import tempfile
import unittest
import zipfile
from datetime import datetime
from pathlib import Path

from action_types import set_attribute
from core.action_runner import ActionRunner
from core.memory import Memory
from core.renderer import render_node
from core.search import format_search_results, search_nodes
from core.snapshots import list_snapshot_records
from tools.import_todos import import_todos
from web.read_service import ReadService


class MossV02Tests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "version.txt").write_text("MOSS v0.2\n", encoding="utf-8")
        self.memory = Memory(project_root=self.root)
        self.actions = ActionRunner(self.memory)

    def tearDown(self):
        self.temporary.cleanup()

    def create(self, node_type, node_id=None, content=""):
        return self.actions.run(
            "create_node",
            {"type": node_type, "id": node_id, "content": content},
            log=False,
        )["node_id"]

    def test_page_descriptions_render_hide_report_defaults_and_search(self):
        page_id = self.create("page", "projects")
        raw = json.loads(self.memory.meta_path(page_id).read_text(encoding="utf-8"))
        self.assertEqual(raw["description"], "")
        self.assertIs(raw["description_visible"], True)

        self.actions.run("set_attribute", {"node_id": page_id, "field": "title", "value": "Projects"}, log=False)
        self.actions.run(
            "set_attribute",
            {"node_id": page_id, "field": "description", "value": "Active projects and supporting material."},
            log=False,
        )
        visible = render_node(self.memory, page_id)
        self.assertTrue(visible.startswith("Projects\nActive projects"))

        self.actions.run(
            "set_attribute",
            {"node_id": page_id, "field": "description_visible", "value": False},
            log=False,
        )
        self.assertNotIn("supporting material", render_node(self.memory, page_id))
        results = search_nodes(self.memory, "supporting material")
        self.assertEqual([result["id"] for result in results], [page_id])
        self.assertIn("supporting material", format_search_results("supporting material", results))

        legacy_id = self.create("page", "legacy")
        legacy = json.loads(self.memory.meta_path(legacy_id).read_text(encoding="utf-8"))
        legacy.pop("description")
        legacy.pop("description_visible")
        self.memory.meta_path(legacy_id).write_text(json.dumps(legacy), encoding="utf-8")
        loaded = self.memory.load_meta(legacy_id)
        self.assertEqual(loaded["description"], "")
        self.assertIs(loaded["description_visible"], True)

    def test_page_and_randomizer_attribute_validation(self):
        page_id = self.create("page", "page_validation")
        with self.assertRaisesRegex(ValueError, "description_visible must be true or false"):
            self.actions.run(
                "set_attribute",
                {"node_id": page_id, "field": "description_visible", "value": "maybe"},
                log=False,
            )
        with self.assertRaisesRegex(ValueError, "Unknown attribute"):
            self.actions.run(
                "set_attribute",
                {"node_id": page_id, "field": "descripton", "value": "typo"},
                log=False,
            )

        text_id = self.create("text", "styled_text")
        self.actions.run(
            "update_node",
            {
                "node_id": text_id,
                "attributes": {"size": "30px", "font": "sans"},
            },
            log=False,
        )
        styled = self.memory.load_meta(text_id)
        self.assertEqual(styled["size"], "30px")
        self.assertEqual(styled["font"], "sans")

        randomizer_id = self.create("randomizer", "choices")
        self.assertEqual(self.memory.load_meta(randomizer_id)["display_mode"], "list")
        for invalid in (0, -1, "nope", True):
            with self.assertRaisesRegex(ValueError, "integer greater than zero"):
                self.actions.run(
                    "set_attribute",
                    {"node_id": randomizer_id, "field": "count", "value": invalid},
                    log=False,
                )
        self.actions.run(
            "set_attribute",
            {"node_id": randomizer_id, "field": "display_mode", "value": "TEXT"},
            log=False,
        )
        self.assertEqual(self.memory.load_meta(randomizer_id)["display_mode"], "text")
        with self.assertRaisesRegex(ValueError, "must be list or text"):
            self.actions.run(
                "set_attribute",
                {"node_id": randomizer_id, "field": "display_mode", "value": "cards"},
                log=False,
            )

    def test_calendar_week_and_event_nodes_share_core_actions(self):
        calendar_id = self.create("calendar", "schedule")
        week_id = self.create("week", "week_2026_08_31")
        event_id = self.create("event", "event_planning")

        self.memory.add_child(calendar_id, week_id)
        self.memory.add_child(week_id, event_id)
        self.actions.run(
            "set_attribute",
            {"node_id": calendar_id, "field": "title", "value": "Calendar"},
            log=False,
        )
        self.actions.run(
            "set_attribute",
            {"node_id": week_id, "field": "start_date", "value": "2026-08-31"},
            log=False,
        )
        self.actions.run(
            "set_attribute",
            {"node_id": event_id, "field": "title", "value": "Planning"},
            log=False,
        )
        self.actions.run(
            "set_attribute",
            {"node_id": event_id, "field": "description", "value": "Review the next steps."},
            log=False,
        )
        self.actions.run(
            "set_attribute",
            {"node_id": event_id, "field": "day", "value": 2},
            log=False,
        )
        self.actions.run(
            "set_attribute",
            {"node_id": event_id, "field": "start_time", "value": "09:00"},
            log=False,
        )
        self.actions.run(
            "set_attribute",
            {"node_id": event_id, "field": "end_time", "value": "10:30"},
            log=False,
        )

        rendered = render_node(self.memory, calendar_id)
        self.assertIn("Week of Aug 31 – Sep 6, 2026", rendered)
        self.assertIn("Planning", rendered)
        self.assertIn("Tuesday, 09:00–10:30", rendered)
        self.assertIn("Review the next steps.", rendered)

        with self.assertRaisesRegex(ValueError, "must be a Monday"):
            self.actions.run(
                "set_attribute",
                {"node_id": week_id, "field": "start_date", "value": "2026-09-01"},
                log=False,
            )
        with self.assertRaisesRegex(ValueError, "integer from 1 to 7"):
            self.actions.run(
                "set_attribute",
                {"node_id": event_id, "field": "day", "value": 8},
                log=False,
            )
        with self.assertRaisesRegex(ValueError, "later than start_time"):
            self.actions.run(
                "set_attribute",
                {"node_id": event_id, "field": "end_time", "value": "08:00"},
                log=False,
            )
        self.assertEqual(self.memory.load_meta(event_id)["end_time"], "10:30")

    def test_create_event_is_one_composite_logged_action(self):
        week_id = self.create("week", "week_2026_08_31")
        self.actions.run(
            "set_attribute",
            {"node_id": week_id, "field": "start_date", "value": "2026-08-31"},
            log=False,
        )
        log_path = self.memory.logs / "action_log.txt"
        before = log_path.read_text(encoding="utf-8").splitlines()

        result = self.actions.run(
            "create_event",
            {
                "week_id": week_id,
                "title": "Planning",
                "description": "Review the next steps.",
                "day": 2,
                "start_time": "09:00",
                "end_time": "10:30",
            },
        )

        event = self.memory.load_meta(result["node_id"])
        after = log_path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(after), len(before) + 1)
        self.assertEqual(event["day"], 2)
        self.assertEqual(event["start_time"], "09:00")
        self.assertEqual(event["end_time"], "10:30")
        self.assertIn(result["node_id"], self.memory.load_meta(week_id)["children"])
        self.assertIn(f"created event {result['node_id']} in {week_id}", after[-1])

    def test_todo_completion_date_rendering_and_ordering(self):
        list_id = self.create("todo_list", "test_todos")
        first = self.create("todo_item", "first", "Test completion date\n")
        second = self.create("todo_item", "second", "Still open\n")
        self.memory.add_child(list_id, first)
        self.memory.add_child(list_id, second)

        self.actions.run(
            "set_attribute",
            {"node_id": first, "field": "checked", "value": True},
        )
        completed = self.memory.load_meta(first)
        self.assertIs(completed["checked"], True)
        self.assertEqual(completed["date_completed"], datetime.now().astimezone().strftime("%Y-%m-%d"))
        self.assertIn("[x] Test completion date", render_node(self.memory, list_id))
        self.assertEqual(self.memory.load_meta(list_id)["children"], [second, first])
        original_date = completed["date_completed"]

        self.actions.run(
            "set_attribute",
            {"node_id": first, "field": "checked", "value": True},
            log=False,
        )
        self.assertEqual(self.memory.load_meta(first)["date_completed"], original_date)
        with self.assertRaisesRegex(ValueError, "managed automatically"):
            self.actions.run(
                "set_attribute",
                {"node_id": first, "field": "date_completed", "value": "2020-01-01"},
                log=False,
            )

        self.actions.run(
            "set_attribute",
            {"node_id": first, "field": "checked", "value": False},
            log=False,
        )
        self.assertIsNone(self.memory.load_meta(first)["date_completed"])
        self.assertIn("[ ] Test completion date", render_node(self.memory, list_id))
        self.assertIn("completed first", (self.memory.logs / "action_log.txt").read_text(encoding="utf-8"))

    def test_randomizer_is_distinct_and_read_only(self):
        randomizer_id = self.create("randomizer", "test_randomizer", "One\nTwo\nThree\nFour\n")
        self.actions.run(
            "set_attribute",
            {"node_id": randomizer_id, "field": "count", "value": 2},
            log=False,
        )
        before = self._memory_digest()
        lines = render_node(self.memory, randomizer_id).splitlines()
        after = self._memory_digest()
        self.assertEqual(len(lines[1:]), 2)
        self.assertEqual(len(set(lines[1:])), 2)
        self.assertEqual(before, after)

    def test_randomizer_title_defaults_hidden_without_migrating_legacy_nodes(self):
        node_id = self.create("randomizer", "example_randomizer", "Example phrase.")
        meta = self.memory.load_meta(node_id)
        self.assertIs(meta["title_visible"], False)
        meta["title"] = "Example title"
        meta.pop("title_visible")
        self.memory.save_meta(node_id, meta)
        self.memory.add_child("home", node_id)
        before = self._memory_digest()
        parent = render_node(self.memory, "home")
        self.assertNotIn("Example title", parent)
        self.assertIn("Example phrase.", parent)
        self.assertIn("Example title", render_node(self.memory, node_id))
        service = ReadService(self.root)
        self.assertIs(service.get_node(node_id)["attributes"]["title_visible"], False)
        self.assertIs(service.get_node("home")["child_nodes"][0]["attributes"]["title_visible"], False)
        self.assertEqual(self._memory_digest(), before)
        self.actions.run("update_node", {
            "node_id": node_id, "attributes": {"title_visible": True},
        })
        self.assertIn("Example title", render_node(self.memory, "home"))
        self.assertIs(service.get_node(node_id)["attributes"]["title_visible"], True)
        with self.assertRaises(ValueError):
            self.actions.run("update_node", {
                "node_id": node_id, "attributes": {"title_visible": "invalid"},
            })

    def test_relative_reordering(self):
        parent = self.create("page", "notes")
        for child in ("child_a", "child_b", "child_c"):
            self.create("text", child)
            self.memory.add_child(parent, child)

        self.actions.run(
            "move_child",
            {"parent_id": parent, "child_id": "child_c", "position": "before", "reference_id": "child_a"},
            log=False,
        )
        self.assertEqual(self.memory.load_meta(parent)["children"], ["child_c", "child_a", "child_b"])
        self.actions.run(
            "move_child",
            {"parent_id": parent, "child_id": "child_c", "position": "after", "reference_id": "child_b"},
            log=False,
        )
        self.assertEqual(self.memory.load_meta(parent)["children"], ["child_a", "child_b", "child_c"])
        self.actions.run(
            "move_child",
            {"parent_id": parent, "child_id": "child_c", "position": "top"},
            log=False,
        )
        self.assertEqual(self.memory.load_meta(parent)["children"], ["child_c", "child_a", "child_b"])
        self.actions.run(
            "move_child",
            {"parent_id": parent, "child_id": "child_c", "position": "bottom"},
            log=False,
        )
        self.assertEqual(self.memory.load_meta(parent)["children"], ["child_a", "child_b", "child_c"])
        with self.assertRaisesRegex(ValueError, "not a child"):
            self.actions.run(
                "move_child",
                {"parent_id": parent, "child_id": "missing", "position": "after", "reference_id": "child_b"},
                log=False,
            )

    def test_item_lists_share_one_field_structure(self):
        item_list = self.create("item_list", "wardrobe")
        self.actions.run(
            "update_item_list_fields",
            {
                "node_id": item_list,
                "fields": [
                    {"id": "rating", "label": "Rating / 10"},
                    {"id": "color", "label": "Color"},
                ],
            },
            log=False,
        )
        item = self.actions.run(
            "create_item",
            {
                "parent_id": item_list,
                "id": "green_shirt",
                "title": "Green shirt",
                "values": {"rating": 9, "color": "forest"},
            },
            log=False,
        )["node_id"]
        self.assertEqual(self.memory.load_meta(item)["values"], {"rating": 9, "color": "forest"})

        with self.assertRaisesRegex(ValueError, "Unknown item fields: size"):
            self.actions.run(
                "update_item",
                {
                    "node_id": item,
                    "values": {"rating": 8, "color": "green", "size": "M"},
                },
                log=False,
            )

        self.actions.run(
            "update_item_list_fields",
            {
                "node_id": item_list,
                "fields": [
                    {"id": "rating", "label": "Score"},
                    {"id": "season", "label": "Season"},
                ],
            },
            log=False,
        )
        self.assertEqual(self.memory.load_meta(item)["values"], {"rating": 9, "season": ""})

        other_list = self.create("item_list", "other_wardrobe")
        with self.assertRaisesRegex(ValueError, "already belongs to item list wardrobe"):
            self.actions.run(
                "link_node",
                {"parent_id": other_list, "child_id": item},
                log=False,
            )

    def test_todo_items_can_have_ordered_child_todos(self):
        todo_list = self.create("todo_list", "nested_list")
        parent = self.actions.run(
            "create_child",
            {
                "parent_id": todo_list,
                "type": "todo_item",
                "id": "parent_todo",
                "content": "Parent",
                "attributes": {},
            },
            log=False,
        )["node_id"]
        for node_id, content in (("child_one", "First child"), ("child_two", "Second child")):
            self.actions.run(
                "create_child",
                {
                    "parent_id": parent,
                    "type": "todo_item",
                    "id": node_id,
                    "content": content,
                    "attributes": {},
                },
                log=False,
            )
        self.actions.run(
            "set_attribute",
            {"node_id": "child_one", "field": "checked", "value": True},
            log=False,
        )

        self.assertEqual(
            self.memory.load_meta(parent)["children"],
            ["child_one", "child_two"],
        )
        rendered = render_node(self.memory, todo_list)
        self.assertLess(rendered.index("[x] First child"), rendered.index("[ ] Second child"))

    def test_relationship_noops_do_not_write_or_log(self):
        parent = self.create("page", "parent")
        child = self.create("text", "child")
        self.actions.run(
            "link_node",
            {"parent_id": parent, "child_id": child},
            log=False,
        )
        before = self._memory_digest()

        with self.assertRaisesRegex(ValueError, "already linked"):
            self.actions.run(
                "link_node",
                {"parent_id": parent, "child_id": child},
            )
        with self.assertRaisesRegex(ValueError, "already in that position"):
            self.actions.run(
                "move_child",
                {"parent_id": parent, "child_id": child, "direction": "up"},
            )
        with self.assertRaisesRegex(ValueError, "not linked"):
            self.actions.run(
                "unlink_node",
                {"parent_id": parent, "child_id": "home"},
            )

        self.assertEqual(before, self._memory_digest())

    def test_snapshot_contents_and_no_overwrite(self):
        result = self.actions.run("snapshot", {"name": "test_snapshot"})
        path = Path(result["path"])
        before = path.read_bytes()
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            self.assertIn("SNAPSHOT.txt", names)
            self.assertIn("version.txt", names)
            self.assertIn("memory/nodes/home/node.json", names)
            snapshot_text = archive.read("SNAPSHOT.txt").decode("utf-8")
            self.assertIn("Snapshot: test_snapshot", snapshot_text)
            self.assertIn("MOSS version: v0.2", snapshot_text)
        records = list_snapshot_records(self.root)
        self.assertEqual([item["name"] for item in records], ["test_snapshot"])
        self.assertEqual(records[0]["status"], "ready")
        self.assertGreater(records[0]["node_count"], 0)
        with self.assertRaisesRegex(FileExistsError, "Snapshot already exists: test_snapshot"):
            self.actions.run("snapshot", {"name": "test_snapshot"})
        self.assertEqual(path.read_bytes(), before)

    def test_search_no_results(self):
        self.assertEqual(format_search_results("absent", search_nodes(self.memory, "absent")), "Search: absent\n\nNo results")

    def test_importer_dry_run_then_real_import(self):
        target = self.create("todo_list", "test_todos")
        source = self.root / "todos.txt"
        source.write_text("- First\n[ ] Second\n- [ ] Third\n\n", encoding="utf-8")
        before = self._memory_digest()
        dry_target, todos, created = import_todos(self.root, target, source, dry_run=True)
        self.assertEqual((dry_target, todos, created), (target, ["First", "Second", "Third"], []))
        self.assertEqual(before, self._memory_digest())

        _, _, created = import_todos(self.root, target, source)
        self.assertEqual(len(created), 3)
        self.assertEqual(self.memory.load_meta(target)["children"], created)
        for node_id, text in zip(created, ("First", "Second", "Third")):
            meta = self.memory.load_meta(node_id)
            self.assertIs(meta["checked"], False)
            self.assertIsNone(meta["date_completed"])
            self.assertEqual(self.memory.read_content(node_id).strip(), text)
        log = (self.memory.logs / "action_log.txt").read_text(encoding="utf-8")
        self.assertEqual(log.count("imported 3 todo items into test_todos"), 1)

    def test_core_version_logs_once(self):
        self.actions.run("update_core_version", {"version": "v0.2"})
        self.actions.run("update_core_version", {"version": "v0.2"})
        log = (self.memory.logs / "action_log.txt").read_text(encoding="utf-8")
        self.assertEqual(log.count("updated core to v0.2"), 1)

    def _memory_digest(self):
        digest = hashlib.sha256()
        for path in sorted(self.memory.root.rglob("*")):
            if path.is_file():
                digest.update(str(path.relative_to(self.memory.root)).encode())
                digest.update(path.read_bytes())
        return digest.hexdigest()


if __name__ == "__main__":
    unittest.main()
