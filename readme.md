# MOSS

MOSS is a local, memory-first workspace built from nodes, actions, and renderers. The high-level purpose is to provide a versatile and structured sandbox workspace that can be easily expanded and improved by adding additional action, node, and rendering logic.

## Core idea

- Nodes are memory objects.
- Nodes contain references to nodes in a graph-like structure.
- Actions change memory.
- Rendering displays memory.
- The `memory/` folder is created locally on first run and is not committed.

## Version

MOSS is currently at `v0`: a basic test skeleton for local memory, node creation, actions, and rendering. Future versions may expand the node/action system, improve the interface, and support more complex personal workspace logic.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python start_moss.py