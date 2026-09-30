# MOSS architecture invariants

MOSS is a foundations-first, local, file-backed system. Keep changes small,
readable, and backward-compatible.

- Python owns node domain rules, defaults, and validation. Add or change node
  attributes, editable content, or generic child rules in
  `core/node_schema.py`; do not recreate those tables in actions or JavaScript.
- `core/node_normalization.py` is the pure shared normalization layer. Reads
  must never write, repair, migrate, or otherwise mutate `memory/`.
- Durable changes go through `ActionRunner`. Browser mutations must remain
  explicitly allowlisted in `web/server.py`. Destructive controls require an
  explicit user action, an exact-target confirmation, and server-side guards.
- Existing `node.json` and `content.txt` files are durable public data. New
  schema defaults must keep older files working without migration.
- Preserve same-origin checks, CSP, safe material-path resolution, action
  allowlisting, and text-only DOM construction. Do not use `innerHTML` or an
  equivalent injection shortcut.
- Frontend renderers own presentation, not domain validation. Editors consume
  the inert schema returned by `/api/schema`.
- Add focused tests whenever schema interpretation, normalization, API shape,
  or rendering contracts change. Confirm read tests leave fixtures byte-for-byte
  unchanged and run JavaScript parse checks.
- Avoid dependencies, frameworks, databases, bundlers, and build tooling unless
  a future requirement clearly justifies them.
- Record code releases in `change_log.json` (newest first) and keep the first
  entry's version in sync with the first line of `version.txt` (`MOSS vX.Y.Z`).
  Every Python change must be described in a release entry; include related
  HTML, CSS, and JavaScript changes in that same release. Increment the patch
  number for small code updates. Keep release notes free of personal content.
  The browser's MOSS Change log reads this file without changing memory.
- Commands, node edits, and other memory changes belong in the existing action
  log through `ActionRunner`; they do not bump the code version. Do not migrate
  personal content into release notes or automatically rewrite old log entries.

## Code flow

Durable node files in `memory/nodes/` flow through the pure Python normalizer
and canonical schema. `ReadService` projects that data into safe JSON through
FastAPI. Native browser modules render it and build schema-driven editors:

`node files → normalization/schema → ReadService/FastAPI → renderer/editor`

Python layout:

- `core/action_catalog.py`: inert reference metadata for registered actions
- `core/node_schema.py`: canonical node contracts and safe public schema
- `core/node_normalization.py`: non-mutating metadata defaults
- `core/node_validation.py`: schema-backed attribute and content validation
- `core/logs.py`: pure validation for log templates and entry snapshots
- `core/items.py`: pure validation for shared item-list fields and item values
- `core/snapshots.py`: safe names and read-only metadata for memory archives
- `core/urls.py`: pure allowlisting and normalization for safe HTTP/HTTPS URLs
- `node_types/`: terminal renderers, with compatibility constants derived from
  the canonical schema
- `action_types/`: validated durable mutations
- `web/read_service.py`: read-only file access and safe API projection
- `web/server.py`: local HTTP and allowlisted mutation boundary

Frontend layout:

- `web/static/app.js`: startup, routes, history, explicit state, composition
- `web/static/api.js`: HTTP calls and server compatibility
- `web/static/dom.js`: shared safe DOM/text helpers
- `web/static/editors.js`: schema-driven node and relationship editors
- `web/static/renderers/`: content, todo, calendar, log, material, and system views

Embedded Notes use a presentation-limited preview, but inline editing always
loads and saves their complete content. Link destinations must be validated in
Python and re-sanitized by read projection before being assigned to an anchor.
Item Lists contain ordered Item children and own their shared field definition;
an Item stores a title plus exactly those field values and has no body content.
Internal Links point to another node without adding a tree relationship;
missing targets must remain visible as broken references rather than being followed.

Log templates and log entries are deliberately separate durable nodes. Every
entry stores its prompt snapshot; changing a template must affect future
entries only and must never reinterpret earlier answers.
