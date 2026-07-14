import hashlib
from mc_iac.resources.base import Resource


class CommandBlock(Resource):
    """
    A single Minecraft command block resource.

    Expected config keys:
        position: [x, y, z]
        command: str  -- the command this block will run
        mode: "impulse" | "chain" | "repeat"  (default: "impulse")
        auto: bool  -- whether it triggers without redstone (default: True)
    """

    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        self.position = config["position"]
        self.command = config["command"]
        self.mode = config.get("mode", "impulse")
        self.auto = config.get("auto", True)

    def _block_id(self) -> str:
        return {
            "impulse": "minecraft:command_block",
            "chain": "minecraft:chain_command_block",
            "repeat": "minecraft:repeating_command_block",
        }[self.mode]

    def create_commands(self) -> list[str]:
        x, y, z = self.position
        block_id = self._block_id()
        auto_flag = 1 if self.auto else 0
        safe_command = self.command.replace('"', '\\"')
        nbt = f'{{Command:"{safe_command}",auto:{auto_flag}b}}'
        return [f"setblock {x} {y} {z} {block_id}{nbt}"]

    def destroy_commands(self) -> list[str]:
        x, y, z = self.position
        return [f"setblock {x} {y} {z} minecraft:air"]

    def fingerprint(self) -> str:
        raw = f"{self.position}|{self.command}|{self.mode}|{self.auto}"
        return hashlib.sha256(raw.encode()).hexdigest()