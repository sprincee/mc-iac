"""
spec.py

Loads a YAML spec file (declared "desired state") and turns each entry
into a Resource object via RESOURCE_REGISTRY.
"""

import yaml
from mc_iac.resources.command_block import CommandBlock
from mc_iac.resources.starter_housev2 import StarterHouse
from mc_iac.resources.well import Well
from mc_iac.resources.farm import Farm
from mc_iac.resources.path import Path
from mc_iac.resources.enchanting_tower import EnchantingTower
from mc_iac.resources.barn import Barn
from mc_iac.resources.blacksmith import Blacksmith

RESOURCE_REGISTRY = {
    "command_block": CommandBlock,
    "starter_house": StarterHouse,
    "well": Well,
    "farm": Farm,
    "path": Path,
    "enchanting_tower": EnchantingTower,
    "barn": Barn,
    "blacksmith": Blacksmith,
}


def load_spec(path: str) -> dict:
    """Load a YAML spec file, return {"stack_name": ..., "resources": {name: Resource}}."""
    with open(path, "r") as f:
        raw = yaml.safe_load(f)

    resources = {}

    for entry in raw.get("resources", []):
        entry = dict(entry)
        resource_type = entry.pop("type")
        name = entry.pop("name")

        if resource_type not in RESOURCE_REGISTRY:
            raise ValueError(
                f"Unknown resource type '{resource_type}' for resource '{name}'. "
                f"Known types: {list(RESOURCE_REGISTRY.keys())}"
            )

        resource_class = RESOURCE_REGISTRY[resource_type]
        resources[name] = resource_class(name=name, config=entry)

    return {
        "stack_name": raw.get("stack_name", "unnamed-stack"),
        "resources": resources,
    }
