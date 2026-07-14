"""
Quick manual test for diff.py — no server/RCON needed here either.
Simulates a few different state scenarios against the same spec.

Run from the project root (with venv activated):
    python test_diff.py
"""

from mc_iac.spec import load_spec
from mc_iac.diff import build_plan, print_plan

spec = load_spec("specs/example.yaml")

print("=== Scenario 1: empty state (first-ever apply) ===")
empty_state = {"resources": {}}
plan = build_plan(spec, empty_state)
print_plan(plan)

print("\n=== Scenario 2: state already matches spec exactly ===")
matching_state = {"resources": {}}
for name, resource in spec["resources"].items():
    matching_state["resources"][name] = {
        "type": type(resource).__name__,
        "fingerprint": resource.fingerprint(),
    }
plan = build_plan(spec, matching_state)
print_plan(plan)

print("\n=== Scenario 3: state has a stale fingerprint (drift/change) ===")
stale_state = {"resources": {}}
for name, resource in spec["resources"].items():
    stale_state["resources"][name] = {
        "type": type(resource).__name__,
        "fingerprint": "this-is-a-fake-outdated-hash",
    }
plan = build_plan(spec, stale_state)
print_plan(plan)

print("\n=== Scenario 4: state has a resource no longer in spec ===")
orphan_state = {"resources": {
    "old_resource_not_in_spec_anymore": {
        "type": "CommandBlock",
        "fingerprint": "whatever",
    }
}}
plan = build_plan(spec, orphan_state)
print_plan(plan)