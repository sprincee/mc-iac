"""
Quick manual test for state.py — no server/RCON needed for this one,
it's pure file I/O logic.

Run from the project root (with venv activated):
    python test_state.py
"""

from mc_iac.state import load_state, save_state, update_resource_state, remove_resource_state

TEST_STATE_FILE = "test_state.json"

# 1. Load state when no file exists yet -- should return empty structure
state = load_state(TEST_STATE_FILE)
print("Initial (empty) state:", state)
assert state == {"resources": {}}

# 2. Add a fake resource entry
state = update_resource_state(
    state,
    name="test_greeting",
    resource_type="command_block",
    fingerprint="abc123fakehash",
)
print("\nState after adding a resource:", state)

# 3. Save it to disk
save_state(state, TEST_STATE_FILE)
print(f"\nSaved to {TEST_STATE_FILE}")

# 4. Reload from disk and confirm it round-tripped correctly
reloaded = load_state(TEST_STATE_FILE)
print("\nReloaded state from disk:", reloaded)
assert reloaded == state, "Reloaded state doesn't match what we saved!"
print("\n✅ Round-trip successful — saved and reloaded state match.")

# 5. Remove the resource and confirm it's gone
reloaded = remove_resource_state(reloaded, "test_greeting")
print("\nState after removing test_greeting:", reloaded)
assert "test_greeting" not in reloaded["resources"]
print("\n✅ Removal successful.")

print("\nAll state.py tests passed. You can delete test_state.json now if you want.")