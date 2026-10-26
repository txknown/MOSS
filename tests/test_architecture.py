import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from core.action_catalog import ACTION_SPECS, action_type_names, public_action_types
from core.action_runner import ActionRunner
from core.memory import Memory
from core.node_normalization import normalize_node_meta
from core.node_schema import (
    NODE_SCHEMAS,
    attribute_defaults,
    public_schema,
    validate_node_schemas,
)
from core.registry import known_action_types, known_node_types, load_node_type
from web.read_service import ReadService


class NodeSchemaArchitectureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.memory = Memory(project_root=self.root)
        self.actions = ActionRunner(self.memory)

    def tearDown(self):
        self.temporary.cleanup()

    def test_new_todos_prepend_without_reordering_existing_children(self):
        for parent_type in ("todo_list", "todo_item"):
            parent_id = f"ordered_{parent_type}"
            self.actions.run("create_node", {"type": parent_type, "id": parent_id})
            original = []
            for suffix in ("first", "done", "last"):
                child_id = f"{parent_id}_{suffix}"
                self.actions.run("create_node", {"type": "todo_item", "id": child_id})
                self.memory.add_child(parent_id, child_id)
                original.append(child_id)
            self.actions.run("update_node", {
                "node_id": original[1], "attributes": {"checked": True},
            })
            original = list(self.memory.load_meta(parent_id)["children"])
            original_bytes = {p: p.read_bytes() for id in original for p in self.memory.node_path(id).iterdir()}
            log_before = self.actions.action_log_path.read_text().splitlines()
            result = self.actions.run("create_child", {
                "parent_id": parent_id, "type": "todo_item", "content": "Newest task",
            })
            self.assertEqual(self.memory.load_meta(parent_id)["children"], [result["node_id"], *original])
            self.assertEqual(len(self.actions.action_log_path.read_text().splitlines()), len(log_before) + 1)
            self.assertEqual(original_bytes, {p: p.read_bytes() for p in original_bytes})
            before = {p: p.read_bytes() for p in self.memory.root.rglob("*") if p.is_file()}
            node = ReadService(self.root).get_node(parent_id)
            self.assertEqual([child["id"] for child in node["child_nodes"]], [result["node_id"], *original])
            self.assertEqual(before, {p: p.read_bytes() for p in self.memory.root.rglob("*") if p.is_file()})

        # Ordinary page children keep their append behavior.
        for id in ("first_note", "second_note"):
            self.actions.run("create_child", {"parent_id": "home", "type": "note", "id": id})
        self.assertEqual(self.memory.load_meta("home")["children"], ["first_note", "second_note"])

    def test_todo_and_calendar_composer_rendering(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js is not installed")
        subprocess.run([node, str(Path(__file__).with_name("test_composers.mjs"))], check=True, capture_output=True)

    def test_week_notes_and_todo_descriptions_round_trip_without_mutating_reads(self):
        self.actions.run("create_node", {"type": "week", "id": "week_notes"})
        self.actions.run("create_node", {"type": "todo_list", "id": "described_todos"})
        before = {p: p.read_bytes() for p in self.memory.root.rglob("*") if p.is_file()}
        service = ReadService(self.root)
        self.assertEqual(service.get_node("week_notes")["attributes"]["notes"], "")
        todo = service.get_node("described_todos")
        self.assertEqual(todo["description"], "")
        self.assertTrue(todo["description_visible"])
        self.assertEqual(before, {p: p.read_bytes() for p in self.memory.root.rglob("*") if p.is_file()})

        notes = "First goal\nA second thought <keep literal>"
        self.actions.run("update_node", {"node_id": "week_notes", "attributes": {"notes": notes}})
        self.actions.run("update_node", {"node_id": "described_todos", "attributes": {
            "description": "Tasks for this project", "description_visible": False,
        }})
        before = {p: p.read_bytes() for p in self.memory.root.rglob("*") if p.is_file()}
        self.assertEqual(service.get_node("week_notes")["attributes"]["notes"], notes)
        todo = service.get_node("described_todos")
        self.assertEqual(todo["description"], "Tasks for this project")
        self.assertFalse(todo["description_visible"])
        self.assertEqual(before, {p: p.read_bytes() for p in self.memory.root.rglob("*") if p.is_file()})
        rendered = load_node_type("week").render(self.memory, self.memory.load_meta("week_notes"))
        for line in notes.splitlines():
            self.assertIn(line, rendered)
        for node_id, field in [("week_notes", "notes"), ("described_todos", "description")]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.actions.run("update_node", {"node_id": node_id, "attributes": {field: "x" * 10001}})
        self.actions.run("update_node", {"node_id": "week_notes", "attributes": {"notes": ""}})
        self.assertEqual(service.get_node("week_notes")["attributes"]["notes"], "")

    def test_stale_ui_settings_fall_back_without_repairing_files(self):
        from core.ui_settings import read_settings, DEFAULTS
        path = self.memory.system / "ui_settings.json"
        path.write_text('{"scheme":"gone", "home_style":"bad", "home_node_id":"missing"}')
        before = path.read_bytes()
        self.assertEqual(read_settings(self.memory), DEFAULTS)
        self.assertEqual(path.read_bytes(), before)
        path.write_text("broken json")
        self.assertEqual(read_settings(self.memory), DEFAULTS)
        self.assertEqual(path.read_text(), "broken json")

    def test_internal_system_targets_validate_and_project_without_mutating_reads(self):
        from core.system_views import SYSTEM_TARGETS
        from core.node_validation import validate_attribute_value

        for number, (target_id, (title, url)) in enumerate(SYSTEM_TARGETS.items()):
            result = self.actions.run("create_child", {
                "parent_id": "home", "type": "internal_link", "id": f"system_jump_{number}",
                "attributes": {"title": title, "target_id": target_id},
            })
            before = {p: p.read_bytes() for p in self.memory.root.rglob("*") if p.is_file()}
            node = ReadService(self.root).get_node(result["node_id"])
            self.assertEqual(node["internal_target"], {
                "id": target_id, "type": "system", "title": title, "url": url,
            })
            self.assertEqual(before, {p: p.read_bytes() for p in self.memory.root.rglob("*") if p.is_file()})
        for value in ["system:unknown", "system:../tree", "//example.com", "javascript:alert(1)"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_attribute_value("target_id", value, "internal_target")
        self.assertEqual(validate_attribute_value("target_id", "my_note", "internal_target"), "my_note")
        self.actions.run("create_node", {"type": "note", "id": "absent_note"})
        broken = self.actions.run("create_child", {
            "parent_id": "home", "type": "internal_link", "id": "still_broken",
            "attributes": {"title": "Missing", "target_id": "absent_note"},
        })
        self.actions.run("trash_node", {"node_id": "absent_note"})
        self.assertIsNone(ReadService(self.root).get_node(broken["node_id"])["internal_target"])

    def test_every_registered_node_has_one_valid_schema_contract(self):
        validate_node_schemas()
        self.assertEqual(tuple(known_node_types()), tuple(NODE_SCHEMAS))
        for node_type, schema in NODE_SCHEMAS.items():
            self.assertEqual(schema.name, node_type)
            self.assertEqual(len({item.name for item in schema.attributes}), len(schema.attributes))
            module = load_node_type(node_type)
            self.assertEqual(
                module.ALLOWED_ATTRIBUTES,
                tuple(item.name for item in schema.attributes),
            )
            self.assertEqual(module.ATTRIBUTE_DEFAULTS, attribute_defaults(node_type))
            self.assertEqual(
                module.ATTRIBUTE_TYPES,
                {item.name: item.value_type for item in schema.attributes},
            )
            self.assertEqual(
                module.SYSTEM_MANAGED_ATTRIBUTES,
                tuple(item.name for item in schema.attributes if item.system_managed),
            )

    def test_action_catalog_is_inert_and_matches_the_registry(self):
        self.assertEqual(tuple(known_action_types()), action_type_names())
        self.assertEqual(len(ACTION_SPECS), len(set(action_type_names())))
        payload = public_action_types({"create_child", "update_node"})
        encoded = json.dumps(payload)
        self.assertEqual(payload["catalog_version"], 1)
        self.assertEqual(
            [item["name"] for item in payload["action_types"]],
            list(action_type_names()),
        )
        available = {
            item["name"] for item in payload["action_types"] if item["browser_available"]
        }
        self.assertEqual(available, {"create_child", "update_node"})
        self.assertNotIn(str(self.root), encoded)
        self.assertNotIn("callable", encoded.casefold())

    def test_type_descriptions_are_reference_metadata_only(self):
        public_types = ReadService(self.root).get_schema()["node_types"]
        for node_type, schema in NODE_SCHEMAS.items():
            with self.subTest(node_type=node_type):
                self.assertIsInstance(schema.description, str)
                self.assertTrue(schema.description.strip())
                self.assertLessEqual(len(schema.description), 200)
                self.assertEqual(public_types[node_type]["description"], schema.description)
                created = self.memory.create_node(node_type)
                self.assertNotEqual(created.get("description"), schema.description)
                normalized = normalize_node_meta({"id": "legacy", "type": node_type}, "legacy")
                self.assertNotEqual(normalized.get("description"), schema.description)

    def test_schema_defaults_match_created_and_legacy_loaded_nodes(self):
        for node_type in NODE_SCHEMAS:
            node_id = f"schema_{node_type}"
            created = self.memory.create_node(node_type, node_id=node_id)
            for field, default in attribute_defaults(node_type).items():
                self.assertEqual(created[field], default)

            raw = {"id": node_id, "type": node_type}
            normalized = normalize_node_meta(raw, node_id)
            self.assertEqual(raw, {"id": node_id, "type": node_type})
            for field, default in attribute_defaults(node_type).items():
                self.assertEqual(normalized[field], default)

    def test_child_creation_rules_match_public_schema(self):
        schema = public_schema()["node_types"]
        for parent_type, definition in schema.items():
            allowed = definition["child_creation_types"]
            if not allowed:
                continue
            parent_id = self.actions.run(
                "create_node",
                {"type": parent_type, "id": f"parent_{parent_type}"},
                log=False,
            )["node_id"]
            child_type = allowed[0]
            result = self.actions.run(
                "create_child",
                {
                    "parent_id": parent_id,
                    "type": child_type,
                    "id": f"child_{parent_type}_{child_type}",
                },
                log=False,
            )
            self.assertIn(result["node_id"], self.memory.load_meta(parent_id)["children"])

        self.assertEqual(schema["week"]["allowed_child_types"], ["event"])
        self.assertEqual(schema["week"]["child_creation_types"], [])

        text_id = self.actions.run(
            "create_node",
            {"type": "text", "id": "parent_text"},
            log=False,
        )["node_id"]
        with self.assertRaisesRegex(ValueError, "Allowed child types: \\(none\\)"):
            self.actions.run(
                "create_child",
                {"parent_id": text_id, "type": "text"},
                log=False,
            )

    def test_public_schema_is_inert_and_json_safe(self):
        payload = public_schema()
        encoded = json.dumps(payload)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(set(payload["node_types"]), set(NODE_SCHEMAS))
        self.assertNotIn(str(self.root), encoded)
        self.assertNotIn("module", encoded.casefold())
        self.assertNotIn("callable", encoded.casefold())

        image = payload["node_types"]["image"]
        size = next(item for item in image["attributes"] if item["name"] == "size")
        self.assertEqual(size["default"], "large")
        self.assertEqual(
            [item["value"] for item in size["editor"]["suggestions"]],
            ["small", "medium", "large"],
        )

        week = payload["node_types"]["week"]
        completed = next(
            item for item in week["attributes"] if item["name"] == "completed"
        )
        self.assertIs(completed["default"], False)
        self.assertEqual(completed["type"], "boolean")
        self.assertEqual(completed["editor"]["input_type"], "checkbox")

        log = payload["node_types"]["log"]
        self.assertEqual(log["allowed_child_types"], ["log_entry"])
        self.assertEqual(log["child_creation_types"], [])
        self.assertFalse(log["relationship_editable"])
        prompts = next(item for item in log["attributes"] if item["name"] == "prompts")
        self.assertEqual(prompts["type"], "log_prompts")
        description = next(
            item for item in log["attributes"] if item["name"] == "description"
        )
        self.assertEqual(description["default"], "")
        self.assertEqual(description["editor"]["input_type"], "textarea")
        self.assertFalse(prompts["editable"])

        link = payload["node_types"]["link"]
        self.assertEqual(link["allowed_child_types"], [])
        attributes = {item["name"]: item for item in link["attributes"]}
        self.assertTrue(attributes["title"]["required"])
        self.assertTrue(attributes["url"]["required"])
        self.assertEqual(attributes["url"]["type"], "web_url")
        self.assertEqual(attributes["url"]["editor"]["input_type"], "url")

        item_list = payload["node_types"]["item_list"]
        self.assertEqual(item_list["allowed_child_types"], ["item"])
        self.assertEqual(item_list["child_creation_types"], [])
        fields = next(item for item in item_list["attributes"] if item["name"] == "fields")
        self.assertEqual(fields["default"], [])
        self.assertFalse(fields["editable"])
        item = payload["node_types"]["item"]
        values = next(attribute for attribute in item["attributes"] if attribute["name"] == "values")
        self.assertEqual(values["default"], {})

        internal_link = payload["node_types"]["internal_link"]
        internal_attributes = {
            item["name"]: item for item in internal_link["attributes"]
        }
        self.assertEqual(internal_attributes["target_id"]["type"], "internal_target")
        self.assertTrue(internal_attributes["target_id"]["required"])
        self.assertIn("item_list", payload["node_types"]["page"]["allowed_child_types"])
        self.assertIn(
            "internal_link", payload["node_types"]["page"]["allowed_child_types"]
        )

    def test_read_service_uses_schema_defaults_without_writing(self):
        node_root = self.root / "memory" / "nodes" / "legacy_page"
        node_root.mkdir()
        meta_path = node_root / "node.json"
        meta_path.write_text(
            json.dumps({"id": "legacy_page", "type": "page"}),
            encoding="utf-8",
        )
        (node_root / "content.txt").write_text("", encoding="utf-8")
        before = meta_path.read_bytes()
        node = ReadService(self.root).get_node("legacy_page")
        self.assertEqual(node["description"], "")
        self.assertIs(node["description_visible"], True)
        self.assertEqual(meta_path.read_bytes(), before)

        log_root = self.root / "memory" / "nodes" / "legacy_log"
        log_root.mkdir()
        log_meta_path = log_root / "node.json"
        log_meta_path.write_text(
            json.dumps({"id": "legacy_log", "type": "log", "prompts": []}),
            encoding="utf-8",
        )
        (log_root / "content.txt").write_text("", encoding="utf-8")
        before_log = log_meta_path.read_bytes()
        legacy_log = ReadService(self.root).get_node("legacy_log")
        self.assertEqual(legacy_log["description"], "")
        self.assertEqual(log_meta_path.read_bytes(), before_log)

    def test_node_type_conversion_preserves_identity_and_rejects_bad_children(self):
        page_id = self.actions.run(
            "create_node", {"type": "page", "id": "convert_me"}, log=False
        )["node_id"]
        self.actions.run(
            "update_node",
            {
                "node_id": page_id,
                "attributes": {"title": "Converted", "description": "Old page field"},
                "content": "",
            },
            log=False,
        )
        result = self.actions.run(
            "convert_node_type", {"node_id": page_id, "type": "note"}, log=False
        )
        converted = self.memory.load_meta(page_id)
        self.assertTrue(result["changed"])
        self.assertEqual(converted["id"], page_id)
        self.assertEqual(converted["type"], "note")
        self.assertEqual(converted["title"], "Converted")
        self.assertNotIn("description", converted)

        child = self.actions.run(
            "create_node", {"type": "text", "id": "conversion_child"}, log=False
        )["node_id"]
        page = self.actions.run(
            "create_node", {"type": "page", "id": "blocked_conversion"}, log=False
        )["node_id"]
        self.actions.run(
            "link_node", {"parent_id": page, "child_id": child}, log=False
        )
        with self.assertRaisesRegex(ValueError, "while it contains: text"):
            self.actions.run(
                "convert_node_type", {"node_id": page, "type": "note"}, log=False
            )

    def test_node_rename_preserves_content_children_and_parent_references(self):
        parent_id = self.actions.run(
            "create_node", {"type": "page", "id": "parent"}, log=False
        )["node_id"]
        note_id = self.actions.run(
            "create_node",
            {"type": "note", "id": "note_001", "content": "Durable note."},
            log=False,
        )["node_id"]
        self.actions.run(
            "set_attribute",
            {"node_id": note_id, "field": "title", "value": "Readable Note"},
            log=False,
        )
        self.actions.run(
            "link_node",
            {"parent_id": parent_id, "child_id": note_id},
            log=False,
        )
        internal_link_id = self.actions.run(
            "create_node", {"type": "internal_link", "id": "jump"}, log=False
        )["node_id"]
        self.actions.run(
            "set_attribute",
            {"node_id": internal_link_id, "field": "title", "value": "Jump"},
            log=False,
        )
        self.actions.run(
            "set_attribute",
            {"node_id": internal_link_id, "field": "target_id", "value": note_id},
            log=False,
        )

        result = self.actions.run(
            "rename_node",
            {"node_id": "note_001", "new_id": "readable_note"},
            log=False,
        )
        self.assertTrue(result["changed"])
        self.assertFalse(self.memory.node_exists("note_001"))
        self.assertTrue(self.memory.node_exists("readable_note"))
        self.assertEqual(self.memory.read_content("readable_note"), "Durable note.")
        self.assertEqual(
            self.memory.load_meta(parent_id)["children"], ["readable_note"]
        )
        self.assertEqual(
            self.memory.load_meta("readable_note")["title"], "Readable Note"
        )
        self.assertEqual(
            self.memory.load_meta(internal_link_id)["target_id"], "readable_note"
        )

        with self.assertRaisesRegex(FileNotFoundError, "target not found"):
            self.actions.run(
                "set_attribute",
                {
                    "node_id": internal_link_id,
                    "field": "target_id",
                    "value": "missing_target",
                },
                log=False,
            )

        with self.assertRaisesRegex(ValueError, "home node ID"):
            self.actions.run(
                "rename_node", {"node_id": "home", "new_id": "elsewhere"}, log=False
            )
        with self.assertRaisesRegex(FileExistsError, "already exists"):
            self.actions.run(
                "rename_node",
                {"node_id": "readable_note", "new_id": "parent"},
                log=False,
            )

    def test_calendar_timing_and_date_rendering(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js is not installed")
        subprocess.run([node, "--test", str(Path(__file__).with_name("calendar_layout.test.js"))], check=True, capture_output=True)

    def test_calendar_preview_limits_only_embedded_views(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js is not installed")
        subprocess.run([node, str(Path(__file__).with_name("test_calendar_preview.mjs"))], check=True, capture_output=True)

    def test_randomizer_browser_rendering(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js is not installed")
        subprocess.run(
            [node, str(Path(__file__).with_name("test_randomizer_rendering.mjs"))],
            check=True, capture_output=True,
        )

    def test_javascript_modules_parse_and_do_not_redeclare_domain_tables(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js is not installed")
        static_root = Path(__file__).resolve().parents[1] / "web" / "static"
        scripts = sorted(static_root.rglob("*.js"))
        self.assertGreater(len(scripts), 1)
        for path in scripts:
            subprocess.run([node, "--check", str(path)], check=True, capture_output=True)
        source = "\n".join(path.read_text(encoding="utf-8") for path in scripts)
        self.assertNotIn("EDITABLE_FIELDS", source)
        self.assertNotIn("CHILD_TYPES", source)


if __name__ == "__main__":
    unittest.main()
