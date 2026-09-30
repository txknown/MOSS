"""Fresh-copy startup and isolation from other local workspaces."""

import hashlib
import json
import os
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import start_web
from core.memory import Memory
from web.read_service import ReadService
from web.server import create_app


def file_digest(root):
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*") if path.is_file()
    }


class SkeletonStartupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "skeleton"
        self.root.mkdir()

    def launch(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(start_web, "PROJECT_ROOT", self.root))
            stack.enter_context(patch.object(start_web, "port_is_available", return_value=True))
            stack.enter_context(patch.object(start_web.threading, "Thread"))
            stack.enter_context(patch.object(start_web.uvicorn, "run"))
            stack.enter_context(redirect_stdout(StringIO()))
            start_web.main()

    def test_fresh_launch_initializes_only_its_own_empty_home(self):
        other = Path(self.temporary.name) / "other_workspace"
        other.mkdir()
        (other / "sentinel.txt").write_text("Existing workspace data.")
        before = file_digest(other)
        previous_cwd = Path.cwd()
        try:
            os.chdir(other)
            self.launch()
        finally:
            os.chdir(previous_cwd)
        self.assertEqual(file_digest(other), before)
        service = ReadService(self.root)
        self.assertTrue(service.health()["memory_available"])
        self.assertEqual(sorted(p.name for p in (self.root / "memory/nodes").iterdir()), ["home"])
        home = service.get_node("home")
        self.assertEqual(home["title"], "Home")
        self.assertEqual(home["children"], [])
        self.assertEqual(home["content"], "")
        self.assertEqual(list((self.root / "memory/materials").iterdir()), [])
        self.assertEqual((self.root / "memory/logs/action_log.txt").read_text(), "")
        for name in ("settings", "counters"):
            self.assertEqual(json.loads((self.root / f"memory/system/{name}.json").read_text()), {})
        self.assertFalse((self.root / "snapshots").exists())

    def test_relaunch_preserves_existing_data(self):
        memory = Memory(self.root)
        memory.create_node("note", node_id="example", content="Keep this note.")
        memory.add_child("home", "example")
        (memory.system / "settings.json").write_text('{"example": true}')
        (memory.logs / "action_log.txt").write_text("Existing log.\n")
        before = file_digest(self.root)
        self.launch()
        self.assertEqual(file_digest(self.root), before)

    def test_app_construction_and_health_do_not_initialize_memory(self):
        application = create_app(self.root)
        self.assertFalse(application.state.read_service.health()["memory_available"])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_occupied_port_never_opens_another_workspace_or_initializes(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(start_web, "PROJECT_ROOT", self.root))
            stack.enter_context(patch.object(start_web, "port_is_available", return_value=False))
            browser = stack.enter_context(patch.object(start_web.webbrowser, "open"))
            server = stack.enter_context(patch.object(start_web.uvicorn, "run"))
            with self.assertRaisesRegex(SystemExit, "being used by another process"):
                start_web.main()
            browser.assert_not_called()
            server.assert_not_called()
        self.assertEqual(list(self.root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
