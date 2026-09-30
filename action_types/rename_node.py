"""Rename a stable node ID while preserving relationships and stored content."""


def run(memory, payload, runner=None):
    if runner is None:
        raise RuntimeError("rename_node must run through ActionRunner")
    if not isinstance(payload, dict):
        raise ValueError("rename_node requires an object")
    unknown = sorted(set(payload) - {"node_id", "new_id"})
    if unknown:
        raise ValueError(f"Unknown rename field: {', '.join(unknown)}")

    node_id = memory.clean_id(payload.get("node_id"))
    new_id = memory.clean_id(payload.get("new_id"))
    if not node_id or not memory.node_exists(node_id):
        raise FileNotFoundError(f"Node not found: {node_id or '(empty node ID)'}")
    if node_id == "home":
        raise ValueError("The home node ID cannot be changed.")
    if not new_id:
        raise ValueError("A new node ID is required.")
    if node_id == new_id:
        return {
            "old_id": node_id,
            "node_id": node_id,
            "changed": False,
            "log": None,
        }
    if memory.node_path(new_id).exists():
        raise FileExistsError(f"Node already exists: {new_id}")

    memory.rename_node(node_id, new_id)
    return {
        "old_id": node_id,
        "node_id": new_id,
        "changed": True,
        "log": f"renamed node {node_id} to {new_id}",
    }
