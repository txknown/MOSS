# MOSS architecture

MOSS is a local, file-backed system built from small, explicit parts. The shared
code supplies capabilities; each user's memory supplies their content and
structure. A workspace can grow without requiring a database or a fixed
organizational template.

| Part | Role |
| --- | --- |
| **Memory** | Stores nodes, content, and relationships. |
| **Actions** | Validate and perform changes. |
| **System views** | Provide ways to inspect or operate MOSS: Search, Memory map, logs, and snapshots. |
| **Presentation** | Determines appearance and navigation without changing content. |
| **AI2 agents** | Organize memory through actions and extend MOSS's code when requested. |
| **Computer** | Stores the files and runs Python and the browser. |

AI2 stands for **Automated Idea Infrastructure**. In this implementation, an
agent is an external collaborator with authorized access to local files and
Python. It uses the same actions and rules as other interfaces.

## Memory and actions

Each node has an ID and a type. `memory/nodes/<id>/node.json` contains attributes
and ordered child IDs; a `content.txt` file holds text where the type supports it.
Parent relationships are derived from child references. An Internal Link points
to another node or an allowlisted system view without becoming its parent.

`core/node_schema.py` defines fields, defaults, validation metadata, and child
rules. The pure normalizer supplies backward-compatible defaults when old files
omit newer fields. Reading never writes, repairs, or migrates node files.

Durable writes pass through `core/action_runner.py` to an action module. Actions
validate their inputs and record a summary in Action log. The web server adds
same-origin checks and an explicit action allowlist. Its lock coordinates web
requests within one process; it does not serialize separate agent or terminal
processes. Coordinate writers when using more than one interface.

## System views

Search and Memory map are projections of memory. Node types and Action types
explain the available capabilities. Action log displays workspace history; MOSS
version log displays code history. Snapshots provides an archive list and an
explicit action to create a backup.

These views are routes and Python/browser code, not content nodes.
`core/system_views.py` defines linkable built-in destinations. Internal Link
nodes and navigation settings can point to these views.

## Presentation

Three kinds of state remain separate:

| Location | Contains |
| --- | --- |
| `memory/system/ui_settings.json` | Scheme, startup mode, home ID, ordered navigation links. |
| `memory/system/node_display.json` | Each selected node's `parent` and `open` display-style IDs. |
| `core/ui_schemes.json`, `core/display_styles.py`, browser modules | Reusable palette/style definitions and renderers shipped with the code. |

Preference files are created on explicit save. Missing preferences use defaults
without writing files. `update_ui_settings` and `update_node_display` validate
and atomically save their respective files. Node renames update presentation
references with the same rollback used for relationship updates.

Navigation is an ordered list of `{ "label": "…", "target": "…" }` entries.
Targets are `home`, `node:<id>`, or an allowlisted `system:<view>`. The top bar
and top-down view use the same list; MOSS UI is appended as a fixed destination.
A missing saved node link stays visible so its target can be repaired or removed.

Display-style IDs are scoped by node type and context. The same parent style is
used wherever a node is embedded. Each context starts at `default`. Unknown or
incompatible selections fall back to Default; removing a style does not remove
content. The Calendar `current-week` parent style selects existing weeks by local
date and reuses the normal week renderer.

## Code layout and data flow

```text
memory/nodes → Python normalization/schema → ReadService/FastAPI → browser renderer
browser editor → allowlisted action → validation → file write + Action log

core/          Storage, schema, validation, action catalog, terminal application
node_types/    Terminal renderers derived from the canonical node schema
action_types/  Durable operations
web/           Read projection, local HTTP boundary, browser modules and styles
tools/         Plain-text todo importer
tests/         Temporary-data Python and JavaScript checks
```

The browser consumes `/api/schema` rather than maintaining a second table of
node validation rules. UI preferences use `/api/ui-settings`; API version 15
identifies the presentation contracts included with v1.1.0.

## Add a node type or action

1. Define node fields, defaults, validation, and child rules in
   `core/node_schema.py`. Use existing field types or extend the shared validator.
2. Add its terminal renderer in `node_types/`. Add browser rendering in
   `web/static/renderers/` and connect it in `web/static/app.js`.
3. Put new durable behavior in `action_types/`. Register it in
   `core/action_catalog.py`; browser access also requires `WEB_ACTIONS` in
   `web/server.py` and the relevant API projection.
4. Test with synthetic data, including older nodes missing new defaults and
   invalid requests that must leave memory unchanged.
5. Record the code release in `change_log.json` and `version.txt`.

Before adding a type, check whether an existing Item List, Log, or Page can
express the need. A dedicated type is useful when it adds a distinct contract
or behavior.

## Add a display style

1. Add an inert catalog entry in `core/display_styles.py` under the node type
   and `parent` or `open` context. Supply an ID, name, and short description.
2. Implement a renderer in a browser module and register its callback in the
   `createDisplayStyles` renderer map in `web/static/app.js`, using the key
   `<node-type>:<context>:<style-id>`.
3. Keep Default unchanged. Return a DOM element, or a promise for one. Use safe
   text helpers and existing read APIs; settings never supply executable code.
   For the `open` context, the shared app adds the standard node header and editor.
4. Add tests for selection, rendering, missing data, and Default fallback.
   Both the node editor and MOSS UI catalog will discover the Python catalog entry.

A style changes presentation, not the node's type or relationships. Any editing
controls in a renderer must still invoke validated actions.

## Add a saved color scheme

Add a record to `core/ui_schemes.json` with a unique slug `id`, a short `name`,
`mode` (`light` or `dark`), and all color keys listed in
`core/ui_settings.py:PALETTE_KEYS`, each as a six-digit hex color. Preserve the
built-in light scheme, which is the fallback. Validate contrast and forms in the
browser, then add release notes. The selector lists saved records automatically.

## Starter workspaces

v1.1.0 starts with an empty Home. A future starter can supply ordinary initial
nodes, presentation preferences, and documentation. No separate starter format,
installer, or merge behavior is part of this release.
