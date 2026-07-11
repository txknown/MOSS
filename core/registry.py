from importlib import import_module


NODE_TYPE_NAMES = [
    "page",
    "text",
    "todo_list",
    "todo_item",
    "image",
]

ACTION_TYPE_NAMES = [
    "create_node",
    "set_content",
    "add_content",
    "edit_content",
    "set_attribute",
    "link_node",
    "unlink_node",
    "move_child",
    "session_started",
    "session_ended",
]


def known_node_types():
    return list(NODE_TYPE_NAMES)


def known_action_types():
    return list(ACTION_TYPE_NAMES)


def load_node_type(name):
    name = str(name).strip().lower()
    if name not in NODE_TYPE_NAMES:
        raise KeyError(f"Unknown node type: {name}")
    return import_module(f"node_types.{name}")


def load_action_type(name):
    name = str(name).strip().lower()
    if name not in ACTION_TYPE_NAMES:
        raise KeyError(f"Unknown action type: {name}")
    return import_module(f"action_types.{name}")
