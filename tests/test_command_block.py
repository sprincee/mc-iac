"""
Quick manual test: build a CommandBlock resource, generate its commands,
and push them to the live server via RconClient.

Run from the project root (with venv activated):
    python test_command_block.py
"""

from mc_iac.rcon_client import RconClient
from mc_iac.resources.command_block import CommandBlock

# Adjust position to somewhere near where you're standing in-game
config = {
    "position": [-20, -60, 35],
    "command": "say hello from mc-iac",
    "mode": "impulse",
    "auto": True,
}

block = CommandBlock(name="test_greeting", config=config)

print("Generated create commands:")
for cmd in block.create_commands():
    print(" ", cmd)

print("\nFingerprint:", block.fingerprint())

client = RconClient(host="localhost", password="Test-Password", port=25575)

print("\nSending to server...")
for cmd in block.create_commands():
    response = client.run(cmd)
    print("Response:", response)

print("\nDone. Check in-game: the command block should be placed.")