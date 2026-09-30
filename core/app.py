import json
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Label, ListItem, ListView, Static

from core.action_runner import ActionRunner
from core.memory import Memory
from core.renderer import render_node
from core.registry import known_node_types, load_node_type
from core.search import format_search_results, search_nodes


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
  info
  attributes
  setattr <field> <value>
  link <node_id>
  unlink <node_id>
  move up <node_id>
  move down <node_id>
  move <node_id> before <reference_node_id>
  move <node_id> after <reference_node_id>
  snapshot <snapshot_name>
  search <query>
  trash <node_id>  (permanently deletes the node)
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
  note
  todo_list
  todo_item
  image
  randomizer
  calendar
  week
  event
""".strip()

TYPE_LABELS = {
    "page": "page",
    "text": "text",
    "note": "note",
    "todo_list": "todo_list",
    "todo_item": "todo_item",
    "image": "image",
    "randomizer": "randomizer",
    "calendar": "calendar",
    "week": "week",
    "event": "event",
}

NAVIGATION_ITEMS = [
    ("home", "Home"),
    ("pages", "All Pages"),
    ("node_types", "All Node Types"),
    ("action_types", "All Action Types"),
    ("action_log", "Action Log"),
]

NODE_TYPE_HELP = {
    "page": "container node; may include a title and optional visible/hidden description",
    "text": "inline content node; renders content directly on parent pages",
    "note": "titled content node; renders as a card/link on parent pages and displays full content when opened",
    "todo_list": "container node; holds todo_item children and handles list ordering behavior",
    "todo_item": "content node with checked and system-managed date_completed",
    "image": "reference node; points to a material/source path",
    "randomizer": "content node containing one phrase per line; renders a random selection",
    "calendar": "container node; presents week children as a calendar",
    "week": "container node; starts on a Monday and holds event children",
    "event": "scheduled node with a title, notes, weekday number, start time, and end time",
}

PARENT_TYPES = {"page", "todo_list", "calendar", "week"}


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
                # Node renderers emit literal labels such as [x], [note], and [page].
                yield Static("", id="detail", markup=False)
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
                await self._show_pages_tree()
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

            if head == "search":
                await self._command_search(command[len("search") :].strip())
                return

            if head == "snapshot":
                await self._command_snapshot(parts[1:] if len(parts) >= 2 else [])
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

            if head in {"info", "attributes"}:
                await self._command_info()
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
                await self._command_move(parts[1:])
                return

            if head == "trash":
                await self._command_trash(parts[1] if len(parts) >= 2 else None)
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
        if result.get("opened"):
            await self.show_message(f"Opened content file:\n{result['path']}")
        else:
            await self.show_message(f"Could not open an editor. Content file:\n{result['path']}")

    async def _command_info(self):
        if not self.selected_id:
            await self.show_message("Select a node first.")
            return
        await self.show_message(self._format_node_info(self.selected_id))

    async def _command_setattr(self, field, value):
        if not self.selected_id:
            await self.show_message("Select a node first.")
            return
        self.actions.run(
            "set_attribute",
            payload={"node_id": self.selected_id, "field": field, "value": value},
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

    async def _command_move(self, arguments):
        parent_id = self._target_parent_id() or "home"
        if len(arguments) == 2 and arguments[0].lower() in {"up", "down"}:
            payload = {"parent_id": parent_id, "child_id": arguments[1], "direction": arguments[0].lower()}
        elif len(arguments) == 3 and arguments[1].lower() in {"before", "after"}:
            payload = {
                "parent_id": parent_id,
                "child_id": arguments[0],
                "position": arguments[1].lower(),
                "reference_id": arguments[2],
            }
        else:
            await self.show_message(
                "Use: move up <node_id>, move down <node_id>, or "
                "move <node_id> before/after <reference_node_id>"
            )
            return
        self.actions.run("move_child", payload=payload)
        await self.show_node(parent_id)

    async def _command_snapshot(self, arguments):
        if len(arguments) != 1:
            await self.show_message("Use: snapshot <snapshot_name>")
            return
        result = self.actions.run("snapshot", payload={"name": arguments[0]})
        await self.show_message(f"Created snapshot: {result['name']}\n{result['path']}")

    async def _command_search(self, query):
        results = search_nodes(self.memory, query)
        await self.show_message(format_search_results(query, results))

    async def _command_trash(self, node_id):
        trashed_id = self.memory.clean_id(node_id)
        self.actions.run("trash_node", payload={"node_id": trashed_id})

        if self.selected_id == trashed_id or self.active_page_id == trashed_id:
            self.active_page_id = "home"
            await self.show_node("home")
        elif self.selected_id and self.memory.node_exists(self.selected_id):
            await self.show_node(self.selected_id)
        else:
            await self.show_node("home")

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
            await self._show_pages_tree()
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

    async def _show_pages_tree(self):
        pages = {meta["id"]: meta for meta in self._read_all_node_metas() if meta.get("type") == "page"}
        visited = set()
        lines = ["All Pages", ""]

        if "home" in pages:
            lines.extend(self._page_tree_lines("home", pages, visited, 0))
        else:
            lines.append("home (missing)")

        unlinked = [page_id for page_id in sorted(pages) if page_id not in visited]
        lines.append("")
        lines.append("Unlinked Pages:")
        if unlinked:
            lines.extend(f"  {page_id}" for page_id in unlinked)
        else:
            lines.append("  (none)")

        self.selected_id = None
        self.query_one("#detail", Static).update("\n".join(lines))
        await self._set_child_items([pages[page_id] for page_id in sorted(pages)])
        self._update_status()

    def _page_tree_lines(self, page_id, pages, visited, depth):
        indent = "  " * depth
        if page_id in visited:
            return [f"{indent}{page_id} (already shown)"]

        meta = pages.get(page_id)
        if not meta:
            return [f"{indent}{page_id} (missing)"]

        visited.add(page_id)
        lines = [f"{indent}{page_id}"]
        for child_id in meta.get("children", []):
            child = pages.get(child_id)
            if child:
                lines.extend(self._page_tree_lines(child["id"], pages, visited, depth + 1))
        return lines

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
        lines = [
            "All Action Types",
            "",
            "Tree actions:",
            "- new",
            "- link",
            "- unlink",
            "- move",
            "- trash",
            "",
            "Content/attribute actions:",
            "- set",
            "- add",
            "- edit",
            "- setattr",
            "",
            "Memory/safety actions:",
            "- snapshot",
            "",
            "System/read actions:",
            "- home",
            "- open",
            "- info / attributes",
            "- search",
            "- all pages",
            "- all node types",
            "- all action types",
            "- action log",
            "- history",
            "- refresh",
        ]
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

    def _update_status(self):
        status = f"selected: {self.selected_id or '(none)'}    active page: {self.active_page_id or '(none)'}"
        self.query_one("#status", Static).update(status)

    def _node_label(self, meta):
        return meta.get("title") or meta["id"]

    def _format_node_info(self, node_id):
        meta = self._read_node_meta(node_id)
        if not meta:
            return f"Node not found: {node_id}"

        node_id = meta.get("id") or self.memory.clean_id(node_id)
        content_path = self.memory.content_path(node_id)
        try:
            content_length = len(content_path.read_text(encoding="utf-8"))
        except OSError:
            content_length = 0

        children = meta.get("children", [])
        parents = self._parent_ids_for(node_id)
        node_type_name = meta.get("type", "(unknown)")
        try:
            node_type = load_node_type(node_type_name)
            allowed = tuple(getattr(node_type, "ALLOWED_ATTRIBUTES", ()))
            defaults = dict(getattr(node_type, "ATTRIBUTE_DEFAULTS", {}))
            managed = set(getattr(node_type, "SYSTEM_MANAGED_ATTRIBUTES", ()))
        except KeyError:
            allowed = ()
            defaults = {}
            managed = set()
        standard_fields = {"id", "type", "children", "files", "created", "updated", *allowed}
        extras = [(key, meta[key]) for key in sorted(meta) if key not in standard_fields]

        lines = [
            f"Node: {node_id}",
            f"Type: {node_type_name}",
            "",
            "Allowed attributes:",
        ]
        if allowed:
            for field in allowed:
                suffix = " (system-managed)" if field in managed else ""
                if field in meta:
                    value = self._format_value(meta[field])
                elif field in defaults:
                    value = f"(unset; default: {self._format_value(defaults[field])})"
                else:
                    value = "(unset)"
                lines.append(f"{field}: {value}{suffix}")
        else:
            lines.append("(none)")
        lines.extend(
            [
                "",
                "Children:",
                f"{len(children)} children",
                *[f"- {child_id}" for child_id in children],
                "",
                "Details:",
                f"content path: {content_path}",
                f"content length: {content_length}",
                f"parent IDs: {', '.join(parents) if parents else '(none)'}",
                f"created: {meta.get('created', '(unknown)')}",
                f"updated: {meta.get('updated', '(unknown)')}",
            ]
        )
        if extras:
            lines.append("extra fields:")
            for key, value in extras:
                lines.append(f"  {key}: {self._format_value(value)}")
        return "\n".join(lines)

    def _parent_ids_for(self, node_id):
        parents = []
        for meta in self._read_all_node_metas():
            if node_id in meta.get("children", []):
                parents.append(meta.get("id", ""))
        return sorted(parent_id for parent_id in parents if parent_id)

    def _read_all_node_metas(self):
        metas = []
        if not self.memory.nodes.exists():
            return metas
        for path in self.memory.nodes.iterdir():
            if path.is_dir():
                meta = self._read_node_meta(path.name)
                if meta:
                    metas.append(meta)
        return metas

    def _read_node_meta(self, node_id):
        path = self.memory.meta_path(node_id)
        try:
            meta = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        meta.setdefault("id", self.memory.clean_id(node_id))
        meta.setdefault("type", "text")
        meta.setdefault("children", [])
        return meta

    def _format_value(self, value):
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=True)
        if value is None:
            return "null"
        if isinstance(value, bool):
            return str(value).lower()
        return str(value)

    def _navigation_sort_key(self, meta):
        type_rank = {
            "page": 1,
            "todo_list": 2,
            "note": 3,
            "text": 4,
            "todo_item": 5,
            "image": 6,
            "randomizer": 7,
            "calendar": 8,
            "week": 9,
            "event": 10,
        }
        if meta["id"] == "home":
            return (0, "", "")
        return (type_rank.get(meta.get("type"), 99), meta.get("title", ""), meta["id"])

    def _end_session(self):
        if self._session_closed or not self.actions:
            return
        self._session_closed = True
        self.actions.run("session_ended")
