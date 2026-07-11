from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Label, ListItem, ListView, Static

from core.action_runner import ActionRunner
from core.memory import Memory
from core.renderer import render_node
from core.registry import known_action_types, known_node_types


PROJECT_ROOT = Path(__file__).resolve().parents[1]

HELP = """
Commands:
  help
  home
  where
  open <node_id>
  new <type> [node_id]
  set <text>
  add <text>
  edit
  setattr <field> <value>
  link <node_id>
  unlink <node_id>
  move up <node_id>
  move down <node_id>
  all pages
  all node types
  all action types
  action log
  history
  refresh
  quit

Node types:
  page
  text
  todo_list
  todo_item
  image
""".strip()

TYPE_LABELS = {
    "page": "page",
    "text": "text",
    "todo_list": "todo_list",
    "todo_item": "todo_item",
    "image": "image",
}

NAVIGATION_ITEMS = [
    ("home", "Home"),
    ("pages", "All Pages"),
    ("node_types", "All Node Types"),
    ("action_types", "All Action Types"),
    ("action_log", "Action Log"),
]

NODE_TYPE_HELP = {
    "page": "new page <node_id>",
    "text": "new text OR new text <node_id>",
    "todo_list": "new todo_list <node_id>",
    "todo_item": "new todo_item",
    "image": "new image <node_id>",
}

ACTION_DESCRIPTIONS = {
    "create_node": "Tree action: create a node.",
    "link_node": "Tree action: link a node under a parent.",
    "unlink_node": "Tree action: unlink a child from a parent.",
    "move_child": "Tree action: move a child up or down.",
    "set_content": "Content action: replace content.txt.",
    "add_content": "Content action: add text to content.txt.",
    "edit_content": "Content action: open content.txt in $EDITOR if configured.",
    "set_attribute": "Attribute action: set a top-level node.json field.",
    "session_started": "System action: log MOSS start.",
    "session_ended": "System action: log MOSS end.",
}

PARENT_TYPES = {"page", "todo_list"}


class NavigationItem(ListItem):
    def __init__(self, nav_key, label):
        super().__init__(Label(label))
        self.nav_key = nav_key


class NodeListItem(ListItem):
    def __init__(self, node_id, label):
        super().__init__(Label(label))
        self.node_id = node_id


