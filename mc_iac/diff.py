"""
diff.py

Compares a loaded spec (desired state, from spec.py) against the
current state (actual last-applied state, from state.json via state.py),
and produces a plan: which resources need to be created, updated, or
destroyed.

This is the core "terraform plan" logic of mc-iac.
"""

from dataclasses import dataclass
from typing import Literal

Action = Literal["create", "update", "destroy", "noop"]


@dataclass
class PlannedChange:
    name: str
    action: Action
    resource: object = None  # the actual Resource object (None for destroy-only)
    resource_type: str = None


def build_plan(spec: dict, state: dict) -> list[PlannedChange]:
    """
    spec: output of spec.load_spec() -> {"stack_name": ..., "resources": {name: Resource}}
    state: output of state.load_state() -> {"resources": {name: {"type": ..., "fingerprint": ...}}}

    Returns a list of PlannedChange, one per resource that needs attention.
    Resources with no changes are included as "noop" so callers can show
    a full picture, or filter them out if they only care about actual changes.
    """
    plan = []

    spec_resources = spec["resources"]           # name -> Resource object
    state_resources = state["resources"]         # name -> {"type", "fingerprint"}

    spec_names = set(spec_resources.keys())
    state_names = set(state_resources.keys())

    # Resources in spec but not in state -> CREATE
    for name in spec_names - state_names:
        resource = spec_resources[name]
        plan.append(PlannedChange(
            name=name,
            action="create",
            resource=resource,
            resource_type=type(resource).__name__,
        ))

    # Resources in both -> compare fingerprints
    for name in spec_names & state_names:
        resource = spec_resources[name]
        current_fingerprint = resource.fingerprint()
        last_applied_fingerprint = state_resources[name]["fingerprint"]

        if current_fingerprint != last_applied_fingerprint:
            plan.append(PlannedChange(
                name=name,
                action="update",
                resource=resource,
                resource_type=type(resource).__name__,
            ))
        else:
            plan.append(PlannedChange(
                name=name,
                action="noop",
                resource=resource,
                resource_type=type(resource).__name__,
            ))

    # Resources in state but not in spec anymore -> DESTROY
    for name in state_names - spec_names:
        plan.append(PlannedChange(
            name=name,
            action="destroy",
            resource=None,
            resource_type=state_resources[name]["type"],
        ))

    return plan


def print_plan(plan: list[PlannedChange]) -> None:
    """
    Pretty-print a plan, Terraform-style.
    """
    symbols = {
        "create": "+",
        "update": "~",
        "destroy": "-",
        "noop": " ",
    }

    changes = [p for p in plan if p.action != "noop"]

    if not changes:
        print("No changes. Infrastructure matches the spec.")
        return

    for p in plan:
        symbol = symbols[p.action]
        print(f"  {symbol} {p.action:8} {p.resource_type:20} {p.name}")

    print(f"\nPlan: "
          f"{sum(1 for p in plan if p.action == 'create')} to create, "
          f"{sum(1 for p in plan if p.action == 'update')} to update, "
          f"{sum(1 for p in plan if p.action == 'destroy')} to destroy.")