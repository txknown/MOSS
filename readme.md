# MOSS

**v1.0.0**

MOSS is a local system for creating and connecting nodes: pages, notes, tasks,
lists, and other content. You choose how to organize them, and you can extend
the code with new node types, actions, and renderers.

For an organizational workspace, a project page might contain notes, a task
list, a schedule, and reference links. You can create and edit these nodes in
the browser using the included types, then add custom behavior when needed.

Python handles storage and validation; HTML, CSS, and JavaScript provide the
web interface. Your data is stored in ordinary files on your computer. MOSS
runs locally without a database, frontend build step, or MOSS account.

## Start the web interface

You need Git and Python 3.10 or newer. This release has been tested with
Python 3.14. The commands below use macOS or Linux; on macOS they also work in
VS Code's integrated terminal.

Clone the repository and install its Python dependencies once:

```sh
git clone https://github.com/txknown/MOSS.git
cd MOSS
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

If you already have the repository, open a terminal in its folder and begin
with the virtual environment step.

Launch MOSS:

```sh
.venv/bin/python start_web.py
```

Your browser opens at <http://127.0.0.1:8766/node/home>. On the first launch,
MOSS creates a local `memory/` directory with an empty **Home** page.

Keep the terminal open while using MOSS. Press **Ctrl+C** in that terminal to
stop the server. To use it again, run the same launch command; dependency
installation is only needed during setup or when requirements change.

If the browser does not open automatically, visit the address above. If the
port is occupied, the launcher reports it and exits. The server listens on
this computer's loopback address and is intended for local use.

## Use MOSS: build a workspace

On **Home**, open **Edit**, find **Create child**, choose a node type, and click
**Create**. Open a node's editor to change its content or attributes. Pages can
also link existing nodes and change their order.

For example, create a page for a project, add a note for its purpose, a to-do
list for next steps, and links to useful resources. Add more pages or node
types as the project grows. Creating and connecting these nodes does not
require changing the code.

Available node types include:

- **Pages, notes, and text** for projects, writing, and reference material.
- **To-do lists and items** for tasks and nested checklists.
- **Calendars, weeks, and events** for schedules.
- **Item lists and items** for collections with shared fields.
- **Logs and log entries** for reusable prompts and recorded answers.
- **Images, links, and internal links** for local materials and references.
- **Randomizers** for selections from a list of phrases or prompts.

Randomizers show their selected text without a heading on parent pages by
default. Enable **Show title on parent page** in the randomizer's editor to
show its heading. The title remains visible when opening the node itself.

The navigation includes **Search**, **Memory map**, and reference pages for
**Node types** and **Action types**. **Snapshots** creates and downloads ZIP
backups of your memory and version information.

## Launch from any folder with zsh

For an optional `moss-web` command, add this function to `~/.zshrc`. Replace
`/absolute/path/to/MOSS` with the full path to your repository; run `pwd` in
its folder to find that path.

```zsh
moss-web() {
  local moss_dir="/absolute/path/to/MOSS"
  "$moss_dir/.venv/bin/python" "$moss_dir/start_web.py" "$@"
}
```

Load the function in your current terminal, then launch:

```zsh
source ~/.zshrc
moss-web
```

New zsh terminals load the function automatically. It uses the project's own
Python environment and works from any folder. If you move the repository,
update the path in the function.

## Your data

Each installation stores its workspace beside the source code:

```text
memory/
  nodes/       Node metadata and text content
  materials/   Local images and other referenced files
  system/      Settings, counters, and the node registry
  logs/        Recorded actions
snapshots/     ZIP backups created through MOSS
```

The repository starts without personal workspace data. Launching MOSS again
uses the existing memory; it does not reset your workspace. Data paths are
relative to the installation, regardless of the terminal's current folder.

`memory/`, `snapshots/`, virtual environments, and caches are excluded by
`.gitignore`. Keep those exclusions when sharing code. A manual folder copy
or ZIP does not apply Git's ignore rules, so choose explicitly whether to
include your workspace data. Snapshots contain your data too.

## Two kinds of history

**Action log** records commands and memory changes made through MOSS, such as
creating a node, editing content, or moving a child.

**MOSS Change log** displays code releases from `change_log.json`. The initial
release is **v1.0.0**. Small code updates increment the patch version, for
example `v1.0.1`; adding notes or completing tasks does not change the code
version. Release entries are maintained alongside code changes, and
`version.txt` identifies the current release.

## Build MOSS: extend the system

MOSS is intended to grow through small, understandable additions. You can
introduce a new kind of node, add an action, or change how a node is rendered
while keeping the underlying file-based model.

- **Nodes** hold content and references to other nodes.
- **Actions** validate and save changes to memory.
- **Renderers** display nodes in the browser or terminal.

```text
core/           Storage, schemas, validation, and the terminal app
action_types/   Operations on nodes and relationships
node_types/     Node-specific terminal renderers
web/            Python web server and HTML/CSS/JavaScript interface
tools/          Plain-text to-do importer
tests/          Tests using temporary, synthetic workspaces
```

Node rules live in `core/node_schema.py`. Durable changes pass through
`ActionRunner`; web reads do not modify or migrate memory.

For a new node type, start with its purpose and the smallest set of fields it
needs. A reading collection, for example, can already use an item list with
shared fields. A dedicated book node becomes useful when it needs its own
behavior or presentation.

When extending the code:

1. Define the node's fields, defaults, validation, and child rules in
   `core/node_schema.py`. The browser's general editors use that schema.
2. Add its terminal renderer in `node_types/` and its browser presentation in
   `web/static/renderers/`, connecting the browser renderer in `web/static/app.js`.
3. If it needs a new operation, implement it in `action_types/`, register it in
   `core/action_catalog.py`, and explicitly allow browser access where needed.
4. Test with temporary data and keep existing saved nodes compatible.
5. Describe the code change in `change_log.json` and update `version.txt` for
   the release.

Keep domain rules in Python and presentation in the renderers. See
[AGENTS.md](AGENTS.md) for the architecture constraints used when extending MOSS.

## Terminal interface

A terminal interface is also available:

```sh
.venv/bin/python start_moss.py
```

It uses the same local memory as the web interface.

## Development checks

From the repository folder:

```sh
.venv/bin/python -B -m unittest discover -s tests -v
```

Tests use temporary data rather than your workspace. Node.js is optional for
running MOSS, but enables the JavaScript syntax and renderer checks in the
test suite; those checks are skipped when Node.js is unavailable.

## License

MOSS is free to use, modify, and share under the [MOSS Free Use License](LICENSE).
The license also includes the project's mission request concerning **MOSS**,
**AI2**, and **186**.
