import base64
import asyncio
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from web.read_service import (
    MalformedNodeError,
    ReadService,
    UnsafeMaterialPathError,
)
from web.server import create_app


PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "YAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)


class WebReadServiceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "memory" / "nodes").mkdir(parents=True)
        (self.root / "memory" / "materials").mkdir(parents=True)
        (self.root / "memory" / "logs").mkdir(parents=True)
        (self.root / "memory" / "system").mkdir(parents=True)
        (self.root / "memory" / "system" / "counters.json").write_text(
            "{}\n",
            encoding="utf-8",
        )
        (self.root / "memory" / "system" / "registry.json").write_text(
            "[]\n",
            encoding="utf-8",
        )
        (self.root / "memory" / "logs" / "action_log.txt").write_text(
            "sentinel log entry\n",
            encoding="utf-8",
        )

        self.write_node(
            "home",
            "page",
            children=[
                "intro",
                "page_a",
                "note_a",
                "todos",
                "image_ok",
                "image_missing",
                "image_blocked",
                "random",
                "mystery",
                "calendar_test",
                "item_list_test",
                "internal_jump",
            ],
            title="Home",
            description="A test home.",
            description_visible=True,
        )
        self.write_node("intro", "text", content="A searchable secret phrase.")
        self.write_node(
            "page_a",
            "page",
            children=["page_b", "missing_node"],
            title="Page A",
        )
        self.write_node("page_b", "page", children=["page_a"], title="Page B")
        self.write_node("orphan", "page", title="Orphan")
        self.write_node("orphan_note", "note", title="Stray Note", content="Unlinked.")
        self.write_node("note_a", "note", title="A Note", content="Full note body.")
        self.write_node(
            "todos",
            "todo_list",
            children=["todo_open", "todo_done"],
            title="Tasks",
        )
        self.write_node(
            "todo_open",
            "todo_item",
            content="Open item",
            checked=False,
            children=["todo_child_done", "todo_child_open"],
        )
        self.write_node(
            "todo_child_done",
            "todo_item",
            content="Completed child",
            checked=True,
        )
        self.write_node(
            "todo_child_open",
            "todo_item",
            content="Open child",
            checked=False,
        )
        self.write_node(
            "todo_done",
            "todo_item",
            content="Done item",
            checked=True,
            date_completed="2026-07-26",
        )
        self.write_node("image_ok", "image", title="Pixel", source="materials/pixel.png")
        self.write_node("image_content", "image", title="Content pixel", content="pixel.png")
        self.write_node("image_missing", "image", source="missing.png")
        self.write_node("image_blocked", "image", source="../../outside.png")
        self.write_node(
            "random",
            "randomizer",
            title="Choices",
            count=2,
            display_mode="text",
            size="24px",
            font="sans",
            content="One\nTwo\nThree\n",
        )
        self.write_node("mystery", "future_type", content="Readable fallback.")
        self.write_node(
            "link_ok",
            "link",
            title="Example",
            url="https://example.com/reference?q=moss",
        )
        self.write_node(
            "link_blocked",
            "link",
            title="Unsafe example",
            url="javascript:alert(1)",
        )
        self.write_node(
            "item_list_test",
            "item_list",
            children=["item_alpha", "item_beta"],
            title="Reference List",
            fields=[{"id": "rating", "label": "Rating / 10"}],
        )
        self.write_node("item_alpha", "item", title="Alpha", values={"rating": 8})
        self.write_node("item_beta", "item", title="Beta", values={"rating": ""})
        self.write_node(
            "internal_jump",
            "internal_link",
            title="Open Page A",
            target_id="page_a",
        )
        self.write_node(
            "calendar_test",
            "calendar",
            children=["week_test"],
            title="Calendar",
        )
        self.write_node(
            "week_test",
            "week",
            children=["event_test"],
            start_date="2026-08-31",
        )
        self.write_node(
            "event_test",
            "event",
            title="Planning",
            description="Review the next steps.",
            day=2,
            start_time="09:00",
            end_time="10:30",
        )
        (self.root / "memory" / "materials" / "pixel.png").write_bytes(PIXEL_PNG)
        self.service = ReadService(self.root)

    def tearDown(self):
        self.temporary.cleanup()

    def write_node(self, node_id, node_type, content="", children=None, **fields):
        node_root = self.root / "memory" / "nodes" / node_id
        node_root.mkdir()
        meta = {
            "id": node_id,
            "type": node_type,
            "children": list(children or []),
            "files": ["content.txt"],
            **fields,
        }
        (node_root / "node.json").write_text(
            json.dumps(meta, indent=2),
            encoding="utf-8",
        )
        (node_root / "content.txt").write_text(content, encoding="utf-8")

    def memory_digest(self):
        digest = hashlib.sha256()
        for path in sorted((self.root / "memory").rglob("*")):
            if path.is_file():
                digest.update(path.relative_to(self.root).as_posix().encode())
                digest.update(path.read_bytes())
        return digest.hexdigest()

    def flatten_tree(self, item):
        yield item
        for child in item.get("children", []):
            yield from self.flatten_tree(child)

    def test_all_reads_leave_memory_byte_for_byte_unchanged(self):
        before = self.memory_digest()
        home = self.service.get_node("home")
        tree = self.service.get_tree()
        search = self.service.search("secret phrase")
        pages = self.service.get_pages()
        action_log = self.service.get_action_log()
        schema = self.service.get_schema()
        material = self.service.resolve_material_request("pixel.png")
        after = self.memory_digest()

        self.assertEqual(before, after)
        self.assertEqual(home["id"], "home")
        self.assertEqual(search["results"][0]["id"], "intro")
        self.assertEqual(pages["pages"][0]["id"], "home")
        self.assertEqual(action_log["entries"][0]["action"], "sentinel log entry")
        self.assertEqual(action_log["entries"][0]["kind"], "other")
        self.assertEqual(action_log["entries"][0]["verb"], "sentinel")
        self.assertEqual(action_log["total"], 1)
        self.assertEqual(material.name, "pixel.png")
        self.assertEqual(
            (self.root / "memory" / "logs" / "action_log.txt").read_text(),
            "sentinel log entry\n",
        )
        self.assertEqual(tree["root"]["id"], "home")
        self.assertIn("text", schema["node_types"])
        self.assertTrue(all(item["description"] for item in schema["node_types"].values()))

    def test_normalizes_node_types_and_safe_material_urls(self):
        todos = self.service.get_node("todos")
        self.assertEqual(
            [item["id"] for item in todos["child_nodes"]],
            ["todo_open", "todo_done"],
        )
        self.assertIs(todos["child_nodes"][1]["checked"], True)
        self.assertEqual(
            todos["child_nodes"][1]["date_completed"],
            "2026-07-26",
        )
        self.assertEqual(
            [item["id"] for item in todos["child_nodes"][0]["child_nodes"]],
            ["todo_child_done", "todo_child_open"],
        )
        self.assertTrue(todos["child_nodes"][0]["child_nodes"][0]["checked"])

        image = self.service.get_node("image_ok")
        self.assertEqual(image["source"], "pixel.png")
        self.assertEqual(image["material_url"], "/materials/pixel.png")
        self.assertTrue(image["material_exists"])
        self.assertEqual(image["attributes"]["size"], "large")

        content_image = self.service.get_node("image_content")
        self.assertEqual(content_image["content"], "pixel.png")
        self.assertEqual(content_image["source"], "pixel.png")
        self.assertEqual(content_image["material_url"], "/materials/pixel.png")
        self.assertTrue(content_image["material_exists"])

        missing = self.service.get_node("image_missing")
        self.assertEqual(missing["material_status"], "missing")
        self.assertIsNone(missing["material_url"])

        blocked = self.service.get_node("image_blocked")
        self.assertEqual(blocked["material_status"], "blocked")
        self.assertIsNone(blocked["source"])
        self.assertIsNone(blocked["material_url"])

        randomizer = self.service.get_node("random")
        self.assertEqual(len(randomizer["random_selection"]), 2)
        self.assertEqual(len(set(randomizer["random_selection"])), 2)
        self.assertEqual(randomizer["attributes"]["display_mode"], "text")
        self.assertEqual(randomizer["attributes"]["size"], "24px")
        self.assertEqual(randomizer["attributes"]["font"], "sans")

        week = self.service.get_node("week_test")
        self.assertIs(week["completed"], False)

        unknown = self.service.get_node("mystery")
        self.assertEqual(unknown["type"], "future_type")
        self.assertEqual(unknown["content"], "Readable fallback.")

        link = self.service.get_node("link_ok")
        self.assertEqual(link["url"], "https://example.com/reference?q=moss")
        self.assertEqual(link["attributes"]["url"], link["url"])
        blocked_link = self.service.get_node("link_blocked")
        self.assertIsNone(blocked_link["url"])
        self.assertNotIn("url", blocked_link["attributes"])

        item_list = self.service.get_node("item_list_test")
        self.assertEqual(item_list["fields"], [{"id": "rating", "label": "Rating / 10"}])
        self.assertEqual([item["title"] for item in item_list["child_nodes"]], ["Alpha", "Beta"])
        self.assertEqual(item_list["child_nodes"][0]["values"], {"rating": 8})
        internal_link = self.service.get_node("internal_jump")
        self.assertEqual(internal_link["target_id"], "page_a")
        self.assertEqual(
            internal_link["internal_target"],
            {"id": "page_a", "type": "page", "title": "Page A"},
        )

        calendar = self.service.get_node("calendar_test")
        week = calendar["child_nodes"][0]
        event = week["child_nodes"][0]
        self.assertEqual(week["start_date"], "2026-08-31")
        self.assertEqual(week["attributes"]["start_date"], "2026-08-31")
        self.assertEqual(week["display_title"], "Aug 31 – Sep 6, 2026")
        self.assertEqual(event["title"], "Planning")
        self.assertEqual(event["description"], "Review the next steps.")
        self.assertEqual(event["day"], 2)
        self.assertEqual(event["start_time"], "09:00")
        self.assertEqual(event["end_time"], "10:30")
        self.assertEqual(event["attributes"]["day"], 2)
        self.assertEqual(event["attributes"]["start_time"], "09:00")
        self.assertEqual(event["attributes"]["end_time"], "10:30")

    def test_tree_marks_cycles_and_lists_unlinked_pages(self):
        tree = self.service.get_tree()
        flat = list(self.flatten_tree(tree["root"]))
        repeated = [
            item
            for item in flat
            if item["id"] == "page_a" and item.get("repeated_reference")
        ]
        self.assertEqual(len(repeated), 1)
        self.assertEqual([item["id"] for item in tree["unlinked_pages"]], ["orphan"])
        self.assertEqual(
            [item["id"] for item in tree["orphaned_nodes"]],
            ["image_content", "link_ok", "orphan", "orphan_note", "link_blocked"],
        )
        self.assertLess(len(flat), 20)

    def test_search_is_case_insensitive_and_paths_are_safe(self):
        results = self.service.search("SECRET PHRASE")["results"]
        self.assertEqual([item["id"] for item in results], ["intro"])
        self.assertIn("secret phrase", results[0]["snippet"])

        path = self.service.get_node("page_b")["path"]
        self.assertEqual([item["id"] for item in path], ["home", "page_a", "page_b"])

        orphan_path = self.service.get_node("orphan")["path"]
        self.assertEqual([item["id"] for item in orphan_path], ["home", "orphan"])

    def test_rejects_traversal_and_malformed_nodes_without_repairing(self):
        with self.assertRaises(UnsafeMaterialPathError):
            self.service.resolve_material_request("../../outside.png")
        with self.assertRaises(MalformedNodeError):
            self.service.get_node("../home")

        bad_root = self.root / "memory" / "nodes" / "bad"
        bad_root.mkdir()
        (bad_root / "node.json").write_text("{not json", encoding="utf-8")
        before = (bad_root / "node.json").read_bytes()
        with self.assertRaises(MalformedNodeError):
            self.service.get_node("bad")
        self.assertEqual((bad_root / "node.json").read_bytes(), before)

    def test_fastapi_surface_has_only_allowlisted_mutation_routes(self):
        application = create_app(self.root)
        api_routes = [
            route
            for route in application.routes
            if getattr(route, "path", "").startswith("/api/")
        ]
        self.assertEqual(
            {route.path for route in api_routes},
            {
                "/api/health",
                "/api/schema",
                "/api/action-types",
                "/api/snapshots",
                "/api/node/{node_id}",
                "/api/tree",
                "/api/search",
                "/api/pages",
                "/api/action-log",
                "/api/change-log",
                "/api/actions",
                "/api/events",
            },
        )
        for route in api_routes:
            if route.path in {"/api/events", "/api/actions"}:
                self.assertEqual(set(route.methods), {"POST"})
            else:
                self.assertTrue(set(route.methods).issubset({"GET", "HEAD"}))

    def test_change_log_is_read_only_and_separate_from_memory(self):
        entries = [
            {"version": "v1.0.1", "date": "2026-09-30", "changes": ["Example code update."]},
            {"version": "v1.0.0", "date": "2026-09-30", "changes": ["Baseline."]},
        ]
        path = self.root / "change_log.json"
        path.write_text(json.dumps(entries), encoding="utf-8")
        source_before = path.read_bytes()
        memory_before = self.memory_digest()
        application = create_app(self.root)
        status, headers, body = self.asgi_request(application, "/api/change-log")
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(json.loads(body), {"current_version": "v1.0.1", "entries": entries})
        status, _headers, body = self.asgi_request(application, "/change-log")
        self.assertEqual(status, 200)
        self.assertIn(b'id="nav-change-log"', body)
        status, _headers, _body = self.asgi_request(application, "/api/change-log", method="POST")
        self.assertEqual(status, 405)
        self.assertEqual(path.read_bytes(), source_before)
        self.assertEqual(self.memory_digest(), memory_before)

    def test_missing_or_invalid_change_log_never_repairs_files(self):
        self.assertEqual(self.service.get_change_log(), {"current_version": None, "entries": []})
        path = self.root / "change_log.json"
        self.assertFalse(path.exists())
        application = create_app(self.root)
        for content in ('{broken', '{}', '[{"version":"v1"}]'):
            path.write_text(content, encoding="utf-8")
            status, _headers, _body = self.asgi_request(application, "/api/change-log")
            self.assertEqual(status, 500)
            self.assertEqual(path.read_text(encoding="utf-8"), content)

    def test_fastapi_gets_work_and_mutation_methods_are_rejected(self):
        application = create_app(self.root)

        status, headers, body = self.asgi_request(application, "/api/health")
        self.assertEqual(status, 200)
        health = json.loads(body)
        self.assertFalse(health["read_only"])
        self.assertEqual(health["application"], "moss")
        self.assertEqual(health["api_version"], 14)
        self.assertEqual(
            health["write_capabilities"],
            [
                "events:create",
                "nodes:update",
                "children:create",
                "items:create",
                "items:update",
                "item-lists:update-fields",
                "children:link",
                "children:move",
                "children:unlink",
                "logs:submit",
                "logs:update-template",
                "logs:update-entry",
                "snapshots:create",
                "nodes:delete",
            ],
        )
        self.assertEqual(headers["cache-control"], "no-store")

        before_schema = self.memory_digest()
        status, headers, body = self.asgi_request(application, "/api/schema")
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        schema = json.loads(body)
        self.assertEqual(schema["schema_version"], 1)
        self.assertIn("randomizer", schema["node_types"])
        self.assertEqual(before_schema, self.memory_digest())

        before_actions = self.memory_digest()
        status, headers, body = self.asgi_request(application, "/api/action-types")
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        action_types = json.loads(body)
        self.assertEqual(action_types["catalog_version"], 1)
        self.assertIn("create_child", [item["name"] for item in action_types["action_types"]])
        create_child = next(
            item for item in action_types["action_types"] if item["name"] == "create_child"
        )
        create_node = next(
            item for item in action_types["action_types"] if item["name"] == "create_node"
        )
        create_event = next(
            item for item in action_types["action_types"] if item["name"] == "create_event"
        )
        self.assertTrue(create_child["browser_available"])
        self.assertTrue(create_event["browser_available"])
        self.assertFalse(create_node["browser_available"])
        self.assertEqual(before_actions, self.memory_digest())

        before_snapshots = self.memory_digest()
        status, headers, body = self.asgi_request(application, "/api/snapshots")
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(json.loads(body), {"snapshots": []})
        self.assertEqual(before_snapshots, self.memory_digest())

        status, _headers, body = self.asgi_request(
            application,
            "/api/health",
            method="POST",
        )
        self.assertEqual(status, 405)
        self.assertIn("not available", json.loads(body)["detail"])

        status, headers, body = self.asgi_request(application, "/node/page_b")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["content-type"])
        self.assertIn(b'<section id="content"', body)

        status, headers, body = self.asgi_request(application, "/tree")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["content-type"])

        status, headers, body = self.asgi_request(application, "/action-log")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["content-type"])

        status, headers, body = self.asgi_request(application, "/node-types")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["content-type"])

        status, headers, body = self.asgi_request(application, "/action-types")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["content-type"])

        status, headers, body = self.asgi_request(application, "/snapshots")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["content-type"])

        status, _headers, body = self.asgi_request(application, "/api/action-log")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["entries"][0]["action"], "sentinel log entry")

        status, headers, body = self.asgi_request(
            application,
            "/materials/pixel.png",
        )
        self.assertEqual(status, 200)
        self.assertEqual(headers["content-security-policy"], "default-src 'none'; sandbox")
        self.assertEqual(body, PIXEL_PNG)

        status, _headers, _body = self.asgi_request(
            application,
            "/materials/not-present.png",
        )
        self.assertEqual(status, 404)

    def test_event_post_uses_action_runner_and_writes_one_log_entry(self):
        application = create_app(self.root)
        payload = json.dumps(
            {
                "week_id": "week_test",
                "title": "Design review",
                "description": "Bring the new sketches.",
                "day": 3,
                "start_time": "13:00",
                "end_time": "14:15",
            }
        ).encode()
        before = (self.root / "memory" / "logs" / "action_log.txt").read_text(
            encoding="utf-8"
        ).splitlines()

        status, _headers, body = self.asgi_request(
            application,
            "/api/events",
            method="POST",
            headers={
                "origin": "http://testserver",
                "sec-fetch-site": "same-origin",
                "content-type": "application/json",
                "x-moss-request": "create-event",
            },
            body=payload,
        )

        self.assertEqual(status, 201)
        response = json.loads(body)
        self.assertEqual(response["event"]["title"], "Design review")
        self.assertEqual(response["event"]["day"], 3)
        self.assertIn(response["event"]["id"], response["week"]["children"])
        after = (self.root / "memory" / "logs" / "action_log.txt").read_text(
            encoding="utf-8"
        ).splitlines()
        self.assertEqual(len(after), len(before) + 1)
        self.assertIn("created event", after[-1])
        self.assertNotIn("set title", after[-1])

    def test_event_post_requires_same_origin_action_request(self):
        application = create_app(self.root)
        payload = json.dumps(
            {
                "week_id": "week_test",
                "title": "Blocked event",
                "day": 1,
                "start_time": "09:00",
                "end_time": "10:00",
            }
        ).encode()
        before = self.memory_digest()

        status, _headers, _body = self.asgi_request(
            application,
            "/api/events",
            method="POST",
            headers={
                "content-type": "application/json",
                "x-moss-request": "create-event",
            },
            body=payload,
        )

        self.assertEqual(status, 403)
        self.assertEqual(before, self.memory_digest())

    def test_node_update_post_changes_content_and_attributes_with_one_log(self):
        application = create_app(self.root)
        before = (self.root / "memory" / "logs" / "action_log.txt").read_text(
            encoding="utf-8"
        ).splitlines()
        payload = json.dumps(
            {
                "action": "update_node",
                "payload": {
                    "node_id": "note_a",
                    "attributes": {"title": "Revised note"},
                    "content": "Revised body.",
                },
            }
        ).encode()

        status, _headers, body = self.asgi_request(
            application,
            "/api/actions",
            method="POST",
            headers={
                "origin": "http://testserver",
                "sec-fetch-site": "same-origin",
                "content-type": "application/json",
                "x-moss-request": "run-action",
            },
            body=payload,
        )

        self.assertEqual(status, 200)
        response = json.loads(body)
        self.assertEqual(response["node"]["title"], "Revised note")
        self.assertEqual(response["node"]["content"], "Revised body.")
        self.assertEqual(response["result"]["changed"], ["content", "title"])
        after = (self.root / "memory" / "logs" / "action_log.txt").read_text(
            encoding="utf-8"
        ).splitlines()
        self.assertEqual(len(after), len(before) + 1)
        self.assertIn("updated note_a: content, title", after[-1])

    def test_snapshot_creation_inventory_and_download_stay_within_the_web_boundary(self):
        (self.root / "version.txt").write_text("MOSS v0.2\n", encoding="utf-8")
        application = create_app(self.root)
        request_headers = {
            "origin": "http://testserver",
            "sec-fetch-site": "same-origin",
            "content-type": "application/json",
            "x-moss-request": "run-action",
        }
        payload = json.dumps(
            {"action": "snapshot", "payload": {"name": "web_snapshot"}}
        ).encode()
        status, _headers, body = self.asgi_request(
            application,
            "/api/actions",
            method="POST",
            headers=request_headers,
            body=payload,
        )
        self.assertEqual(status, 200)
        response = json.loads(body)
        self.assertEqual(response["result"], {"name": "web_snapshot"})
        self.assertNotIn("path", body.decode())

        archive_path = self.root / "snapshots" / "web_snapshot.zip"
        self.assertTrue(archive_path.is_file())
        archive_bytes = archive_path.read_bytes()
        status, response_headers, body = self.asgi_request(application, "/api/snapshots")
        self.assertEqual(status, 200)
        records = json.loads(body)["snapshots"]
        self.assertEqual([item["name"] for item in records], ["web_snapshot"])
        self.assertEqual(records[0]["status"], "ready")
        self.assertEqual(records[0]["moss_version"], "v0.2")
        self.assertGreater(records[0]["node_count"], 0)
        self.assertEqual(records[0]["download_url"], "/snapshots/web_snapshot.zip")

        status, response_headers, body = self.asgi_request(
            application, "/snapshots/web_snapshot.zip"
        )
        self.assertEqual(status, 200)
        self.assertEqual(response_headers["content-type"], "application/zip")
        self.assertIn("attachment", response_headers["content-disposition"])
        self.assertEqual(body, archive_bytes)

        invalid = json.dumps(
            {"action": "snapshot", "payload": {"name": "../unsafe"}}
        ).encode()
        status, _headers, _body = self.asgi_request(
            application,
            "/api/actions",
            method="POST",
            headers=request_headers,
            body=invalid,
        )
        self.assertEqual(status, 422)
        self.assertFalse((self.root / "unsafe.zip").exists())

    def test_image_size_update_round_trips_through_the_web_boundary(self):
        application = create_app(self.root)
        payload = json.dumps(
            {
                "action": "update_node",
                "payload": {
                    "node_id": "image_ok",
                    "attributes": {"size": "420px"},
                },
            }
        ).encode()

        status, _headers, body = self.asgi_request(
            application,
            "/api/actions",
            method="POST",
            headers={
                "origin": "http://testserver",
                "sec-fetch-site": "same-origin",
                "content-type": "application/json",
                "x-moss-request": "run-action",
            },
            body=payload,
        )

        self.assertEqual(status, 200)
        response = json.loads(body)
        self.assertEqual(response["result"]["changed"], ["size"])
        self.assertEqual(response["node"]["attributes"]["size"], "420px")

    def test_create_child_post_creates_links_and_logs_once(self):
        application = create_app(self.root)
        before = (self.root / "memory" / "logs" / "action_log.txt").read_text(
            encoding="utf-8"
        ).splitlines()
        payload = json.dumps(
            {
                "action": "create_child",
                "payload": {
                    "parent_id": "page_a",
                    "type": "note",
                    "id": "new_note",
                    "content": "A new note.",
                    "attributes": {"title": "New note"},
                },
            }
        ).encode()

        status, _headers, body = self.asgi_request(
            application,
            "/api/actions",
            method="POST",
            headers={
                "origin": "http://testserver",
                "sec-fetch-site": "same-origin",
                "content-type": "application/json",
                "x-moss-request": "run-action",
            },
            body=payload,
        )

        self.assertEqual(status, 200)
        response = json.loads(body)
        self.assertEqual(response["created"]["id"], "new_note")
        self.assertIn("new_note", response["node"]["children"])
        after = (self.root / "memory" / "logs" / "action_log.txt").read_text(
            encoding="utf-8"
        ).splitlines()
        self.assertEqual(len(after), len(before) + 1)
        self.assertIn("created note new_note in page_a", after[-1])

    def test_link_child_requires_and_safely_round_trips_a_web_url(self):
        application = create_app(self.root)
        headers = {
            "origin": "http://testserver",
            "sec-fetch-site": "same-origin",
            "content-type": "application/json",
            "x-moss-request": "run-action",
        }
        payload = json.dumps(
            {
                "action": "create_child",
                "payload": {
                    "parent_id": "page_a",
                    "type": "link",
                    "id": "moss_site",
                    "attributes": {
                        "title": "MOSS reference",
                        "url": "https://example.com/moss",
                    },
                },
            }
        ).encode()
        status, _headers, body = self.asgi_request(
            application, "/api/actions", method="POST", headers=headers, body=payload
        )
        self.assertEqual(status, 200)
        created = json.loads(body)["created"]
        self.assertEqual(created["type"], "link")
        self.assertEqual(created["title"], "MOSS reference")
        self.assertEqual(created["url"], "https://example.com/moss")

        missing_url = json.dumps(
            {
                "action": "create_child",
                "payload": {
                    "parent_id": "page_a",
                    "type": "link",
                    "attributes": {"title": "Incomplete"},
                },
            }
        ).encode()
        before = self.memory_digest()
        status, _headers, body = self.asgi_request(
            application, "/api/actions", method="POST", headers=headers, body=missing_url
        )
        self.assertEqual(status, 422)
        self.assertIn("Required child attributes: url", json.loads(body)["detail"])
        self.assertEqual(before, self.memory_digest())

    def test_log_entries_snapshot_templates_and_reject_disallowed_choices(self):
        prompts = [
            {"id": "date", "label": "Date", "type": "date", "required": True},
            {
                "id": "ritual_1",
                "label": "Ritual 1",
                "type": "choice",
                "required": True,
                "options": [0, 1, 3],
            },
            {"id": "notes", "label": "Notes", "type": "text", "required": False},
        ]
        self.write_node(
            "daily_log",
            "log",
            title="Daily Log",
            description="A short daily reflection.",
            prompts=prompts,
        )
        application = create_app(self.root)
        headers = {
            "origin": "http://testserver",
            "sec-fetch-site": "same-origin",
            "content-type": "application/json",
            "x-moss-request": "run-action",
        }
        log_node = ReadService(self.root).get_node("daily_log")
        self.assertEqual(log_node["description"], "A short daily reflection.")

        invalid = json.dumps(
            {
                "action": "submit_log_entry",
                "payload": {
                    "log_id": "daily_log",
                    "answers": {"date": "2026-09-08", "ritual_1": 2, "notes": "No."},
                },
            }
        ).encode()
        before = self.memory_digest()
        status, _headers, body = self.asgi_request(
            application, "/api/actions", method="POST", headers=headers, body=invalid
        )
        self.assertEqual(status, 422)
        self.assertIn("must be one of: 0, 1, 3", json.loads(body)["detail"])
        self.assertEqual(before, self.memory_digest())

        valid = json.dumps(
            {
                "action": "submit_log_entry",
                "payload": {
                    "log_id": "daily_log",
                    "answers": {"date": "2026-09-08", "ritual_1": 3, "notes": "Good."},
                },
            }
        ).encode()
        status, _headers, body = self.asgi_request(
            application, "/api/actions", method="POST", headers=headers, body=valid
        )
        self.assertEqual(status, 200)
        response = json.loads(body)
        entry_id = response["result"]["node_id"]
        self.assertIn(entry_id, response["node"]["children"])
        entry = ReadService(self.root).get_node(entry_id)
        self.assertEqual(entry["entry_date"], "2026-09-08")
        self.assertEqual(entry["answers"]["ritual_1"], 3)
        self.assertEqual(entry["prompts"], prompts)

        revised_prompts = [
            {"id": "date", "label": "Day", "type": "date", "required": True},
            {"id": "notes", "label": "Reflection", "type": "text", "required": False},
        ]
        update = json.dumps(
            {
                "action": "update_log_template",
                "payload": {"node_id": "daily_log", "prompts": revised_prompts},
            }
        ).encode()
        status, _headers, _body = self.asgi_request(
            application, "/api/actions", method="POST", headers=headers, body=update
        )
        self.assertEqual(status, 200)
        current_log = ReadService(self.root).get_node("daily_log")
        self.assertEqual(current_log["prompts"], revised_prompts)
        preserved_entry = ReadService(self.root).get_node(entry_id)
        self.assertEqual(preserved_entry["prompts"], prompts)
        self.assertEqual(preserved_entry["answers"]["notes"], "Good.")

    def test_web_delete_is_explicit_allowlisted_and_home_remains_protected(self):
        application = create_app(self.root)
        before = self.memory_digest()
        payload = json.dumps(
            {"action": "trash_node", "payload": {"node_id": "page_a"}}
        ).encode()

        status, _headers, body = self.asgi_request(
            application,
            "/api/actions",
            method="POST",
            headers={
                "origin": "http://testserver",
                "sec-fetch-site": "same-origin",
                "content-type": "application/json",
                "x-moss-request": "run-action",
            },
            body=payload,
        )

        self.assertEqual(status, 200)
        response = json.loads(body)
        self.assertIsNone(response["node"])
        self.assertTrue(response["result"]["deleted"])
        self.assertFalse((self.root / "memory" / "nodes" / "page_a").exists())
        self.assertNotIn("page_a", ReadService(self.root).get_node("home")["children"])
        self.assertTrue((self.root / "memory" / "nodes" / "page_b").exists())
        self.assertNotEqual(before, self.memory_digest())

        protected_before = self.memory_digest()
        protected_payload = json.dumps(
            {"action": "trash_node", "payload": {"node_id": "home"}}
        ).encode()
        status, _headers, body = self.asgi_request(
            application,
            "/api/actions",
            method="POST",
            headers={
                "origin": "http://testserver",
                "sec-fetch-site": "same-origin",
                "content-type": "application/json",
                "x-moss-request": "run-action",
            },
            body=protected_payload,
        )
        self.assertEqual(status, 422)
        self.assertIn("Cannot trash home", json.loads(body)["detail"])
        self.assertEqual(protected_before, self.memory_digest())

    def test_frontend_never_uses_html_injection(self):
        static_root = Path(__file__).resolve().parents[1] / "web" / "static"
        for path in static_root.rglob("*.js"):
            script = path.read_text(encoding="utf-8")
            self.assertNotIn("innerHTML", script, path.name)
            self.assertNotIn("insertAdjacentHTML", script, path.name)

    def test_frontend_page_children_use_document_flow_contract(self):
        static_root = Path(__file__).resolve().parents[1] / "web" / "static"
        app_source = (static_root / "app.js").read_text(encoding="utf-8")
        material_source = (static_root / "renderers" / "materials.js").read_text(
            encoding="utf-8"
        )
        styles = (static_root / "styles.css").read_text(encoding="utf-8")

        self.assertIn('rendered.classList.add("page-child")', app_source)
        self.assertIn('link.className = "flow-text-link"', app_source)
        self.assertNotIn('createElement("div", "cards-grid")', app_source)
        self.assertIn(': makeHeadingLink(node, path)', material_source)
        self.assertIn('imageLink.target = "_blank"', material_source)
        self.assertIn(".page-child.starts-section:not(:first-child)", styles)
        self.assertIn(".page-body .image-frame", styles)

    def test_calendar_and_node_type_directory_frontend_contracts(self):
        static_root = Path(__file__).resolve().parents[1] / "web" / "static"
        calendar_source = (
            static_root / "renderers" / "calendar.js"
        ).read_text(encoding="utf-8")
        schema_source = (
            static_root / "renderers" / "schema.js"
        ).read_text(encoding="utf-8")
        snapshots_source = (
            static_root / "renderers" / "snapshots.js"
        ).read_text(encoding="utf-8")

        self.assertIn("weekNode.completed", calendar_source)
        self.assertIn('createElement("details", "past-weeks")', calendar_source)
        self.assertIn("Object.entries(nodeSchemas)", schema_source)
        self.assertIn("schema.allowed_child_types", schema_source)
        self.assertIn("schema.child_creation_types", schema_source)
        self.assertIn('createElement("span", "node-type-description", schema.description)', schema_source)
        self.assertIn("summary.append(\n    identity,", schema_source)
        self.assertIn('apiJson("/api/action-types")', schema_source)
        self.assertIn("action.browser_available", schema_source)
        self.assertIn('runMossAction("snapshot"', snapshots_source)
        self.assertIn('apiJson("/api/snapshots")', snapshots_source)
        self.assertIn("snapshot.download_url", snapshots_source)

        editor_source = (static_root / "editors.js").read_text(encoding="utf-8")
        self.assertIn('`${child.type || "node"} · ID · ${child.id}`', editor_source)
        self.assertIn("Type ${node.id} to confirm", editor_source)

        content_source = (static_root / "renderers" / "content.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("NOTE_PREVIEW_LENGTH = 420", content_source)
        self.assertIn('runMossAction("update_node"', content_source)
        self.assertIn("appendText(preview, previewContent, node)", content_source)
        self.assertIn('external.rel = "noopener noreferrer"', content_source)
        self.assertIn("headingRow.append(heading, edit)", content_source)
        self.assertIn('editLink.className = "parent-edit-icon"', content_source)

        logs_source = (static_root / "renderers" / "logs.js").read_text(
            encoding="utf-8"
        )
        self.assertIn('form.hidden = false', logs_source)
        self.assertIn('"linked-node-description", node.description', logs_source)

        system_source = (static_root / "renderers" / "system.js").read_text(
            encoding="utf-8"
        )
        self.assertIn('createElement("div", "toc-table")', system_source)
        self.assertIn("data.orphaned_nodes", system_source)
        self.assertNotIn("graph-node-card", system_source)
        self.assertIn("function renderInternalLink", content_source)
        items_source = (static_root / "renderers" / "items.js").read_text(encoding="utf-8")
        self.assertIn("function renderItemList", items_source)
        self.assertIn('runMossAction("create_item"', items_source)
        self.assertIn('["Top", "position", "top"', editor_source)

    def test_frontend_serves_native_module_graph(self):
        application = create_app(self.root)
        status, headers, body = self.asgi_request(application, "/")
        self.assertEqual(status, 200)
        self.assertIn(b'type="module"', body)
        self.assertIn(b'/static/app.js?v=24', body)
        self.assertIn(b'href="/search" id="nav-search"', body)
        self.assertIn(b'href="/node-types" id="nav-node-types"', body)
        self.assertIn(b'href="/action-types" id="nav-action-types"', body)
        self.assertIn(b'href="/snapshots" id="nav-snapshots"', body)
        self.assertIn("script-src 'self'", headers["content-security-policy"])

        module_paths = (
            "/static/app.js",
            "/static/api.js",
            "/static/dom.js",
            "/static/editors.js",
            "/static/renderers/calendar.js",
            "/static/renderers/content.js",
            "/static/renderers/materials.js",
            "/static/renderers/logs.js",
            "/static/renderers/items.js",
            "/static/renderers/schema.js",
            "/static/renderers/snapshots.js",
            "/static/renderers/system.js",
            "/static/renderers/todos.js",
        )
        for path in module_paths:
            status, module_headers, module_body = self.asgi_request(application, path)
            self.assertEqual(status, 200, path)
            self.assertIn("javascript", module_headers["content-type"], path)
            self.assertEqual(module_headers["cache-control"], "no-store", path)
            self.assertTrue(module_body.strip(), path)

    @staticmethod
    def asgi_request(application, path, method="GET", headers=None, body=b""):
        messages = []
        request_sent = False

        async def receive():
            nonlocal request_sent
            if request_sent:
                return {"type": "http.disconnect"}
            request_sent = True
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            messages.append(message)

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": [
                (b"host", b"testserver"),
                (b"content-length", str(len(body)).encode()),
                *[
                    (key.lower().encode(), value.encode())
                    for key, value in (headers or {}).items()
                ],
            ],
            "client": ("127.0.0.1", 50000),
            "server": ("testserver", 80),
            "root_path": "",
        }
        asyncio.run(application(scope, receive, send))
        start = next(message for message in messages if message["type"] == "http.response.start")
        body = b"".join(
            message.get("body", b"")
            for message in messages
            if message["type"] == "http.response.body"
        )
        headers = {
            key.decode("latin-1"): value.decode("latin-1")
            for key, value in start["headers"]
        }
        return start["status"], headers, body


if __name__ == "__main__":
    unittest.main()
