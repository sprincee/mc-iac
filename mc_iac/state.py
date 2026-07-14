"""
state.py

Handles reading and writing state.json — mc-iac's record of what's
currently been provisioned (similar to Terraform's .tfstate file).

The state file looks like:

{
    "resources": {
        "test_greeting": {
            "type": "command_block",
            "fingerprint": "a1b2c3..."
        },
        ...
    }
}
"""

import json
import os

STATE_FILE = "state.json"


def load_state(path: str = STATE_FILE) -> dict:
    """
    Load state.json from disk. If it doesn't exist yet (first run ever),
    return an empty state structure instead of crashing.
    """
    if not os.path.exists(path):
        return {"resources": {}}

    with open(path, "r") as f:
        return json.load(f)


def save_state(state: dict, path: str = STATE_FILE) -> None:
    """
    Write the state dict back to disk as pretty-printed JSON.
    """
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


def update_resource_state(state: dict, name: str, resource_type: str, fingerprint: str) -> dict:
    """
    Record (or overwrite) a single resource's entry in the state dict.
    Does NOT save to disk — call save_state() after you're done making changes.
    """
    state["resources"][name] = {
        "type": resource_type,
        "fingerprint": fingerprint,
    }
    return state


def remove_resource_state(state: dict, name: str) -> dict:
    """
    Remove a resource's entry from state (used after destroy).
    """
    state["resources"].pop(name, None)
    return state