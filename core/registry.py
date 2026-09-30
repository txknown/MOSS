from importlib import import_module


from core.action_catalog import action_type_names
from core.node_schema import node_type_names


NODE_TYPE_NAMES = list(node_type_names())

ACTION_TYPE_NAMES = list(action_type_names())


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
