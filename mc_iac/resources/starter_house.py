import hashlib
from mc_iac.resources.base import Resource


class StarterHouse_arch(Resource):
    """
    A parameterized procedural house: floor, four walls, a door
    opening, and a flat roof, built entirely from /fill commands.

    Expected config keys:
        position: [x, y, z]   -- south-west floor corner
        width: int             -- size along x (default 5)
        depth: int              -- size along z (default 5)
        height: int             -- wall height, y-direction (default 3)
        wall_material: str      -- e.g. "oak_planks" (default "cobblestone")
        floor_material: str     -- default "oak_planks"
        roof_material: str      -- default "cobblestone"

    NOTE: fixed orientation for v1 -- door is always on the south wall,
    centered. Multiple door placements / window carving are good v2
    additions once this base version is proven reliable.
    """

    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        self.position = config["position"]
        self.width = config.get("width", 5)
        self.depth = config.get("depth", 5)
        self.height = config.get("height", 3)
        self.wall_material = config.get("wall_material", "cobblestone")
        self.floor_material = config.get("floor_material", "oak_planks")
        self.roof_material = config.get("roof_material", "cobblestone")

        if self.height < 3:
            raise ValueError("height must be at least 3 to fit a door opening")
        if self.width < 3 or self.depth < 3:
            raise ValueError("width and depth must be at least 3")

    def create_commands(self) -> list[str]:
        x, y, z = self.position
        w, d, h = self.width, self.depth, self.height
        cmds = []

        x2 = x + w - 1
        z2 = z + d - 1

        cmds.append(f"fill {x} {y} {z} {x2} {y} {z2} minecraft:{self.floor_material}")

        cmds.append(f"fill {x} {y+1} {z} {x2} {y+h} {z} minecraft:{self.wall_material}")
        cmds.append(f"fill {x} {y+1} {z2} {x2} {y+h} {z2} minecraft:{self.wall_material}")
        cmds.append(f"fill {x} {y+1} {z} {x} {y+h} {z2} minecraft:{self.wall_material}")
        cmds.append(f"fill {x2} {y+1} {z} {x2} {y+h} {z2} minecraft:{self.wall_material}")

        door_x = x + (w // 2)
        cmds.append(f"fill {door_x} {y+1} {z} {door_x} {y+2} {z} minecraft:air")

        cmds.append(f"fill {x} {y+h+1} {z} {x2} {y+h+1} {z2} minecraft:{self.roof_material}")

        return cmds

    def destroy_commands(self) -> list[str]:
        x, y, z = self.position
        w, d, h = self.width, self.depth, self.height
        x2 = x + w - 1
        z2 = z + d - 1
        return [f"fill {x} {y} {z} {x2} {y+h+1} {z2} minecraft:air"]

    def fingerprint(self) -> str:
        raw = (
            f"{self.position}|{self.width}|{self.depth}|{self.height}|"
            f"{self.wall_material}|{self.floor_material}|{self.roof_material}"
        )
        return hashlib.sha256(raw.encode()).hexdigest()