"""
Quick manual test for spec.py — confirms YAML loads correctly into
real Resource objects with working create_commands()/fingerprint().

Run from the project root (with venv activated):
    python test_spec.py
"""

from mc_iac.spec import load_spec

spec = load_spec("specs/example.yaml")

print("Stack name:", spec["stack_name"])
print("Resources found:", list(spec["resources"].keys()))

for name, resource in spec["resources"].items():
    print(f"\n--- {name} ---")
    print("Type:", type(resource).__name__)
    print("Fingerprint:", resource.fingerprint())
    print("Create commands:")
    for cmd in resource.create_commands():
        print(" ", cmd)
    print("Destroy commands:")
    for cmd in resource.destroy_commands():
        print(" ", cmd)

print("\n✅ Spec loaded and resources built successfully.")