"""Presentation contracts: validated writes, pure reads, and stable references."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from core.action_runner import ActionRunner
from core.memory import Memory
from core.ui_settings import read_settings, DEFAULTS
from core.display_styles import read_node_styles, STYLE_CATALOG


class PresentationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.memory = Memory(self.root)
        self.runner = ActionRunner(self.memory)
        self.runner.run('create_node', {'id':'cal', 'type':'calendar'})

    def digest(self, root=None):
        return {str(p):p.read_bytes() for p in (root or self.memory.root).rglob('*') if p.is_file()}

    def test_display_style_roundtrip_fallback_and_content_isolation(self):
        before = self.digest()
        self.assertEqual(read_node_styles(self.memory), {})
        self.assertEqual(self.digest(), before)
        before_nodes = self.digest(self.memory.nodes)
        payload = {'node_id':'cal', 'parent':'current-week', 'open':'default'}
        self.runner.run('update_node_display', payload)
        self.assertEqual(read_node_styles(self.memory)['cal'], {'parent':'current-week','open':'default'})
        self.assertEqual(self.digest(self.memory.nodes), before_nodes)
        before = self.digest()
        for invalid in [dict(payload, open='current-week'), dict(payload,parent='missing'),
                        dict(payload,node_id='home'), dict(payload,node_id='../cal'),
                        dict(payload, parent={}), dict(payload, extra=1)]:
            with self.assertRaises(ValueError): self.runner.run('update_node_display', invalid)
            self.assertEqual(self.digest(), before)
        with patch.dict(STYLE_CATALOG['calendar'], {'parent':[{'id':'default'}]}):
            self.assertEqual(read_node_styles(self.memory)['cal']['parent'], 'default')
            self.assertEqual(self.digest(), before)
        self.runner.run('update_node_display', dict(payload,parent='default'))
        self.assertEqual(read_node_styles(self.memory), {})
        self.assertIn('updated display styles for cal', self.runner.action_log_path.read_text())

    def test_navigation_validation_and_stale_references(self):
        before = self.digest()
        self.assertEqual(read_settings(self.memory), DEFAULTS)
        self.assertEqual(self.digest(), before)
        links = [{'label':'My schedule','target':'node:cal'}, {'label':'Find','target':'system:search'}]
        self.runner.run('update_ui_settings', {'navigation':links})
        self.assertEqual(read_settings(self.memory)['navigation'], links)
        before = self.digest()
        for invalid in [[{'label':'No','target':'javascript:alert(1)'}], [{'label':'','target':'home'}],
                        [{'label':'Missing','target':'node:absent'}], [{'label':'UI','target':'system:ui'}],
                        [{'label':'Escape','target':'node:../home'}], {'bad':True}, [None]]:
            with self.assertRaises(ValueError): self.runner.run('update_ui_settings', {'navigation':invalid})
            self.assertEqual(self.digest(), before)
        # An already-saved missing node remains a visible reference and can be removed.
        shutil.rmtree(self.memory.node_path('cal'))
        before = self.digest()
        self.assertEqual(read_settings(self.memory)['navigation'], links)
        self.assertEqual(self.digest(), before)
        self.runner.run('update_ui_settings', {'navigation':links, 'scheme':'moss-dark'})
        self.runner.run('update_ui_settings', {'navigation':[]})
        self.assertEqual(read_settings(self.memory)['navigation'], [])

    def test_rename_updates_presentation_references_with_rollback(self):
        self.runner.run('update_ui_settings', {'home_node_id':'cal','navigation':[{'label':'Calendar','target':'node:cal'}]})
        self.runner.run('update_node_display', {'node_id':'cal','parent':'current-week','open':'default'})
        before = self.digest()
        original = self.memory._write_json_file
        def fail(path, value):
            if path.name == 'node_display.json': raise OSError('test disk failure')
            return original(path,value)
        with patch.object(self.memory, '_write_json_file', side_effect=fail):
            with self.assertRaises(OSError): self.runner.run('rename_node', {'node_id':'cal','new_id':'calendar_new'})
        self.assertEqual(self.digest(), before)
        self.runner.run('rename_node', {'node_id':'cal','new_id':'calendar_new'})
        self.assertEqual(read_settings(self.memory)['home_node_id'], 'calendar_new')
        self.assertEqual(read_settings(self.memory)['navigation'][0]['target'], 'node:calendar_new')
        self.assertIn('calendar_new', read_node_styles(self.memory))
        self.assertNotIn('cal', read_node_styles(self.memory))

    def test_rendering_contracts(self):
        node = shutil.which('node')
        if not node: self.skipTest('Node.js not installed')
        subprocess.run([node, str(Path(__file__).with_name('test_display_styles.mjs'))],check=True,capture_output=True)