class MossApp(App):
    CSS_PATH = str(PROJECT_ROOT / "moss.tcss")
    BINDINGS = [("q", "quit", "Quit"), ("r", "refresh", "Refresh")]

    def __init__(self):
        super().__init__()
        self.memory = None
        self.actions = None
        self.selected_id = "home"
        self.active_page_id = "home"
        self._session_closed = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="layout"):
            with Vertical(id="sidebar"):
                yield Static("MOSS", id="sidebar-title")
                yield ListView(id="navigation-list")
            with Vertical(id="main"):
                yield Static("", id="detail")
                yield Static("Children / Page Links", id="child-title")
                yield ListView(id="child-list")
                yield Static("", id="status")
                yield Input(placeholder="Type: help", id="command")
        yield Footer()

    async def on_mount(self):
        self.memory = Memory()
        self.actions = ActionRunner(self.memory)
        self.actions.run("session_started")
        await self.refresh_navigation()
        await self.show_node("home")
        self.query_one("#command", Input).focus()

    def on_unmount(self):
        self._end_session()

    async def action_quit(self):
        self._end_session()
        self.exit()

    async def action_refresh(self):
        await self.refresh_navigation()
        if self.selected_id:
            await self.show_node(self.selected_id)

    async def refresh_navigation(self):
        view = self.query_one("#navigation-list", ListView)
        await view.clear()
        for nav_key, label in NAVIGATION_ITEMS:
            await view.append(NavigationItem(nav_key, label))

    async def on_list_view_selected(self, event: ListView.Selected):
        if isinstance(event.item, NavigationItem):
            await self._open_navigation(event.item.nav_key)
        elif isinstance(event.item, NodeListItem):
            await self.show_node(event.item.node_id)
        self.query_one("#command", Input).focus()

    async def on_input_submitted(self, event: Input.Submitted):
        command = event.value.strip()
        event.input.value = ""
        if command:
            await self.run_command(command)

    async def show_node(self, node_id):
        try:
            meta = self.memory.load_meta(node_id)
        except FileNotFoundError:
            await self.show_message(f"Node not found: {node_id}")
            return

        self.selected_id = meta["id"]
        if meta.get("type") == "page":
            self.active_page_id = meta["id"]
        self.query_one("#detail", Static).update(render_node(self.memory, meta["id"]))
        await self._show_child_items(meta)
        self._update_status()

    async def show_message(self, text):
        self.query_one("#detail", Static).update(text)
        await self._set_child_items([])
        self._update_status()

    async def run_command(self, command):
        parts = command.split()
        head = parts[0].lower()

        try:
            if head == "help":
                await self.show_message(HELP)
                return

            if head == "home":
                await self.show_node("home")
                return

            if command.lower() in {"all pages", "pages"}:
                await self._show_collection("All Pages", "page")
                return

            if command.lower() in {"all node types", "node types"}:
                await self._show_node_types()
                return

            if command.lower() in {"all action types", "action types"}:
                await self._show_action_types()
                return

            if head in {"history", "actionlog"} or command.lower() == "action log":
                await self._show_action_log()
                return

            if head == "where":
                await self._command_where()
                return

            if head == "refresh":
                await self.action_refresh()
                return

            if head in {"q", "quit", "exit"}:
                self._end_session()
                self.exit()
                return

            if head == "open" and len(parts) >= 2:
                await self.show_node(parts[1])
                return

            if head == "new" and len(parts) >= 2:
                node_id = parts[2] if len(parts) >= 3 else None
                await self._command_new(parts[1], node_id)
                return

            if head == "set" and len(parts) >= 2:
                await self._command_set(command[len("set") :].strip())
                return

            if head == "add" and len(parts) >= 2:
                await self._command_add(command[len("add") :].strip())
                return

            if head == "edit":
                await self._command_edit()
                return

            if head == "setattr" and len(parts) >= 3:
                await self._command_setattr(parts[1], command.split(maxsplit=2)[2])
                return

            if head == "link" and len(parts) >= 2:
                await self._command_link(parts[1])
                return

            if head == "unlink" and len(parts) >= 2:
                await self._command_unlink(parts[1])
                return

            if head == "move" and len(parts) >= 3:
                await self._command_move(parts[1].lower(), parts[2])
                return
        except Exception as error:
            await self.show_message(str(error))
            return

        await self.show_message(f"Unknown command:\n{command}\n\n{HELP}")

    async def _command_new(self, node_type, node_id):
        if node_id and any(character.isspace() for character in node_id):
            await self.show_message("Use one snake_case node_id.")
            return

        result = self.actions.run("create_node", payload={"type": node_type, "id": node_id})
        new_node_id = result["node_id"]
        parent_id = self._target_parent_id()
        if parent_id and new_node_id != parent_id:
            self.actions.run("link_node", payload={"parent_id": parent_id, "child_id": new_node_id})
        await self.show_node(new_node_id)

    async def _command_set(self, text):
        if not self.selected_id:
            await self.show_message("Select a node first.")
            return
        self.actions.run("set_content", payload={"node_id": self.selected_id, "text": f"{text}\n" if text else ""})
        await self.show_node(self.selected_id)

    async def _command_add(self, text):
        if not self.selected_id:
            await self.show_message("Select a node first.")
            return
        if not text:
            await self.show_message("Use: add <text>")
            return
        self.actions.run("add_content", payload={"node_id": self.selected_id, "text": text})
        await self.show_node(self.selected_id)

    async def _command_edit(self):
        if not self.selected_id:
            await self.show_message("Select a node first.")
            return
        result = self.actions.run("edit_content", payload={"node_id": self.selected_id})
        await self.show_message(f"Content file:\n{result['path']}")

    async def _command_setattr(self, field, value):
        if not self.selected_id:
            await self.show_message("Select a node first.")
            return
        parsed_value = self._parse_value(value)
        self.actions.run(
            "set_attribute",
            payload={"node_id": self.selected_id, "field": field, "value": parsed_value},
        )
        await self.show_node(self.selected_id)

    async def _command_link(self, child_id):
        parent_id = self._target_parent_id()
        if not parent_id:
            parent_id = "home"
        self.actions.run("link_node", payload={"parent_id": parent_id, "child_id": child_id})
        await self.show_node(parent_id)

    async def _command_unlink(self, child_id):
        parent_id = self._target_parent_id()
        if not parent_id:
            parent_id = "home"
        self.actions.run("unlink_node", payload={"parent_id": parent_id, "child_id": child_id})
        await self.show_node(parent_id)

    async def _command_move(self, direction, child_id):
        if direction not in {"up", "down"}:
            await self.show_message("Use: move up <node_id> or move down <node_id>")
            return
        parent_id = self._target_parent_id() or "home"
        self.actions.run("move_child", payload={"parent_id": parent_id, "child_id": child_id, "direction": direction})
        await self.show_node(parent_id)

    async def _command_where(self):
        selected_type = "(none)"
        selected_path = "(none)"
        if self.selected_id:
            meta = self.memory.load_meta(self.selected_id)
            selected_type = meta.get("type", "(unknown)")
            selected_path = str(self.memory.node_path(meta["id"]))

        await self.show_message(
            "\n".join(
                [
                    "Where",
                    "",
                    f"selected: {self.selected_id or '(none)'}",
                    f"selected type: {selected_type}",
                    f"active page: {self.active_page_id or '(none)'}",
                    f"selected path: {selected_path}",
                ]
            )
        )

    async def _open_navigation(self, nav_key):
        if nav_key == "home":
            await self.show_node("home")
        elif nav_key == "pages":
            await self._show_collection("All Pages", "page")
        elif nav_key == "node_types":
            await self._show_node_types()
        elif nav_key == "action_types":
            await self._show_action_types()
        elif nav_key == "action_log":
            await self._show_action_log()

    async def _show_collection(self, title, node_type):
        items = [meta for meta in sorted(self.memory.list_nodes(), key=self._navigation_sort_key) if meta.get("type") == node_type]
        self.selected_id = None
        lines = [title, ""]
        if items:
            for meta in items:
                lines.append(f"- {self._node_label(meta)}")
        else:
            lines.append("Nothing here yet.")
        self.query_one("#detail", Static).update("\n".join(lines))
        await self._set_child_items(items)
        self._update_status()

    async def _show_node_types(self):
        self.selected_id = None
        lines = ["All Node Types", ""]
        for node_type in known_node_types():
            lines.append(f"- {node_type}: {NODE_TYPE_HELP[node_type]}")
        self.query_one("#detail", Static).update("\n".join(lines))
        await self._set_child_items([])
        self._update_status()

    async def _show_action_types(self):
        self.selected_id = None
        lines = ["All Action Types", ""]
        for action_type in known_action_types():
            lines.append(f"- {action_type}: {ACTION_DESCRIPTIONS.get(action_type, 'Action.')}")
        self.query_one("#detail", Static).update("\n".join(lines))
        await self._set_child_items([])
        self._update_status()

    async def _show_action_log(self, limit=30):
        self.selected_id = None
        path = self.memory.logs / "action_log.txt"
        lines = ["Action Log", ""]
        if path.exists():
            recent = path.read_text(encoding="utf-8").splitlines()[-limit:]
            lines.extend(recent or ["No action history yet."])
        else:
            lines.append("No action history yet.")
        self.query_one("#detail", Static).update("\n".join(lines))
        await self._set_child_items([])
        self._update_status()

    async def _show_child_items(self, meta):
        if meta.get("type") not in PARENT_TYPES:
            await self._set_child_items([])
            return

        items = []
        for child_id in meta.get("children", []):
            try:
                items.append(self.memory.load_meta(child_id))
            except FileNotFoundError:
                continue
        await self._set_child_items(items)

    async def _set_child_items(self, metas):
        view = self.query_one("#child-list", ListView)
        await view.clear()
        for meta in metas:
            type_label = TYPE_LABELS.get(meta.get("type"), meta.get("type", "node"))
            await view.append(NodeListItem(meta["id"], f"{type_label}  {self._node_label(meta)}"))

    def _target_parent_id(self):
        if self.selected_id:
            selected = self.memory.load_meta(self.selected_id)
            if selected.get("type") in PARENT_TYPES:
                return selected["id"]
        return self.active_page_id or "home"

    def _parse_value(self, value):
        lower = str(value).strip().lower()
        if lower == "true":
            return True
        if lower == "false":
            return False
        return value

    def _update_status(self):
        status = f"selected: {self.selected_id or '(none)'}    active page: {self.active_page_id or '(none)'}"
        self.query_one("#status", Static).update(status)

    def _node_label(self, meta):
        return meta.get("title") or meta["id"]

    def _navigation_sort_key(self, meta):
        type_rank = {
            "page": 1,
            "todo_list": 2,
            "text": 3,
            "todo_item": 4,
            "image": 5,
        }
        if meta["id"] == "home":
            return (0, "", "")
        return (type_rank.get(meta.get("type"), 99), meta.get("title", ""), meta["id"])

    def _end_session(self):
        if self._session_closed or not self.actions:
            return
        self._session_closed = True
        self.actions.run("session_ended")
