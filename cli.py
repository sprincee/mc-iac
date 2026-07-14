"""
cli.py

mc-iac entrypoint:
    python cli.py plan    --spec specs/example.yaml
    python cli.py apply   --spec specs/example.yaml
    python cli.py destroy --spec specs/example.yaml

Each spec file gets its own state file under .mc_iac_state/, so every
YAML file is an independent stack.
"""

import argparse
import os

from mc_iac.spec import load_spec
from mc_iac.state import load_state, save_state, update_resource_state, remove_resource_state
from mc_iac.diff import build_plan, print_plan
from mc_iac.rcon_client import RconClient

# --- Adjust these to match your server.properties ---
RCON_HOST = os.environ.get("MC_IAC_RCON_HOST", "localhost")
RCON_PASSWORD = os.environ.get("MC_IAC_RCON_PASSWORD", "changeme123")
RCON_PORT = int(os.environ.get("MC_IAC_RCON_PORT", "25575"))

STATE_DIR = ".mc_iac_state"


def get_client() -> RconClient:
    return RconClient(host=RCON_HOST, password=RCON_PASSWORD, port=RCON_PORT)


def state_path_for_spec(spec_path: str) -> str:
    os.makedirs(STATE_DIR, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(spec_path))[0]
    return os.path.join(STATE_DIR, f"{base_name}.state.json")


def cmd_plan(args):
    spec = load_spec(args.spec)
    state_path = state_path_for_spec(args.spec)
    state = load_state(state_path)
    plan = build_plan(spec, state)
    print(f"Stack: {spec['stack_name']}  (state: {state_path})\n")
    print_plan(plan)


def cmd_apply(args):
    spec = load_spec(args.spec)
    state_path = state_path_for_spec(args.spec)
    state = load_state(state_path)
    plan = build_plan(spec, state)

    changes = [p for p in plan if p.action != "noop"]
    if not changes:
        print("No changes. Infrastructure matches the spec.")
        return

    print(f"Stack: {spec['stack_name']}  (state: {state_path})\n")
    print_plan(plan)

    client = get_client()

    for change in changes:
        if change.action in ("create", "update"):
            commands = change.resource.create_commands()
            print(f"\nApplying {change.action} for '{change.name}' "
                  f"({len(commands)} commands)...")
            client.run_many(commands)
            print(f"  done.")

            state = update_resource_state(
                state,
                name=change.name,
                resource_type=change.resource_type,
                fingerprint=change.resource.fingerprint(),
            )

        elif change.action == "destroy":
            print(f"\nDestroying '{change.name}'...")
            old_resource = spec["resources"].get(change.name)
            if old_resource is not None:
                client.run_many(old_resource.destroy_commands())
                print(f"  done.")
            else:
                print(f"  (no resource definition available for '{change.name}', "
                      f"removing from state only)")

            state = remove_resource_state(state, change.name)

    save_state(state, state_path)
    print("\n Apply complete. State saved.")


def cmd_destroy(args):
    state_path = state_path_for_spec(args.spec)
    state = load_state(state_path)

    if not state["resources"]:
        print(f"Nothing to destroy -- state is empty ({state_path}).")
        return

    spec = load_spec(args.spec)
    client = get_client()

    for name, entry in list(state["resources"].items()):
        print(f"Destroying '{name}'...")
        resource = spec["resources"].get(name)
        if resource is not None:
            client.run_many(resource.destroy_commands())
            print(f"  done.")
        else:
            print(f"  (no resource definition available for '{name}', "
                  f"removing from state only)")

        state = remove_resource_state(state, name)

    save_state(state, state_path)
    print("\n Destroy complete. State cleared.")


def main():
    parser = argparse.ArgumentParser(description="mc-iac: Infrastructure as Code for Minecraft")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name, func in [("plan", cmd_plan), ("apply", cmd_apply), ("destroy", cmd_destroy)]:
        sub = subparsers.add_parser(name)
        sub.add_argument("--spec", default="specs/example.yaml", help="Path to the YAML spec file")
        sub.set_defaults(func=func)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
