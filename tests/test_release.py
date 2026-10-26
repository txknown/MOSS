"""Public release integration: legacy reads, recovery, and terminal catalogs."""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from core.action_runner import ActionRunner
from core.memory import Memory
from core.node_schema import NODE_SCHEMAS
from core.ui_settings import read_settings
from core.display_styles import read_node_styles
from web.read_service import ReadService


def digest(root):
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob('*') if path.is_file()}


class ReleaseIntegrationTests(unittest.TestCase):
    def test_v1_nodes_project_new_defaults_without_rewriting_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            memory = Memory(root)
            # Synthetic v1-style records intentionally omit later default fields.
            legacy = {
                'home': {'id':'home','type':'page','title':'Original home','children':['calendar','tasks','note']},
                'calendar': {'id':'calendar','type':'calendar','title':'Schedule','children':['week']},
                'week': {'id':'week','type':'week','title':'My original title','start_date':'2026-10-19','children':[]},
                'tasks': {'id':'tasks','type':'todo_list','title':'Tasks','children':['second','first']},
                'first': {'id':'first','type':'todo_item','children':[],'checked':False},
                'second': {'id':'second','type':'todo_item','children':[],'checked':True},
                'note': {'id':'note','type':'note','title':'Keep this title','children':[]},
            }
            for node_id, meta in legacy.items():
                path = memory.node_path(node_id)
                path.mkdir(exist_ok=True)
                (path/'node.json').write_text(json.dumps(meta))
            (memory.node_path('note')/'content.txt').write_text('Keep exact wording.\n\nAnd spacing.\n')
            before = digest(root)
            service = ReadService(root)
            self.assertEqual(service.get_node('week')['attributes']['notes'], '')
            self.assertEqual(service.get_node('week')['title'], 'My original title')
            self.assertEqual(service.get_node('tasks')['children'], ['second','first'])
            self.assertEqual(service.get_node('note')['content'], 'Keep exact wording.\n\nAnd spacing.\n')
            service.get_node('home')
            service.get_tree()
            service.search('wording')
            read_settings(memory)
            read_node_styles(memory)
            self.assertEqual(digest(root), before)

    def test_snapshot_restores_memory_and_preferences_without_replacing_code_version(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)/'source'; root.mkdir()
            (root/'version.txt').write_text('MOSS v1.1.0\n')
            memory = Memory(root)
            runner = ActionRunner(memory)
            runner.run('create_child', {'parent_id':'home','type':'scratchpad','id':'inbox'})
            runner.run('jot', {'parent_id':'inbox','content':'Keep this jot.\n'})
            runner.run('create_child', {'parent_id':'home','type':'calendar','id':'calendar'})
            runner.run('update_ui_settings', {'scheme':'moss-dark','home_style':'top-down',
                'navigation':[{'label':'Inbox','target':'node:inbox'}]})
            runner.run('update_node_display', {'node_id':'calendar','parent':'current-week','open':'default'})
            (memory.materials/'example.txt').write_text('A local material.')
            before = digest(memory.root)
            result = runner.run('snapshot', {'name':'before_update'})
            restored = Path(temporary)/'restored'; restored.mkdir()
            (restored/'version.txt').write_text('MOSS v1.1.1\n')
            with zipfile.ZipFile(result['path']) as archive:
                for member in archive.namelist():
                    if member.startswith('memory/'):
                        archive.extract(member, restored)
            self.assertEqual(digest(restored/'memory'), before)
            self.assertEqual((restored/'version.txt').read_text(), 'MOSS v1.1.1\n')
            restored_memory = Memory(restored, initialize=False)
            self.assertEqual(read_settings(restored_memory)['scheme'], 'moss-dark')
            self.assertEqual(read_node_styles(restored_memory)['calendar']['parent'], 'current-week')
            self.assertEqual(ReadService(restored).get_node('inbox')['child_nodes'][0]['content'], 'Keep this jot.\n')
            self.assertEqual(digest(restored/'memory'), before)


class TerminalReleaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_terminal_lists_all_types_actions_and_scratchpad_children(self):
        from core.app import MossApp
        from core.action_catalog import ACTION_SPECS
        from textual.widgets import Static, ListView
        with tempfile.TemporaryDirectory() as temporary:
            memory = Memory(Path(temporary))
            runner = ActionRunner(memory)
            runner.run('create_child', {'parent_id':'home','type':'scratchpad','id':'inbox'})
            runner.run('jot', {'parent_id':'inbox','content':'A synthetic jot.'})
            with patch('core.app.Memory', return_value=memory):
                app = MossApp()
                async with app.run_test(size=(120,40)):
                    await app._show_node_types()
                    rendered = str(app.query_one('#detail', Static).render())
                    for node_type in NODE_SCHEMAS:
                        self.assertIn(node_type, rendered)
                    await app._show_action_types()
                    rendered = str(app.query_one('#detail', Static).render())
                    for spec in ACTION_SPECS:
                        self.assertIn(spec.name, rendered)
                    await app.show_node('inbox')
                    self.assertEqual(len(app.query_one('#child-list', ListView).children), 1)
